"""
Database Tools voor Elia Open Data & Belpex Market Data.

Functies:
- Automatische installatie van vereiste Python-modules.
- Definitie van SQLAlchemy-modellen voor zonne-energie, windenergie en Belpex-prijzen.
- Batchgewijs importeren van JSON- en CSV-data naar een SQLite-database.
- Automatische parsing en verrijking van datetime-informatie.
- Selectief verwerken van datasets via het `to_sql()`-commando.
"""

# database_tools.py

# ----------- Imports -----------

import os
import json
import csv
from datetime import datetime
import re
from toolbox import update_or_install_if_missing

# Controleer en installeer indien nodig de vereiste modules
# Dit is een vangnet als de gebruiker geen rekening houdt met requirements.txt.
update_or_install_if_missing("sqlalchemy","2.0.0")
update_or_install_if_missing("tqdm","4.60.0")

# Pas na installatie importeren
from tqdm import tqdm
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

# Database setup:
# Initialisatie van de SQLite-engine en sessie, met automatische creatie van tabellen op basis van gedefinieerde modellen.
Base = declarative_base()
DB_PATH = os.path.join(os.path.dirname(__file__), "Database", "energie_data.sqlite")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)
session = Session()

# Models
class SolarData(Base):
    """
    SQLAlchemy-model voor het opslaan van zonne-energiegegevens in de database.
    
    Unieke combinatie: datetime + region
    Index op de kolommen year, month, day en hour
    """
    __tablename__ = "solar_data"
    id = Column(Integer, primary_key=True)
    datetime = Column(DateTime, nullable=False)
    resolutioncode = Column(String, info={"beschrijving": "Length of the time interval expressed in compliance with ISO 8601."})
    region = Column(String, info={"beschrijving": "Location of the production unit."})
    measured = Column(Float, info={"beschrijving": "The value running average measured for the reported time interval."})
    mostrecentforecast = Column(Float, info={"beschrijving": "Most recently forecasted volume."})
    mostrecentconfidence10 = Column(Float, 
                                    info={"beschrijving": "Most recently forecasted volume with a probability of less than 10% that a lower volume will be produced."})
    mostrecentconfidence90 = Column(Float, 
                                    info={"beschrijving": "Most recently forecasted volume with a probability of less than 10% that a higher volume will be produced."})
    dayahead11hforecast = Column(Float, info={"beschrijving": "Day-ahead forecasted volume published at 11AM. "})
    dayahead11hconfidence10 = Column(Float, 
                                     info={"beschrijving": "Day-ahead forecasted volume with a probability of less than 10% that a lower volume will be produced, "
                                     "published at 11AM."})
    dayahead11hconfidence90 = Column(Float, 
                                     info={"beschrijving": "Day-ahead forecasted volume with a probability of less than 10% that a higher volume will be produced, "
                                     "published at 11AM."})
    dayaheadforecast = Column(Float, info={"beschrijving": "Day-ahead forecasted volume to be produced."})
    dayaheadconfidence10 = Column(Float, 
                                  info={"beschrijving": "Day-ahead forecasted volume with a probability of less than 10% that a lower volume will be produced."})
    dayaheadconfidence90 = Column(Float, info={"beschrijving": "Forecasted volume with a probability of less than 10% that a higher volume will be produced."})
    weekaheadforecast = Column(Float, info={"beschrijving": "Week-ahead forecasted volume."})
    weekaheadconfidence10 = Column(Float, 
                                   info={"beschrijving": "Week-ahead forecasted volume with a probability of less than 10% that a lower volume will be produced."})
    weekaheadconfidence90 = Column(Float, 
                                   info={"beschrijving": "Week-ahead forecasted volume with a probability of less than 10% that a higher volume will be produced."})
    monitoredcapacity = Column(Float, info={"beschrijving": "Total available production capacity."})
    loadfactor = Column(Float, info={"beschrijving": "The percentage ratio between measured power generation and the total monitored power capacity."})
    day = Column(Integer)
    month = Column(Integer)
    year = Column(Integer)
    hour = Column(Integer)
    minute = Column(Integer)
    week = Column(Integer)
    __table_args__ = (
        UniqueConstraint('datetime', 'region', name='_datetime_region_uc'),
        Index('idx_solar_year', 'year'),
        Index('idx_solar_month', 'month'),
        Index('idx_solar_day', 'day'),
        Index('idx_solar_hour', 'hour'),
    )

class WindData(Base):
    """
    SQLAlchemy-model voor het opslaan van windenergiegegevens in de database.
    
    Unieke combinatie: datetime + region + offshoreonshore + gridconnectiontype
    Index op de kolommen year, month, day en hour
    """
    __tablename__ = "wind_data"
    id = Column(Integer, primary_key=True)
    datetime = Column(DateTime, nullable=False)
    resolutioncode = Column(String, info={"beschrijving": "Length of the time interval expressed in compliance with ISO 8601."})
    offshoreonshore = Column(String, info={"beschrijving": "Indicates whether the wind farm is offshore or onshore."})
    region = Column(String, info={"beschrijving": "Location of the production unit."})
    gridconnectiontype = Column(String, 
                                info={"beschrijving": "Indicates whether the production unit is connected to the Elia grid or to a DSO grid."})
    measured = Column(Float, info={"beschrijving": "The value running average measured for the reported time interval."})
    mostrecentforecast = Column(Float, info={"beschrijving": "Most recently forecasted volume."})
    mostrecentconfidence10 = Column(Float, 
                                    info={"beschrijving": "Most recently forecasted volume with a probability of less than 10% that a lower volume will be produced."})
    mostrecentconfidence90 = Column(Float, 
                                    info={"beschrijving": "Most recently forecasted volume with a probability of less than 10% that a higher volume will be produced."})
    dayahead11hforecast = Column(Float, 
                                 info={"beschrijving": "Day-ahead forecasted volume published at 11AM. "})
    dayahead11hconfidence10 = Column(Float, 
                                     info={"beschrijving": "Day-ahead forecasted volume with a probability of less than 10% that a lower volume will be produced, "
                                     "published at 11AM. "})
    dayahead11hconfidence90 = Column(Float, 
                                     info={"beschrijving": "Day-ahead forecasted volume with a probability of less than 10% that a higher volume will be produced, "
                                     "published at 11AM."})
    dayaheadforecast = Column(Float, 
                              info={"beschrijving": "Day-ahead forecasted volume to be produced."})
    dayaheadconfidence10 = Column(Float, 
                                  info={"beschrijving": "Day-ahead forecasted volume with a probability of less than 10% that a lower volume will be produced."})
    dayaheadconfidence90 = Column(Float, info={"beschrijving": "Forecasted volume with a probability of less than 10% that a higher volume will be produced."})
    weekaheadforecast = Column(Float, info={"beschrijving": "Week-ahead forecasted volume."})
    weekaheadconfidence10 = Column(Float, 
                                   info={"beschrijving": "Week-ahead forecasted volume with a probability of less than 10% that a lower volume will be produced."})
    weekaheadconfidence90 = Column(Float, 
                                   info={"beschrijving": "Week-ahead forecasted volume with a probability of less than 10% that a higher volume will be produced."})
    monitoredcapacity = Column(Float, info={"beschrijving": "Total available production capacity."})
    loadfactor = Column(Float, info={"beschrijving": "The percentage ratio between measured power generation and the total monitored power capacity."})
    decrementalbidid = Column(String, 
                              info={"beschrijving": "Elia has requested the wind park to reduce production below its maximum capacity during this QH. "
                              "This is defined as the amount of Megawatt for a given quarter-hour (QH).Empty: No decremental bids were requested by Elia, "
                              "and the wind park is not required to lower its production during this QH..Note: Elia does not publish any information around "
                              "decremental bids on request of the parks owners themselves."})
    day = Column(Integer)
    month = Column(Integer)
    year = Column(Integer)
    hour = Column(Integer)
    minute = Column(Integer)
    week = Column(Integer)
    __table_args__ = (
        UniqueConstraint('datetime', 'region', 'offshoreonshore', 'gridconnectiontype', name='_datetime_region_offshore_connectiontype_uc'),
        Index('idx_wind_year', 'year'),
        Index('idx_wind_month', 'month'),
        Index('idx_wind_day', 'day'),
        Index('idx_wind_hour', 'hour'),
    )

class BelpexPrice(Base):
    """
    SQLAlchemy-model voor het opslaan van Belpex-elektriciteitsprijzen in de database.
    
    Uniek veld: datetime
    Index op de kolommen year, month, day en hour
    """
    __tablename__ = "belpex_prices"
    id = Column(Integer, primary_key=True)
    datetime = Column(DateTime, nullable=False, unique=True)
    price_eur_per_mwh = Column(Float)
    day = Column(Integer)
    month = Column(Integer)
    year = Column(Integer)
    hour = Column(Integer)
    minute = Column(Integer)
    week = Column(Integer)
    __table_args__ = (
        Index('idx_belpex_year', 'year'),
        Index('idx_belpex_month', 'month'),
        Index('idx_belpex_day', 'day'),
        Index('idx_belpex_hour', 'hour'),
    )
# Creëer tabellen op basis van de klassen die afstammen van de klasse Base
Base.metadata.create_all(engine)


def parse_record(record):
    """
    Zet een record om naar het juiste datetime-formaat en voegt datumcomponenten toe.

    Parameters:
    - record (dict): Een dictionary met ten minste een 'datetime'-sleutel (ISO-formaat).

    Returns:
    - dict | None: Het verrijkte record of None bij een parsing-fout.
    """
    try:
        dt = datetime.fromisoformat(record["datetime"].replace("Z", "+00:00"))
        record["datetime"] = dt
        record["day"] = dt.day
        record["month"] = dt.month
        record["year"] = dt.year
        record["hour"] = dt.hour
        record["minute"] = dt.minute
        record["week"] = dt.isocalendar()[1]
        return record
    except Exception as e:
        return None

def insert_batch(batch, model):
    """
    Voegt een batch records toe aan de database via een `INSERT OR IGNORE` statement.

    Parameters:
    - batch (list[dict]): Een lijst met dictionaries die overeenkomen met de databasekolommen.
    - model (Base): SQLAlchemy-modelklasse waarin de data wordt opgeslagen.

    Returns:
    - int: Aantal succesvol toegevoegde records.
    """
    try:
        stmt = sqlite_insert(model).prefix_with("OR IGNORE").values(batch)
        result = session.execute(stmt)
        session.commit()
        return result.rowcount
    except Exception as e:
        print(f"⚠️ Fout bij batch-insert: {e} — probeer individuele inserts...")
        inserted = 0
        for record in batch:
            try:
                stmt = sqlite_insert(model).prefix_with("OR IGNORE").values(**record)
                result = session.execute(stmt)
                if result.rowcount:
                    inserted += 1
            except Exception as e:
                print(f"⚠️ Individuele insert mislukt: {e}")
        session.commit()
        return inserted

def process_directory(path, model, batch_size=1000):
    """
    Verwerkt alle JSON-bestanden in submappen (per jaar) van een opgegeven map en slaat ze batchgewijs op in de database.
    
    Parameters:
    - path (str): Pad naar de hoofdmap met submappen per jaar.
    - model (Base): SQLAlchemy-model waarin de records moeten worden opgeslagen (bv. SolarData of WindData).
    - batch_size (int): Aantal records per batch-insert (default = 1000).
    """

    for year_dir in sorted(os.listdir(path)):
        inserted_records = 0
        total_records = 0

        year_path = os.path.join(path, year_dir)
        if not os.path.isdir(year_path) or not year_dir.isdigit():
            continue

        all_files = [
            os.path.join(root, f)
            for root, _, files in os.walk(year_path)
            for f in files if f.endswith(".json")
        ]

        batch = []

        for filepath in tqdm(all_files, desc=f"Verwerken van {model.__name__} van het jaar {year_dir}"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    records = json.load(f)
                    if isinstance(records, dict):
                        records = [records]
            except Exception as e:
                print(f"⚠️ Fout bij laden van bestand {filepath}: {e}")
                continue

            for record in records:
                total_records += 1
                parsed = parse_record(record)
                if parsed is None:
                    continue
                batch.append(parsed)

                if len(batch) >= batch_size:
                    inserted_records += insert_batch(batch, model)
                    batch.clear()

        if batch:
            inserted_records += insert_batch(batch, model)

        if inserted_records > 0:
            print(f"✅ {inserted_records} van {total_records} records van het jaar {year_dir} succesvol toegevoegd aan {model.__tablename__} (duplicaten genegeerd).")
        else:
            print(f"✅ Jaar {year_dir} van {model.__name__} is bijgewerkt in de database.")
 
def process_belpex_directory(path, batch_size=1000):
    """
    Doorloopt een directory met CSV-bestanden met Belpex-data en voegt records toe aan de database.

    Parameters:
    - path (str): Pad naar de directory met .csv-bestanden.
    - batch_size (int): Aantal records per batch-insert (default = 1000).
    """
    all_files = [os.path.join(path, f) for f in os.listdir(path) if f.endswith(".csv")]
    inserted_records = 0
    total_records = 0
    batch = []

    for filepath in tqdm(all_files, desc="Verwerken van Belpex-data"):
        with open(filepath, encoding='iso-8859-1') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            for row in reader:
                total_records += 1
                try:
                    dt = datetime.strptime(row["Date"], "%d/%m/%Y %H:%M:%S")
                    euro_raw = row["Euro"]
                    # Verwijder alles behalve cijfers, komma, punt en minteken
                    euro_cleaned = re.sub(r"[^\d,.\-]", "", euro_raw)
                    euro = float(euro_cleaned.replace(",", "."))
                    record = {
                        "datetime": dt,
                        "price_eur_per_mwh": euro,
                        "day": dt.day,
                        "month": dt.month,
                        "year": dt.year,
                        "hour": dt.hour,
                        "minute": dt.minute,
                        "week": dt.isocalendar()[1]
                    }
                    batch.append(record)
                except Exception as e:
                    print(f"⚠️ Fout bij record in {filepath}: {e}")

                if len(batch) >= batch_size:
                    inserted_records += insert_batch(batch, BelpexPrice)
                    batch.clear()

    if batch:
        inserted_records += insert_batch(batch, BelpexPrice)

    if inserted_records > 0:
        print(f"✅ {inserted_records} van {total_records} Belpex-records toegevoegd (duplicaten genegeerd).")
    else:
        print(f"✅ Belpexprijzen zijn bijgewerkt in de database.")

def to_sql(data_type="all"):
    """
    Laadt gegevens vanuit vaste mappenstructuur en schrijft deze naar de SQLite-database,
    afhankelijk van het opgegeven type data.
    Je kunt zelf kiezen welke datasets verwerkt worden:
        - solar: Verwerk zonne-energie (JSON-bestanden)
        - wind: Verwerk windenergie (JSON-bestanden)
        - belpex: Verwerk Belpex-prijzen (CSV-bestanden)
        - all: Verwerk alle types (JSON- en CSV-bestanden)

    Parameters:
    - data_type (str): 'solar', 'wind', 'belpex' of 'all' — bepaalt welke gegevens worden verwerkt.
    """
    BASE_DATA = os.path.join(os.path.dirname(__file__), "data")

    try:
        if data_type in ("solar", "all"):
            try:
                process_directory(os.path.join(BASE_DATA, "SolarForecast"), SolarData)
            except Exception as e:
                print(f"❌ Fout bij verwerken data zonne-energie: {e}")

        if data_type in ("wind", "all"):
            try:
                process_directory(os.path.join(BASE_DATA, "WindForecast"), WindData)
            except Exception as e:
                print(f"❌ Fout bij verwerken data windenergie: {e}")

        if data_type in ("belpex", "all"):
            try:
                process_belpex_directory(os.path.join(BASE_DATA, "Belpex"))
            except Exception as e:
                print(f"❌ Fout bij verwerken data Belpexprijzen: {e}")

    except KeyboardInterrupt:
        print("\n🛑 Script onderbroken door gebruiker.")
    except Exception as e:
        print(f"❌ Onverwachte fout: {e}")
    finally:
        session.close()
        engine.dispose()
        print("\n🔒 Databaseverbinding correct afgesloten.\n")

# --------------- Info over databasemodel ---------------

def alle_modellen_en_kolommen(base_class):
    """
    Genereert een overzicht van alle SQLAlchemy-modellen die afstammen van een gegeven basisklasse,
    samen met hun kolomnamen en optionele beschrijvingen.

    Voor elke subklasse van `base_class` (typisch gemaakt met declarative_base()) wordt gecontroleerd
    of deze daadwerkelijk gekoppeld is aan een database-tabel (via __tablename__ en __table__).
    Vervolgens worden alle kolommen weergegeven, inclusief eventuele beschrijvingen die zijn toegevoegd
    via het `info`-attribuut van SQLAlchemy.

    Parameters:
    - base_class : declarative_base()
        De basisklasse waarvan alle SQLAlchemy-modellen afstammen. 
        Voorbeeld: Base = declarative_base()

    Returns:
    - str
        Een overzichtelijke string die de naam van elk model toont, gevolgd door de lijst van kolommen.
        Indien beschikbaar, wordt ook een korte beschrijving per kolom getoond.
    """
    uitvoer = []

    # Doorloop alle subklassen (modellen) die van base_class zijn afgeleid
    for cls in base_class.__subclasses__():
        # Controleer of het een geldig SQLAlchemy-model is met een gekoppelde tabel
        if hasattr(cls, '__tablename__') and hasattr(cls, '__table__'):
            uitvoer.append(f"Model: {cls.__name__}")

            # Doorloop alle kolommen van de tabel
            for kolom in cls.__table__.columns:
                kolom_naam = kolom.name  # naam van de kolom
                # Haal optionele beschrijving op (indien aanwezig)
                beschrijving = kolom.info.get("beschrijving", None)
                
                # Voeg de kolom toe aan de uitvoer, met of zonder beschrijving
                if beschrijving:
                    uitvoer.append(f"  - {kolom_naam}: {beschrijving}")
                else:
                    uitvoer.append(f"  - {kolom_naam}")

            uitvoer.append("")

    return "\n".join(uitvoer)