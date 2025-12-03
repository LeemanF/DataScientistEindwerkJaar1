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
update_or_install_if_missing("pandas","1.3.0")
update_or_install_if_missing("openpyxl","3.1.0")

# Pas na installatie importeren
from src.utils.safe_requests import safe_requests_get
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd

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
    - tuple[str, str]: Een tuple met (from_date, until_date) in formaat yyyy-mm-dd.
    """

    # Bepaal de laatste dag van de vorige maand voor de 'from_date'
    if month == 1:
        previous_month = 12
        previous_year = year - 1
    else:
        previous_month = month - 1
        previous_year = year
    _, days_previous_month = calendar.monthrange(previous_year, previous_month)
    previous_month_last_day = datetime(previous_year, previous_month, days_previous_month)
    
    from_date = previous_month_last_day.strftime("%Y-%m-%d")

    # Bepaal de eerste dag van de volgende maand voor de 'until_date'
    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year
    next_month_first_day = datetime(next_year, next_month, 1)
    until_date = next_month_first_day.strftime("%Y-%m-%d")

    return from_date, until_date

def prepare_download_dir(
    base_dir: str
) -> Tuple[str, str]:
    """
    Maak indien nodig de downloadmap aan en verwijder eventueel oud bestand 'quarter-hourly-spot-belpex--c--elexys.xlsx'.

    Parameters:
    - base_dir (str): Het basispad naar de downloadmap.

    Returns:
    - tuple[str, str]: Een tuple met het pad naar de downloadmap (als string) en het bestand (als string).
    """

    download_dir = str(base_dir)
    os.makedirs(download_dir, exist_ok=True)

    filename = "quarter-hourly-belpex--c--elexys.xlsx"
    file_path = os.path.join(download_dir, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ❌ Niet hernoemde bestand {filename} werd verwijderd.")

    return download_dir, file_path

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

def download_belpex_xlsx(
    driver: webdriver.Chrome,
    from_date: str,
    until_date: str
) -> None:
    """
    Download Excel Belpex-bestanden via Elexys.
    """

    url = (f"https://www.elexys.be/insights/quarter-hourly-belpex-day-ahead-spot-be?from={from_date}&until={until_date}")
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       🌐 Open URL: {url}")
    driver.get(url)

    # Sluit interactieve popup indien aanwezig
    try:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ⏳ Controleren op popup...")

        wait.until(EC.element_to_be_clickable((By.ID, "interactive-close-button")))
        close_btn = driver.find_element(By.ID, "interactive-close-button")

        driver.execute_script("arguments[0].click();", close_btn)
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ❌ Popup gesloten")

        time.sleep(1)  # Mini delay voor stabiliteit
    except Exception:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ✔️ Geen popup gevonden")
    
    wait = WebDriverWait(driver, 20)
    
    time.sleep(2)

    # Zoek ALLE exportknoppen
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ⏳ Wachten op exportknoppen...")
    buttons = wait.until(
        EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "a.c-insights-export-button")
        )
    )

    # Vind de juiste knop op basis van tekst
    for btn in buttons:
        text = btn.text.strip().lower()

        if "excel" in text:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       🚀 Klik op 'Export Excel'")
            # Klik op de juiste export-div
            driver.execute_script("arguments[0].click();", btn)

    # Wacht op de download
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ⏳ Wacht op download...")
    time.sleep(5)  # Wacht op downloads

def rename_belpex_file(
    download_file: str,
    year: int,
    month: int
) -> None:
    """
    Hernoem quarter-hourly-spot-belpex--c--elexys.xlsx naar Belpex_YYYYMM.xlsx indien download gelukt is.

    Parameters:
    - download_dir (str): Het pad waar de download zich bevindt.
    - year (int): Het jaar van de download.
    - month (int): De maand van de download.

    Returns:
    - None
    """

    new_filename = f"Belpex_{year}{month:02d}.xlsx"
    download_dir = os.path.dirname(download_file)
    new_path = os.path.join(download_dir, new_filename)

    if os.path.exists(download_file):
        os.rename(download_file, new_path)
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ✅ Gedownload en hernoemd naar: {new_filename}")
    else:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ❌ Download mislukt.")

def convert_elexys_xlsx_to_csv(xlsx_path: str, csv_path: str, year: int, month: int) -> None:
    """
    Converteer een gedownload Elexys XLSX-bestand naar het oude CSV-formaat,
    waarbij kwartierprijzen worden omgerekend naar uurprijzen (gemiddelde per uur).

    Deze functie:
    - Controleert of het XLSX-bestand geldige data bevat.
    - Filtert de rijen op het opgegeven jaar (`year`) en maand (`month`) om consistentie
      met de historische data van de oude website te behouden.
    - Converteert kwartierwaarden naar uurwaarden.
    - Converteert de kolommen 'Datum' en 'Time' naar één datetime-kolom in formaat dd/mm/YYYY HH:MM:SS.
    - Voegt een extra euro-teken toe aan de kolom 'Euro'.
    - Schrijft de output naar CSV met ';' separator en ANSI (cp1252) encoding.
    - Indien er geen data beschikbaar is, wordt CSV niet aangemaakt, en er volgt een melding.

    Parameters:
    - xlsx_path (str): Pad naar het Elexys XLSX-bestand dat geconverteerd moet worden.
    - csv_path (str): Pad waar het geconverteerde CSV-bestand opgeslagen wordt.
    - year (int): Jaar waarvoor de data behouden moet blijven in de output.
    - month (int): Maand waarvoor de data behouden moet blijven in de output (1 t.e.m. 12).

    Returns:
    - None

    Voorbeeld (Excel input):
        Datum        Time     Euro
        31/10/2025   23u45    € 31,86
        31/10/2025   23u30    € 46,05
        31/10/2025   23u15    € 56,27
        31/10/2025   23u00    € 75,00

    Output (CSV):
        Date;Euro
        31/10/2025 23:00:00;€ € 52,30
    """

    # Probeer Excel in te lezen
    try:
        df = pd.read_excel(xlsx_path, skiprows=2)
    except Exception as e:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ⚠️  Kon Excel-bestand '{os.path.basename(xlsx_path)}' niet inlezen: {e}")
        return

    # Verwijder volledig lege rijen
    df = df.dropna(how="all")

    # Controleren of het bestand info bevat
    if df.empty:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ⚠️  Geen data beschikbaar in XLSX-bestand '{os.path.basename(xlsx_path)}' — conversie overgeslagen.")
        return

    # Kolomnamen opschonen
    df.columns = [col.strip() for col in df.columns]

    # Controleren of vereiste kolommen aanwezig zijn
    required_cols = {"Datum", "Time", "Euro"}
    if not required_cols.issubset(df.columns):
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ⚠️  Vereiste kolommen ontbreken in XLSX-bestand '{os.path.basename(xlsx_path)}' — gevonden kolommen: {list(df.columns)}")
        return

    # Titel verwijderen indien aanwezig
    if df.columns[0].lower().startswith("quarter"):
        df = df.iloc[1:].dropna(how="all").reset_index(drop=True)

    if df.empty:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ⚠️  XLSX '{os.path.basename(xlsx_path)}' bevat geen datarijen na verwijderen titel — conversie overgeslagen.")
        return

    # Converteer Time (bv. '0u45') naar '00:45'
    def convert_time(t: str) -> str:
        t = t.strip().lower()
        if "u" in t:
            hour, minute = t.split("u")
            return f"{int(hour):02d}:{int(minute):02d}"
        return t

    # Combineer Datum + Time
    try:
        df["Time"] = df["Time"].astype(str).apply(convert_time)
        df["Date"] = pd.to_datetime(df["Datum"] + " " + df["Time"], format="%d/%m/%Y %H:%M")
    except Exception as e:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ⚠️  Datum/Tijd kon niet worden geconverteerd: {e}")
        return

    # Filter enkel rijen voor het juiste jaar + maand
    df = df[(df["Date"].dt.year == year) & (df["Date"].dt.month == month)]

    # Controleer of na filtering nog rijen beschikbaar zijn
    if df.empty:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ⚠️  Geen data voor {year}-{month:02d} — CSV niet aangemaakt.")
        return

    # Euro converteren naar numeriek
    df["Euro"] = df["Euro"].astype(str).str.replace("€", "").str.replace(",", ".").str.strip()
    df["Euro"] = pd.to_numeric(df["Euro"], errors="coerce")

    df = df.dropna(subset=["Euro"])
    if df.empty:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ⚠️  Geen data voor {year}-{month:02d} — CSV niet aangemaakt.")
        return

    # Uur afleiden
    df["Hour"] = df["Date"].dt.floor("h")  # afronden naar uur

    # Gemiddelde per uur
    df_hourly = df.groupby("Hour", as_index=False)["Euro"].mean().sort_values("Hour", ascending=False)

    # Omzetten naar vereiste layout: dd/mm/YYYY HH:MM:SS
    df_hourly["Date"] = df_hourly["Hour"].dt.strftime("%d/%m/%Y %H:%M:%S")

    # Euro weer formatteren in de oude layout
    df_hourly["Euro"] = df_hourly["Euro"].apply(lambda x: f"€ € {x:.2f}".replace(".", ","))

    # Output
    df_out = df_hourly[["Date", "Euro"]]

    # Wegschrijven als ANSI (cp1252)
    df_out.to_csv(csv_path, sep=";", index=False, encoding="cp1252")

    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       💾 Conversie naar CSV voltooid: '{os.path.basename(csv_path)}'")

@retry_on_failure(tries=DEFAULT_ATTEMPTS, delay=RETRY_DELAY, backoff=2)
def import_belpex(
    year: int,
    month: int
) -> None:
    """
    Download Belpex-spotmarktprijzen via browserautomatisering (Selenium).

    Deze functie automatiseert het downloaden van maandelijkse Belpex-spotmarktprijzen
    van de Elexys-website met behulp van een headless (onzichtbare) Chrome-browser.
    De resultaten worden gedownload als xlsx en opgeslagen met bestandsnaam 'Belpex_YYYYMM.xslx'.

    Parameters:
    - year (int): Het jaar waarvoor data opgehaald moet worden.
    - month (int): De maand waarvoor data opgehaald moet worden (1 t.e.m. 12).

    Opmerkingen:
    - Gebruikt een headless Chrome-browser (geen visueel venster).
    - Downloadlocatie: ./Data/Belpex/Belpex_YYYYMM.xlsx
    - Indien het bestand reeds bestaat, wordt het niet opnieuw gedownload.
    """
    
    from_date, until_date = get_belpex_date_range(year, month)
    download_dir, download_file = prepare_download_dir(BELPEX_DIR)
    new_filename_csv = f"Belpex_{year}{month:02d}.csv"
    new_file_csv_path = os.path.join(download_dir, new_filename_csv)
    new_filename_xlsx = f"Belpex_{year}{month:02d}.xlsx"
    new_file_xlsx_path = os.path.join(download_dir, new_filename_xlsx)

    # Indien het csv-bestand reeds bestaat, sla deze maand over
    if os.path.exists(new_file_csv_path):
        #print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - ✅ Bestand bestaat al: {new_filename_csv}")
        return

    # xlxs-bestand verwijderen als dit bestaat
    if os.path.exists(new_file_xlsx_path):
        os.remove(new_file_xlsx_path)
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ❌ {new_filename_xlsx} werd verwijderd.")

    driver = setup_chrome_driver(download_dir)

    try:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -       ⬇️ Starten met het opvragen Belpex-gegevens periode {month}/{year}")
        download_belpex_xlsx(driver, from_date, until_date)
        rename_belpex_file(download_file, year, month)
        convert_elexys_xlsx_to_csv(new_file_xlsx_path, new_file_csv_path, year=year, month=month)
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