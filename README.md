# Evolutie productie zonne- en windenergie en Belpex marktprijzen (stand van zaken 06/06/2025)

Automatiseer het ophalen, verwerken en lokaal opslaan van energiegegevens uit Elia Open Data (zon en wind) en Belpex marktprijzen.  
De gegevens worden na import automatisch opgeslagen in een SQLite-database voor verdere analyse.

---

## 📁 Bestandsstructuur

- `auto_update.py`: 
  Script dat automatisch de volledige updateprocedure start en logging verzorgt.  
  Wordt idealiter uitgevoerd via Windows Taakplanner.  
  Dit script roept intern de volgende modules aan:
  
  - `data_import_tools.py`: Bevat functies voor het ophalen van data, en het (un)zippen van bestanden.
  - `database_tools.py`: Bevat functies voor het verwerken van data en het wegschrijven naar een lokale SQLite-database.

- `main.ipynb`: 
  Jupyter-notebook dat dient als manueel controlescript of testomgeving voor analyse en dataverwerking.

---

## 📦 Functionaliteiten

✅ Ophalen van:
- Wind- en zonneproductiegegevens via Elia Open Data API (bestand per dag, als JSON)
- Belpex spotprijzen via geautomatiseerde webbrowser (Selenium, CSV)

✅ Ondersteuning voor:
- Retry-mechanismen bij netwerkproblemen
- Per jaar zip/unzip van data voor efficiënte opslag
- Automatische verwerking naar SQLite-database

✅ Logging:
- Alle uitvoer van het script `auto_update.py` wordt gelogd naar een bestand per dag (`Log/log_YYYY-MM-DD.txt`) én naar de console.

---

## 🚀 Uitvoeren

Voor automatische updates (bijv. via Windows Taakplanner):

```bash
python auto_update.py
```

Of manueel via Python:

```python
from data_import_tools import update_data
from database_tools import to_sql

# Data ophalen van 2023 tot 2025
update_data(from_year=2023, to_year=2025, data_type="all")

# Data wegschrijven naar database
to_sql(data_type="all")
```

---

## 🔧 Installatie

1. Zorg voor een recente Python-omgeving (3.10+ aanbevolen).
2. Installeer vereiste modules (automatisch via scripts, maar handmatig kan ook):

```bash
pip install requests selenium sqlalchemy tqdm webdriver-manager
```

3. Zorg dat ChromeDriver of EdgeDriver beschikbaar is (automatisch via `webdriver_manager`).

---

## 🗃️ Database

De SQLite-database bevindt zich standaard in:  
`./Database/energie_data.sqlite`

Tabellen:
- `solar_data`
- `wind_data`
- `belpex_prices`

Elke tabel bevat indexen op jaar/maand/dag/uur en gebruikt unieke constraints om duplicaten te vermijden.

---

## 📂 Verwachte mappenstructuur

```
Project/
├── .gitignore                     # Bestanden/mappen uitgesloten van versiebeheer
├── auto_update.py                # Script voor automatische updates van data
├── main.ipynb                    # Hoofdnotebook voor analyse en/of verwerking
├── requirements.txt              # Vereiste Python-pakketten
├── settings.py                   # Centrale instellingen (paden, parameters)
├── Data/                         # Bevat alle geïmporteerde of verwerkte data
│   ├── Belpex/                   # CSV-bestanden met Belpex-marktprijzen
│   │   ├── Belpex_202001.csv
│   │   ├── Belpex_202002.csv
│   │   └── ...
│   ├── SolarForecast/            # Zonneproductievoorspellingen en - metingen (JSON & ZIP)
│   │   ├── SolarForecast_2020.zip
│   │   ├── ...
│   │   ├── 2025/
│   │   │   ├── SolarForecast_Elia_20250425.json
│   │   │   ├── ...
│   └── WindForecast/             # Windproductievoorspellingen en - metingen (JSON & ZIP)
│       ├── WindForecast_2020.zip
│       ├── ...
│       ├── 2025/
│       │   ├── WindForecast_Elia_20250425.json
│       │   ├── ...
├── Database/
│   └── energie_data.sqlite       # SQLite-database met gestructureerde gegevens
├── Documents/                    # Documentatie van het project
│   ├── Solar.json
│   └── Wind.json
├── Log/                          # Logbestanden gegenereerd door scripts
│   └── log_YYYY-MM-DD.txt
├── src/                          # Broncode van het project (modulair opgebouwd)
│   ├── __init__.py
│   ├── data_import_tools.py      # Importtools voor verschillende databronnen
│   ├── database_tools.py         # Tools voor interactie met SQLite
│   └── utils/                    # Algemene hulpfuncties en helpers
│       ├── __init__.py
│       ├── constants_inspector.py
│       ├── decorators.py
│       ├── dual_logger.py
│       ├── package_tools.py
│       └── safe_requests.py
```


## 👨‍💻 Auteur

Ontwikkeld door Frank Leeman.  
Gebruik dit project om historische en actuele energiegegevens eenvoudig beschikbaar te maken voor analyse.