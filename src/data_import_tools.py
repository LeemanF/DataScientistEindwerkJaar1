"""
data_import_tools.py

Data Import Tools for Elia Open Data & Belpex Market Data.

Functies:
- Automatische installatie van vereiste Python-modules.
- Ophalen en lokaal opslaan van wind- en zonne-energievoorspellingen en -metingen (per dag) (JSON).
    ° windenergie: https://opendata.elia.be/explore/dataset/ods031/information/
    ° zonne-energie: https://opendata.elia.be/explore/dataset/ods032/information/
- Ophalen van Belpex-spotmarktprijzen via webscraping (CSV).
- Zippen en unzippen van de json-bestanden (wind- en zonne-energie) per jaar.
- Opvangen van netwerkfouten en browserproblemen via retry-mechanismen.
"""

# ----------- Imports -----------

import os
import calendar
import json
import time
import shutil
from datetime import datetime
import zipfile
from typing import Optional, List, Dict, Any, Tuple, Literal

from src.utils.package_tools import update_or_install_if_missing
from src.utils.decorators import retry_on_failure
from settings import HTTP_TIMEOUT, DEFAULT_ATTEMPTS, RETRY_DELAY, BELPEX_DIR, SOLAR_FORECAST_DIR, WIND_FORECAST_DIR, BASE_DIR

# Controleer en installeer indien nodig de vereiste modules
# Dit is een vangnet als de gebruiker geen rekening houdt met requirements.txt.
update_or_install_if_missing("requests","2.25.0")
update_or_install_if_missing("selenium","4.1.0")
update_or_install_if_missing("webdriver_manager","3.5.0")

# Pas na installatie importeren
from src.utils.safe_requests import safe_requests_get
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ----------- Data Import Functies -----------

def get_days_in_month(
    year: int, 
    month: int
) -> List[str]:
    """
    Geef een lijst van alle dagen (YYYY-MM-DD) in de opgegeven maand van een bepaald jaar terug.

    Parameters:
        year (int): Het jaar (bijv. 2025).
        month (int): De maand als integer van 1 t/m 12.

    Returns:
        List[str]: Een lijst met datums in het formaat 'YYYY-MM-DD'.
    """
    _, num_days = calendar.monthrange(year, month)
    return [f"{year}-{month:02d}-{day:02d}" for day in range(1, num_days + 1)]

def fetch_forecast_day(
    url: str,
    date_str: str,
    extra_filters: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Haal alle records (in batches) van de Elia API op voor een specifieke dag.

    Parameters:
    - url (str): API-endpoint (wind of solar dataset).
    - date_str (str): Datum in formaat YYYY-MM-DD (vereist door Elia API).
    - extra_filters (list[str], optioneel): Extra filters zoals regio.

    Returns:
    - list[dict]: Alle records van die dag.
    """

    all_records = []
    limit = 100  # Elia legt een beperking op van 100 records per call
    offset = 0

    while True:
        # Stel API-filters samen
        refine = [f'datetime:"{date_str}"']  # Filter op specifieke dag
        if extra_filters:
            refine.extend(extra_filters)     # Extra filters zoals vb. Belgische regio

        # API-parameters inclusief filter
        params = {
            "order_by": "datetime",          # Sorteer op tijd
            "limit": limit,                  # Aantal records per batch
            "offset": offset,                # Startpunt voor batch
            "refine": refine
        }

        # Voer het verzoek uit via de veilige request-functie met retry
        response = safe_requests_get(
            url,
            params=params,
            tries=DEFAULT_ATTEMPTS,
            delay=RETRY_DELAY,
            timeout=HTTP_TIMEOUT
        )

        # Extra controle op HTTP-status (niet echt nodig door raise_for_status(), maar extra informatief)
        if response.status_code != 200:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ❌ Fout bij {date_str} (offset {offset}): {response.status_code}")
            break

        # Haal JSON-gegevens op, neem alleen 'results' (records)
        data = response.json().get("results", [])
        if not data:
            break  # Geen data meer, stop loop

        all_records.extend(data)

        # Print voortgang als er batches zijn
        if offset != 0:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ⏳ De eerste {offset} records werden binnengehaald.", end='\r')
        offset += limit

    return all_records

def save_forecast_json(
    output_path: str,
    records: List[Dict[str, Any]]
) -> None:
    """
    Sla een lijst van records op in een JSON-bestand.

    Parameters:
    - output_path (str): Volledig pad naar het te schrijven bestand.
    - records (list[dict]): Lijst met datarecords.
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

@retry_on_failure(tries=DEFAULT_ATTEMPTS, delay=RETRY_DELAY)
def import_forecast(
    year: int,
    month: int,
    url: str,
    year_folder: str,
    prefix: str,
    extra_filters: Optional[List[str]] = None
) -> None:
    """
    Download en sla forecast-data (wind of zon) op voor een opgegeven maand uit de Elia Open Data API.

    Deze functie haalt voor elke dag van de opgegeven maand de voorspellingen en metingen op
    via de Elia API en slaat deze lokaal op in afzonderlijke JSON-bestanden per dag, per jaar gestructureerd.

    Indien er een netwerkprobleem of andere tijdelijke fout optreedt tijdens het ophalen,
    wordt de volledige functie automatisch herhaald tot 3 keer dankzij de retry-decorator.

    Parameters:
    - year (int): Het jaar waarvoor data opgehaald moet worden.
    - month (int): De maand waarvoor data opgehaald moet worden (1 t.e.m. 12).
    - url (str): Basis-URL van de Elia API (bijv. wind of solar dataset).
    - year_folder (str): Map waarin de JSON-bestanden per jaar moeten worden opgeslagen.
    - prefix (str): Prefix voor de bestandsnamen, bijv. 'WindForecast_Elia' of 'SolarForecast_Elia'.
    - extra_filters (list[str], optioneel): Extra API-filters zoals ['region:"Belgium"'].

    Werking:
    - Controleert per dag of het JSON-bestand al bestaat; zo ja, deze dag wordt overgeslagen.
    - Haalt records op in batches van 100 (beperking van Elia API).
    - Print status per dag en per batch.
    - Slaat de records op in een JSON-bestand met naam <prefix>_YYYYMMDD.json.
    - Print of het bestand succesvol is opgeslagen of dat er geen data beschikbaar was.
    """

    # Maak de jaarmap aan indien nodig
    os.makedirs(year_folder, exist_ok=True)

    # Loop over elke dag van de maand
    for date_str in get_days_in_month(year, month):
        # Bestandsnaam en volledig pad genereren voor output
        output_filename = f"{prefix}_{date_str.replace('-', '')}.json"
        output_path = os.path.join(year_folder, output_filename)

        # Indien het bestand reeds bestaat, sla deze dag over
        if os.path.exists(output_path):
            #print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - ✅ Bestand bestaat al: {output_filename}")
            continue

        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ⬇️ Ophalen: {output_filename}")

        # Ophalen van alle records voor deze dag
        all_records = fetch_forecast_day(url, date_str, extra_filters)

        # Als er data gevonden werd, sla deze op in JSON-bestand
        if all_records:
            save_forecast_json(output_path, all_records)
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ✅ Opgeslagen ({len(all_records)} records): {output_filename}")
        else:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ❌ Geen data voor {date_str}")

def import_wind(
    year: int,
    month: int
) -> None:
    """
    Download en sla windforecast-data op voor een opgegeven maand via `import_forecast`.

    Parameters:
    - year (int): Jaar van de data.
    - month (int): Maand van de data.

    Bestanden worden opgeslagen in: <WIND_FORECAST_DIR>/<jaar>/WindForecast_Elia_YYYYMMDD.json
    """

    url = "https://opendata.elia.be/api/explore/v2.1/catalog/datasets/ods031/records"
    folder = os.path.join(WIND_FORECAST_DIR, str(year))
    import_forecast(year, month, url, folder, "WindForecast_Elia")

def import_solar(
    year: int,
    month: int
) -> None:
    """
    Download en sla zonneforecast-data op voor een opgegeven maand via `import_forecast`.

    Parameters:
    - year (int): Jaar van de data.
    - month (int): Maand van de data.

    Bestanden worden opgeslagen in: <SOLAR_FORECAST_DIR>/<jaar>/SolarForecast_Elia_YYYYMMDD.json
    """

    url = "https://opendata.elia.be/api/explore/v2.1/catalog/datasets/ods032/records"
    folder = os.path.join(SOLAR_FORECAST_DIR, str(year))
    import_forecast(year, month, url, folder, "SolarForecast_Elia", extra_filters=['region:"Belgium"'])

def get_belpex_date_range(
    year: int,
    month: int
) -> Tuple[str, str]:
    """
    Bepaal de 'from' en 'until' datums voor de Belpex-export.

    Parameters:
    - year (int): Het jaar waarvoor de datums bepaald worden.
    - month (int): De maand waarvoor de datums bepaald worden.

    Returns:
    - tuple[str, str]: Een tuple met (from_date, until_date) in formaat dd/mm/yyyy.
    """

    from_date = f"01/{month:02d}/{year}"

    # Bepaal de eerste dag van de volgende maand voor de 'until_date'
    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year
    next_month_first_day = datetime(next_year, next_month, 1)
    until_date = next_month_first_day.strftime("%d/%m/%Y")

    return from_date, until_date

def prepare_download_dir(
    base_dir: str
) -> str:
    """
    Maak de downloadmap aan en verwijder eventueel oud bestand 'BelpexFilter.csv'.

    Parameters:
    - base_dir (str): Het basispad naar de downloadmap.

    Returns:
    - str: Het pad naar de downloadmap (als string).
    """

    download_dir = str(base_dir)
    os.makedirs(download_dir, exist_ok=True)

    filter_path = os.path.join(download_dir, "BelpexFilter.csv")
    if os.path.exists(filter_path):
        os.remove(filter_path)
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ❌ Niet hernoemde bestand BelpexFilter.csv werd verwijderd.")

    return download_dir

def setup_chrome_driver(
    download_dir: str
) -> webdriver.Chrome:
    """
    Configureer een headless Chrome-driver voor automatisch downloaden.

    Parameters:
    - download_dir (str): Het pad waar downloads automatisch opgeslagen moeten worden.

    Returns:
    - webdriver.Chrome: Een geconfigureerde headless Chrome-driver.
    """

    options = Options()
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_argument("--headless")  # Chrome wordt onzichtbaar geopend
    options.add_experimental_option("prefs", prefs)
    return webdriver.Chrome(options=options)

def download_belpex_csv(
    driver: webdriver.Chrome,
    from_date: str,
    until_date: str
) -> None:
    """
    Automatiseer het invullen van datums en exporteren van de Belpex-data naar CSV.

    Parameters:
    - driver (webdriver.Chrome): De actieve Selenium-webdriver.
    - from_date (str): Startdatum in formaat dd/mm/yyyy.
    - until_date (str): Einddatum in formaat dd/mm/yyyy.

    Returns:
    - None
    """

    # Ga naar de website
    driver.get("https://my.elexys.be/MarketInformation/SpotBelpex.aspx")

    # Wacht op beschikbaarheid van datumvelden
    wait = WebDriverWait(driver, 20)
    wait.until(EC.presence_of_element_located((By.ID, "contentPlaceHolder_fromASPxDateEdit_I")))

    # Vul de datums in
    from_input = driver.find_element(By.ID, "contentPlaceHolder_fromASPxDateEdit_I")
    until_input = driver.find_element(By.ID, "contentPlaceHolder_untilASPxDateEdit_I")

    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       📆 Vul 'From' datum in: {from_date}")
    from_input.clear()
    from_input.send_keys(from_date)

    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       📆 Vul 'Until' datum in: {until_date}")
    until_input.clear()
    until_input.send_keys(until_date)

    # Klik op "Show data"
    show_data_button = driver.find_element(By.ID, "contentPlaceHolder_refreshBelpexCustomButton_I")
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       🚀 Klik op 'Show data'")
    driver.execute_script("arguments[0].click();", show_data_button)

    # Wacht tot de resultaten zichtbaar zijn in de tabel
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ⏳ Wacht op zoekresultaten...")
    wait.until(EC.presence_of_element_located((By.ID, "contentPlaceHolder_belpexFilterGrid_DXMainTable")))
    time.sleep(5)  # Extra wachttijd voor stabiliteit

    # Klik op de juiste export-div
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       🚀 Klik op 'Exporteer naar CSV'")
    export_button_div = wait.until(EC.element_to_be_clickable((By.ID, "ctl00_contentPlaceHolder_GridViewExportUserControl1_csvExport")))
    driver.execute_script("arguments[0].click();", export_button_div)

    # Wacht op de download
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ⏳ Wacht op download...")
    time.sleep(5)

def rename_belpex_file(
    download_dir: str,
    year: int,
    month: int
) -> None:
    """
    Hernoem BelpexFilter.csv naar Belpex_YYYYMM.csv indien download gelukt is.

    Parameters:
    - download_dir (str): Het pad waar de download zich bevindt.
    - year (int): Het jaar van de download.
    - month (int): De maand van de download.

    Returns:
    - None
    """

    new_filename = f"Belpex_{year}{month:02d}.csv"
    filter_path = os.path.join(download_dir, "BelpexFilter.csv")
    new_path = os.path.join(download_dir, new_filename)

    if os.path.exists(filter_path):
        os.rename(filter_path, new_path)
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ✅ Gedownload en hernoemd naar: {new_filename}")
    else:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ❌ Download mislukt.")

@retry_on_failure(tries=DEFAULT_ATTEMPTS, delay=RETRY_DELAY)
def import_belpex(
    year: int,
    month: int
) -> None:
    """
    Download Belpex-spotmarktprijzen via browserautomatisering (Selenium).

    Deze functie automatiseert het downloaden van maandelijkse Belpex-spotmarktprijzen
    van de Elexys-website met behulp van een headless (onzichtbare) Chrome-browser.
    De resultaten worden gedownload als CSV en opgeslagen met bestandsnaam 'Belpex_YYYYMM.csv'.

    Parameters:
    - year (int): Het jaar waarvoor data opgehaald moet worden.
    - month (int): De maand waarvoor data opgehaald moet worden (1 t.e.m. 12).

    Opmerkingen:
    - Gebruikt een headless Chrome-browser (geen visueel venster).
    - Downloadlocatie: ./Data/Belpex/Belpex_YYYYMM.csv
    - Indien het bestand reeds bestaat, wordt het niet opnieuw gedownload.
    """
    
    from_date, until_date = get_belpex_date_range(year, month)
    download_dir = prepare_download_dir(BELPEX_DIR)
    new_filename = f"Belpex_{year}{month:02d}.csv"

    # Indien het bestand reeds bestaat, sla deze maand over
    if new_filename in os.listdir(download_dir):
        #print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - ✅ Bestand bestaat al: {new_filename}")
        return
    
    driver = setup_chrome_driver(download_dir)

    try:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ⬇️ Starten met het opvragen Belpex-gegevens periode {month}/{year}")
        download_belpex_csv(driver, from_date, until_date)
        rename_belpex_file(download_dir, year, month)
    finally:
        # Sluit de browser
        driver.quit()


# ----------- Zip Functies -----------

def file_needs_zip(
    zip_path: str,
    folder_path: str
) -> bool:
    """
    Controleer of een ZIP-bestand ouder is dan de JSON-bestanden in een opgegeven map.

    Parameters:
    - zip_path (str): Pad naar het te controleren ZIP-bestand.
    - folder_path (str): Map waarin .json-bestanden zich bevinden.

    Returns:
    - bool:
        - True als:
            - het ZIP-bestand niet bestaat, of
            - één of meer JSON-bestanden in de map nieuwer zijn dan het ZIP-bestand.
        - False als:
            - alle JSON-bestanden ouder zijn dan het ZIP-bestand (zip is up-to-date).
    """
    if not os.path.exists(zip_path):
        return True  # Zip bestaat niet → zeker zippen

    zip_mtime = os.path.getmtime(zip_path)

    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                if os.path.getmtime(file_path) > zip_mtime:
                    return True  # Bestand is recenter dan de zip → zip nodig
    return False  # Alles is ouder → zip is up-to-date

def zip_forecast_data(
    forecast_types: List[str] = ["SolarForecast", "WindForecast"]
) -> None:
    """
    Maak ZIP-bestanden aan voor zonne- en windbestanden (JSON) per jaar en per type.

    Parameters:
    - forecast_types (list[str]): Lijst met types, zoals "SolarForecast" of "WindForecast".

    Werking:
    - Voor elk type en elk jaar wordt gecontroleerd of er een zip moet worden aangemaakt.
    - Bestanden met extensie `.json` worden gebundeld in één zip per jaar.
    - Bestandsstructuur binnen de zip wordt behouden relatief aan het forecasttypepad.
    - Bestaat een zip reeds en is deze up-to-date, dan wordt deze overgeslagen.
    """
    for forecast_type in forecast_types:
        if forecast_type == "WindForecast":
            type_folder = WIND_FORECAST_DIR
        elif forecast_type == "SolarForecast":
            type_folder = SOLAR_FORECAST_DIR
        else:
            type_folder = os.path.join(BASE_DIR, forecast_type)

        if not os.path.isdir(type_folder):
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -    ⚠️ Map bestaat niet: {type_folder}")
            continue

        for year in os.listdir(type_folder):
            year_path = os.path.join(type_folder, year)

            if not os.path.isdir(year_path):
                continue  # Sla bestanden of vreemde dingen over

            zip_filename = f"{forecast_type}_{year}.zip"
            zip_path = os.path.join(type_folder, zip_filename)

            # Check of zip nodig is
            if not file_needs_zip(zip_path, year_path):
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -    ⏭️ Up-to-date: {zip_filename}")
                continue

            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -    📦 Zippen van {year_path} → {zip_filename}")

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:  # 'w" overschrijft vorig bestand als dit bestaat
                for root, _, files in os.walk(year_path):
                    for file in files:
                        if file.endswith(".json"):
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, type_folder)
                            zipf.write(file_path, arcname)

            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -    ✅ Klaar: {zip_filename}")

def unzip_forecast_data(
    zip_path: str,
    extract_to: Optional[str] = None
) -> None:
    """
    Pak een zipbestand met forecastgegevens uit, met behoud van tijdstempels.

    Parameters:
    - zip_path (str): Pad naar het te unzippen bestand.
    - extract_to (str of None): Doelmap. Indien None, gebruik de map waarin het zipbestand zit.

    Werking:
    - Alleen nieuwe bestanden worden uitgepakt (bestaande worden overgeslagen).
    - Herstelt originele modificatietijd (modification time) per bestand.
    """
    if extract_to is None:
        extract_to = os.path.dirname(zip_path)

    with zipfile.ZipFile(zip_path, 'r') as zipf:
        for member in zipf.infolist():
            extracted_path = os.path.join(extract_to, member.filename)
            if os.path.exists(extracted_path):
                # Sla bestaande bestanden over
                continue
            os.makedirs(os.path.dirname(extracted_path), exist_ok=True)
            with zipf.open(member) as source, open(extracted_path, 'wb') as target:
                shutil.copyfileobj(source, target)
            # Zet de oorspronkelijke modificatie-tijd terug
            date_time = time.mktime(member.date_time + (0, 0, -1))
            os.utime(extracted_path, (date_time, date_time))
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ✅ Uitgepakt: {member.filename}")

def unzip_all_forecast_zips(
    forecast_types: List[str] = ["SolarForecast", "WindForecast"]
) -> None:
    """
    Pak alle zipbestanden uit in opgegeven forecastfolders.

    Parameters:
    - forecast_types (list[str]): Lijst van types met forecasts, bijvoorbeeld ["SolarForecast", "WindForecast"].

    Werking:
    - Zoekt in elk type-folder naar alle `.zip`-bestanden en roept `unzip_forecast_data()` op.
    - Alleen nieuwe bestanden worden uitgepakt.
    """
    for forecast_type in forecast_types:
        if forecast_type == "WindForecast":
            type_folder = WIND_FORECAST_DIR
        elif forecast_type == "SolarForecast":
            type_folder = SOLAR_FORECAST_DIR
        else:
            type_folder = os.path.join(BASE_DIR, forecast_type)

        if not os.path.isdir(type_folder):
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -    ❌ Map niet gevonden: {type_folder}")
            continue

        for file in os.listdir(type_folder):
            if file.endswith(".zip"):
                zip_path = os.path.join(type_folder, file)
                print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -    📦 Bezig met uitpakken: {file}")
                unzip_forecast_data(zip_path)

    print('')

# ----------- Bijwerken van de data-bestanden -----------

def get_latest_available_year_month(
    today: Optional[datetime] = None
) -> Tuple[int, int]:
    """
    Bepaal het meest recente jaar/maand waarvoor data beschikbaar is.
    Pas vanaf de 5de dag is de info van de vorige maand beschikbaar.

    Parameters:
    - today (datetime, optional): Referentiedatum. Default = vandaag.

    Returns:
    - tuple[int, int]: (jaar, maand) meest recente beschikbare data.
    """

    if today is None:
        today = datetime.today()

    if today.day <= 4:
        latest_available_month = today.month - 2
    else:
        latest_available_month = today.month - 1

    latest_available_year = today.year
    if latest_available_month <= 0:
        latest_available_month += 12
        latest_available_year -= 1

    return latest_available_year, latest_available_month

def update_data(
    from_year: Optional[int] = None,
    to_year: Optional[int] = None,
    data_type: Literal['wind', 'solar', 'belpex', 'all'] = 'all'
) -> None:
    """
    Update wind-, zonne- en/of Belpex-data tussen opgegeven jaartallen.
    Hierbij worden eerste de bestaande zip-bestanden uitgepakt.
    Vervolgens wordt de recentste data opgehaald bij Elia en Elexys.
    Ten slotte wordt nieuwe data toegevoegd aan de zip-bestanden.
    
    Parameters:
    - from_year (int, optional): Startjaar. Default = vorig jaar.
    - to_year (int, optional): Eindjaar. Default = huidig jaar.
    - data_type (Literal['wind', 'solar', 'belpex', 'all'], optional):
        Kies welke datasets worden geüpdatet. Default = 'all'.
    """

    today = datetime.today()

    # Defaults
    if from_year is None:
        from_year = today.year - 1
    if to_year is None:
        to_year = today.year

    # Bepaal de laatste beschikbare maand en jaar
    latest_available_year, latest_available_month = get_latest_available_year_month(today)

    allowed_types = {'wind', 'solar', 'belpex', 'all'}
    if data_type not in allowed_types:
        raise ValueError(f"❌ Ongeldig data_type '{data_type}'. Kies uit {allowed_types}.")

    # Altijd eerst de huidige bestanden unzippen als er gekozen werd voor 'wind' of 'solar'
    if data_type in ('wind', 'solar', 'all'):
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 📦 Unzippen van de forecast-data...")
        unzip_all_forecast_zips()

    # Process map (data_type → functie + label)
    import_funcs = {
        "wind":   (import_wind,   "winddata"),
        "solar":  (import_solar,  "zonnedata"),
        "belpex": (import_belpex, "Belpex-data"),
    }

    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 📅 Start met ophalen data voor periode {from_year}-{to_year}")
    counter = 0

    # Loop over jaren en maanden
    for year in range(from_year, to_year + 1):
        for month in range(1, 13):
            if (year == latest_available_year and month > latest_available_month) or (year > latest_available_year):
                continue

            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -    📅 Ophalen data voor {year}-{month:02d} ({data_type})")

            # Loop over process map
            for dtype, (func, label) in import_funcs.items():
                if data_type in (dtype, "all"):
                    try:
                        func(year, month)
                        counter += 1
                    except Exception as e:
                        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - ❌ Fout bij ophalen {label} {year}-{month:02d}: {e}")

    if counter == 0:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -    ❌ Geen data beschikbaar.")

    # Alleen als 'wind' of 'solar' werd geüpdatet: zip de forecast-data
    if data_type in ('wind', 'solar', 'all'):
        print(f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 📦 Zippen van de forecast-data...")
        zip_forecast_data()

    print(f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - ✅ Data-import afgerond.\n")