"""Static reference list of the possible Kortz Center artifacts.

Names and categories don't change between heists - only price does, along
with which items happen to be on offer, which is the client's three-piece
request, and which are solo-obtainable. That variable, per-heist data lives
in session.py, not here.
"""
from .models import ArtifactType

# (name, type, location)
CATALOG = [
    # VAULT
    ("Swingset Study No. LXIX", ArtifactType.ARTWORK, None),
    ("The Hunter Becomes the Hunted", ArtifactType.ARTWORK, None),
    ("With Friends Like These", ArtifactType.ARTWORK, None),
    ("Het Gouden Hondje", ArtifactType.ARTWORK, None),

    # BELL BUILDING
    ("Orange Crush", ArtifactType.ARTWORK, None),
    ("The Chief", ArtifactType.ARTWORK, None),
    ("Canis Hominem Edit", ArtifactType.ARTWORK, None),
    ("Do You See Me", ArtifactType.ARTWORK, None),
    ("La Duchesse", ArtifactType.ARTWORK, None),
    ("Explain Yourself", ArtifactType.ARTWORK, None),
    ("Sod Off", ArtifactType.ARTWORK, None),
    ("The Great Circle Back", ArtifactType.ARTWORK, None),
    ("Don't Forgo These Blueprints", ArtifactType.ARTWORK, None),
    ("Cooked", ArtifactType.ARTWORK, None),

    ("Memento Non Mori (Diamond)", ArtifactType.VERTICAL_CASE, None),
    ("Memento Non Mori (Emerald)", ArtifactType.VERTICAL_CASE, None),
    ("Memento Non Mori (Amethyst)", ArtifactType.VERTICAL_CASE, None),
    ("Coquard Carcanet (Yellow Diamond)", ArtifactType.VERTICAL_CASE, None),
    ("Coquard Carcanet (Red Spinel)", ArtifactType.VERTICAL_CASE, None),
    ("Coquard Carcanet (Emeralds)", ArtifactType.VERTICAL_CASE, None),
    ("Coquard Carcanet (Tanzanite)", ArtifactType.VERTICAL_CASE, None),
    ("Coquard Carcanet (Imperial Topaz)", ArtifactType.VERTICAL_CASE, None),
    ("Venus d'Algernon (Marble)", ArtifactType.VERTICAL_CASE, None),
    ("Venus d'Algernon (Silver)", ArtifactType.VERTICAL_CASE, None),
    ("Venus d'Algernon (Ivory)", ArtifactType.VERTICAL_CASE, None),
    ("Ruby Gemstone", ArtifactType.VERTICAL_CASE, None),
    ("Yellow Topaz", ArtifactType.VERTICAL_CASE, None),
    ("Aquamarine Gemstone", ArtifactType.VERTICAL_CASE, None),
    ("Silver Dapple Pinto", ArtifactType.VERTICAL_CASE, None),
    ("Perlino Andalusian", ArtifactType.VERTICAL_CASE, None),
    ("Fold Turkoman", ArtifactType.VERTICAL_CASE, None),
    ("Cremello Dutch Warmblood", ArtifactType.VERTICAL_CASE, None),

    ("Meteorite Fragment", ArtifactType.HORIZONTAL_CASE_CUSHION, None),
    ## Needs checking, pretty sure some statues will spawn main floor and some crisp
    ("Fertility Statue (Ivory)", ArtifactType.HORIZONTAL_CASE_CUSHION, None),
    ("Fertility Statue (Bronze)", ArtifactType.HORIZONTAL_CASE_CUSHION, None),
    ("Fertility Statue (Gold)", ArtifactType.HORIZONTAL_CASE_CUSHION, None),
    ("Fertility Statue (Silver)", ArtifactType.HORIZONTAL_CASE_CUSHION, None),
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
    ("Coquard Rings", ArtifactType.HORIZONTAL_CASE, None),
    ("Art Deco Circlets", ArtifactType.HORIZONTAL_CASE, None),
    ("Antique Rings", ArtifactType.HORIZONTAL_CASE, None),
    ("Byzantine Hoops", ArtifactType.HORIZONTAL_CASE, None),

    # Loading Bay
    ('Cash case', ArtifactType.CASH_CASE, None),
]

CATALOG_BY_NAME = {name: art_type for name, art_type, location in CATALOG}
CATALOG_NAMES = [name for name, art_type, location in CATALOG]
