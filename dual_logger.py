"""
dual_logger.py

Bevat de klasse DualLogger, die zowel sys.stdout als sys.stderr tijdelijk omleidt zodat alle uitvoer (print-statements en foutmeldingen) gelijktijdig naar de console én naar een opgegeven logbestand worden geschreven. De klasse kan gebruikt worden als contextmanager (met `with`) of als losse instantie (met handmatige .close()).
"""
import sys

class DualLogger:
    """
    Vervangt sys.stdout en sys.stderr zodat alle output (zowel print als foutmeldingen)
    tegelijkertijd naar de console én naar een logbestand geschreven wordt.

    Deze klasse werkt zowel als:
    - Contextmanager: gebruik `with DualLogger(path):` om automatisch stdout/stderr te vervangen
                      en het logbestand na afloop veilig te sluiten.
    - Losse instantie: roep `logger = DualLogger(path)` aan, en vergeet `logger.close()` niet.

    Parameters:
    - logfile_path (str): Volledig pad naar het logbestand (zal geopend worden in append-modus).

    Gebruik als contextmanager:
    ----------------------------
    with DualLogger("pad/naar/log.txt"):
        print("Dit gaat naar console én naar logbestand.")
        raise Exception("Fouten ook!")

    Gebruik als losse instantie:
    ----------------------------
    logger = DualLogger("pad/naar/log.txt")
    sys.stdout = sys.stderr = logger
    print("Loggen zonder contextmanager.")
    logger.close()  # Belangrijk!
    """

    def __init__(self, logfile_path):
        # Sla pad op en open het logbestand (append-modus, UTF-8)
        self.logfile_path = logfile_path
        self.log = open(self.logfile_path, "a", encoding="utf-8", errors="replace")

        # Bewaar originele standaard streams om later te kunnen herstellen
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

    def write(self, message):
        """
        Wordt automatisch aangeroepen door print() of foutmeldingen.
        Schrijft het bericht zowel naar het scherm als naar het logbestand.
        """
        self.original_stdout.write(message)   # Toon op het scherm
        self.log.write(message)               # Schrijf naar het logbestand

    def flush(self):
        """
        Wordt automatisch aangeroepen om de buffer te legen.
        Noodzakelijk voor realtime logging of bij gebruik van print(..., flush=True).
        """
        self.original_stdout.flush()
        self.log.flush()

    def close(self):
        # Herstel standaard streams
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr

        # Sluit expliciet het logbestand bij manueel gebruik
        self.log.close()

    def __enter__(self):
        # Contextmanager start: vervang stdout en stderr door deze logger
        sys.stdout = sys.stderr = self
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Herstel oorspronkelijke streams
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        # Sluit het logbestand
        self.log.close()

    def __del__(self):
        # Herstel standaard streams indien nog actief
        try:
            if sys.stdout is self:
                sys.stdout = self.original_stdout
            if sys.stderr is self:
                sys.stderr = self.original_stderr
        except Exception:
            pass  # Tijdens interpreter shutdown kunnen globals verdwijnen

        # Probeer logbestand te sluiten indien nog open
        try:
            if hasattr(self, "log") and not self.log.closed:
                self.log.close()
        except Exception:
            pass  # Stilletjes falen indien iets misloopt bij garbage collection