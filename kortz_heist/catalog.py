"""Static reference list of the possible Kortz Center artifacts.

Names and categories don't change between heists - only price does, along
with which items happen to be on offer, which is the client's three-piece
request, and which are solo-obtainable. That variable, per-heist data lives
in session.py, not here.
"""
from .models import ArtifactType

# (name, type)
CATALOG = [
    # VAULT
    ("Swingset Study No. LXIX", ArtifactType.ARTWORK),
    ("The Hunter Becomes the Hunted", ArtifactType.ARTWORK),
    ("With Friends Like These", ArtifactType.ARTWORK),
    ("Het Gouden Hondje", ArtifactType.ARTWORK),

    # BELL BUILDING
    ("Orange Crush", ArtifactType.ARTWORK),
    ("The Chief", ArtifactType.ARTWORK),
    ("Canis Hominem Edit", ArtifactType.ARTWORK),
    ("Do You See Me", ArtifactType.ARTWORK),
    ("La Duchesse", ArtifactType.ARTWORK),
    ("Explain Yourself", ArtifactType.ARTWORK),
    ("Sod Off", ArtifactType.ARTWORK),
    ("The Great Circle Back", ArtifactType.ARTWORK),
    ("Don't Forgo These Blueprints", ArtifactType.ARTWORK),
    ("Cooked", ArtifactType.ARTWORK),

    ("Memento Non Mori (Diamond)", ArtifactType.VERTICAL_CASE),
    ("Coquard Carcanet (Yellow Diamond)", ArtifactType.VERTICAL_CASE),
    ("Venus d'Algernon (Marble)", ArtifactType.VERTICAL_CASE),
    ("Ruby Gemstone", ArtifactType.VERTICAL_CASE),
    ("Fertility Statue (Gold)", ArtifactType.VERTICAL_CASE),
    ("Silver Dapple Pinto", ArtifactType.VERTICAL_CASE),

    ("Meteorite Fragment", ArtifactType.HORIZONTAL_CASE_CUSHION),
    ("Oeuf de Coquard Verdoyant", ArtifactType.HORIZONTAL_CASE_CUSHION),
    ("Fertility Statue (Ivory)", ArtifactType.HORIZONTAL_CASE_CUSHION),
    ("Oeuf de Coquard de Vouivre", ArtifactType.HORIZONTAL_CASE_CUSHION),

    ("Coquard Bracelets", ArtifactType.HORIZONTAL_CASE),
    ("Antique Bands", ArtifactType.HORIZONTAL_CASE),
    ("Art Deco Rings", ArtifactType.HORIZONTAL_CASE),
    ("Pharaonic Bangles", ArtifactType.HORIZONTAL_CASE),
    ("Coquard Rings", ArtifactType.HORIZONTAL_CASE),
    ("Art Deco Circlets", ArtifactType.HORIZONTAL_CASE),
    ("Antique Rings", ArtifactType.HORIZONTAL_CASE),
    ("Byzantine Hoops", ArtifactType.HORIZONTAL_CASE),
]

CATALOG_BY_NAME = {name: art_type for name, art_type in CATALOG}
