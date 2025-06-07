"""
sqlalchemy_model_utils.py

Hulpfuncties voor inspectie van SQLAlchemy-modellen.

Bevat tools om automatisch een overzicht te genereren van alle modellen die afstammen van een 
gegeven basisklasse, inclusief hun kolomnamen en optionele beschrijvingen.

Geschikt voor debugging, documentatie, of het dynamisch genereren van gebruikersinterfaces 
op basis van SQLAlchemy-modeldefinities.

Voorbeeldgebruik:
    from sqlalchemy_model_utils import alle_modellen_en_kolommen
    print(alle_modellen_en_kolommen(Base))
"""

def alle_modellen_en_kolommen(base_class):
    """
    Genereert een overzicht van alle SQLAlchemy-modellen die afstammen van een gegeven basisklasse,
    samen met hun kolomnamen en optionele beschrijvingen.

    Voor elke subklasse van `base_class` (typisch gemaakt met declarative_base()) wordt gecontroleerd
    of deze daadwerkelijk gekoppeld is aan een database-tabel (via __tablename__ en __table__).
    Vervolgens worden alle kolommen weergegeven, inclusief eventuele beschrijvingen die zijn toegevoegd
    via het `info`-attribuut van SQLAlchemy.

    Parameters:
    - base_class : declarative_base()
        De basisklasse waarvan alle SQLAlchemy-modellen afstammen. 
        Voorbeeld: Base = declarative_base()

    Returns:
    - str
        Een overzichtelijke string die de naam van elk model toont, gevolgd door de lijst van kolommen.
        Indien beschikbaar, wordt ook een korte beschrijving per kolom getoond.
    """
    uitvoer = []

    # Doorloop alle subklassen (modellen) die van base_class zijn afgeleid
    for cls in base_class.__subclasses__():
        # Controleer of het een geldig SQLAlchemy-model is met een gekoppelde tabel
        if hasattr(cls, '__tablename__') and hasattr(cls, '__table__'):
            uitvoer.append(f"Model: {cls.__name__}")

            # Doorloop alle kolommen van de tabel
            for kolom in cls.__table__.columns:
                kolom_naam = kolom.name  # naam van de kolom
                # Haal optionele beschrijving op (indien aanwezig)
                beschrijving = kolom.info.get("beschrijving", None)
                
                # Voeg de kolom toe aan de uitvoer, met of zonder beschrijving
                if beschrijving:
                    uitvoer.append(f"  - {kolom_naam}: {beschrijving}")
                else:
                    uitvoer.append(f"  - {kolom_naam}")

            uitvoer.append("")

    return "\n".join(uitvoer)