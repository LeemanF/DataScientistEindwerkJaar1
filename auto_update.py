r"""
auto_update.py

Automatisch update-script voor periodieke datavernieuwing.

Beschrijving:
- Dit script is bedoeld om automatisch uitgevoerd te worden via Windows Taakplanner.
- Het importeert de laatste energiegegevens (bv. van Elia en Belpex) en schrijft deze weg naar een lokale SQL-database.
- Alle output wordt zowel weergegeven op het scherm als gelogd in een bestand.

Modules:
- data_import_tools: bevat logica voor ophalen en verwerken van data.
- database_tools: bevat logica voor het wegschrijven naar een SQL-database.
- dual_logger: bevat logica om de printopdrachten ook naar een logbestand te schrijven.
- settings: bevat alle globale variabelen.

Gebruik:
- Inplannen via Windows Task Scheduler (bijv. maandelijks op de 5de dag).


Registratie in Windows Taakplanner:
1. Open de Taakplanner (Task Scheduler) via het startmenu.
2. Klik in het rechterpaneel op "Taak maken" (niet "Basis-taak maken" voor meer controle).
3. Op het tabblad **Algemeen**:
  - Geef de taak een herkenbare naam, bv. `Auto Update Script`.
  - Kies "Uitvoeren ongeacht of gebruiker is aangemeld" (optioneel) en geef indien nodig wachtwoord op.
4. Op het tabblad **Triggers**:
  - Klik op "Nieuw..." en stel in wanneer de taak moet worden uitgevoerd (bv. dagelijks om 06:00).
5. Op het tabblad **Acties**:
  - Klik op "Nieuw..." en kies bij "Actie": `Programma starten`.
  - Vul bij "Programma/script" het pad in naar je Python-interpreter, bv.:
    `C:\Users\<gebruikersnaam>\Anaconda3\python.exe`
  - Vul bij "Parameters toevoegen" het pad in naar dit script (tussen dubbele aanhalingstekens!), bv.:
    `C:\pad\naar\project\auto_update.py`
  - **Beginnen in (optioneel)**: vul hier de map in waarin het script zich bevindt, zonder aanhalingstekens.
    Bijvoorbeeld:
    `C:\pad\naar\project`
    Dit is belangrijk als je script relatieve paden gebruikt (zoals voor logbestanden of instellingen).
  - Of gebruik een `.bat`-bestand dat de juiste omgeving activeert en daarna het script uitvoert (aanbevolen).
6. (Optioneel) Op het tabblad **Instellingen** kun je herstartpogingen inschakelen als het mislukt.
7. Klik op OK om de taak op te slaan.
"""

import os
import traceback
from datetime import datetime

from src.data_import_tools import update_data
from src.database_tools import to_sql
from src.utils.dual_logger import DualLogger
from settings import LOG_DIR

# -------- Logging Setup --------

# Maak een map aan voor logbestanden (indien die nog niet bestaat)
os.makedirs(LOG_DIR, exist_ok=True)

# Stel het logbestand in met als naam het huidige datumformaat (log_YYYY-MM-DD.txt)
log_filename = datetime.now().strftime("log_%Y-%m-%d.txt")
log_path = os.path.join(LOG_DIR, log_filename)


# -------- Scriptuitvoering --------

with DualLogger(log_path):
    print(f"=================================================================================================")
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 🕒 Start Auto Update.")
    print(f"=================================================================================================\n")


    try:
        print("---------------------------------------------------------------------------------------")
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 📥 Start downloaden data.")
        print("---------------------------------------------------------------------------------------\n")
        update_data()
        print("---------------------------------------------------------------------------------------")
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 🗄️ Start bijwerken database.")
        print("---------------------------------------------------------------------------------------\n")
        to_sql()
        print(f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - ✅ Update afgerond.\n")
    except Exception as e:
        print(f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - ❌ Fout tijdens update: - {e}")
        print("\n------------------------------------------------------------------------\n")
        print(traceback.format_exc())
        print("------------------------------------------------------------------------\n")