"""
Automatisch update-script voor periodieke datavernieuwing.

Beschrijving:
- Dit script is bedoeld om automatisch uitgevoerd te worden via Windows Taakplanner.
- Het importeert de laatste energiegegevens (bv. van Elia en Belpex) en schrijft deze weg naar een lokale SQL-database.
- Alle output wordt zowel weergegeven op het scherm als gelogd in een bestand.

Modules:
- data_import_tools: bevat logica voor ophalen en verwerken van data. Enkel update_data wordt geïmporteerd
- database_tools: bevat logica voor het wegschrijven naar een SQL-database. Enkel to_sql wordt geïmporteerd

Vereisten:
- De benodigde Python-omgeving moet actief zijn tijdens uitvoering (via `.bat` of taakplanner).
- De modules `data_import_tools` en `database_tools` moeten correct geïnstalleerd zijn of zich in het pad bevinden.

Gebruik:
- Inplannen via Windows Task Scheduler (bijv. dagelijks om 06:00).
"""

# auto_update.py

import os
import traceback
from datetime import datetime

from data_import_tools import update_data
from database_tools import to_sql
from dual_logger import DualLogger

# -------- Logging Setup --------

# Maak een map aan voor logbestanden (indien die nog niet bestaat)
LOG_DIR = os.path.join(os.path.dirname(__file__), "Log")
os.makedirs(LOG_DIR, exist_ok=True)

# Stel het logbestand in met als naam het huidige datumformaat (log_YYYY-MM-DD.txt)
log_filename = datetime.now().strftime("log_%Y-%m-%d.txt")
log_path = os.path.join(LOG_DIR, log_filename)


# -------- Scriptuitvoering --------

with DualLogger(log_path):
    print("=======================================================================================")
    print(f"🕒 Start auto-update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        update_data()
        to_sql()
        print(f"\n✅ Update afgerond: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    except Exception as e:
        print(f"\n❌ Fout tijdens update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {e}")
        print("\n------------------------------------------------------------------------\n")
        print(traceback.format_exc())
        print("------------------------------------------------------------------------\n")