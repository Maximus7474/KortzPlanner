"""Data models for the Kortz Center heist loot optimizer."""
from dataclasses import dataclass
from enum import Enum


class ArtifactType(Enum):
    ARTWORK = "artwork"
    VERTICAL_CASE = "vertical_case"
    HORIZONTAL_CASE_CUSHION = "horizontal_case_cushion"
    HORIZONTAL_CASE = "horizontal_case"


# Space each artifact type takes up, as a percentage of a single bag.
SPACE_COST_PERCENT = {
    ArtifactType.ARTWORK: 50,
    ArtifactType.VERTICAL_CASE: 30,
    ArtifactType.HORIZONTAL_CASE_CUSHION: 20,
    ArtifactType.HORIZONTAL_CASE: 10,
}

# Typical (min, max) price for each type, used only to flag outliers when
# entering data - out-of-range prices are still accepted, just called out
# so a typo or an unusually high value doesn't slip through unnoticed.
TYPICAL_PRICE_RANGE = {
    ArtifactType.ARTWORK: (70_000, 160_000),
    ArtifactType.VERTICAL_CASE: (70_000, 130_000),
    ArtifactType.HORIZONTAL_CASE_CUSHION: (30_000, 90_000),
    ArtifactType.HORIZONTAL_CASE: (20_000, 50_000),
}


def price_warning(art_type: ArtifactType, price: int) -> str | None:
    """Return a warning string if `price` falls outside the typical range
    for `art_type`, else None. Informational only - never blocks or clamps
    the value."""
    low, high = TYPICAL_PRICE_RANGE[art_type]
    if price < low:
        return f"${price:,} is below the usual ${low:,}-${high:,} range for {art_type.value}"
    if price > high:
        return f"${price:,} is above the usual ${low:,}-${high:,} range for {art_type.value}"
    return None

# Smallest unit of bag space needed to represent every cost exactly
# (10% == 1 unit), so a full, empty bag == 10 units of capacity.
SPACE_UNIT_PERCENT = 10
BAG_CAPACITY_UNITS = 100 // SPACE_UNIT_PERCENT  # 10 units per bag

CLIENT_SET_BONUS = 100_000


@dataclass(frozen=True)
class Artifact:
    """A single lootable item.

    is_client_target: True for the three pieces that make up the client's
        specific request. Securing all three (by anyone on the crew, not
        necessarily one player) earns a payout bonus - see solver.solve().
    solo_available: False if this item cannot actually be obtained when
        running the heist with only one player. The CLI/solver will not
        silently drop these - see cli.run() - it just flags them for a
        solo player to double-check before committing to a route.
    """

    name: str
    type: ArtifactType
    value: int
    is_client_target: bool = False
    solo_available: bool = True

    @property
    def space_percent(self) -> int:
        return SPACE_COST_PERCENT[self.type]

    @property
    def space_units(self) -> int:
        """Space cost in integer bag units (1 unit == 10% of a bag)."""
        units, remainder = divmod(self.space_percent, SPACE_UNIT_PERCENT)
        if remainder:
            raise ValueError(
                f"{self.name}: space cost {self.space_percent}% is not a "
                f"multiple of {SPACE_UNIT_PERCENT}%"
            )
        return units
