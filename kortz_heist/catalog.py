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
    ("Swingset study no.LXIX", ArtifactType.ARTWORK),
    ("the hunter becomes the hunted", ArtifactType.ARTWORK),
    ("with friends like these", ArtifactType.ARTWORK),
    ("het gouden hondje", ArtifactType.ARTWORK),

    # BOTTOM FLOOR
    ("Byzantine hoops", ArtifactType.HORIZONTAL_CASE),
    ("oeuf de coquard de vouivre", ArtifactType.HORIZONTAL_CASE_CUSHION),
    ("Memento non mori (diamond)", ArtifactType.VERTICAL_CASE),

    # MIDDLE FLOOR
    ("Antique bands", ArtifactType.HORIZONTAL_CASE),
    ("art deco rings", ArtifactType.HORIZONTAL_CASE),
    ("orange crush", ArtifactType.ARTWORK),
    ("the chief", ArtifactType.ARTWORK),
    ("canis hominem edit", ArtifactType.ARTWORK),
    ("do you see me", ArtifactType.ARTWORK),
    ("la duchesse", ArtifactType.ARTWORK),
    ("explain yourself", ArtifactType.ARTWORK),
    ("pharaonic bangles", ArtifactType.HORIZONTAL_CASE),
    ("coquard rings", ArtifactType.HORIZONTAL_CASE),
    ("fertility statue (ivory)", ArtifactType.HORIZONTAL_CASE_CUSHION),

    # TOP FLOOR
    ("sod off", ArtifactType.ARTWORK),
    ("art deco circlets", ArtifactType.HORIZONTAL_CASE),
    ("the great circle back", ArtifactType.ARTWORK),
    ("don't forgo these blueprints", ArtifactType.ARTWORK),
    ("coquard carcanet (yellow diamond)", ArtifactType.VERTICAL_CASE),
    ("oeuf de coquard verdoyant", ArtifactType.HORIZONTAL_CASE_CUSHION),
]

CATALOG_BY_NAME = {name: art_type for name, art_type in CATALOG}

CLIENT_BONUS = 100_000
