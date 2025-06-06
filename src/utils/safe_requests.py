"""
safe_requests.py

Bevat de functie `safe_requests_get` - een uitgebreide en veilige wrapper rond `requests.get()` met ingebouwde retry-logica.

Deze module biedt een eenvoudige manier om HTTP GET-verzoeken uit te voeren met foutafhandeling en herhaalde pogingen bij mislukking.
Ideaal voor scripts die robuust moeten omgaan met tijdelijke netwerk- of serverproblemen (bijv. bij het ophalen van data van externe APIs).

Voorbeeldgebruik:
    from safe_requests import safe_requests_get

    response = safe_requests_get("https://api.example.com/data", tries=5, delay=1)
"""

import time
import requests

def safe_requests_get(url, params=None, headers=None, tries=3, delay=2, timeout=10):
    """
    Uitgebreide en veilige versie van requests.get() met ingebouwde retry-logica.

    Deze functie probeert een HTTP GET-verzoek uit te voeren naar de opgegeven URL.
    Als het verzoek faalt door een netwerkfout of een HTTP-fout (zoals 5xx of 4xx-status),
    wordt het verzoek automatisch opnieuw geprobeerd tot een maximum van `tries` keer.
    Na elke mislukte poging wordt `delay` seconden gewacht alvorens opnieuw te proberen.

    Parameters:
    - url (str): De URL waarnaar het GET-verzoek wordt verzonden.
    - params (dict, optional): Optionele query parameters toe te voegen aan het verzoek.
    - headers (dict, optional): Optionele headers om mee te sturen met het verzoek.
    - tries (int): Aantal pogingen bij fouten. Standaard is 3.
    - delay (int or float): Wachtijd (in seconden) tussen pogingen. Standaard is 2.
    - timeout (int or float): Maximum wachttijd voor een antwoord van de server. Standaard is 10 seconden.

    Retourneert:
    - response (requests.Response): Het response-object als het verzoek succesvol was.

    Raises:
    - requests.exceptions.RequestException: Als alle pogingen mislukken of er een andere fout optreedt.
    
    Gebruik:
    response = safe_requests_get("https://api.example.com/data", tries=5, delay=1)

    """
    # Lokale kopie van tries maken zodat de oorspronkelijke waarde behouden blijft bij hergebruik
    _tries = tries
    while _tries > 1:
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            # Roep een uitzondering op bij een HTTP-statuscode die een fout aangeeft (4xx of 5xx)
            response.raise_for_status()
            return response
        except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
            print(f"⚠️ Request fout: {e}. Nog {_tries-1} pogingen... Wacht {delay}s.")
            # Wacht voor het opgegeven aantal seconden
            time.sleep(delay)
            _tries -= 1
    # Laatste poging buiten de loop: als deze faalt, wordt de uitzondering niet meer opgevangen
    response = requests.get(url, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response