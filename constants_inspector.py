def list_module_constants(module, sort=False):
    """
    Drukt alle configuratievariabelen (in hoofdletters) van een gegeven module af
    en retourneert ze ook als dictionary.

    Parameters:
        module (module): De module waarvan de constanten moeten worden weergegeven.
        sort (bool): Of de constante variabelen gesorteerd moeten worden afgedrukt (standaard True).

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