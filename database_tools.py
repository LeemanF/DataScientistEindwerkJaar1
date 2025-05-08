"""
Database Tools voor Elia Open Data & Belpex Market Data.

Functies:
- Automatische installatie van vereiste Python-modules.
- Definitie van SQLAlchemy-modellen voor zonne-energie, windenergie en Belpex-prijzen.
- Batchgewijs importeren van JSON- en CSV-data naar een SQLite-database.
- Automatische parsing en verrijking van datetime-informatie.
- Selectief verwerken van datasets via het `to_sql()`-commando.
"""

# ----------- Imports -----------

import os
import json
import subprocess
import sys
import csv
from datetime import datetime
import re

# Automatische installatie van noodzakelijke modules

def install_if_missing(package_name):
    """
    Controleert of een Python-module is geïnstalleerd en installeert deze indien nodig via pip.

    Parameters:
    package_name (str): De naam van de te installeren module.
    """
    try:
        __import__(package_name)
    except ImportError:
        print(f"Module '{package_name}' niet gevonden. Bezig met installeren...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        print(f"✅ Module '{package_name}' geïnstalleerd.")

# Controleer en installeer de vereiste modules
install_if_missing("sqlalchemy")
install_if_missing("tqdm")

# Pas na installatie importeren
from tqdm import tqdm
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, UniqueConstraint
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
    """
    __tablename__ = "solar_data"
    id = Column(Integer, primary_key=True)
    datetime = Column(DateTime, nullable=False)
    resolutioncode = Column(String)
    region = Column(String)
    measured = Column(Float)
    mostrecentforecast = Column(Float)
    mostrecentconfidence10 = Column(Float)
    mostrecentconfidence90 = Column(Float)
    dayahead11hforecast = Column(Float)
    dayahead11hconfidence10 = Column(Float)
    dayahead11hconfidence90 = Column(Float)
    dayaheadforecast = Column(Float)
    dayaheadconfidence10 = Column(Float)
    dayaheadconfidence90 = Column(Float)
    weekaheadforecast = Column(Float)
    weekaheadconfidence10 = Column(Float)
    weekaheadconfidence90 = Column(Float)
    monitoredcapacity = Column(Float)
    loadfactor = Column(Float)
    day = Column(Integer)
    month = Column(Integer)
    year = Column(Integer)
    hour = Column(Integer)
    minute = Column(Integer)
    week = Column(Integer)
    __table_args__ = (
        UniqueConstraint('datetime', 'region', name='_datetime_region_uc'),
    )

class WindData(Base):
    """
    SQLAlchemy-model voor het opslaan van windenergiegegevens in de database.
    
    Unieke combinatie: datetime + region + offshoreonshore + gridconnectiontype
    """
    __tablename__ = "wind_data"
    id = Column(Integer, primary_key=True)
    datetime = Column(DateTime, nullable=False)
    resolutioncode = Column(String)
    offshoreonshore = Column(String)
    region = Column(String)
    gridconnectiontype = Column(String)
    measured = Column(Float)
    mostrecentforecast = Column(Float)
    mostrecentconfidence10 = Column(Float)
    mostrecentconfidence90 = Column(Float)
    dayahead11hforecast = Column(Float)
    dayahead11hconfidence10 = Column(Float)
    dayahead11hconfidence90 = Column(Float)
    dayaheadforecast = Column(Float)
    dayaheadconfidence10 = Column(Float)
    dayaheadconfidence90 = Column(Float)
    weekaheadforecast = Column(Float)
    weekaheadconfidence10 = Column(Float)
    weekaheadconfidence90 = Column(Float)
    monitoredcapacity = Column(Float)
    loadfactor = Column(Float)
    decrementalbidid = Column(String)
    day = Column(Integer)
    month = Column(Integer)
    year = Column(Integer)
    hour = Column(Integer)
    minute = Column(Integer)
    week = Column(Integer)
    __table_args__ = (
        UniqueConstraint('datetime', 'region', 'offshoreonshore', 'gridconnectiontype', name='_datetime_region_offshore_connectiontype_uc'),
    )

class BelpexPrice(Base):
    """
    SQLAlchemy-model voor het opslaan van Belpex-elektriciteitsprijzen in de database.
    
    Uniek veld: datetime
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

# Creëer tabellen
Base.metadata.create_all(engine)

def parse_record(record):
    """
    Zet een record om naar het juiste datetime-formaat en voegt datumcomponenten toe.

    Parameters:
    record (dict): Een dictionary met ten minste een 'datetime'-sleutel (ISO-formaat).

    Returns:
    dict | None: Het verrijkte record of None bij een parsing-fout.
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
    batch (list[dict]): Een lijst met dictionaries die overeenkomen met de databasekolommen.
    model (Base): SQLAlchemy-modelklasse waarin de data wordt opgeslagen.

    Returns:
    int: Aantal succesvol toegevoegde records.
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
        path (str): Pad naar de hoofdmap met submappen per jaar.
        model (Base): SQLAlchemy-model waarin de records moeten worden opgeslagen (bv. SolarData of WindData).
        batch_size (int): Aantal records per batch-insert (default = 1000).
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

        for filepath in tqdm(all_files, desc=f"Verwerken van {os.path.basename(path)} voor het jaar {year_dir}"):
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
            print(f"✅ Jaar {year_dir} van {model.__tablename__} is up to date.")
 
def process_belpex_directory(path, batch_size=1000):
    """
    Doorloopt een directory met CSV-bestanden met Belpex-data en voegt records toe aan de database.

    Parameters:
    path (str): Pad naar de directory met .csv-bestanden.
    batch_size (int): Aantal records per batch-insert (default = 1000).
    """
    all_files = [os.path.join(path, f) for f in os.listdir(path) if f.endswith(".csv")]
    inserted_records = 0
    total_records = 0
    batch = []

    for filepath in tqdm(all_files, desc="Belpex-data verwerken"):
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
        print(f"✅ Belpexprijzen zijn up to date.")

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
        data_type (str): 'solar', 'wind', 'belpex' of 'all' — bepaalt welke gegevens worden verwerkt.
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