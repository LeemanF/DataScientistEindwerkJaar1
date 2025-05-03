"""
Data Import Tools for Elia Open Data & Belpex Market Data.

Functies:
- Ophalen en lokaal opslaan van wind- en zonne-energievoorspellingen (per dag).
- Ophalen van Belpex-spotmarktprijzen via browserautomatisering.
- Zippen en unzippen van forecast-data per jaar.
- Omgaan met netwerkfouten en browserproblemen via retry-mechanismen.
"""

# ----------- Imports -----------

import os
import calendar
import json
import time
import shutil
from datetime import datetime
import zipfile
import functools
import sys
import subprocess

# ----------- Automatische installatie van modules -----------

def install_if_missing(package_name):
    """Installeer een ontbrekende Python-module via pip."""
    try:
        __import__(package_name)
    except ImportError:
        print(f"📦 Module '{package_name}' niet gevonden. Bezig met installeren...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        print(f"✅ Module '{package_name}' geïnstalleerd.")

# Controleer en installeer afzonderlijke modules
install_if_missing("requests")
install_if_missing("selenium")
install_if_missing("webdriver_manager")

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ----------- Retry Decorator & Safe Request -----------

def retry_on_failure(tries=3, delay=2, backoff=1, allowed_exceptions=(Exception,)):
    """Decorator om een functie meerdere keren opnieuw te proberen bij fouten."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _tries, _delay = tries, delay
            while _tries > 1:
                try:
                    return func(*args, **kwargs)
                except allowed_exceptions as e:
                    _tries -= 1
                    print(f"⚠️ Fout '{e}' in {func.__name__}(). Nog {_tries} pogingen over... Wacht {_delay:.1f}s.")
                    time.sleep(_delay)
                    _delay *= backoff
            return func(*args, **kwargs)
        return wrapper
    return decorator

def safe_requests_get(url, params=None, headers=None, tries=3, delay=2, timeout=10):
    """Aangepast versie van requests.get() met retries bij fouten."""
    _tries = tries
    while _tries > 1:
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response
        except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
            print(f"⚠️ Request fout: {e}. Nog {_tries-1} pogingen... Wacht {delay}s.")
            time.sleep(delay)
            _tries -= 1
    response = requests.get(url, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response

# ----------- Data Import Functies -----------

@retry_on_failure(tries=3, delay=5)
def import_wind(year,month):
    """Download en sla windforecast-data op voor een bepaalde maand."""

    # Bepaal het aantal dagen in de maand
    _, num_days = calendar.monthrange(year, month)

    # Submap per jaar aanmaken
    base_folder = r"Data\WindForecast"
    year_folder = os.path.join(base_folder, str(year))
    os.makedirs(year_folder, exist_ok=True)

    # Loop over elke dag van de maand
    for day in range(1, num_days + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"  # Opgelet: gebruik "-" i.p.v. "/"
        output_filename = f"WindForecast_Elia_{year}{month:02d}{day:02d}.json"
        output_path = os.path.join(year_folder, output_filename)

        if os.path.exists(output_path):
            #print(f"✅ Bestand bestaat al: {output_filename}")
            continue

        print(f"⬇️ Ophalen: {output_filename}")

        url = "https://opendata.elia.be/api/explore/v2.1/catalog/datasets/ods031/records"
        all_records = []
        limit = 100
        offset = 0

        while True:
            params = {
                "order_by": "datetime",
                "limit": limit,
                "offset": offset,
                "refine": [
                    f'datetime:"{date_str}"'
                ]
            }

            response = safe_requests_get(url, params=params)

            if response.status_code != 200:
                print(f"❌ Fout bij {date_str} (offset {offset}): {response.status_code}")
                break

            data = response.json().get("results", [])
            if not data:
                break  # Geen data meer, stop loop

            all_records.extend(data)
            if offset != 0: 
                print(f'⏳ De eerste {offset} records werden binnengehaald.', end='\r')
            offset += limit

        if all_records:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(all_records, f, ensure_ascii=False, indent=2)
            print(f"✅ Opgeslagen ({len(all_records)} records): {output_filename}")
        else:
            print(f"❌ Geen data voor {date_str}")

@retry_on_failure(tries=3, delay=5)
def import_solar(year,month):
    """Download en sla zonneforecast-data op voor een bepaalde maand."""

    # Bepaal het aantal dagen in de maand
    _, num_days = calendar.monthrange(year, month)

    # Map voor opslag
    base_folder = r"Data\SolarForecast"
    year_folder = os.path.join(base_folder, str(year))
    os.makedirs(year_folder, exist_ok=True)

    # Loop over elke dag van de maand
    for day in range(1, num_days + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"  # Gebruik "-" in plaats van "/"
        output_filename = f"SolarForecast_Elia_{year}{month:02d}{day:02d}.json"
        output_path = os.path.join(year_folder, output_filename)

        if os.path.exists(output_path):
            #print(f"✅ Bestand bestaat al: {output_filename}")
            continue

        print(f"⬇️ Ophalen: {output_filename}")

        url = "https://opendata.elia.be/api/explore/v2.1/catalog/datasets/ods032/records"
        all_records = []
        limit = 100
        offset = 0

        while True:
            params = {
                "order_by": "datetime",
                "limit": limit,
                "offset": offset,
                "refine": [
                    f'datetime:"{date_str}"',
                    'region:"Belgium"'
                ]
            }

            response = safe_requests_get(url, params=params)

            if response.status_code != 200:
                print(f"❌ Fout bij {date_str} (offset {offset}): {response.status_code}")
                break

            data = response.json().get("results", [])
            if not data:
                break  # Geen data meer, stop loop

            all_records.extend(data)
            if offset != 0: 
                print(f'⏳ De eerste {offset} records werden binnengehaald.', end='\r')
            offset += limit

        if all_records:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(all_records, f, ensure_ascii=False, indent=2)
            print(f"✅ Opgeslagen ({len(all_records)} records): {output_filename}")
        else:
            print(f"❌ Geen data voor {date_str}")

@retry_on_failure(tries=3, delay=5)
def import_belpex(year, month):
    """Download Belpex-spotmarktprijzen via browserautomatisering."""

    # Bereken de datums voor de maand
    from_date = f"01/{month:02d}/{year}"  # Eerste dag van de maand

    # Bepaal de eerste dag van de volgende maand voor de 'until_date'
    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year

    # De eerste dag van de volgende maand
    next_month_first_day = datetime(next_year, next_month, 1)
    until_date = next_month_first_day
    until_date = until_date.strftime("%d/%m/%Y")

    # Downloadpad instellen
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
        print("❌ Niet hernoemde bestand BelpexFilter.csv werd verwijderd.")

    new_filename = f"Belpex_{year}{month:02d}.csv"


    if new_filename in os.listdir(download_dir):
        #print(f"✅ Bestand bestaat al: {new_filename}")
        pass
    else:
        # Ga naar de website
        driver.get("https://my.elexys.be/MarketInformation/SpotBelpex.aspx")

        print(f"⬇️ Starten met het opvragen Belpex-gegevens periode {month}/{year}")
        
        # Wacht tot het formulier en de knop "Show data" beschikbaar zijn
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.ID, "contentPlaceHolder_fromASPxDateEdit_I")))

        # Vul de datums in
        from_input = driver.find_element(By.ID, "contentPlaceHolder_fromASPxDateEdit_I")
        until_input = driver.find_element(By.ID, "contentPlaceHolder_untilASPxDateEdit_I")

        print(f"📆 Vul 'From' datum in: {from_date}")
        from_input.clear()
        from_input.send_keys(from_date)

        print(f"📆 Vul 'Until' datum in: {until_date}")
        until_input.clear()
        until_input.send_keys(until_date)

        # Klik op "Show data"
        show_data_button = driver.find_element(By.ID, "contentPlaceHolder_refreshBelpexCustomButton_I")
        print("🚀 Klik op 'Show data'")
        driver.execute_script("arguments[0].click();", show_data_button)

        # Wacht op tabelresultaten
        print("⏳ Wacht op zoekresultaten...")
        wait.until(EC.presence_of_element_located((By.ID, "contentPlaceHolder_belpexFilterGrid_DXMainTable")))
        time.sleep(5)  # Extra wachttijd voor stabiliteit

        # ✅ Klik op de juiste export-div
        print("🚀 Klik op 'Exporteer naar CSV'")
        export_button_div = wait.until(EC.element_to_be_clickable((By.ID, "ctl00_contentPlaceHolder_GridViewExportUserControl1_csvExport")))
        driver.execute_script("arguments[0].click();", export_button_div)

        # Wacht op de download
        print("⏳ Wacht op download...")
        time.sleep(5)

        # Als het bestand bestaat, hernoem het bestand naar 'Belpex_JJJJMM.csv' (bijv. Belpex_202401.csv)
        if "BelpexFilter.csv" in os.listdir(download_dir):
            new_filename = f"Belpex_{year}{month:02d}.csv"
            os.rename(os.path.join(download_dir, "BelpexFilter.csv"), os.path.join(download_dir, new_filename))
            print(f"✅ Gedownload en hernoemd naar: {new_filename}")
        else:
            print("❌ Download mislukt.")

        # Sluit de browser
        driver.quit()

# ----------- Zip Functies -----------

def file_needs_zip(zip_path, folder_path):
    """Controleer of zip verouderd is t.o.v. bestanden in de map"""
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
    """Zip forecast JSON-bestanden per jaar."""
    for forecast_type in forecast_types:
        type_folder = os.path.join(base_dir, forecast_type)

        if not os.path.isdir(type_folder):
            print(f"⚠️ Map bestaat niet: {type_folder}")
            continue

        for year in os.listdir(type_folder):
            year_path = os.path.join(type_folder, year)

            if not os.path.isdir(year_path):
                continue  # Sla bestanden of vreemde dingen over

            zip_filename = f"{forecast_type}_{year}.zip"
            zip_path = os.path.join(type_folder, zip_filename)

            # Check of zip nodig is
            if not file_needs_zip(zip_path, year_path):
                print(f"⏭️ Up-to-date: {zip_filename}")
                continue

            print(f"📦 Zippen van {year_path} → {zip_filename}")

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:  # 'w" overschrijft vorig bestand als dit bestaat
                for root, _, files in os.walk(year_path):
                    for file in files:
                        if file.endswith(".json"):
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, type_folder)
                            zipf.write(file_path, arcname)

            print(f"✅ Klaar: {zip_filename}")

def unzip_forecast_data(zip_path, extract_to=None):
    """Unzip een enkele zip-forecastfile."""
    if extract_to is None:
        extract_to = os.path.dirname(zip_path)

    with zipfile.ZipFile(zip_path, 'r') as zipf:
        for member in zipf.infolist():
            extracted_path = os.path.join(extract_to, member.filename)
            if os.path.exists(extracted_path):
																 
                continue
            os.makedirs(os.path.dirname(extracted_path), exist_ok=True)
            with zipf.open(member) as source, open(extracted_path, 'wb') as target:
                shutil.copyfileobj(source, target)
            # Zet de oorspronkelijke modificatie-tijd terug
            date_time = time.mktime(member.date_time + (0, 0, -1))
            os.utime(extracted_path, (date_time, date_time))
            print(f"✅ Uitgepakt: {member.filename}")

def unzip_all_forecast_zips(base_dir="Data", forecast_types=["SolarForecast", "WindForecast"]):
    """Unzip alle forecast zip-bestanden in een basisdirectory."""
    for forecast_type in forecast_types:
        type_folder = os.path.join(base_dir, forecast_type)

        if not os.path.isdir(type_folder):
            print(f"❌ Map niet gevonden: {type_folder}")
            continue

        for file in os.listdir(type_folder):
            if file.endswith(".zip"):
                zip_path = os.path.join(type_folder, file)
                print(f"📦 Bezig met uitpakken: {file}")
                unzip_forecast_data(zip_path)

    print('\n')

# ----------- Combine functions and update data -----------

def update_data(from_year=None, to_year=None, data_type='all'):
    """
    Update wind-, zonne- en/of Belpex-data tussen opgegeven jaartallen.
    
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
    if today.day < 4:
        latest_available_month = today.month - 2
    else:
        latest_available_month = today.month - 1

    if latest_available_month <= 0:
        latest_available_month += 12
        to_year -= 1

    allowed_types = {'wind', 'solar', 'belpex', 'all'}
    if data_type not in allowed_types:
        raise ValueError(f"❌ Ongeldig data_type '{data_type}'. Kies uit {allowed_types}.")

    # Altijd eerst de huidige bestanden unzippen
    if data_type in ('wind', 'solar', 'all'):
        print("\n📦Unzippen van de forecast-data...")
        unzip_all_forecast_zips()

    # Loop over jaren en maanden
    for year in range(from_year, to_year + 1):
        for month in range(1, 13):
            if (year == today.year and month > latest_available_month) or (year > to_year):
                continue

            print(f"📅 Ophalen data voor {year}-{month:02d} ({data_type})...")

            if data_type in ('wind', 'all'):
                try:
                    import_wind(year, month)
                except Exception as e:
                    print(f"❌ Fout bij ophalen winddata {year}-{month:02d}: {e}")

            if data_type in ('solar', 'all'):
                try:
                    import_solar(year, month)
                except Exception as e:
                    print(f"❌ Fout bij ophalen zonndata {year}-{month:02d}: {e}")

            if data_type in ('belpex', 'all'):
                try:
                    import_belpex(year, month)
                except Exception as e:
                    print(f"❌ Fout bij ophalen Belpex-data {year}-{month:02d}: {e}")

    # Alleen als 'wind' of 'solar' werd geüpdatet: zip de forecast-data
    if data_type in ('wind', 'solar', 'all'):
        print("\n📦 Zippen van de forecast-data...")
        zip_forecast_data()

    print("\n✅ Data-update afgerond.")