"""
constants_inspector.py

Module om alle constante variabelen (in hoofdletters) uit een ander Python-module uit te lezen, af te drukken en terug te geven als dictionary.

Deze utility volgt de conventie dat constanten in hoofdletters worden benoemd en niet beginnen met een underscore ("_").
"""

def list_module_constants(module):
    """
    Drukt alle configuratievariabelen (in hoofdletters) van een gegeven module af
    en retourneert ze ook als dictionary.

    Parameters:
        module (module): De module waarvan de constanten moeten worden weergegeven.

    Returns:
        dict: Een dictionary met de namen en waarden van de constante variabelen.
    """
    consts = {
        name: value
        for name, value in module.__dict__.items()
        if name.isupper() and not name.startswith("_")
    }

    for name, value in sorted(consts.items()):
        print(f"{name:20} = {value}")

    return consts