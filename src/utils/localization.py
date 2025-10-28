"""
localization.py

Bevat maand- en weekdagnamen in het Nederlands, Frans en Engels,
zowel in korte als volledige vorm.

Gebruik:
    from src.utils.localization import get_name, MONTHS, WEEKDAYS

    print(get_name(3, "month", lang="nl", full=False))   # Mrt
    print(get_name(5, "month", lang="fr", full=True))    # Mai
    print(get_name(2, "weekday", lang="en", full=True))  # Tuesday
"""
from datetime import datetime

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

def get_month_name(month_number: int, lang: str = "nl", short: bool = True) -> str:
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


def get_weekday_name(weekday_number: int, lang: str = "nl", short: bool = True) -> str:
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


def get_month_name_from_date(date_obj: datetime, lang: str = "nl", short: bool = True) -> str:
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


def get_weekday_name_from_date(date_obj: datetime, lang: str = "nl", short: bool = True) -> str:
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