"""
decorators.py

Verzameling van algemene decorators voor hergebruik in verschillende projecten.

Deze module bevat momenteel:

- retry_on_failure: een decorator die functies automatisch opnieuw probeert uit te voeren
  bij tijdelijke fouten, met configureerbare parameters voor aantal pogingen, wachttijd,
  exponentiële backoff en toegestane uitzonderingen.

In de toekomst kunnen hier meer decorators toegevoegd worden.
"""

import functools
import time
from typing import Callable, Tuple, Type, Any

def retry_on_failure(
    tries: int = 3,
    delay: float = 2,
    backoff: float = 1,
    allowed_exceptions: Tuple[Type[BaseException], ...] = (Exception,)
) -> Callable[
        [Callable[..., Any]],  # Input van de decorator: een functie die willekeurige arguments (*args, **kwargs) accepteert
        Callable[..., Any]     # Output van de decorator: een nieuwe functie met exact dezelfde signature
    ]:
    """
    Decorator om een functie meerdere keren opnieuw uit te voeren wanneer er een fout optreedt.

    Deze decorator is nuttig bij tijdelijke fouten, zoals netwerkproblemen of onstabiele API-responses.
    Als de gedecoreerde functie een uitzondering genereert die voorkomt in `allowed_exceptions`, 
    zal ze automatisch opnieuw uitgevoerd worden tot het maximum aantal `tries` is bereikt.
    Tussen elke poging wacht de functie `delay` seconden. Na elke fout wordt de wachttijd vermenigvuldigd 
    met `backoff` (exponentiële backoff).

    Parameters:
    - tries (int): Het maximaal aantal pogingen voor de functie wordt opgegeven. Standaard: 3.
    - delay (float): De initiële wachttijd (in seconden) tussen pogingen. Standaard: 2.
    - backoff (float): De vermenigvuldigingsfactor voor de wachttijd bij elke fout. Standaard: 1 (geen toename).
                      Een waarde >1 verhoogt de wachttijd exponentieel (bijv. 2 voor verdubbeling).
    - allowed_exceptions (tuple): Een tuple van uitzonderingen waarvoor een retry toegestaan is.
                                  Standaard: (Exception,), wat alle standaardfouten omvat.

    Returns:
    - Callable[[Callable[..., Any]], Callable[..., Any]]:
        Een decorator-functie die de originele functie neemt en een nieuwe functie teruggeeft.
        De nieuwe functie voert de originele functie uit en probeert deze automatisch opnieuw
        als een van de `allowed_exceptions` optreedt, volgens de parameters `tries`, `delay` en `backoff`.

    Intern maakt de wrapper gebruik van lokale kopieën van de parameters `_tries` en `_delay`
    om te voorkomen dat de oorspronkelijke decoratorwaarden (die gedeeld worden door alle oproepen)
    overschreven of beïnvloed worden tijdens het uitvoeren van retries.

    Gebruik:
    @retry_on_failure(tries=5, delay=1, backoff=2, allowed_exceptions=(ConnectionError,))
    def fetch_data():
        ...
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Zorgt ervoor dat de metadata (naam, docstring, enz.) van de originele functie 
        # behouden blijft in de gegenereerde wrapperfunctie.
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Lokale kopieën maken om te vermijden dat de originele decorator-argumenten 
            # gewijzigd worden tijdens herhaalde pogingen
            _tries, _delay = tries, delay
            while _tries > 1:
                try:
                    return func(*args, **kwargs)
                except allowed_exceptions as e:
                    _tries -= 1
                    print(f"⚠️ Fout '{e}' in {func.__name__}(). Nog {_tries} pogingen over... Wacht {_delay:.1f}s.")
                    # Wacht voor het opgegeven aantal seconden
                    time.sleep(_delay)
                    _delay *= backoff
            # Laatste poging buiten de while-loop: als deze ook faalt, wordt de uitzondering doorgegeven
            return func(*args, **kwargs)
        return wrapper
    return decorator