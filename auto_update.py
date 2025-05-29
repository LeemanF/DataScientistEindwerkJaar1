"""
Automatisch update-script voor periodieke datavernieuwing.

Beschrijving:
- Dit script is bedoeld om automatisch uitgevoerd te worden via Windows Taakplanner.
- Het importeert de laatste energiegegevens (bv. van Elia en Belpex) en schrijft deze weg naar een lokale SQL-database.
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

    Deze klasse werkt zowel als:
    - Contextmanager: gebruik `with DualLogger(path):` om automatisch stdout/stderr te vervangen
                      en het logbestand na afloop veilig te sluiten.
    - Losse instantie: roep `logger = DualLogger(path)` aan, en vergeet `logger.close()` niet.

    Parameters:
    - logfile_path (str): Volledig pad naar het logbestand (zal geopend worden in append-modus).

    Gebruik als contextmanager:
    ----------------------------
    with DualLogger("pad/naar/log.txt"):
        print("Dit gaat naar console én naar logbestand.")
        raise Exception("Fouten ook!")

    Gebruik als losse instantie:
    ----------------------------
    logger = DualLogger("pad/naar/log.txt")
    sys.stdout = sys.stderr = logger
    print("Loggen zonder contextmanager.")
    logger.close()  # Belangrijk!
    """

    def __init__(self, logfile_path):
        # Sla pad op en open het logbestand (append-modus, UTF-8)
        self.logfile_path = logfile_path
        self.log = open(self.logfile_path, "a", encoding="utf-8", errors="replace")

        # Bewaar originele standaard streams om later te kunnen herstellen
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

    def write(self, message):
        """
        Wordt automatisch aangeroepen door print() of foutmeldingen.
        Schrijft het bericht zowel naar het scherm als naar het logbestand.
        """
        self.original_stdout.write(message)   # Toon op het scherm
        self.log.write(message)               # Schrijf naar het logbestand

    def flush(self):
        """
        Wordt automatisch aangeroepen om de buffer te legen.
        Noodzakelijk voor realtime logging of bij gebruik van print(..., flush=True).
        """
        self.original_stdout.flush()
        self.log.flush()

    def close(self):
        # Herstel standaard streams
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr

        # Sluit expliciet het logbestand bij manueel gebruik
        self.log.close()

    def __enter__(self):
        # Contextmanager start: vervang stdout en stderr door deze logger
        sys.stdout = sys.stderr = self
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Herstel oorspronkelijke streams
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        # Sluit het logbestand
        self.log.close()

# -------- Scriptuitvoering --------

with DualLogger(log_path):
    print("=======================================================================================")
    print(f"🕒 Start auto-update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        dit.update_data()
        dbt.to_sql()
        print(f"\n✅ Update afgerond: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    except Exception as e:
        print(f"\n❌ Fout tijdens update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {e}")
        print("\n------------------------------------------------------------------------\n")
        print(traceback.format_exc())
        print("------------------------------------------------------------------------\n")