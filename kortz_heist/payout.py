"""Per-player payout estimation for a solved heist plan.

The solver maximizes total loot value; this module turns its assignment
into what each participant actually receives:

- the primary target is paid in full to the planner / owner (player 1);
- each accomplice receives a flat task cut;
- secondary loot (every artifact in a bag) is split evenly across all
  participants, with any remainder going to the owner;
- the buyer's request bonus is paid individually to every participant on
  top of their share, never split.

This module intentionally has no UI or solver imports so it can be reused
by the CLI, the GUI and tests alike.
"""
from dataclasses import dataclass

from .models import Artifact

ACCOMPLICE_FLAT_CUT = 100_000


@dataclass(frozen=True)
class PlayerPayout:
    player: int
    role: str
    artifacts: tuple[Artifact, ...]
    loot_share: int
    primary_share: int
    flat_cut: int
    buyer_bonus: int

    @property
    def total(self) -> int:
        return (
            self.loot_share
            + self.primary_share
            + self.flat_cut
            + self.buyer_bonus
        )

    @property
    def bag_value(self) -> int:
        return sum(a.value for a in self.artifacts)

    @property
    def used_percent(self) -> int:
        return sum(a.space_percent for a in self.artifacts)


@dataclass(frozen=True)
class PayoutEstimate:
    players: tuple[PlayerPayout, ...]
    num_players: int
    loot_total: int
    primary_total: int
    flat_cut_total: int
    buyer_bonus_per_player: int
    buyer_bonus_total: int
    crew_total: int
    left_behind: tuple[Artifact, ...] = ()


def estimate_payouts(
    assignment: list[list[Artifact]],
    bonus_applied: int,
    num_players: int,
    primary_target_value: int,
    left_behind: list[Artifact] | None = None,
    accomplice_flat: int = ACCOMPLICE_FLAT_CUT,
) -> PayoutEstimate:
    """Estimate what each participant receives from a solved assignment.

    `assignment[0]` is the owner's bag; the remaining bags belong to the
    accomplices. `bonus_applied` is the buyer-request bonus already
    awarded by the solver (0 when the request was not completed).
    """
    if num_players < 1:
        raise ValueError("num_players must be at least 1")
    if len(assignment) != num_players:
        raise ValueError("assignment must contain exactly one bag per player")
    if primary_target_value < 0:
        raise ValueError("primary_target_value can't be negative")
    if bonus_applied < 0:
        raise ValueError("bonus_applied can't be negative")
    if accomplice_flat < 0:
        raise ValueError("accomplice_flat can't be negative")

    bags = [tuple(bag) for bag in assignment]
    loot_total = sum(a.value for bag in bags for a in bag)
    base, remainder = divmod(loot_total, num_players)

    players = []
    for index, bag in enumerate(bags):
        is_owner = index == 0
        players.append(
            PlayerPayout(
                player=index + 1,
                role="Owner" if is_owner else "Accomplice",
                artifacts=bag,
                loot_share=base + (remainder if is_owner else 0),
                primary_share=primary_target_value if is_owner else 0,
                flat_cut=0 if is_owner else accomplice_flat,
                buyer_bonus=bonus_applied,
            )
        )

    return PayoutEstimate(
        players=tuple(players),
        num_players=num_players,
        loot_total=loot_total,
        primary_total=primary_target_value,
        flat_cut_total=sum(p.flat_cut for p in players),
        buyer_bonus_per_player=bonus_applied,
        buyer_bonus_total=bonus_applied * num_players,
        crew_total=sum(p.total for p in players),
        left_behind=tuple(left_behind or ()),
    )
