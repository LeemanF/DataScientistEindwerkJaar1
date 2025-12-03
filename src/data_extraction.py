"""
data_extraction.py

Data Extractie voor Elia Open Data & Belpex Market Data.

Functies:
- Ophalen van maandelijkse data uit de SQLite-database:
  - Windproductie (onshore en offshore)
  - Zonne-energieproductie
  - Belpex-spotprijzen
- Automatische omzetting van waarden naar GWh en EUR/MWh.
- Optionele pivotering van de data:
  - Rijen = jaar (en offshore/onshore voor wind)
  - Kolommen = maandnamen (taal instelbaar via `localization.py`)
- Ondersteuning voor meertalige maandnamen (NL/FR/EN, kort of volledig).
- Gescheiden functies voor ruwe dataframes en geaggregeerde pivot-tabellen.
- Compatibel met visualisatie- en analysetools in `visualisation_tools.py`.
"""

# -------------------------------------------------------------------
# 📦 Imports en modulecontrole
# -------------------------------------------------------------------

import sqlite3
import os
from typing import Literal, Union, List
from settings import DB_FILE
from datetime import datetime
from src.utils.localization import get_month_name, get_weekday_name, LangCode, TRANSLATIONS
from src.utils.package_tools import update_or_install_if_missing
from src.data_import_tools import unzip_all_forecast_zips
from src.database_tools import to_sql

# Controleer en installeer indien nodig de vereiste modules
# Dit is een vangnet als de gebruiker geen rekening houdt met requirements.txt.
update_or_install_if_missing("pandas","1.3.0")

# Pas na installatie importeren
import pandas as pd


# -------------------------------------------------------------------
# 🔧 Database-initiatie bij import
# -------------------------------------------------------------------

def _initialize_database():
    """
    Controleer of de SQLite-database bestaat en minstens 1 MB groot is. 
    Zo niet, unzip bestanden en bouw de database op.
    """
    if not os.path.exists(DB_FILE) or os.path.getsize(DB_FILE) < 1_000_000:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - ℹ️ Database '{os.path.basename(DB_FILE)}' bestaat niet. Initialisatie gestart...")

        # Unzip alle benodigde bestanden
        try:
            unzip_all_forecast_zips()
        except Exception as e:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - ❌ Fout bij unzippen: {e}")
            return False

        # Maak en vul de database
        try:
            to_sql()
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - ✅ Database succesvol aangemaakt en gevuld.")
        except Exception as e:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - ❌ Fout bij database-opbouw: {e}")
            return False

    return True


# Bij import meteen controleren
_DB_READY = _initialize_database()
if not _DB_READY:
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - ⚠️  Database initialisatie mislukt. Data-extractie kan problemen geven.")


# -------------------------------------------------------------------
# 🧩 Hulpfuncties
# -------------------------------------------------------------------

def make_pivot(
    df: pd.DataFrame,
    index_cols: Union[str, List[str]],
    value_col: str,
    aggfunc: str = "sum",
    lang: LangCode = "nl",
    short: bool = True,
    include_totals: bool = False,
    fill_value: Union[int, float, None] = None
) -> pd.DataFrame:
    """
    Interne hulpfunctie om een DataFrame te pivoteren op maand en te vertalen naar maandnamen.

    Optioneel kan een kolomtotaal worden toegevoegd en lege cellen worden opgevuld.

    Args:
        df (pd.DataFrame): Input DataFrame met kolom 'month'.
        index_cols (str | list[str]): Kolom of lijst van kolommen voor de rijen.
        value_col (str): Waardekolom.
        aggfunc (str): Aggregatiefunctie ('sum' of 'mean').
        lang (LangCode): 'nl', 'fr' of 'en'.
        short (bool): korte of volledige maandnaam.
        include_totals (bool): Indien True wordt een extra kolom 'Totaal' toegevoegd met de som van de maanden.
        fill_value (int | float | None): Waarde waarmee lege cellen worden opgevuld. Default = None.

    Returns:
        pd.DataFrame: Geaggregeerde pivot-tabel met maandnamen als kolommen,
                      eventueel aangevuld met een 'Totaal'-kolom.
    """
    pivot = df.pivot_table(
        index=index_cols,
        columns="month",
        values=value_col,
        aggfunc=aggfunc,
        fill_value=fill_value
    )
    
    # Kolomnamen omzetten naar maandnamen
    pivot.columns = [get_month_name(m, lang=lang, short=short) for m in pivot.columns]

    # Indexnaam vertalen indien het een enkele kolom is
    if isinstance(index_cols, str) and index_cols.lower() == "year":
        pivot.index.name = TRANSLATIONS["year"].get(lang, TRANSLATIONS["year"]["nl"])

    # Kolomtotaal toevoegen indien gevraagd
    if include_totals:
        pivot[TRANSLATIONS["totals"][lang]] = pivot.sum(axis=1)

    return pivot


def execute_query(query: str, db_file: str = DB_FILE) -> pd.DataFrame:
    """
    Voert een SQL-query uit op de opgegeven SQLite-database en retourneert het resultaat als DataFrame.

    Deze functie wordt gebruikt als generieke helper voor het uitvoeren van leesqueries
    in alle datafuncties (zoals wind-, zonne- en Belpex-data). 
    De functie maakt automatisch een verbinding met de database, voert de query uit,
    sluit de connectie en logt eventuele fouten via console-uitvoer.

    Args:
        query (str): 
            De SQL-query die moet worden uitgevoerd.
        db_file (str, optional): 
            Pad naar het SQLite-databasebestand. 
            Standaard wordt `DB_FILE` gebruikt.

    Returns:
        pd.DataFrame: 
            Een DataFrame met het resultaat van de query. 
            Indien de query mislukt, wordt None geretourneerd.

    Raises:
        KeyboardInterrupt: 
            Wanneer de gebruiker het script handmatig onderbreekt (Ctrl+C).
    """
    try:
        with sqlite3.connect(db_file) as conn:
            return pd.read_sql_query(query, conn)
    except KeyboardInterrupt:
        print(f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 🛑 Script onderbroken door gebruiker.")
    except Exception as e:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - ❌ Onverwachte fout: {e}")


# -------------------------------------------------------------------
# 🌬️ WINDENERGIE
# -------------------------------------------------------------------

def get_wind_dataframe_split() -> pd.DataFrame:
    """
    Haalt de maandelijkse windproductie op, opgesplitst in offshore en onshore.

    De data worden uit de database geladen, omgerekend van kwartierwaarden naar
    GWh per maand, en per type wind (offshore/onshore) geaggregeerd.

    Returns:
        pd.DataFrame: met kolommen ['offshoreonshore', 'year', 'month', 'total_GWh']
                      waarbij elke rij één maand voor één type (offshore/onshore) voorstelt.
    """
    query = """
        SELECT offshoreonshore, year, month, SUM(measured)/4/1000.0 AS total_GWh
        FROM tbl_wind_data
        GROUP BY offshoreonshore, year, month
        ORDER BY offshoreonshore, year, month
    """
    return execute_query(query)


def get_wind_pivot_split(
    lang: LangCode = "nl",
    short: bool = True,
    include_totals: bool = False
) -> pd.DataFrame:
    """
    Maakt een pivot-tabel met maandelijkse windproductie, opgesplitst in
    offshore en onshore.

    Rijen stellen (offshoreonshore, jaar) voor; kolommen zijn maandnamen
    in de gewenste taal (korte of volledige naam).

    Optioneel kan een kolomtotaal worden toegevoegd.

    Args:
        lang (LangCode): taalcode ('nl', 'fr' of 'en')
        short (bool): gebruik korte maandnamen (True) of volledige (False)
        include_totals (bool): Indien True wordt een extra kolom 'Totaal' toegevoegd
                               met de som van alle maanden per rij.

    Returns:
        pd.DataFrame: pivot-tabel met windproductie in GWh per maand,
                      eventueel aangevuld met een 'Totaal'-kolom.
    """
    df = get_wind_dataframe_split()
    return make_pivot(
        df,
        index_cols=["offshoreonshore", "year"],
        value_col="total_GWh",
        aggfunc="sum",
        lang=lang,
        short=short,
        include_totals=include_totals
    )


def get_wind_dataframe_total() -> pd.DataFrame:
    """
    Haalt de totale maandelijkse windproductie (onshore + offshore) op uit de database.

    De data worden omgerekend naar GWh en geaggregeerd per jaar en maand.

    Returns:
        pd.DataFrame: met kolommen ['year', 'month', 'total_GWh']
                      waarbij elke rij één maandelijkse totaalwaarde voorstelt.
    """
    query = """
        SELECT year, month, SUM(measured)/4/1000.0 AS total_GWh
        FROM tbl_wind_data
        GROUP BY year, month
        ORDER BY year, month
    """
    return execute_query(query)


def get_wind_pivot_total(
    lang: LangCode = "nl",
    short: bool = True,
    include_totals: bool = False
) -> pd.DataFrame:
    """
    Maakt een pivot-tabel met de totale windproductie (onshore + offshore samen).

    Rijen stellen jaren voor; kolommen zijn maandnamen in de opgegeven taal
    (kort of volledig). De waarden zijn totale maandelijkse producties in GWh.

    Optioneel kan een kolomtotaal worden toegevoegd.

    Args:
        lang (LangCode): taalcode ('nl', 'fr' of 'en')
        short (bool): gebruik korte maandnamen (True) of volledige (False)
        include_totals (bool): Indien True wordt een extra kolom 'Totaal' toegevoegd
                               met de som van alle maanden per jaar.

    Returns:
        pd.DataFrame: pivot-tabel met totale windproductie (GWh) per maand,
                      eventueel aangevuld met een 'Totaal'-kolom.
    """
    df = get_wind_dataframe_total()
    return make_pivot(
        df,
        index_cols="year",
        value_col="total_GWh",
        aggfunc="sum",
        lang=lang,
        short=short,
        include_totals=include_totals
    )


# -------------------------------------------------------------------
# ☀️ ZONNE-ENERGIE
# -------------------------------------------------------------------

def get_solar_dataframe() -> pd.DataFrame:
    """
    Haalt maandelijkse zonne-energieproductie op uit de database.
    Omgezet naar GWh, zonder pivotering.

    Returns:
        pd.DataFrame: Kolommen = ['year', 'month', 'total_GWh']
    """
    query = """
        SELECT year, month, SUM(measured)/4/1000.0 AS total_GWh
        FROM tbl_solar_data
        GROUP BY year, month
        ORDER BY year, month
    """
    return execute_query(query)


def get_solar_pivot(
    lang: LangCode = "nl",
    short: bool = True,
    include_totals: bool = False
) -> pd.DataFrame:
    """
    Maakt een pivot-tabel voor zonne-energieproductie.

    Rijen stellen jaren voor; kolommen zijn maandnamen in de opgegeven taal
    (kort of volledig). De waarden zijn totale maandelijkse producties in GWh.

    Optioneel kan een kolomtotaal worden toegevoegd.

    Args:
        lang (LangCode): taalcode ('nl', 'fr' of 'en')
        short (bool): gebruik korte maandnamen (True) of volledige (False)
        include_totals (bool): Indien True wordt een extra kolom 'Totaal' toegevoegd
                               met de som van alle maanden per jaar.

    Returns:
        pd.DataFrame: pivot-tabel met zonne-energieproductie (GWh) per maand,
                      eventueel aangevuld met een 'Totaal'-kolom.
    """
    df = get_solar_dataframe()
    return make_pivot(
        df,
        index_cols="year",
        value_col="total_GWh",
        aggfunc="sum",
        lang=lang,
        short=short,
        include_totals=include_totals
    )


# -------------------------------------------------------------------
# ⚡ BELPEX-PRIJZEN (maandbasis)
# -------------------------------------------------------------------

def get_belpex_dataframe() -> pd.DataFrame:
    """
    Haalt maandelijkse Belpex-spotprijzen op uit de database.

    Returns:
        pd.DataFrame: Kolommen = ['year', 'month', 'avg_price']
    """
    query = """
        SELECT year, month, AVG(price_eur_per_MWh) AS avg_price
        FROM tbl_belpex_prices
        GROUP BY year, month
        ORDER BY year, month
    """
    return execute_query(query)


def get_belpex_pivot(
    lang: LangCode = "nl",
    short: bool = True,
    include_totals: bool = False
) -> pd.DataFrame:
    """
    Maakt een pivot-tabel voor Belpex-prijzen.

    Rijen stellen jaren voor; kolommen zijn maandnamen in de opgegeven taal
    (kort of volledig). De waarden zijn gemiddelde maandprijzen in EUR/MWh.

    Optioneel kan een kolomtotaal worden toegevoegd.

    Args:
        lang (LangCode): taalcode ('nl', 'fr' of 'en')
        short (bool): gebruik korte maandnamen (True) of volledige (False)
        include_totals (bool): Indien True wordt een extra kolom 'Totaal' toegevoegd
                               met de gemiddelde prijs van alle maanden per jaar.

    Returns:
        pd.DataFrame: pivot-tabel met Belpex-prijzen per maand,
                      eventueel aangevuld met een 'Totaal'-kolom.
    """
    df = get_belpex_dataframe()
    return make_pivot(
        df,
        index_cols="year",
        value_col="avg_price",
        aggfunc="mean",
        lang=lang,
        short=short,
        include_totals=include_totals
    )


# -------------------------------------------------------------------
# ⚡ BELPEX-PRIJZEN (uurbasis)
# -------------------------------------------------------------------

def get_belpex_hourly_dataframe() -> pd.DataFrame:
    query = """
        SELECT 
            month,
            weekday,
            hour,
            AVG(price_eur_per_MWh) AS avg_price
        FROM tbl_belpex_prices
        GROUP BY month, weekday, hour
        ORDER BY month, weekday, hour
    """
    return execute_query(query)


def get_belpex_hourly_pivot(
    group_by: Literal["weekday", "month"] = "weekday",
    lang: LangCode = "nl",
    short: bool = True
) -> pd.DataFrame:
    """
    Maakt een pivot-tabel met gemiddelde Belpex-prijzen per uur,
    gegroepeerd per weekdag of per maand.

    De namen van weekdagen of maanden worden vertaald op basis van de
    opgegeven taal en notatie (kort of volledig).

    Args:
        group_by (Literal["weekday", "month"]): Kies 'weekday' voor een overzicht
            per weekdag, of 'month' voor een overzicht per maand.
        lang (LangCode): 'nl', 'fr' of 'en'
        short (bool): gebruik korte namen (True) of volledige (False)

    Returns:
        pd.DataFrame: pivot-tabel met:
            - rijen = uren (0-23)
            - kolommen = weekdagen of maanden
            - waarden = gemiddelde prijs (EUR/MWh)
    """
    # Data ophalen
    df = get_belpex_hourly_dataframe()

    if df is None or df.empty:
        print("⚠️ Geen resultaten gevonden voor Belpex-prijzen per uur.")
        return pd.DataFrame()

    # Namen toevoegen volgens gekozen groepering
    if group_by == "weekday":
        df["label"] = df["weekday"].apply(lambda w: get_weekday_name(w, lang=lang, short=short))
        ordered_labels = [get_weekday_name(i, lang=lang, short=short) for i in range(1,8)]
        column_label = TRANSLATIONS["weekday"][lang]
    elif group_by == "month":
        df["label"] = df["month"].apply(lambda m: get_month_name(m, lang=lang, short=short))
        ordered_labels = [get_month_name(i, lang=lang, short=short) for i in range(1, 13)]
        column_label = TRANSLATIONS["month"][lang]
    else:
        raise ValueError("❌ Ongeldige waarde voor 'group_by'. Gebruik 'weekday' of 'month'.")

    # Correcte volgorde behouden (niet alfabetisch)
    df["label"] = pd.Categorical(df["label"], categories=ordered_labels, ordered=True)

    # Pivot-tabel bouwen
    pivot = df.pivot_table(
        index="hour",
        columns="label",
        values="avg_price",
        aggfunc="mean",
        fill_value=0,
        observed=False  # ✅ voorkomt FutureWarning
    )

    # Index- en kolomnamen instellen voor nette output
    pivot.index.name = TRANSLATIONS["hour"][lang]
    pivot.columns.name = column_label

    return pivot


# -------------------------------------------------------------------
# 🔗 GECOMBINEERDE DATA (Wind + Zon + Belpex)
# -------------------------------------------------------------------

def get_combined_dataframe(fillna: bool = False, lang: LangCode = "nl", short: bool = True) -> pd.DataFrame:
    """
    Combineert wind-, zonne-energie- en Belpex-data in één DataFrame.

    Haalt maandelijkse waarden op uit de database, hernoemt kolommen voor
    consistentie en voegt alles samen op jaar en maand. Verrijkt de dataset
    met een periodekolom ('period', formaat YYYY-MM) en een maandnaamkolom
    ('month_name') in de gewenste taal en notatie.

    Args:
        fillna (bool, optional): 
            Indien True worden ontbrekende waarden (NaN) vervangen door 0.
            Standaard is False, zodat de ruwe data behouden blijven.
        lang (LangCode, optional): 
            Taalcode voor maandnamen ('nl', 'fr', of 'en'). 
            Standaard is 'nl'.
        short (bool, optional): 
            Gebruik korte maandnamen (True) of volledige maandnamen (False).
            Standaard is True.

    Returns:
        pd.DataFrame: DataFrame met kolommen:
            ['year', 'month', 'wind_GWh', 'solar_GWh', 
             'belpex_EUR_per_MWh', 'period', 'month_name']
    """
    # Data ophalen
    df_wind = get_wind_dataframe_total()
    df_solar = get_solar_dataframe()
    df_belpex = get_belpex_dataframe()

    # Kolomnamen hernoemen voor duidelijkheid
    df_wind = df_wind.rename(columns={'total_GWh': 'wind_GWh'})
    df_solar = df_solar.rename(columns={'total_GWh': 'solar_GWh'})
    df_belpex = df_belpex.rename(columns={'avg_price': 'belpex_EUR_per_MWh'})

    # Datasets samenvoegen op jaar en maand
    df_compare = (
        df_wind.merge(df_solar, on=['year', 'month'], how='outer')
               .merge(df_belpex, on=['year', 'month'], how='outer')
    )

    # Chronologische volgorde garanderen
    df_compare = df_compare.sort_values(["year", "month"])

    # Periode-label toevoegen (YYYY-MM)
    df_compare["period"] = (
        df_compare["year"].astype(str)
        + "-"
        + df_compare["month"].astype(str).str.zfill(2)
    )

    # Maandnamen toevoegen
    df_compare["month_name"] = df_compare["month"].apply(
        lambda m: get_month_name(m, lang=lang, short=short)
    )

    # Ontbrekende waarden vervangen indien gevraagd
    if fillna:
        df_compare = df_compare.fillna(0)

    return df_compare


# -------------------------------------------------------------------
# 📉 BELPEX – NEGATIEVE PRIJZEN
# -------------------------------------------------------------------

def get_negative_price_counts_pivot(
    lang: LangCode = "nl",
    short: bool = True,
    include_totals: bool = False,
    cumulative: bool = False
) -> pd.DataFrame:
    """
    Maakt een pivot-tabel met het aantal negatieve Belpex-prijzen per maand en per jaar.

    De maandnamen worden vertaald naar de opgegeven taal en notatie
    (kort of volledig). Optioneel kan een kolomtotaal worden toegevoegd.
    Optioneel kan een cumulatief totaal per jaar worden berekend.

    Args:
        lang (LangCode): 'nl', 'fr' of 'en'
        short (bool): gebruik korte maandnamen (True) of volledige (False)
        include_totals (bool): Indien True wordt een extra kolom 'Totaal' toegevoegd
                               met het totaal aantal negatieve prijzen per jaar.
        cumulative (bool): Indien True worden de aantallen cumulatief opgeteld over de maanden.

    Returns:
        pd.DataFrame: pivot-tabel met kolommen = maandnamen (+ 'Totaal' indien gevraagd)
    """
    query = """
        SELECT 
            year,
            month,
            COUNT(price_belpex_MWh) AS count_neg
        FROM v_belpex
        WHERE price_belpex_MWh < 0
        GROUP BY year, month
        ORDER BY year, month
    """

    df = execute_query(query)

    if df is None or df.empty:
        print("⚠️ Geen resultaten gevonden voor negatieve prijzen.")
        return pd.DataFrame()

    # Pivot: jaren als rijen, maanden als kolommen
    pivot = make_pivot(
        df,
        index_cols="year",
        value_col="count_neg",
        aggfunc="sum",
        lang=lang,
        short=short,
        include_totals=include_totals,
        fill_value=0
    )

    # Cumulatief maken indien gevraagd
    if cumulative:
        pivot = pivot.cumsum(axis=1)

    # Indexnaam vertalen
    pivot.index.name = TRANSLATIONS["year"].get(lang, TRANSLATIONS["year"]["nl"])

    return pivot


# -------------------------------------------------------------------
# 🌍 PIEK HERNIEUWBARE PRODUCTIE (Wind + Zon)
# -------------------------------------------------------------------

def get_peak_renewable_production(lang: LangCode = "nl") -> pd.DataFrame:
    """
    Haalt de jaarlijkse piekproductie van hernieuwbare energie (wind + zon) op uit de database.

    De query combineert wind- en zonneproductie per kwartier, berekent de som per timestamp
    en bepaalt via een windowfunctie (RANK) het hoogste productiemoment per jaar.
    Het resultaat bevat voor elk jaar de datum, het tijdstip en het piekvermogen in MW.

    De kolomnamen worden vertaald naar de opgegeven taal.

    Args:
        lang (LangCode): 'nl', 'fr' of 'en'

    Returns:
        pd.DataFrame: met kolommen:
            ['datum', 'tijd', 'Piek productie hernieuwbaar in MW']  # afhankelijk van taal
    """
    query = """
        SELECT
            DATE(datetime) AS date,
            TIME(datetime) AS time,
            Renewable_MW AS "renewable_peak"
        FROM(
            SELECT
                w.year,
                w.datetime,
                CAST((w.measured_wind_MW + s.measured_solar_MW) AS INTEGER) AS Renewable_MW,
                RANK() OVER (
                    PARTITION BY w.year 
                    ORDER BY (w.measured_wind_MW + s.measured_solar_MW) DESC
                ) AS volgorde
            FROM 
                v_solar s
                LEFT JOIN v_wind w ON s.datetime = w.datetime
            ORDER BY Renewable_MW DESC
        )
        WHERE volgorde = 1
        ORDER BY year
    """

    df = execute_query(query)

    if df is None or df.empty:
        print("⚠️ Geen resultaten gevonden voor piekproductie hernieuwbaar.")
        return pd.DataFrame()

    df = df.rename(columns={
            "date": TRANSLATIONS["date"][lang],
            "time": TRANSLATIONS["time"][lang],
            "renewable_peak": TRANSLATIONS["labels"]["renewable_peak"][lang],
        })

    return df
