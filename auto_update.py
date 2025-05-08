"""
Automatisch update-script voor periodieke datavernieuwing.

Beschrijving:
- Dit script is bedoeld om automatisch uitgevoerd te worden via Windows Taakplanner.
- Het importeert de laatste energiegegevens (bv. van Elia en Belpex) en schrijft deze weg naar een lokale SQL-database.
- De functies zijn onderverdeeld in aparte modules voor herbruikbaarheid en onderhoudbaarheid.
- Alle output wordt ook gelogd.

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

# Map aanmaken voor logbestanden
LOG_DIR = os.path.join(os.path.dirname(__file__), "Log")
os.makedirs(LOG_DIR, exist_ok=True)

# Logbestand met datum in de naam
log_filename = datetime.now().strftime("log_%Y-%m-%d.txt")
log_path = os.path.join(LOG_DIR, log_filename)

# Klasse voor dubbele logging (console + bestand)
class DualLogger:
    def __init__(self, stdout, logfile_path):
        self.terminal = stdout
        self.log = open(logfile_path, "a", encoding="utf-8", errors="replace")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()

# Activeer logging
sys.stdout = sys.stderr = DualLogger(sys.stdout, log_path)

# -------- Scriptuitvoering --------

print("=======================================================================================")
print(f"🕒 Start auto-update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

try:
    dit.update_data('abc')
    dbt.to_sql()
    print(f"\n✅ Update succesvol afgerond: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
except Exception as e:
    print(f"\n❌ Fout tijdens update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {e}")
    print("\n------------------------------------------------------------------------\n")
    print(traceback.format_exc())
    print("------------------------------------------------------------------------")