![Banner](Documents/Images/Banner.png)  
# Evolutie productie zonne- en windenergie

Laatste update 09/10/2025

Voor de opleiding Data-Scientist werd gevraagd om een eindproef in Python te maken met de focus op het ETL-proces:
- **Extract**: het binnenhalen van de data  
- **Transform**: het bewerken (opkuisen) van de data  
- **Load**: het analyseren van de opgekuiste data  

De opdracht moest voldoende complex maar haalbaar zijn, en bovendien in staat om nieuwe of bijkomende data te verwerken.

Ik koos voor een analyse van de productie van zonne- en windenergie, gecombineerd met de Belpex-spotmarktprijzen.

---

## 🛢️ Databronnen

### Elia

Elia stelt via hun website gegevens beschikbaar:  
- [Zonne-energieproductie](https://www.elia.be/nl/grid-data/productie/zonne-energieproductie)  
- [Windenergieproductie](https://www.elia.be/nl/grid-data/productie-gegevens/windenergieproductie)

`UPDATE 06/07/2025: Elia biedt niet langer de data aan via een gewone download op hun website en verplicht het gebruik van API`

Omdat Elia ook een API aanbiedt, werd gekozen voor deze stabielere oplossing:  
- [Dataset zonne-energie (ODS031)](https://opendata.elia.be/explore/dataset/ods031/information/)  
- [Dataset windenergie (ODS032)](https://opendata.elia.be/explore/dataset/ods032/information/)

Meer informatie over de aangeboden data vind je hier:  
- Voorbeeld van opgehaalde windgegevens: [Wind.json](Documents/Wind.json)  
- Voorbeeld van opgehaalde zonnegegevens: [Solar.json](Documents/Solar.json)

Een toelichting over het verschil tussen vermogen en energie vind je via de volgende link: [vermogen vs energie](Documents/vermogen_energie.md)

### Elexys (Belpex)

De Belpex-spotmarktprijzen zijn beschikbaar via de Elexys-website:  
[https://my.elexys.be/MarketInformation/SpotBelpex.aspx](https://my.elexys.be/MarketInformation/SpotBelpex.aspx)

Omdat er geen API beschikbaar is, werd hiervoor gebruik gemaakt van **webscraping**.

---

## 🧱 Projectopbouw

### Configuratie (`settings.py`)
De standaardlocaties van de data- en outputbestanden zijn configureerbaar via het bestand [`settings.py`](settings.py).

### Extractie van gegevens (`data_import_tools.py`)
Het ophalen van data gebeurt via het script [`data_import_tools.py`](src/data_import_tools.py). De belangrijkste functies zijn:  

- `import_wind(year, month)`
- `import_solar(year, month)`
- `import_belpex(year, month)`  

Omdat Elia maximaal 100 records per request toelaat, werd ervoor gekozen om de data dag per dag op te halen en afzonderlijk op te slaan.

#### Foutafhandeling
Om fouten tijdens het ophalen van data op te vangen, wordt gebruik gemaakt van:
- `retry_on_failure(...)`: een decorator die herhaalde pogingen toelaat bij falende requests.
- `safe_requests_get(...)`: een robuustere versie van `requests.get()` met retry- en timeout-logica.

Hierdoor worden netwerkproblemen automatisch opgevangen met maximaal twee extra pogingen.

#### Gegevensopslag en compressie
De opgehaalde Elia-data worden opgeslagen als dagelijkse JSON-bestanden.  
Om opslagruimte te beperken en versiebeheer te vereenvoudigen, worden deze per maand gecomprimeerd (.zip).  
De zip-bestanden bevatten steeds een volledige maand per type (zonne- of windenergie), wat ook het manueel beheren vergemakkelijkt.  

Belangrijke functies:
- `zip_forecast_data(...)`
- `unzip_all_forecast_zips(...)`

Het hele proces kan automatisch uitgevoerd worden met:
- `update_data()`: deze functie automatiseert het ophalen, unzippen, verwerken en opslaan van alle data over een gekozen periode.


### Transformatie van gegevens (`database_tools.py`)

De module [`database_tools.py`](src/database_tools.py) bevat de klassen en functies die nodig zijn om de data op te slaan in een SQLite-database.  
Volgende klassen vormen het fundament van het SQLAlchemy-model:

- `class SolarData`: model voor het creëren en vullen van de tabel `tbl_solar_data`
- `class WindData`: model voor het creëren en vullen van de tabel `tbl_wind_data`
- `class BelpexPrice`: model voor het creëren en vullen van de tabel `tbl_belpex_prices`

Een overzicht van de beschikbare modellen en hun kolommen is terug te vinden via de functie `alle_modellen_en_kolommen()` in de module  
[`sqlalchemy_model_utils.py`](src/utils/sqlalchemy_model_utils.py).

#### Verrijking van de data
De verkregen data wordt in alle modellen aangevuld met extra tijdsdimensies in de vorm van onderstaande kolommen:

- `day`
- `month`
- `year`
- `weekday`
- `hour`
- `minute`  

Deze extra tijdsdimensies maken het mogelijk om flexibel te groeperen en te visualiseren op dag-, week-, maand-, weekdag- of uurniveau.

#### Toevoegen records aan database

De JSON-bestanden (Elia) en de CSV-bestanden (Belpex-prijzen) worden op een andere manier verwerkt.  
Het verrijken van de JSON-bestanden gebeurt via de functie `parse_record()`.  
Bij de CSV-bestanden wordt de extra data toegevoegd bij het inlezen.

- `process_directory()`: verwerking van de zonne- en windenergiedata  
- `process_belpex_directory()`: opkuisen, verrijken en verwerken van de Belpex-prijzen  

De functie `insert_batch()` maakt connectie met de database en verstuurt de records in batches.  
Als de verwerking per batch fouten oplevert, worden de records afzonderlijk verwerkt.  
Zo gaat er bij een fout in één record geen volledige batch verloren.

Er is bewust gekozen om alle beschikbare data te laten doorstromen naar de database.  
Hierdoor blijft alle data beschikbaar voor extra analyses in de toekomst.

Het volledige proces van transformeren en verwerken wordt samengebracht in de functie `to_sql()`.

### Automatische update (`auto_update.py`)
Het script [`auto_update.py`](auto_update.py) automatiseert zowel het ophalen als het verwerken van de data.  
De functies `update_data()` en `to_sql()` worden hierbij binnen de contextmanager `DualLogger()` uitgevoerd.  
Dit script kan via de Windows Taakplanner automatisch op maandelijkse basis uitgevoerd worden: zie [voorbeeld instellingen](Documents/Images/Taakplanner.png)

#### Logging (`dual_logger.py`)
De klasse [`DualLogger()`](src/utils/dual_logger.py) zorgt ervoor dat alle console-uitvoer ook naar een logbestand geschreven wordt: zie [voorbeeld](Documents/log_2025-10-05.txt).  
Hoewel de logging-module de professionele standaard is, biedt DualLogger in het kader van dit eindproject een eenvoudige, robuuste en onderhoudsarme manier om zowel standaarduitvoer als foutmeldingen en tqdm-voortgangsbalken simultaan te loggen. Voor grotere projecten zou ik uiteraard de logging-module verkiezen.

### Laden en visualiseren van de data
*Under construction*  
In een latere fase worden interactieve grafieken en samenvattende visualisaties toegevoegd op basis van de opgeladen data.

---

## 🔧 Installatie

1. Zorg voor een recente Python-omgeving (3.10+ aanbevolen).
2. Installeer vereiste modules (bij voorkeur manueel, maar dit verloopt ook automatisch via het importeren van de scripts): zie [requirements.txt](requirements.txt)
```bash
pip install -r requirements.txt
```
3. Zorg dat ChromeDriver of EdgeDriver beschikbaar is (wordt automatisch beheerd via `webdriver_manager`, geen handmatige installatie nodig).

---

## 🗃️ Database

De SQLite-database bevindt zich standaard in:  
`./Database/energie_data.sqlite`

Tabellen:
- [tbl_solar_data](Documents/tbl_solar_data.txt)
- [tbl_wind_data](Documents/tbl_wind_data.txt)
- [tbl_belpex_prices](Documents/tbl_belpex_prices.txt)

Elke tabel bevat indexen op datetime, jaar, maand, dag, weekdag en uur, en gebruikt unieke constraints om duplicaten te vermijden.

Views:
- `v_solar`
- `v_wind`
- `v_belpex`

---

## 📚 Documentatie
De volledige code is voorzien van duidelijke docstrings (conform de [PEP 257](https://peps.python.org/pep-0257/)-stijl) en inline commentaar waar nodig.  
Dit vergemakkelijkt het onderhoud, hergebruik en uitbreiding van het project.

---

## 🧩 Herbruikbaarheid code
De code is modulair opgebouwd, met een duidelijke scheiding tussen extractie, transformatie/opslag en — in de toekomst — visualisaties.  
Veelgebruikte logica is ondergebracht in herbruikbare hulpfuncties binnen de `utils`-map.  
Hierdoor is het eenvoudig om het project uit te breiden met andere databronnen of opslagstructuren.

---

## 📂 Verwachte mappenstructuur

```
Project/
├── .gitignore                          # Bestanden/mappen uitgesloten van versiebeheer
├── auto_update.py                      # Script voor automatische updates van data
├── main.ipynb                          # Hoofdnotebook voor analyse en/of visualisaties
├── README.md                           # Beschrijving van het project
├── requirements.txt                    # Vereiste Python-pakketten
├── settings.py                         # Centrale instellingen (paden, parameters)
├── Data/                               # Bevat alle geïmporteerde data
│   ├── Belpex/                         # CSV-bestanden met Belpex-marktprijzen
│   │   ├── Belpex_202001.csv
│   │   ├── Belpex_202002.csv
│   │   └── ...
│   ├── SolarForecast/                  # Zonneproductievoorspellingen en - metingen (JSON & ZIP)
│   │   ├── SolarForecast_2020.zip
│   │   ├── ...
│   │   ├── 2025/
│   │   │   ├── SolarForecast_Elia_20250425.json
│   │   │   └── ...
│   └── WindForecast/                   # Windproductievoorspellingen en - metingen (JSON & ZIP)
│       ├── WindForecast_2020.zip
│       ├── ...
│       ├── 2025/
│       │   ├── WindForecast_Elia_20250425.json
│       │   └── ...
├── Database/
│   └── energie_data.sqlite             # SQLite-database met gestructureerde gegevens
├── Documents/                          # Bijkomende documentatie van het project
│   ├── Solar.json
│   ├── Wind.json
│   ├── Images/                         # Afbeeldingen die gebruikt worden in README.md
│   │   ├── Banner.png
│   │   └── ... 
├── Log/                                # Logbestanden gegenereerd door scripts
│   └── log_YYYY-MM-DD.txt
├── src/                                # Broncode van het project (modulair opgebouwd)
│   ├── __init__.py
│   ├── data_import_tools.py            # Importtools voor verschillende databronnen
│   ├── database_tools.py               # Tools voor interactie met SQLite
│   └── utils/                          # Algemene hulpfuncties en helpers
│       ├── __init__.py
│       ├── constants_inspector.py      # Inspecteert de datakolommen en types
│       ├── decorators.py               # Decorators zoals retry_on_failure
│       ├── dual_logger.py              # Print + logfile logging in één
│       ├── package_tools.py            # Controle en installatie van dependencies
│       └── safe_requests.py            # Veilige HTTP-requests met retries
```

---

## 🌐 Gebruikte bronnen en documentatie

Tijdens de ontwikkeling van dit project werden volgende websites geraadpleegd:

### Data- en API-bronnen
- [Elia Grid Data](https://www.elia.be/nl/grid-data) — overzichtspagina van de Elia-webinterface
- [Elia Open Data](https://opendata.elia.be) — officiële datasets voor zonne- en windenergie
- [Elexys - Spotmarktprijzen](https://my.elexys.be/MarketInformation/SpotBelpex.aspx) — bron van Belpex-prijzen

### Python, tools en documentatie
- [Python Documentation](https://docs.python.org/3/) — officiële Python documentatie
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [webdriver-manager](https://pypi.org/project/webdriver-manager/) — automatische driverinstallatie voor Selenium
- [retrying package](https://pypi.org/project/retrying/) — decorator voor herhaalpogingen
- [PEP 257 – Docstring Conventions](https://peps.python.org/pep-0257/) — richtlijnen voor docstrings
- [Stack Overflow](https://stackoverflow.com/) — veelgebruikte bron voor specifieke codevragen
- [Real Python](https://realpython.com/) — heldere tutorials en uitleg over Python-concepten
- [How to redirect stdout and stderr to logger in Python](https://stackoverflow.com/questions/19425736/how-to-redirect-stdout-and-stderr-to-logger-in-python)

---

## 🤖 Ondersteuning via ChatGPT

Bij het opzetten van dit project werd ChatGPT gebruikt als aanvulling op eigen onderzoek en ontwikkeling.  
De tool diende vooral ter ondersteuning bij:

- Het verfijnen van Python-syntax en foutafhandeling
- Het opzoeken van documentatie en best practices
- Het uitschrijven van bepaalde functies of decoratoren
- Het herformuleren van uitleg of commentaar in de code
- Het structureren van de `README.md` in heldere markdownstijl