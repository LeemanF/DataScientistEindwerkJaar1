"""
constants_inspector.py

Deze module biedt een hulpfunctie om alle constante configuratievariabelen (in hoofdletters)
uit een opgegeven Python-module te inspecteren. De functie `list_module_constants` detecteert
alle publieke constante attributen (d.w.z. variabelen met hoofdletters die niet beginnen met een
underscore), drukt ze af en retourneert ze als een dictionary.

Typisch gebruik is het overzichtelijk weergeven van instellingen of configuratieparameters die
in aparte modules zijn gedefinieerd.

Voorbeeld:
    import settings
    from constants_inspector import list_module_constants

    constants = list_module_constants(settings, sort=True)
"""

def list_module_constants(module, sort=False):
    """
    Drukt alle configuratievariabelen (in hoofdletters) van een gegeven module af
    en retourneert ze ook als dictionary.

    Parameters:
        module (module): De module waarvan de constanten moeten worden weergegeven.
        sort (bool): Of de constante variabelen gesorteerd moeten worden afgedrukt (standaard False).

    Returns:
        dict: Een dictionary met de namen en waarden van de constante variabelen.
    """
    consts = {
        name: value
        for name, value in module.__dict__.items()
        if name.isupper() and not name.startswith("_")
    }

    items = sorted(consts.items()) if sort else consts.items()

    for name, value in items:
        print(f"{name:20} = {value}")

    return consts