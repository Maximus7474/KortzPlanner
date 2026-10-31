"""Static reference list of the possible Kortz Center artifacts.

Names and categories don't change between heists - only price does, along
with which items happen to be on offer, which is the client's three-piece
request, and which are solo-obtainable. That variable, per-heist data lives
in session.py, not here.
"""
from dataclasses import dataclass

from .models import ArtifactLocations, ArtifactType

@dataclass(frozen=True)
class CatalogArtifact:
    type: ArtifactType
    location: str | None

# (name, type, location)
CATALOG = [
    # VAULT
    ("Swingset Study No. LXIX", ArtifactType.ARTWORK, ArtifactLocations.VAULT),
    ("The Hunter Becomes the Hunted", ArtifactType.ARTWORK, ArtifactLocations.VAULT),
    ("With Friends Like These", ArtifactType.ARTWORK, ArtifactLocations.VAULT),
    ("Het Gouden Hondje", ArtifactType.ARTWORK, ArtifactLocations.VAULT),

    # BELL BUILDING
    ("Orange Crush", ArtifactType.ARTWORK, ArtifactLocations.MAINFLOOR),
    ("The Chief", ArtifactType.ARTWORK, ArtifactLocations.MAINFLOOR),
    ("Canis Hominem Edit", ArtifactType.ARTWORK, ArtifactLocations.MAINFLOOR),
    ("Do You See Me", ArtifactType.ARTWORK, ArtifactLocations.MAINFLOOR),
    ("La Duchesse", ArtifactType.ARTWORK, ArtifactLocations.MAINFLOOR),
    ("Explain Yourself", ArtifactType.ARTWORK, ArtifactLocations.MAINFLOOR),
    ("Sod Off", ArtifactType.ARTWORK, ArtifactLocations.UPPERFLOOR),
    ("The Great Circle Back", ArtifactType.ARTWORK, ArtifactLocations.CRISPGALLERY),
    ("Don't Forgo These Blueprints", ArtifactType.ARTWORK, ArtifactLocations.CRISPGALLERY),
    ("Cooked", ArtifactType.ARTWORK, ArtifactLocations.UPPERFLOOR),

    ("Memento Non Mori (Diamond)", ArtifactType.VERTICAL_CASE, ArtifactLocations.LOWERFLOOR),
    ("Memento Non Mori (Emerald)", ArtifactType.VERTICAL_CASE, ArtifactLocations.LOWERFLOOR),
    ("Memento Non Mori (Amethyst)", ArtifactType.VERTICAL_CASE, ArtifactLocations.LOWERFLOOR),
    ("Coquard Carcanet (Yellow Diamond)", ArtifactType.VERTICAL_CASE, ArtifactLocations.UPPERFLOOR),
    ("Coquard Carcanet (Red Spinel)", ArtifactType.VERTICAL_CASE, ArtifactLocations.UPPERFLOOR),
    ("Coquard Carcanet (Emeralds)", ArtifactType.VERTICAL_CASE, ArtifactLocations.UPPERFLOOR),
    ("Coquard Carcanet (Tanzanite)", ArtifactType.VERTICAL_CASE, ArtifactLocations.UPPERFLOOR),
    ("Coquard Carcanet (Imperial Topaz)", ArtifactType.VERTICAL_CASE, ArtifactLocations.UPPERFLOOR),
    ("Venus d'Algernon (Marble)", ArtifactType.VERTICAL_CASE, ArtifactLocations.CRISPGALLERY),
    ("Venus d'Algernon (Silver)", ArtifactType.VERTICAL_CASE, ArtifactLocations.CRISPGALLERY),
    ("Venus d'Algernon (Ivory)", ArtifactType.VERTICAL_CASE, ArtifactLocations.CRISPGALLERY),
    ("Ruby Gemstone", ArtifactType.VERTICAL_CASE, ArtifactLocations.CRISPGALLERY),
    ("Yellow Topaz", ArtifactType.VERTICAL_CASE, ArtifactLocations.CRISPGALLERY),
    ("Aquamarine Gemstone", ArtifactType.VERTICAL_CASE, ArtifactLocations.CRISPGALLERY),
    ("Silver Dapple Pinto", ArtifactType.VERTICAL_CASE, ArtifactLocations.UPPERFLOOR),
    ("Perlino Andalusian", ArtifactType.VERTICAL_CASE, ArtifactLocations.UPPERFLOOR),
    ("Fold Turkoman", ArtifactType.VERTICAL_CASE, ArtifactLocations.UPPERFLOOR),
    ("Cremello Dutch Warmblood", ArtifactType.VERTICAL_CASE, ArtifactLocations.UPPERFLOOR),

    ("Meteorite Fragment", ArtifactType.HORIZONTAL_CASE_CUSHION, ArtifactLocations.CRISPGALLERY),
    ## Needs checking, pretty sure some statues will spawn main floor and some crisp
    ("Fertility Statue (Ivory)", ArtifactType.HORIZONTAL_CASE_CUSHION, ArtifactLocations.MAINFLOOR),
    ("Fertility Statue (Bronze)", ArtifactType.HORIZONTAL_CASE_CUSHION, None),
    ("Fertility Statue (Gold)", ArtifactType.HORIZONTAL_CASE_CUSHION, ArtifactLocations.CRISPGALLERY),
    ("Fertility Statue (Silver)", ArtifactType.HORIZONTAL_CASE_CUSHION, ArtifactLocations.CRISPGALLERY),
    ## Needs checking, pretty sure some statues will spawn main floor and some upper floor
    ("Oeuf de Coquard Verdoyant", ArtifactType.HORIZONTAL_CASE_CUSHION, None),
    ("Oeuf de Coquard de Vouivre", ArtifactType.HORIZONTAL_CASE_CUSHION, None),
    ("Oeuf de Coquard Enchanté", ArtifactType.HORIZONTAL_CASE_CUSHION, None),
    ("Oeuf de Coquard Forestier", ArtifactType.HORIZONTAL_CASE_CUSHION, None),
    ("Oeuf de Coquard Décoratif", ArtifactType.HORIZONTAL_CASE_CUSHION, None),

    ("Coquard Bracelets", ArtifactType.HORIZONTAL_CASE, None),
    ("Antique Bands", ArtifactType.HORIZONTAL_CASE, None),
    ("Art Deco Rings", ArtifactType.HORIZONTAL_CASE, None),
    ("Pharaonic Bangles", ArtifactType.HORIZONTAL_CASE, None),
    ("Coquard Rings", ArtifactType.HORIZONTAL_CASE, ArtifactLocations.LOWERFLOOR),
    ("Art Deco Circlets", ArtifactType.HORIZONTAL_CASE, ArtifactLocations.CRISPGALLERY),
    ("Antique Rings", ArtifactType.HORIZONTAL_CASE, None),
    ("Byzantine Hoops", ArtifactType.HORIZONTAL_CASE, ArtifactLocations.LOWERFLOOR),

    # Loading Bay
    ('Cash case', ArtifactType.CASH_CASE, ArtifactLocations.LOADINGBAY),
]

CATALOG_BY_NAME: dict[str, CatalogArtifact] = {
    name: CatalogArtifact(
        type=art_type,
        location=location
    )
    for name, art_type, location in CATALOG
}
CATALOG_NAMES = [name for name, art_type, location in CATALOG]
