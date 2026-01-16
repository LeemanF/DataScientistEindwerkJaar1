"""
localization.py

Bevat meertalige ondersteuning (Nederlands, Frans en Engels) voor:
- Maand- en weekdagnamen (kort en volledig)
- Vertalingen van titels en labels voor grafieken en tabellen

Structuur:
    TRANSLATIONS   → Tekstlabels en grafiektitels per taal
    MONTHS         → Maandnamen (kort & voluit)
    WEEKDAYS       → Weekdagnamen (kort & voluit)
    Helperfuncties → Naamopvraging per nummer of datetime-object

Gebruik:
    from src.utils.localization import (
        get_month_name, 
        get_weekday_name, 
        get_month_name_from_date,
        get_weekday_name_from_date,
        TRANSLATIONS, 
        MONTHS, 
        WEEKDAYS
    )

Voorbeelden:
    >>> get_month_name(3, lang="nl", short=False)
    'Maart'

    >>> get_weekday_name(5, lang="fr", short=True)
    'Ven'

    >>> get_month_name_from_date(datetime(2024, 7, 15), lang="en")
    'Jul'

    >>> TRANSLATIONS["titles"]["solar"]["nl"]
    'Maandelijkse zonne-energieproductie (GWh)'
"""

from datetime import datetime
from typing import Literal

# Type voor taalcode: momenteel beperkt tot Nederlands, Frans of Engels
LangCode = Literal["nl", "fr", "en"]
"""Ondersteunde taalcodes voor meertalige functies."""

# -------------------------------------------------------------------
# Vertalingen voor visuals
# -------------------------------------------------------------------
TRANSLATIONS = {
        "titles": {
            "wind_split": {
                "nl": "Maandelijkse windproductie (GWh)",
                "fr": "Production éolienne mensuelle (GWh)",
                "en": "Monthly wind production (GWh)"
            },
            "wind_total": {
                "nl": "Totale maandelijkse windproductie (GWh)",
                "fr": "Production éolienne totale mensuelle (GWh)",
                "en": "Total monthly wind production (GWh)"
            },
            "wind_cumulative": {
                "nl": "Cumulatieve windproductie per jaar (GWh)",
                "fr": "Production éolienne cumulée par année (GWh)",
                "en": "Cumulative wind production per year (GWh)"
            },
            "solar": {
                "nl": "Maandelijkse zonne-energieproductie (GWh)",
                "fr": "Production solaire mensuelle (GWh)",
                "en": "Monthly solar production (GWh)"
            },
            "solar_cumulative": {
                "nl": "Cumulatieve zonne-energieproductie per jaar (GWh)",
                "fr": "Production solaire cumulée par année (GWh)",
                "en": "Cumulative solar production per year (GWh)"
            },
            "solar_cumulative_zone": {
                "nl": "Cumulatieve zonne-energieproductie - historisch bereik en huidig jaar (GWh)",
                "fr": "Production solaire cumulée - plage historique et année en cours (GWh)",
                "en": "Cumulative solar production - historical range and current year (GWh)"
            },
            "combined": {
                "nl": "Hernieuwbare energieproductie en Belpex-prijs per maand",
                "fr": "Production d'énergies renouvelables et prix Belpex par mois",
                "en": "Renewable energy production and Belpex price per month"
            },
            "belpex": {
                "nl": "Gemiddelde Belpex-prijs (€/MWh)",
                "fr": "Prix moyen Belpex (€/MWh)",
                "en": "Average Belpex price (€/MWh)"
            },
            "belpex_hourly_weekday": {
                "nl": "Gemiddelde Belpex-prijs per uur per weekdag",
                "fr": "Prix Belpex moyen par heure et jour de la semaine",
                "en": "Average Belpex price per hour per weekday"
            },
            "belpex_hourly_month": {
                "nl": "Gemiddelde Belpex-prijs per uur per maand",
                "fr": "Prix moyen Belpex par heure et par mois",
                "en": "Average Belpex price per hour per month"
            },
            "negative_price_cumulative": {
                "nl": "Cumulatief aantal uren met negatieve Belpex-prijzen",
                "fr": "Nombre cumulatif d'heures avec prix négatifs Belpex",
                "en": "Cumulative number of hours with negative Belpex prices"
            },
            "negative_price": {
                "nl": "Aantal uren met negatieve Belpex-prijzen",
                "fr": "Nombre d'heures avec des prix négatifs Belpex",
                "en": "Number of hours with negative Belpex prices"
            },
            "belpex_distribution": {
                "nl": "Verdeling Belpex-prijzen per maand",
                "fr": "Distribution des prix Belpex par mois",
                "en": "Distribution of Belpex prices per month"
            }
        },
        "labels": {
            "belpex_EUR_per_MWh": {
                "nl": "Belpex prijs (€/MWh)",
                "fr": "Prix Belpex (€/MWh)",
                "en": "Belpex price (€/MWh)"
            },
            "price": {
                "nl": "Prijs (€/MWh)",
                "fr": "Prix (€/MWh)",
                "en": "Price (€/MWh)"
            },
            "wind_GWh": {
                "nl": "Wind (GWh)",
                "fr": "Éolien (GWh)",
                "en": "Wind (GWh)"
            },
            "solar_GWh": {
                "nl": "Zon (GWh)",
                "fr": "Solaire (GWh)",
                "en": "Solar (GWh)"
            },
            "renewable_peak": {
                "nl": "Piek productie hernieuwbaar in MW",
                "fr": "Production renouvelable maximale en MW",
                "en": "Peak renewable production in MW"
            },
            "negative_price_cumulative": {
                "nl": "Cumulatief aantal uren",
                "fr": "Nombre cumulatif d'heures",
                "en": "Cumulative hours"
            },
            "peak1": {
                "nl": "Marktschok (Oekraïne)",
                "fr": "Choc du marché (Ukraine)",
                "en": "Market shock (Ukraine)"
            },
            "peak2": {
                "nl": "Gascrisis / Nord Stream",
                "fr": "Crise du gaz / Nord Stream",
                "en": "Gas crisis / Nord Stream"
            }
        },
        "errors": {
            "no_data_to_plot": {
                "nl": "⚠️ Geen data beschikbaar om te plotten.",
                "fr": "⚠️ Pas de données disponibles pour tracer.",
                "en": "⚠️ No data available to plot."
            }
        },
        "year": {
            "nl": "Jaar",
            "fr": "Année",
            "en": "Year"
        },
        "month": {
            "nl": "Maand",
            "fr": "Mois",
            "en": "Month"
        },
        "weekday": {
            "nl": "Weekdag",
            "fr": "Jour de la semaine",
            "en": "Weekday"
        },
        "date": {
            "nl": "Datum", 
            "fr": "Date", 
            "en": "Date"
        },
        "hour": {
            "nl": "Uur",
            "fr": "Heure",
            "en": "Hour"
        },
        "time": {
            "nl": "Tijdstip", 
            "fr": "Heure", 
            "en": "Time"
        },
        "totals": {
            "nl": "Totaal",
            "fr": "Total",
            "en": "Total"
        },
        "source": {
            "nl": "Bron",
            "fr": "Source",
            "en": "Source"
        }
    }

# -------------------------------------------------------------------
# Maandnamen
# -------------------------------------------------------------------
MONTHS = {
    "nl": {
        "short": {
            1: "Jan", 
            2: "Feb", 
            3: "Mrt", 
            4: "Apr",
            5: "Mei", 
            6: "Jun", 
            7: "Jul", 
            8: "Aug",
            9: "Sep", 
            10: "Okt", 
            11: "Nov", 
            12: "Dec"
        },
        "full": {
            1: "Januari", 
            2: "Februari", 
            3: "Maart", 
            4: "April",
            5: "Mei", 
            6: "Juni", 
            7: "Juli", 
            8: "Augustus",
            9: "September", 
            10: "Oktober", 
            11: "November", 
            12: "December"
        }
    },
    "fr": {
        "short": {
            1: "Janv", 
            2: "Févr", 
            3: "Mars", 
            4: "Avr",
            5: "Mai", 
            6: "Juin", 
            7: "Juil", 
            8: "Août",
            9: "Sept", 
            10: "Oct", 
            11: "Nov", 
            12: "Déc"
        },
        "full": {
            1: "Janvier", 
            2: "Février", 
            3: "Mars", 
            4: "Avril",
            5: "Mai", 
            6: "Juin", 
            7: "Juillet", 
            8: "Août",
            9: "Septembre", 
            10: "Octobre", 
            11: "Novembre", 
            12: "Décembre"
        }
    },
    "en": {
        "short": {
            1: "Jan", 
            2: "Feb", 
            3: "Mar", 
            4: "Apr",
            5: "May", 
            6: "Jun", 
            7: "Jul", 
            8: "Aug",
            9: "Sep", 
            10: "Oct", 
            11: "Nov",
            12: "Dec"
        },
        "full": {
            1: "January", 
            2: "February", 
            3: "March", 
            4: "April",
            5: "May", 
            6: "June", 
            7: "July", 
            8: "August",
            9: "September", 
            10: "October", 
            11: "November", 
            12: "December"
        }
    }
}

# -------------------------------------------------------------------
# Weekdagnamen (1 = maandag, 7 = zondag)
# -------------------------------------------------------------------
WEEKDAYS = {
    "nl": {
        "short": {
            1: "Ma", 
            2: "Di", 
            3: "Wo", 
            4: "Do", 
            5: "Vr", 
            6: "Za", 
            7: "Zo"
        },
        "full": {
            1: "Maandag", 
            2: "Dinsdag", 
            3: "Woensdag", 
            4: "Donderdag",
            5: "Vrijdag", 
            6: "Zaterdag", 
            7: "Zondag"
        }
    },
    "fr": {
        "short": {
            1: "Lun", 
            2: "Mar",
            3: "Mer", 
            4: "Jeu", 
            5: "Ven", 
            6: "Sam", 
            7: "Dim"
        },
        "full": {
            1: "Lundi", 
            2: "Mardi", 
            3: "Mercredi", 
            4: "Jeudi",
            5: "Vendredi", 
            6: "Samedi", 
            7: "Dimanche"
        }
    },
    "en": {
        "short": {
            1: "Mon", 
            2: "Tue", 
            3: "Wed", 
            4: "Thu", 
            5: "Fri", 
            6: "Sat", 
            7: "Sun"
        },
        "full": {
            1: "Monday", 
            2: "Tuesday", 
            3: "Wednesday", 
            4: "Thursday",
            5: "Friday", 
            6: "Saturday", 
            7: "Sunday"
        }
    }
}

# -------------------------------------------------------------------
# Helperfuncties
# -------------------------------------------------------------------

def get_month_name(month_number: int, lang: LangCode = "nl", short: bool = True) -> str:
    """
    Geeft de maandnaam terug op basis van maandnummer (1-12).

    Args:
        month_number (int): Maandnummer (1 t/m 12)
        lang (str): 'nl', 'fr' of 'en'
        short (bool): Korte (default) of volledige naam

    Returns:
        str: Maandnaam in de gevraagde taal
    """
    style = "short" if short else "full"
    return MONTHS.get(lang, MONTHS["nl"])[style].get(month_number, "Onbekend")


def get_weekday_name(weekday_number: int, lang: LangCode = "nl", short: bool = True) -> str:
    """
    Geeft de weekdag terug op basis van nummer (1 = maandag, 7 = zondag).

    Args:
        weekday_number (int): Weekdagnummer (1-7)
        lang (str): 'nl', 'fr' of 'en'
        short (bool): Korte (default) of volledige naam

    Returns:
        str: Weekdagnaam in de gevraagde taal
    """
    style = "short" if short else "full"
    return WEEKDAYS.get(lang, WEEKDAYS["nl"])[style].get(weekday_number, "Onbekend")


def get_month_name_from_date(date_obj: datetime, lang: LangCode = "nl", short: bool = True) -> str:
    """
    Geeft de maandnaam voor een gegeven datetime-object.

    Args:
        date_obj (datetime): Datum
        lang (str): 'nl', 'fr' of 'en'
        short (bool): Korte (default) of volledige naam

    Returns:
        str: Maandnaam
    """
    return get_month_name(date_obj.month, lang, short)


def get_weekday_name_from_date(date_obj: datetime, lang: LangCode = "nl", short: bool = True) -> str:
    """
    Geeft de weekdagnaam voor een gegeven datetime-object.

    Args:
        date_obj (datetime): Datum
        lang (str): 'nl', 'fr' of 'en'
        short (bool): Korte (default) of volledige naam

    Returns:
        str: Weekdagnaam
    """
    weekday = date_obj.isoweekday()  # maandag = 1, zondag = 7
    return get_weekday_name(weekday, lang, short)