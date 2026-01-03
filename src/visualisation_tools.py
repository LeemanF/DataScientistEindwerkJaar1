"""
visualisation_tools.py

Visualisatietools voor hernieuwbare energie en Belpex-prijzen.

Deze module bevat functies voor het visualiseren van wind- en zonne-energieproductie
samen met Belpex spotmarktprijzen. Ondersteuning voor meerdere talen (NL/FR/EN)
en korte/volledige maandnamen is inbegrepen.

Functies:

Windproductie:
- plot_wind_split(): maandelijkse windproductie per categorie (offshore/onshore).
- plot_wind_total(): totale maandelijkse windproductie, keuze tussen layout per jaar of per maand.

Zonne-energie:
- plot_solar(): maandelijkse zonne-energieproductie, keuze tussen layout per jaar of per maand.
- plot_solar_interactive(): interactieve versie van plot_solar() met Plotly.

Belpex-prijzen:
- plot_belpex_heatmap(): heatmap van gemiddelde Belpex-prijzen per maand en jaar.
- plot_belpex_hourly(): gemiddelde Belpex-prijzen per uur, gegroepeerd per weekdag of maand.
- plot_negative_price_counts_cumulative(): cumulatief aantal uren met negatieve prijzen per maand/jaar.
- plot_negative_price_counts_bubble(): aantal uren met negatieve prijzen als bubble chart.

Gecombineerde visualisaties:
- plot_combined(): gecombineerde weergave van wind, zon en Belpex-prijs in één grafiek.

Algemene kenmerken:
- Ondersteuning voor meertalige labels (nl/fr/en) en korte/volledige maandnamen.
- Alle grafieken worden direct weergegeven via matplotlib/seaborn.
- Indien geen data beschikbaar, geeft de functie een waarschuwing en genereert
  geen grafiek.
"""
from src.data_extraction import (
    get_wind_pivot_split,
    get_wind_pivot_total,
    get_solar_pivot,
    get_solar_dataframe,
    get_belpex_pivot,
    get_belpex_hourly_pivot,
    get_negative_price_counts_pivot,
    get_combined_dataframe
)
from src.utils.localization import TRANSLATIONS, LangCode, get_month_name
from typing import Literal
from src.utils.package_tools import update_or_install_if_missing

# Controleer en installeer indien nodig de vereiste modules
# Dit is een vangnet als de gebruiker geen rekening houdt met requirements.txt.
update_or_install_if_missing("matplotlib","3.5.0")
update_or_install_if_missing("seaborn","0.11.0")
update_or_install_if_missing("pandas","1.3.0")
update_or_install_if_missing("plotly","5.0")

# Pas na eventuele installatie importeren
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# -------------------------------------------------------------------
# 🌬️ Windproductie - opsplitsing Offshore/Onshore
# -------------------------------------------------------------------
def plot_wind_split(lang: LangCode = "nl", short: bool = True) -> None:
    """
    Visualiseert opgesplitste windproductie per categorie (onshore/offshore),
    waarbij voor elke categorie een afzonderlijke stacked bar chart wordt
    weergegeven.

    Elke categorie toont de maandelijkse windproductie als gestapelde balken
    (GWh), met de jaren op de X-as en maandsegmenten boven elkaar. Voor elke
    categorie wordt automatisch een aparte grafiek gegenereerd.

    Args:
        lang (LangCode, optional):
            Taalcode voor labels en maandnamen ('nl', 'fr' of 'en').
            Bepaalt ook de titelvertalingen. Standaard is 'nl'.

        short (bool, optional):
            Gebruik korte maandnamen (True) of volledige maandnamen (False).
            Standaard is True.

    Returns:
        None:
            De functie toont één grafiek per windcategorie via matplotlib
            en geeft geen waarde terug.
    """
    pivot_wind = get_wind_pivot_split(lang=lang, short=short)

    if pivot_wind.empty:
        print(TRANSLATIONS["errors"]["no_data_to_plot"][lang])
        return
 
    for category in pivot_wind.index.get_level_values(0).unique():
        data = pivot_wind.loc[category]
        data.plot(kind='bar', stacked=True, figsize=(12,6), colormap='viridis')
        plt.title(f'{TRANSLATIONS["titles"]["wind_split"][lang]} - {category}')
        plt.xlabel(TRANSLATIONS["year"][lang])
        plt.ylabel("GWh")
        plt.legend(title=TRANSLATIONS["month"][lang], bbox_to_anchor=(1.05,1), loc='upper left')
        plt.tight_layout()
        plt.show()

# -------------------------------------------------------------------
# 🌬️ Windproductie - totaal
# -------------------------------------------------------------------
def plot_wind_total(
        lang: LangCode = "nl",
        short: bool = True,
        layout: Literal["years", "months"] = "years"
    ) -> None:
    """
    Visualiseert de totale maandelijkse windproductie, met keuze tussen twee
    weergavelayouts: jaren op de X-as (stacked) of maanden op de X-as
    (gegroepeerde staafjes per jaar).

    Bij layout='years' worden de jaren op de X-as geplaatst en worden de
    maanden gestapeld weergegeven (GWh). Bij layout='months' worden de
    maandnamen op de X-as getoond en worden de verschillende jaren als
    afzonderlijke balken naast elkaar geplot.

    Args:
        lang (LangCode, optional):
            Taalcode voor labels en maandnamen ('nl', 'fr' of 'en').
            Bepaalt ook de titelvertalingen. Standaard is 'nl'.

        short (bool, optional):
            Gebruik korte maandnamen (True) of volledige maandnamen (False).
            Standaard is True.

        layout (Literal["years", "months"], optional):
            Selecteert de grafiekindeling:
            - "years": jaren op de X-as, maanden stacked.
            - "months": maanden op de X-as, jaren gegroepeerd.
            Standaard is "years".

    Returns:
        None:
            De functie toont de grafiek rechtstreeks via matplotlib
            en geeft geen waarde terug.
    """
    pivot_wind_total = get_wind_pivot_total(lang=lang, short=short)

    if pivot_wind_total.empty:
        print(TRANSLATIONS["errors"]["no_data_to_plot"][lang])
        return

    if layout == "years":
        # Jaren op de x-as, maanden stacked
        ax = pivot_wind_total.plot(
            kind='bar',
            stacked=True,
            figsize=(12, 6),
            colormap='viridis'
        )
        xlabel = TRANSLATIONS["year"][lang]
        legend_title = TRANSLATIONS["month"][lang]

    elif layout == "months":
        # Maanden op de x-as, jaren naast elkaar
        df = pivot_wind_total.T
        ax = df.plot(
            kind='bar',
            figsize=(12, 6)
        )
        xlabel = TRANSLATIONS["month"][lang]
        legend_title = TRANSLATIONS["year"][lang]

    else:
        raise ValueError("layout must be 'years' or 'months'")

    ax.set_title(TRANSLATIONS["titles"]["wind_total"][lang])
    ax.set_xlabel(xlabel)
    ax.set_ylabel("GWh")

    ax.legend(
        title=legend_title,
        bbox_to_anchor=(1.05, 1),
        loc='upper left'
    )

    plt.tight_layout()
    plt.show()


# -------------------------------------------------------------------
# ☀️ Zonne-energie
# -------------------------------------------------------------------
def plot_solar(
        lang: LangCode = "nl",
        short: bool = True,
        layout: Literal["years", "months", "cumulative", "cumulative_zone", "cumulative_zone"] = "years"
    ) -> None:
    """
    Visualiseert de maandelijkse zonne-energieproductie, met keuze tussen vier
    weergavelayouts: gestapelde balken per jaar, gegroepeerde balken per maand,
    cumulatieve lijndiagrammen per jaar of een cumulatieve zoneweergave met het
    meest recente jaar als lijn.

    Bij layout='years' worden de jaren op de X-as geplaatst en worden de maanden
    als gestapelde balken weergegeven (GWh).  
    Bij layout='months' verschijnen de maandnamen op de X-as en worden de
    productiegegevens voor de verschillende jaren als afzonderlijke balken naast
    elkaar getoond.  
    Bij layout='cumulative' staan de maanden op de X-as en wordt per jaar de
    cumulatieve zonne-energieproductie weergegeven als een lijndiagram.  
    Bij layout='cumulative_zone' wordt het historisch bereik van de cumulatieve
    productie weergegeven als een zone (min–max), met het meest recente jaar als
    afzonderlijke lijn.

    Args:
        lang (LangCode, optional):
            Taalcode voor labels en maandnamen ('nl', 'fr' of 'en').
            Bepaalt ook de titelvertalingen. Standaard is 'nl'.

        short (bool, optional):
            Gebruik korte maandnamen (True) of volledige maandnamen (False).
            Standaard is True.

        layout (Literal["years", "months", "cumulative", "cumulative_zone"], optional):
            Selecteert de grafiekindeling:
            - "years": jaren op de X-as, maanden als gestapelde balken.
            - "months": maanden op de X-as, jaren als gegroepeerde balken.
            - "cumulative": maanden op de X-as, cumulatieve maandtotalen per jaar (lijn).
            - "cumulative_zone": maanden op de X-as, historisch bereik als zone en
              het meest recente jaar als lijn.
            Standaard is "years".

    Returns:
        None:
            De functie toont de grafiek rechtstreeks via matplotlib
            en geeft geen waarde terug.
    """
    pivot_solar = get_solar_pivot(lang=lang, short=short)

    if pivot_solar.empty:
        print(TRANSLATIONS["errors"]["no_data_to_plot"][lang])
        return

    if layout == "years":
        # Jaren op x-as, maanden stacked
        ax = pivot_solar.plot(
            kind='bar',
            stacked=True,
            figsize=(12, 6),
            colormap='plasma'
        )
        xlabel = TRANSLATIONS["year"][lang]
        legend_title = TRANSLATIONS["month"][lang]

    elif layout == "months":
        # Maanden op x-as, jaren naast elkaar
        df = pivot_solar.T
        ax = df.plot(
            kind='bar',
            figsize=(12, 6),
            colormap='plasma'
        )
        xlabel = TRANSLATIONS["month"][lang]
        legend_title = TRANSLATIONS["year"][lang]

    elif layout == "cumulative":
        df = pivot_solar.T.cumsum()
        ax = df.plot(
            kind="line",
            figsize=(12, 6),
            linewidth=2
        )
        xlabel = TRANSLATIONS["month"][lang]
        legend_title = TRANSLATIONS["year"][lang]

    elif layout == "cumulative_zone":
        df = pivot_solar.T.cumsum()

        last_year = df.columns.max()
        historical = df.drop(columns=last_year)
        current = df[last_year]

        fig, ax = plt.subplots(figsize=(12, 6))

        ax.fill_between(
            df.index,
            historical.min(axis=1),
            historical.max(axis=1),
            color="gold",
            alpha=0.25,
            label=f"{historical.columns.min()}–{historical.columns.max()}"
        )

        ax.plot(
            df.index,
            current,
            color="gold",
            linewidth=2.5,
            label=str(last_year)
        )

        xlabel = TRANSLATIONS["month"][lang]
        legend_title = TRANSLATIONS["year"][lang]

    else:
        raise ValueError("layout must be 'years', 'months', 'cumulative' or 'cumulative_zone'")

    if layout == "cumulative_zone":
        ax.set_title(TRANSLATIONS["titles"]["solar_cumulative_zone"][lang])
    elif layout == "cumulative":
        ax.set_title(TRANSLATIONS["titles"]["solar_cumulative"][lang])
    else:
        ax.set_title(TRANSLATIONS["titles"]["solar"][lang])

    ax.set_xlabel(xlabel)
    ax.set_ylabel("GWh")

    ax.legend(
        title=legend_title,
        bbox_to_anchor=(1.05, 1),
        loc='upper left'
    )

    plt.tight_layout()
    plt.show()


# -------------------------------------------------------------------
# ☀️ Zonne-energie INTERACTIEF
# -------------------------------------------------------------------
def plot_solar_interactive(
        lang: LangCode = "nl",
        short: bool = True,
        layout: Literal["years", "months", "cumulative"] = "years"
    ) -> None:
    """
    Visualiseert de maandelijkse zonne-energieproductie met interactieve
    Plotly-grafieken, gebruikmakend van een long-format DataFrame.

    Deze functie is de interactieve tegenhanger van `plot_solar` (matplotlib)
    en maakt gebruik van Plotly Express om zoom, hover-informatie en het
    in- en uitschakelen van reeksen via de legenda mogelijk te maken.

    De data wordt opgehaald via `get_solar_dataframe()` en bevat per rij:
    - een jaar
    - een maand
    - de totale zonne-energieproductie in GWh

    Afhankelijk van de gekozen `layout` wordt deze long-format data:
    - rechtstreeks gebruikt (cumulative),
    - of licht herschikt voor staafdiagrammen (years / months).

    Ondersteunde layouts:
    - "years":
        Gestapelde staafdiagrammen per jaar.
        De X-as toont de jaren, de kleuren stellen de maanden voor.
    - "months":
        Gegroepeerde staafdiagrammen per maand.
        De X-as toont de maanden, de kleuren stellen de jaren voor.
    - "cumulative":
        Lijndiagrammen met cumulatieve maandtotalen per jaar.
        De X-as toont de maanden, elke lijn stelt een jaar voor.

    Args:
        lang (LangCode, optional):
            Taalcode voor labels, titels en maand-/jaarnamen.
            Ondersteunt 'nl', 'fr' en 'en'. 
            Standaard is 'nl'.

        short (bool, optional):
            Bepaalt of korte (True) of volledige (False) maandnamen gebruikt worden. 
            Standaard is True.

        layout (Literal["years", "months", "cumulative"], optional):
            Selecteert de grafiekindeling. 
            Standaard is "years".

    Returns:
        None:
            De functie toont de grafiek interactief in de browser
            (of notebook) en geeft geen waarde terug.
    """
    df = get_solar_dataframe()

    if df.empty:
        print(TRANSLATIONS["errors"]["no_data_to_plot"][lang])
        return

    # Zorg voor correcte sortering
    df = df.sort_values(["year", "month"])

    # Omzetten van maandnummers naar maandnamen
    df["month"] = [
        get_month_name(m, lang=lang, short=short)
        for m in df["month"]
    ]

    year_col = TRANSLATIONS["year"][lang]
    month_col = TRANSLATIONS["month"][lang]

    # Hernoem kolommen voor consistente labels
    df = df.rename(
        columns={
            "year": year_col,
            "month": month_col,
            "total_GWh": "GWh"
        }
    )

    # stacked bars per jaar
    if layout == "years":
        fig = px.bar(
            df,
            x=year_col,
            y="GWh",
            color=month_col,
            title=TRANSLATIONS["titles"]["solar"][lang],
            labels={
                "GWh": "GWh"
            }
        )

        legend_title = month_col

    # grouped bars per maand
    elif layout == "months":
        df[year_col] = df[year_col].astype(str)
        fig = px.bar(
            df,
            x=month_col,
            y="GWh",
            color=year_col,
            barmode="group",
            title=TRANSLATIONS["titles"]["solar"][lang],
            labels={
                "GWh": "GWh"
            }
        )

        legend_title = year_col

    # cumulatieve lijnen per year
    elif layout == "cumulative":
        # Bereken cumulatieve productie per jaar
        df["cumulative_GWh"] = (
            df.groupby(year_col)["GWh"].cumsum()
        )

        fig = px.line(
            df,
            x=month_col,
            y="cumulative_GWh",
            color=year_col,
            title=TRANSLATIONS["titles"]["solar_cumulative"][lang],
            labels={
                "cumulative_GWh": "GWh"
            }
        )

        legend_title = year_col

    else:
        raise ValueError("layout must be 'years', 'months' or 'cumulative'")

    fig.update_layout(
        legend_title_text=legend_title,
        hovermode="closest"
    )

    fig.show()


# -------------------------------------------------------------------
# ⚡ Belpex-prijzen - heatmap
# -------------------------------------------------------------------
def plot_belpex_heatmap(lang: LangCode = "nl", short: bool = True) -> None:
    """
    Visualiseert Belpex spotmarktprijzen als een heatmap.

    De rijen van de heatmap tonen de jaren en de kolommen de maanden.
    Elke cel geeft de prijs weer in EUR/MWh, met een kleurencode
    gebaseerd op de waarde (coolwarm). De maand- en jaarlabels worden
    weergegeven in de gekozen taal.

    Args:
        lang (LangCode, optional):
            Taalcode voor labels en maandnamen ('nl', 'fr' of 'en').
            Standaard is 'nl'.

        short (bool, optional):
            Gebruik korte maandnamen (True) of volledige maandnamen (False).
            Standaard is True.

    Returns:
        None:
            De functie toont de heatmap rechtstreeks via matplotlib/seaborn
            en geeft geen waarde terug.
    """
    pivot_belpex = get_belpex_pivot(lang=lang, short=short)

    if pivot_belpex.empty:
        print(TRANSLATIONS["errors"]["no_data_to_plot"][lang])
        return

    plt.figure(figsize=(12,6))
    sns.heatmap(pivot_belpex, annot=True, fmt=".2f", cmap="coolwarm",
                xticklabels=pivot_belpex.columns)
    plt.title(TRANSLATIONS["titles"]["belpex"][lang])
    plt.xlabel(TRANSLATIONS["month"][lang])
    plt.ylabel(TRANSLATIONS["year"][lang])
    plt.tight_layout()
    plt.show()


# -------------------------------------------------------------------
# ⚡ Belpex-prijzen - gemiddeld per uur
# -------------------------------------------------------------------
def plot_belpex_hourly(
    group_by: Literal["weekday", "month"] = "weekday",
    lang: LangCode = "nl",
    short: bool = True,
    figsize: tuple[int, int] = (12, 6),
    title: str | None = None
) -> None:
    """
    Visualiseert gemiddelde Belpex spotmarktprijzen per uur.

    De functie maakt een lijngrafiek van de gemiddelde uurprijzen, gegroepeerd
    per weekdag of per maand. De X-as toont de uren (0-23), de Y-as de prijs
    in EUR/MWh. Elke lijn vertegenwoordigt een weekdag of maand.

    Args:
        group_by (Literal["weekday", "month"], optional):
            Bepaal de groepering van de lijnen: 'weekday' voor weekdagen of
            'month' voor maanden. Standaard is 'weekday'.

        lang (LangCode, optional):
            Taalcode voor labels ('nl', 'fr' of 'en'). Standaard is 'nl'.

        short (bool, optional):
            Korte (True) of volledige (False) namen van weekdagen/maanden.
            Standaard is True.

        figsize (tuple[int, int], optional):
            Grootte van de figuur in inches (breedte, hoogte). Standaard is (12, 6).

        title (str | None, optional):
            Optionele titel voor de grafiek. Als deze niet is opgegeven,
            wordt automatisch een titel gekozen op basis van de waarde van
            `group_by`.

    Returns:
        None:
            De functie toont de grafiek direct via matplotlib en geeft niets terug.
    """

    # 🔹 Pivot-tabel ophalen
    pivot_belpex_hourly = get_belpex_hourly_pivot(group_by=group_by, lang=lang, short=short)

    if pivot_belpex_hourly.empty:
        print(TRANSLATIONS["errors"]["no_data_to_plot"][lang])
        return

    # 🔹 Standaard titel indien niet opgegeven
    if title is None:
        if group_by == "weekday":
            title = TRANSLATIONS["titles"]["belpex_hourly_weekday"][lang]
        else:
            title = TRANSLATIONS["titles"]["belpex_hourly_month"][lang]
    # 🔹 Lijngrafiek
    plt.figure(figsize=figsize)
    for col in pivot_belpex_hourly.columns:
        plt.plot(pivot_belpex_hourly.index, pivot_belpex_hourly[col], marker=None, label=col)

    # 🔹 Aslabels en titel
    plt.xlabel(pivot_belpex_hourly.index.name)       # bv. "Uur"
    plt.ylabel(TRANSLATIONS["labels"]["price"][lang])
    plt.title(title)

    # 🔹 Legenda en grid
    #plt.legend(title=pivot.columns.name)  # bv. "Weekdag" of "Maand"

    plt.legend(
        title=pivot_belpex_hourly.columns.name,     # bv. "Weekdag" of "Maand"
        bbox_to_anchor=(1.05, 1),    # zet legende rechts van de plot
        loc='upper left'              # ankerpunt van legende
    )
    plt.tight_layout()  # zorgt dat alles netjes binnen de figuur past
    plt.grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()
    plt.show()


# -------------------------------------------------------------------
# ⚡ Belpex: cumulatieve negatieve prijzen
# -------------------------------------------------------------------
def plot_negative_price_counts_cumulative(lang: LangCode = "nl", short: bool = True) -> None:
    """
    Visualiseert het cumulatieve aantal uren met negatieve Belpex-prijzen per maand/jaren.
    
    Args:
        lang (LangCode, optional):
            Taalcode voor labels en maandnamen ('nl', 'fr' of 'en').
            Standaard is 'nl'.

        short (bool, optional):
            Gebruik korte maandnamen (True) of volledige maandnamen (False).
            Standaard is True.
    
    Returns:
        None:
            De functie toont een cumulatieve lijnplot via matplotlib.
    """
    pivot = get_negative_price_counts_pivot(lang=lang, short=short)
    
    if pivot.empty:
        print(TRANSLATIONS["errors"]["no_data_to_plot"][lang])
        return

    # Cumulatief optellen per rij (jaar)
    cumulative = pivot.cumsum(axis=1)

    plt.figure(figsize=(12, 6))
    for year in cumulative.index:
        plt.plot(
            cumulative.columns,
            cumulative.loc[year],
            #marker='o',
            label=str(year)
        )

    plt.title(TRANSLATIONS["titles"]["negative_price_cumulative"][lang])
    plt.xlabel(TRANSLATIONS["month"][lang])
    plt.ylabel(TRANSLATIONS["labels"]["negative_price_cumulative"][lang])
    plt.legend(title=TRANSLATIONS["year"][lang], bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.show()


# -------------------------------------------------------------------
# 🔵 Belpex: aantal uren met negatieve prijzen (Bubble Chart)
# -------------------------------------------------------------------
def plot_negative_price_counts_bubble(lang: str = "nl", short: bool = True):
    """
    Visualiseert het aantal uren met negatieve Belpex-prijzen
    als bubble chart (grootte van de bubbles = aantal uren).

    Args:
        lang (str, optional): Taalcode voor labels ('nl', 'fr', 'en'). Default 'nl'.
        short (bool, optional): Korte maandnamen (True) of volledige (False). Default True.
    """
    pivot = get_negative_price_counts_pivot(lang=lang, short=short)
    
    if pivot.empty:
        print(TRANSLATIONS["errors"]["no_data_to_plot"][lang])
        return
    
    plt.figure(figsize=(12, 6))
    
    # Voor elke jaar een scatter plot
    for year in pivot.index:
        plt.scatter(
            pivot.columns,                  # x = maand
            [year]*len(pivot.columns),      # y = jaar
            s=pivot.loc[year]*10,           # bubble size = aantal uren * schaalfactor
            alpha=0.6,                      # transparantie
            label=str(year)
        )
    
    plt.title(TRANSLATIONS["titles"]["negative_price"][lang])
    plt.xlabel(TRANSLATIONS["month"][lang])
    plt.ylabel(TRANSLATIONS["year"][lang])
    plt.legend(title=TRANSLATIONS["year"][lang], bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.tight_layout()
    plt.show()


# -------------------------------------------------------------------
# 🔗 Gecombineerde visualisatie: wind + zon + Belpex-prijs
# -------------------------------------------------------------------
def plot_combined(lang: LangCode = "nl", short: bool = True) -> None:
    """
    Visualiseert gecombineerde windproductie, zonneproductie en Belpex-prijzen
    in één grafiek.

    Wind- en zonneproductie worden weergegeven als gestapelde balken (GWh),
    terwijl de Belpex-prijs als een lijnplot (EUR/MWh) wordt gevisualiseerd.
    De X-as toont maandnamen in de gekozen taal, met jaarscheiding en
    dynamische jaarlabels.

    Args:
        lang (LangCode, optional):
            Taalcode voor labels en maandnamen ('nl', 'fr' of 'en').
            Standaard is 'nl'.

        short (bool, optional):
            Gebruik korte maandnamen (True) of volledige maandnamen (False).
            Standaard is True.

    Returns:
        None:
            De functie toont de grafiek rechtstreeks via matplotlib
            en geeft geen waarde terug.
    """

    df_compare = get_combined_dataframe(fillna=True, lang=lang, short=short)

    if df_compare.empty:
        print(TRANSLATIONS["errors"]["no_data_to_plot"][lang])
        return

    # Maak een continue x-index voor plotting
    df_compare['x_index'] = range(len(df_compare))

    # Overzetten naar Numpy arrays om sneller te verwerken
    wind_vals = df_compare['wind_GWh'].to_numpy()
    solar_vals = df_compare['solar_GWh'].to_numpy()
    belpex_vals = df_compare['belpex_EUR_per_MWh'].to_numpy()
    x_index = df_compare['x_index'].to_list()

    max_prod = (wind_vals + solar_vals).max()
    max_price = belpex_vals.max()

    # Plot aanmaken
    fig, ax1 = plt.subplots(figsize=(14, 6))

    # Stacked bars: wind + zon
    ax1.bar(
        x_index,
        wind_vals,
        label=TRANSLATIONS["labels"]["wind_GWh"][lang],
        color="steelblue",
    )
    ax1.bar(
        x_index,
        solar_vals,
        bottom=wind_vals,
        label=TRANSLATIONS["labels"]["solar_GWh"][lang],
        color="gold",
    )
    ax1.set_ylabel("GWh")
    ax1.set_ylim(0, max_prod)
    ax1.legend(loc="upper left")

    # Lijngrafiek: Belpex-prijs
    ax2 = ax1.twinx()
    ax2.plot(
        x_index,
        belpex_vals,
        color="red",
        marker="o",
        label=TRANSLATIONS["labels"]["belpex_EUR_per_MWh"][lang],
    )
    ax2.set_ylabel(TRANSLATIONS["labels"]["belpex_EUR_per_MWh"][lang])
    ax2.set_ylim(0, max_price)
    ax2.legend(loc="upper right")

    # X-as opmaak: maandnamen
    ax1.set_xticks(x_index)
    ax1.set_xticklabels(df_compare['month_name'], rotation=90)

    # Jaarscheiding en labels
    years = df_compare['year'].unique()
    for y in years:
        year_mask = df_compare['year'] == y
        xpos_mean = df_compare.loc[year_mask, 'x_index'].mean()
        
        # Jaarlabel onder de maandnamen
        # Dynamische offset op basis van short/full maandnamen
        y_offset = -max_prod * (0.2 if not short else 0.10)

        ax1.text(
            xpos_mean,
            y_offset,
            str(y),
            ha='center',
            va='top',
            fontsize=10,
            fontweight='bold'
        )
        
        # Verticale scheiding (behalve laatste jaar)
        if y != years[-1]:
            last_x = df_compare.loc[year_mask, 'x_index'].max()
            ax1.axvline(x=last_x + 0.5, color='gray', linestyle='--', alpha=0.5)

    # Horizontale grid op ax1 (productie)
    #ax1.grid(axis='y', linestyle='--', alpha=0.5)
    # Horizontale grid  ax2 (Belpex-lijn)
    #ax2.grid(axis='y', linestyle='--', alpha=0.3)

    # Titel en layout
    plt.title(TRANSLATIONS["titles"]["combined"][lang])
    plt.tight_layout()
    plt.show()