"""
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

# data_import_tools.py

# ----------- Imports -----------

import os
import calendar
import json
import time
import shutil
from datetime import datetime
import zipfile
import functools
from toolbox import update_or_install_if_missing

# Controleer en installeer indien nodig de vereiste modules
# Dit is een vangnet als de gebruiker geen rekening houdt met requirements.txt.
update_or_install_if_missing("requests","2.25.0")
update_or_install_if_missing("selenium","4.1.0")
update_or_install_if_missing("webdriver_manager","3.5.0")

# Pas na installatie importeren
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ----------- Retry Decorator & Safe Request -----------

def retry_on_failure(tries=3, delay=2, backoff=1, allowed_exceptions=(Exception,)):
    """
    Decorator om een functie meerdere keren opnieuw uit te voeren wanneer er een fout optreedt.

    Deze decorator is nuttig bij tijdelijke fouten, zoals netwerkproblemen of onstabiele API-responses.
    Als de gedecoreerde functie een uitzondering genereert die voorkomt in `allowed_exceptions`, 
    zal ze automatisch opnieuw uitgevoerd worden tot het maximum aantal `tries` is bereikt.
    Tussen elke poging wacht de functie `delay` seconden. Na elke fout wordt de wachttijd vermenigvuldigd 
    met `backoff` (exponentiële backoff).

    Parameters:
    - tries (int): Het maximaal aantal pogingen voor de functie wordt opgegeven. Standaard: 3.
    - delay (float): De initiële wachttijd (in seconden) tussen pogingen. Standaard: 2.
    - backoff (float): De vermenigvuldigingsfactor voor de wachttijd bij elke fout. Standaard: 1 (geen toename).
                      Een waarde >1 verhoogt de wachttijd exponentieel (bijv. 2 voor verdubbeling).
    - allowed_exceptions (tuple): Een tuple van uitzonderingen waarvoor een retry toegestaan is.
                                  Standaard: (Exception,), wat alle standaardfouten omvat.

    Intern maakt de wrapper gebruik van lokale kopieën van de parameters `_tries` en `_delay`
    om te voorkomen dat de oorspronkelijke decoratorwaarden (die gedeeld worden door alle oproepen)
    overschreven of beïnvloed worden tijdens het uitvoeren van retries.

    Gebruik:
    @retry_on_failure(tries=5, delay=1, backoff=2, allowed_exceptions=(ConnectionError,))
    def fetch_data():
        ...

    """
    def decorator(func):
        # Zorgt ervoor dat de metadata (naam, docstring, enz.) van de originele functie 
        # behouden blijft in de gegenereerde wrapperfunctie.
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Lokale kopieën maken om te vermijden dat de originele decorator-argumenten 
            # gewijzigd worden tijdens herhaalde pogingen
            _tries, _delay = tries, delay
            while _tries > 1:
                try:
                    return func(*args, **kwargs)
                except allowed_exceptions as e:
                    _tries -= 1
                    print(f"⚠️ Fout '{e}' in {func.__name__}(). Nog {_tries} pogingen over... Wacht {_delay:.1f}s.")
                    # Wacht voor het opgegeven aantal seconden
                    time.sleep(_delay)
                    _delay *= backoff
            # Laatste poging buiten de while-loop: als deze ook faalt, wordt de uitzondering doorgegeven
            return func(*args, **kwargs)
        return wrapper
    return decorator

def safe_requests_get(url, params=None, headers=None, tries=3, delay=2, timeout=10):
    """
    Uitgebreide en veilige versie van requests.get() met ingebouwde retry-logica.

    Deze functie probeert een HTTP GET-verzoek uit te voeren naar de opgegeven URL.
    Als het verzoek faalt door een netwerkfout of een HTTP-fout (zoals 5xx of 4xx-status),
    wordt het verzoek automatisch opnieuw geprobeerd tot een maximum van `tries` keer.
    Na elke mislukte poging wordt `delay` seconden gewacht alvorens opnieuw te proberen.

    Parameters:
    - url (str): De URL waarnaar het GET-verzoek wordt verzonden.
    - params (dict, optional): Optionele query parameters toe te voegen aan het verzoek.
    - headers (dict, optional): Optionele headers om mee te sturen met het verzoek.
    - tries (int): Aantal pogingen bij fouten. Standaard is 3.
    - delay (int or float): Wachtijd (in seconden) tussen pogingen. Standaard is 2.
    - timeout (int or float): Maximum wachttijd voor een antwoord van de server. Standaard is 10 seconden.

    Retourneert:
    - response (requests.Response): Het response-object als het verzoek succesvol was.

    Raises:
    - requests.exceptions.RequestException: Als alle pogingen mislukken of er een andere fout optreedt.
    
    Gebruik:
    response = safe_requests_get("https://api.example.com/data", tries=5, delay=1)

    """
    # Lokale kopie van tries maken zodat de oorspronkelijke waarde behouden blijft bij hergebruik
    _tries = tries
    while _tries > 1:
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            # Roep een uitzondering op bij een HTTP-statuscode die een fout aangeeft (4xx of 5xx)
            response.raise_for_status()
            return response
        except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
            print(f"⚠️ Request fout: {e}. Nog {_tries-1} pogingen... Wacht {delay}s.")
            # Wacht voor het opgegeven aantal seconden
            time.sleep(delay)
            _tries -= 1
    # Laatste poging buiten de loop: als deze faalt, wordt de uitzondering niet meer opgevangen
    response = requests.get(url, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response

# ----------- Data Import Functies -----------

@retry_on_failure(tries=3, delay=5)
def import_wind(year,month):
    """
    Download en sla windforecast-data op voor een opgegeven maand uit de Elia Open Data API.

    Deze functie haalt voor elke dag van de opgegeven maand de windvoorspellingsgegevens en metingen op
    via de Elia API en slaat deze lokaal op in afzonderlijke JSON-bestanden per dag, per jaar gestructureerd.

    Indien er een netwerkprobleem of andere tijdelijke fout optreedt tijdens het ophalen,
    wordt de volledige functie automatisch herhaald tot 3 keer dankzij de retry-decorator.

    Parameters:
    - year (int): Het jaar waarvoor data opgehaald moet worden.
    - month (int): De maand waarvoor data opgehaald moet worden (1 t.e.m. 12).

    Opmerkingen:
    - Bestanden worden opgeslagen in: Data\WindForecast\<jaar>\WindForecast_Elia_YYYYMMDD.json
    - Bestanden die al bestaan worden niet opnieuw gedownload.
    """

    # Bepaal het aantal dagen in de gevraagde maand en jaar
    _, num_days = calendar.monthrange(year, month)

    # Stel pad samen voor jaarspecifieke map en maak deze aan indien nodig
    base_folder = r"Data\WindForecast"
    year_folder = os.path.join(base_folder, str(year))
    os.makedirs(year_folder, exist_ok=True)

    # Loop over elke dag van de maand
    for day in range(1, num_days + 1):
        # Datum omzetten naar formaat YYYY-MM-DD (vereist door Elia API)
        date_str = f"{year}-{month:02d}-{day:02d}"
        
        # Bestandsnaam en volledig pad genereren voor output
        output_filename = f"WindForecast_Elia_{year}{month:02d}{day:02d}.json"
        output_path = os.path.join(year_folder, output_filename)

        # Indien het bestand reeds bestaat, sla deze dag over
        if os.path.exists(output_path):
            #print(f"✅ Bestand bestaat al: {output_filename}")
            continue

        print(f"      ⬇️ Ophalen: {output_filename}")

        # Basis-URL van de Elia API voor winddata
        url = "https://opendata.elia.be/api/explore/v2.1/catalog/datasets/ods031/records"
        all_records = []
        limit = 100  # Elia legt een beperking op van 100 records per call
        offset = 0

        while True:
            # API-parameters inclusief filter op specifieke dag
            params = {
                "order_by": "datetime",          # Sorteer op tijd
                "limit": limit,                  # Aantal records per batch
                "offset": offset,                # Startpunt voor batch
                "refine": [
                    f'datetime:"{date_str}"'     # Filter op specifieke dag
                ]
            }

            # Voer het verzoek uit via de veilige request-functie met retry
            response = safe_requests_get(url, params=params)

            # Extra controle op HTTP-status (niet echt nodig door raise_for_status(), maar extra informatief)
            if response.status_code != 200:
                print(f"      ❌ Fout bij {date_str} (offset {offset}): {response.status_code}")
                break

            # Haal JSON-gegevens op, neem alleen 'results' (records)
            data = response.json().get("results", [])
            if not data:
                break  # Geen data meer, stop loop

            all_records.extend(data)
            if offset != 0: 
                print(f'      ⏳ De eerste {offset} records werden binnengehaald.', end='\r')
            offset += limit

        # Als er data gevonden werd, sla deze op in JSON-bestand
        if all_records:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(all_records, f, ensure_ascii=False, indent=2)
            print(f"      ✅ Opgeslagen ({len(all_records)} records): {output_filename}")
        else:
            print(f"      ❌ Geen data voor {date_str}")

@retry_on_failure(tries=3, delay=5)
def import_solar(year,month):
    """
    Download en sla zonneforecast-data op voor een opgegeven maand uit de Elia Open Data API.

    Deze functie haalt voor elke dag van de opgegeven maand de zonvoorspellingsgegevens en metingen op
    via de Elia API en slaat deze lokaal op in afzonderlijke JSON-bestanden per dag, per jaar gestructureerd.

    Parameters:
    - year (int): Het jaar waarvoor data opgehaald moet worden.
    - month (int): De maand waarvoor data opgehaald moet worden (1 t.e.m. 12).

    Opmerkingen:
    - Bestanden worden opgeslagen in: Data\SolarForecast\<jaar>\SolarForecast_Elia_YYYYMMDD.json
    - Bestanden die al bestaan worden niet opnieuw opgehaald.
    - Enkel records voor de regio "Belgium" worden opgehaald om te vermijden dat er dubbele data is.
    """

    # Bepaal het aantal dagen in de gevraagde maand en jaar
    _, num_days = calendar.monthrange(year, month)

    # Stel pad samen voor jaarspecifieke map en maak deze aan indien nodig
    base_folder = r"Data\SolarForecast"
    year_folder = os.path.join(base_folder, str(year))
    os.makedirs(year_folder, exist_ok=True)

    # Loop over elke dag van de maand
    for day in range(1, num_days + 1):
        # Datum omzetten naar formaat YYYY-MM-DD (vereist door Elia API)
        date_str = f"{year}-{month:02d}-{day:02d}"
        
        # Bestandsnaam en volledig pad genereren voor output
        output_filename = f"SolarForecast_Elia_{year}{month:02d}{day:02d}.json"
        output_path = os.path.join(year_folder, output_filename)

        # Indien het bestand reeds bestaat, sla deze dag over
        if os.path.exists(output_path):
            #print(f"✅ Bestand bestaat al: {output_filename}")
            continue

        print(f"      ⬇️ Ophalen: {output_filename}")

        # Basis-URL van de Elia API voor zonnedata
        url = "https://opendata.elia.be/api/explore/v2.1/catalog/datasets/ods032/records"
        all_records = []
        limit = 100  # Elia legt een beperking op van 100 records per call
        offset = 0

        while True:
            # API-parameters inclusief filter op specifieke dag en regio
            params = {
                "order_by": "datetime",          # Sorteer op tijd
                "limit": limit,                  # Aantal records per batch
                "offset": offset,                # Startpunt voor batch
                "refine": [
                    f'datetime:"{date_str}"',    # Filter op specifieke dag
                    'region:"Belgium"'           # Filter op Belgische regio
                ]
            }

             # Voer het verzoek uit via de veilige request-functie met retry
            response = safe_requests_get(url, params=params)

            # Extra controle op HTTP-status (niet echt nodig door raise_for_status(), maar extra informatief)
            if response.status_code != 200:
                print(f"      ❌ Fout bij {date_str} (offset {offset}): {response.status_code}")
                break

            # Haal JSON-gegevens op, neem alleen 'results' (records)
            data = response.json().get("results", [])
            if not data:
                break  # Geen data meer, stop loop

            all_records.extend(data)
            if offset != 0: 
                print(f'      ⏳ De eerste {offset} records werden binnengehaald.', end='\r')
            offset += limit

        # Als er data gevonden werd, sla deze op in JSON-bestand
        if all_records:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(all_records, f, ensure_ascii=False, indent=2)
            print(f"      ✅ Opgeslagen ({len(all_records)} records): {output_filename}")
        else:
            print(f"      ❌ Geen data voor {date_str}")

@retry_on_failure(tries=3, delay=5)
def import_belpex(year, month):
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
    # Stel de 'from'-datum in op de eerste dag van de maand (dd/mm/yyyy)
    from_date = f"01/{month:02d}/{year}"

    # Bepaal de eerste dag van de volgende maand voor de 'until_date'
    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year

    # De eerste dag van de volgende maand
    next_month_first_day = datetime(next_year, next_month, 1)
    until_date = next_month_first_day.strftime("%d/%m/%Y")

    # Downloadpad instellen en aanmaken indien nodig
    download_dir = os.path.join(os.getcwd(), "Data\\Belpex")
    os.makedirs(download_dir, exist_ok=True)

    # Setup voor Chrome
    options = Options()
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_argument("--headless")  # Chrome wordt onzichtbaar geopend
    options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(options=options)


    # Niet hernoemde bestanden opkuisen
    if "BelpexFilter.csv" in os.listdir(download_dir):
        os.remove(os.path.join(download_dir, "BelpexFilter.csv"))
        print("      ❌ Niet hernoemde bestand BelpexFilter.csv werd verwijderd.")

    new_filename = f"Belpex_{year}{month:02d}.csv"


    # Indien het bestand reeds bestaat, sla deze maand over
    if new_filename in os.listdir(download_dir):
        #print(f"✅ Bestand bestaat al: {new_filename}")
        pass
    else:
        # Ga naar de website
        driver.get("https://my.elexys.be/MarketInformation/SpotBelpex.aspx")

        print(f"      ⬇️ Starten met het opvragen Belpex-gegevens periode {month}/{year}")
        
        # Wacht op beschikbaarheid van datumvelden
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.ID, "contentPlaceHolder_fromASPxDateEdit_I")))

        # Vul de datums in
        from_input = driver.find_element(By.ID, "contentPlaceHolder_fromASPxDateEdit_I")
        until_input = driver.find_element(By.ID, "contentPlaceHolder_untilASPxDateEdit_I")

        print(f"      📆 Vul 'From' datum in: {from_date}")
        from_input.clear()
        from_input.send_keys(from_date)

        print(f"      📆 Vul 'Until' datum in: {until_date}")
        until_input.clear()
        until_input.send_keys(until_date)

        # Klik op "Show data"
        show_data_button = driver.find_element(By.ID, "contentPlaceHolder_refreshBelpexCustomButton_I")
        print("      🚀 Klik op 'Show data'")
        driver.execute_script("arguments[0].click();", show_data_button)

        # Wacht tot de resultaten zichtbaar zijn in de tabel
        print("      ⏳ Wacht op zoekresultaten...")
        wait.until(EC.presence_of_element_located((By.ID, "contentPlaceHolder_belpexFilterGrid_DXMainTable")))
        time.sleep(5)  # Extra wachttijd voor stabiliteit

        # Klik op de juiste export-div
        print("      🚀 Klik op 'Exporteer naar CSV'")
        export_button_div = wait.until(EC.element_to_be_clickable((By.ID, "ctl00_contentPlaceHolder_GridViewExportUserControl1_csvExport")))
        driver.execute_script("arguments[0].click();", export_button_div)

        # Wacht op de download
        print("      ⏳ Wacht op download...")
        time.sleep(5)

        # Als het bestand bestaat, hernoem het bestand naar 'Belpex_JJJJMM.csv' (bijv. Belpex_202401.csv)
        if "BelpexFilter.csv" in os.listdir(download_dir):
            new_filename = f"Belpex_{year}{month:02d}.csv"
            os.rename(os.path.join(download_dir, "BelpexFilter.csv"), os.path.join(download_dir, new_filename))
            print(f"      ✅ Gedownload en hernoemd naar: {new_filename}")
        else:
            print("      ❌ Download mislukt.")

        # Sluit de browser
        driver.quit()

# ----------- Zip Functies -----------

def file_needs_zip(zip_path, folder_path):
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

def zip_forecast_data(base_dir="Data", forecast_types=["SolarForecast", "WindForecast"]):
    """
    Maak ZIP-bestanden aan voor zonne- en windbestanden (JSON) per jaar en per type.

    Parameters:
    - base_dir (str): Basisdirectory waarin de data zich bevindt.
    - forecast_types (list[str]): Lijst met types, zoals "SolarForecast" of "WindForecast".

    Werking:
    - Voor elk type en elk jaar wordt gecontroleerd of er een zip moet worden aangemaakt.
    - Bestanden met extensie `.json` worden gebundeld in één zip per jaar.
    - Bestandsstructuur binnen de zip wordt behouden relatief aan het forecasttypepad.
    - Bestaat een zip reeds en is deze up-to-date, dan wordt deze overgeslagen.
    """
    for forecast_type in forecast_types:
        type_folder = os.path.join(base_dir, forecast_type)

        if not os.path.isdir(type_folder):
            print(f"   ⚠️ Map bestaat niet: {type_folder}")
            continue

        for year in os.listdir(type_folder):
            year_path = os.path.join(type_folder, year)

            if not os.path.isdir(year_path):
                continue  # Sla bestanden of vreemde dingen over

            zip_filename = f"{forecast_type}_{year}.zip"
            zip_path = os.path.join(type_folder, zip_filename)

            # Check of zip nodig is
            if not file_needs_zip(zip_path, year_path):
                print(f"   ⏭️ Up-to-date: {zip_filename}")
                continue

            print(f"   📦 Zippen van {year_path} → {zip_filename}")

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:  # 'w" overschrijft vorig bestand als dit bestaat
                for root, _, files in os.walk(year_path):
                    for file in files:
                        if file.endswith(".json"):
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, type_folder)
                            zipf.write(file_path, arcname)

            print(f"   ✅ Klaar: {zip_filename}")

def unzip_forecast_data(zip_path, extract_to=None):
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
            print(f"      ✅ Uitgepakt: {member.filename}")

def unzip_all_forecast_zips(base_dir="Data", forecast_types=["SolarForecast", "WindForecast"]):
    """
    Pak alle zipbestanden uit in opgegeven forecastfolders.

    Parameters:
    - base_dir (str): Basisdirectory waarin forecasttypes zich bevinden.
    - forecast_types (list[str]): Lijst van types met forecasts, bijvoorbeeld ["SolarForecast", "WindForecast"].

    Werking:
    - Zoekt in elk type-folder naar alle `.zip`-bestanden en roept `unzip_forecast_data()` op.
    - Alleen nieuwe bestanden worden uitgepakt.
    """
    for forecast_type in forecast_types:
        type_folder = os.path.join(base_dir, forecast_type)

        if not os.path.isdir(type_folder):
            print(f"   ❌ Map niet gevonden: {type_folder}")
            continue

        for file in os.listdir(type_folder):
            if file.endswith(".zip"):
                zip_path = os.path.join(type_folder, file)
                print(f"   📦 Bezig met uitpakken: {file}")
                unzip_forecast_data(zip_path)

    print('')

# ----------- Bijwerken van de data-bestanden -----------

def update_data(from_year=None, to_year=None, data_type='all'):
    """
    Update wind-, zonne- en/of Belpex-data tussen opgegeven jaartallen.
    Hierbij worden eerste de bestaande zip-bestanden uitgepakt.
    Vervolgens wordt de recenste data opgehaald bij Elia en Elexys.
    Ten slotte wordt nieuwe data toegevoegd aan de zip-bestanden
    
    Parameters:
    - from_year (int, optional): Startjaar. Default = vorig jaar.
    - to_year (int, optional): Eindjaar. Default = huidig jaar.
    - data_type (str, optional): 'wind', 'solar', 'belpex' of 'all'. Default = 'all'.
    """

    today = datetime.today()

    # Defaults
    if from_year is None:
        from_year = today.year - 1
    if to_year is None:
        to_year = today.year

    # Bepalen tot welke maand er data beschikbaar is. Pas vanaf de 4de dag is de info van de vorige maand beschikbaar.
    if today.day <= 4:
        latest_available_month = today.month - 2
    else:
        latest_available_month = today.month - 1

    latest_available_year = today.year
    if latest_available_month <= 0:
        latest_available_month += 12
        latest_available_year -= 1

    allowed_types = {'wind', 'solar', 'belpex', 'all'}
    if data_type not in allowed_types:
        raise ValueError(f"❌ Ongeldig data_type '{data_type}'. Kies uit {allowed_types}.")

    # Altijd eerst de huidige bestanden unzippen als er gekozen werd voor 'wind' of 'solar'
    if data_type in ('wind', 'solar', 'all'):
        print("\n📦Unzippen van de forecast-data...")
        unzip_all_forecast_zips()


    print(f"📅 Start met ophalen data voor periode {from_year}-{to_year}")
    counter = 0
    # Loop over jaren en maanden
    for year in range(from_year, to_year + 1):
        for month in range(1, 13):
            if (year == latest_available_year and month > latest_available_month) or (year > latest_available_year):
                continue

            print(f"   📅 Ophalen data voor {year}-{month:02d} ({data_type})")

            if data_type in ('wind', 'all'):
                try:
                    import_wind(year, month)
                    counter += 1
                except Exception as e:
                    print(f"❌ Fout bij ophalen winddata {year}-{month:02d}: {e}")

            if data_type in ('solar', 'all'):
                try:
                    import_solar(year, month)
                    counter += 1
                except Exception as e:
                    print(f"❌ Fout bij ophalen zonndata {year}-{month:02d}: {e}")

            if data_type in ('belpex', 'all'):
                try:
                    import_belpex(year, month)
                    counter += 1
                except Exception as e:
                    print(f"❌ Fout bij ophalen Belpex-data {year}-{month:02d}: {e}")
    if counter == 0:
        print("   ❌ Geen data beschikbaar.")

    # Alleen als 'wind' of 'solar' werd geüpdatet: zip de forecast-data
    if data_type in ('wind', 'solar', 'all'):
        print("\n📦 Zippen van de forecast-data...")
        zip_forecast_data()

    print("\n✅ Data-import afgerond.\n")