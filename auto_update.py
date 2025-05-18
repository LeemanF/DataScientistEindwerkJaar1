"""
Automatisch update-script voor periodieke datavernieuwing.

Beschrijving:
- Dit script is bedoeld om automatisch uitgevoerd te worden via Windows Taakplanner.
- Het importeert de laatste energiegegevens (bv. van Elia en Belpex) en schrijft deze weg naar een lokale SQL-database.
- De functies zijn onderverdeeld in aparte modules voor herbruikbaarheid en onderhoudbaarheid.
- Alle output wordt zowel weergegeven op het scherm als gelogd in een bestand.

Modules:
- data_import_tools (als 'dit'): bevat logica voor ophalen en verwerken van data.
- database_tools (als 'dbt'): bevat logica voor het wegschrijven naar een SQL-database.

Vereisten:
- De benodigde Python-omgeving moet actief zijn tijdens uitvoering (via `.bat` of taakplanner).
- De modules `data_import_tools` en `database_tools` moeten correct geïnstalleerd zijn of zich in het pad bevinden.

Gebruik:
- Inplannen via Windows Task Scheduler (bijv. dagelijks om 06:00).

"""

# auto_update.py

import sys
import os
import traceback
from datetime import datetime

import data_import_tools as dit
import database_tools as dbt

# -------- Logging Setup --------

# Maak een map aan voor logbestanden (indien die nog niet bestaat)
LOG_DIR = os.path.join(os.path.dirname(__file__), "Log")
os.makedirs(LOG_DIR, exist_ok=True)

# Stel het logbestand in met als naam het huidige datumformaat (log_YYYY-MM-DD.txt)
log_filename = datetime.now().strftime("log_%Y-%m-%d.txt")
log_path = os.path.join(LOG_DIR, log_filename)

# Klasse voor dubbele logging (console + bestand)
class DualLogger:
    """
    Vervangt sys.stdout en sys.stderr zodat alle output (zowel print als foutmeldingen)
    tegelijkertijd naar de console én naar een logbestand geschreven wordt.

    Parameters:
        stdout (TextIO): de originele standaarduitvoer (meestal de console).
        logfile_path (str): pad naar het logbestand.
    """
    def __init__(self, stdout, logfile_path):
        self.terminal = stdout  # Originele stdout (bijv. console)
        self.log = open(logfile_path, "a", encoding="utf-8", errors="replace")  # Logbestand in append-modus

    def write(self, message):
        """
        Wordt automatisch aangeroepen door print() of foutmeldingen.
        Schrijft het bericht zowel naar het scherm als naar het logbestand.
        """
        self.terminal.write(message)  # Toon op het scherm
        self.log.write(message)       # Schrijf naar het logbestand

    def flush(self):
        """
        Wordt automatisch aangeroepen om de buffer te legen.
        Noodzakelijk voor realtime logging of bij gebruik van print(..., flush=True).
        """
        self.terminal.flush()
        self.log.flush()

# Vervang sys.stdout en sys.stderr door een instantie van DualLogger
# Hierdoor worden alle print()'s en foutmeldingen automatisch dubbel gelogd:
# zichtbaar op het scherm én opgeslagen in het logbestand.
# Bewaar eerst originele outputkanalen
original_stdout = sys.stdout
original_stderr = sys.stderr
sys.stdout = sys.stderr = DualLogger(sys.stdout, log_path)

# -------- Scriptuitvoering --------

print("=======================================================================================")
print(f"🕒 Start auto-update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

try:
    dit.update_data()
    dbt.to_sql()
    print(f"\n✅ Update afgerond: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
except Exception as e:
    print(f"\n❌ Fout tijdens update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {e}")
    print("\n------------------------------------------------------------------------\n")
    print(traceback.format_exc())  # Print volledige fout-traceback
    print("------------------------------------------------------------------------\n")
finally:
    # Sluit het logbestand netjes af
    sys.stdout.log.close()
    # Herstel oorspronkelijke sys.stdout en sys.stderr
    sys.stdout = original_stdout
    sys.stderr = original_stderr