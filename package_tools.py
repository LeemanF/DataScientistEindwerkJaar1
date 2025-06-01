"""
package_tools.py

Hulpfuncties voor het beheren van Python-packages binnen een project.

Deze module bevat functies om te controleren of een package aanwezig is, indien nodig automatisch te installeren of te upgraden, en het package vervolgens te importeren en terug te geven.

Momenteel bevat deze module:

- update_or_install_if_missing(package_name, min_version=None):
    Installeert of upgrade een package indien het ontbreekt of de versie
    niet aan de minimumvereiste voldoet, en importeert het daarna.
"""

import importlib
import importlib.util
import subprocess
import sys

def update_or_install_if_missing(package_name, min_version=None):
    """
    Zorgt ervoor dat een Python-package geïnstalleerd is, en indien gewenst,
    dat het voldoet aan een minimale versie.

    - Installeert het package als het nog niet aanwezig is.
    - Voert een upgrade uit als de aanwezige versie te laag is of niet numeriek vergelijkbaar is.
    - Herlaadt het package na installatie of upgrade, zodat het meteen bruikbaar is.

    Parameters:
    - package_name (str): Naam van het package zoals op PyPI (bv. 'requests').
    - min_version (str, optional): Minimale vereiste versie (bv. '2.25.0'). Indien None, wordt geen versiecontrole uitgevoerd.

    Returns:
    - module: Het geïmporteerde package-object (na installatie of upgrade indien nodig).
    """

    def parse_version(v, width=None):
        """
        Zet een versie-string (bv. '2.10.3' of '2.25.0.1') om naar een lijst van gehele getallen.
        Indien 'width' is opgegeven, wordt de lijst opgevuld tot die lengte met nullen.
        Als 'width' None is, wordt de ruwe lijst teruggegeven.

        Parameters:
        - v (str): Versie als string (bv. '2.10.3').
        - width (int or None): Minimale lengte van de resulterende lijst (aangevuld met nullen indien nodig).

        Returns:
        - list[int]: Lijst van gehele getallen.

        Raises:
        - ValueError: Als een deel van de versie geen geheel getal is (bv. '2.10a1').
        """
        parts = v.split('.')
        int_parts = []
        for p in parts:
            if not p.isdigit():
                raise ValueError(f"Niet-numeriek versieonderdeel: '{p}'")
            int_parts.append(int(p))
        if width:
            return int_parts + [0] * (width - len(int_parts))
        return int_parts

    def is_version_at_least(current, minimum):
        """
        Vergelijkt twee versie-strings op basis van numerieke onderdelen.
        De kortere lijst wordt opgevuld met nullen zodat beide even lang zijn.

        Parameters:
        - current (str): Huidige geïnstalleerde versie.
        - minimum (str): Vereiste minimumversie.

        Returns:
        - bool: True als current >= minimum, anders False.
                Geeft ook False terug als de versie niet numeriek vergeleken kan worden.
        """
        try:
            current_parts = parse_version(current)
            minimum_parts = parse_version(minimum)
            max_len = max(len(current_parts), len(minimum_parts))
            current_parts += [0] * (max_len - len(current_parts))
            minimum_parts += [0] * (max_len - len(minimum_parts))
            return current_parts >= minimum_parts
        except ValueError as e:
            print(f"⚠️  Versie '{current}' is niet numeriek vergelijkbaar ({e}) → installeren/upgrade vereist")
            return False

    needs_reload = False  # vlag om te bepalen of we herladen na installatie/upgrade

    # Controleer of het package al aanwezig is
    spec = importlib.util.find_spec(package_name)
    if spec is None:
        # Package is nog niet geïnstalleerd → installeer het
        print(f"📦 Module '{package_name}' niet gevonden. Bezig met installeren...")
        pip_target = f"{package_name}>={min_version}" if min_version else package_name
        subprocess.check_call([sys.executable, "-m", "pip", "install", pip_target])
        needs_reload = True
    else:
        # Package is reeds aanwezig → importeer het
        module = importlib.import_module(package_name)

        if min_version:
            # Controleer de huidige versie (default = '0.0.0' als niet beschikbaar)
            current_version = getattr(module, "__version__", "0.0.0")

            # Vergelijk versies; upgrade indien nodig
            if not is_version_at_least(current_version, min_version):
                print(f"🔁 Upgrade nodig: {package_name} ({current_version} < {min_version})")
                subprocess.check_call([sys.executable, "-m", "pip", "install", f"{package_name}>={min_version}"])

                # Verwijder het package en submodules uit sys.modules om herladen mogelijk te maken
                to_delete = [mod for mod in sys.modules if mod == package_name or mod.startswith(package_name + ".")]
                for mod in to_delete:
                    del sys.modules[mod]

                needs_reload = True

    # Herlaad het package indien nodig
    module = importlib.import_module(package_name)

    # Toon geïnstalleerde of geüpgradede versie indien herladen
    if needs_reload:
        version = getattr(module, "__version__", "onbekend")
        print(f"✅ Module '{package_name}' geïnstalleerd (versie {version}).")

    return module