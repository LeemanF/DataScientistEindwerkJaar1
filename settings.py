# settings.py

from pathlib import Path

# ─────────────────────────────────────────────────────────────
# Basisdirectory van de datamappen
BASE_DIR = Path(__file__).resolve().parent  # de map waarin settings.py staat
#BASE_DIR = Path("D:/Eindwerk")

# Scripts en vereisten in de projectroot 
REQUIREMENTS_FILE = BASE_DIR / "requirements.txt"
AUTO_UPDATE_SCRIPT = BASE_DIR / "auto_update.py"
MAIN_SCRIPT = BASE_DIR / "main.ipynb"

# ─────────────────────────────────────────────────────────────
# Package-map
SRC_DIR = BASE_DIR / "src"

# ─────────────────────────────────────────────────────────────
# Data-dir met de submappen Belpex, SolarForecast, WindForecast
DATA_DIR            = BASE_DIR / "Data"
BELPEX_DIR          = DATA_DIR / "Belpex"
SOLAR_FORECAST_DIR  = DATA_DIR / "SolarForecast"
WIND_FORECAST_DIR   = DATA_DIR / "WindForecast"

# ─────────────────────────────────────────────────────────────
# Log-directory
LOG_DIR = BASE_DIR / "Log"

# ─────────────────────────────────────────────────────────────
# Database-bestanden
DB_DIR  = BASE_DIR / "Database"
DB_FILE = DB_DIR / "energie_data.sqlite"

# ─────────────────────────────────────────────────────────────
# (Optioneel) Timeouts, retries, etc.
HTTP_TIMEOUT = 10  # default timeout voor API-calls
DEFAULT_ATTEMPTS = 3    # default aantal pogingen bij fouten
RETRY_DELAY   = 5  # default wachttijd bij retry
