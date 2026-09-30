"""Optimizer: assign artifacts to players' bags to maximize total payout."""
import math
from dataclasses import dataclass
from functools import lru_cache
from .models import Artifact, BAG_CAPACITY_UNITS

_INFEASIBLE = -math.inf


@dataclass
class SolveResult:
    assignment: list[list[Artifact]]  # assignment[i] = artifacts given to player i
    left_behind: list[Artifact]
    total_value: int
    client_set_completed: bool
    bonus_applied: int


def solve(
    artifacts: list[Artifact],
    num_players: int,
    bag_capacity_units: int = BAG_CAPACITY_UNITS,
    client_set_bonus: int = 0,
    require_client_set: bool = True,
    skip_inaccessible: bool = False,
) -> SolveResult:
    """Find the assignment of artifacts to players that maximizes total
    payout (item values, plus the client-set bonus if all client-target
    items are collected), subject to each player having one bag of
    `bag_capacity_units` capacity.

    Exact search with memoization - fine for a single heist's item count
    (tens of items), not meant to scale to huge inventories.
    """
    if not 1 <= num_players <= 4:
        raise ValueError("num_players must be between 1 and 4")

    # Filter out inaccessible items for solo runs if requested
    items = [
        a for a in artifacts
        if not (skip_inaccessible and num_players == 1 and not a.solo_available)
    ]
    n = len(items)

    client_target_idxs = [i for i, a in enumerate(items) if a.is_client_target]
    client_bit = {idx: 1 << pos for pos, idx in enumerate(client_target_idxs)}
    full_client_mask = (1 << len(client_target_idxs)) - 1

    # Require full set completion ONLY if requested AND all targets are present
    # (If an item was filtered out by skip_inaccessible, full_client_mask won't match original catalog targets,
    # making set completion impossible if any target was removed).
    original_target_count = sum(1 for a in artifacts if a.is_client_target)
    can_complete_original_set = len(client_target_idxs) == original_target_count

    must_complete_set = (
        require_client_set
        and bool(full_client_mask)
        and can_complete_original_set
    )

    if require_client_set and not can_complete_original_set and original_target_count > 0:
        raise ValueError(
            "Cannot fulfill client request: some required items are inaccessible in solo mode."
        )

    @lru_cache(maxsize=None)
    def best(i: int, caps: tuple[int, ...], collected_mask: int) -> tuple[float, tuple]:
        if i == n:
            set_completed = (
                bool(full_client_mask)
                and collected_mask == full_client_mask
                and can_complete_original_set
            )
            if must_complete_set and not set_completed:
                return _INFEASIBLE, ()
            return (client_set_bonus if set_completed else 0), ()

        item = items[i]
        cost = item.space_units

        # Option 1: Leave this item behind
        best_value, best_trace = best(i + 1, caps, collected_mask)
        best_choice = None

        # Option 2: Give it to whichever player yields the highest combined payout
        for p in range(num_players):
            if caps[p] >= cost:
                new_caps = list(caps)
                new_caps[p] -= cost
                new_mask = collected_mask | client_bit.get(i, 0)
                value, trace = best(i + 1, tuple(new_caps), new_mask)
                value += item.value
                if value > best_value:
                    best_value = value
                    best_choice = p
                    best_trace = trace

        return best_value, ((i, best_choice),) + best_trace

    start_caps = tuple([bag_capacity_units] * num_players)
    total_value, trace = best(0, start_caps, 0)
    best.cache_clear()

    if total_value == _INFEASIBLE:
        raise ValueError(
            "The client's request can't be completed with this many players "
            "and bags - every client-target item can't fit at once."
        )

    assignment: list[list[Artifact]] = [[] for _ in range(num_players)]
    left_behind: list[Artifact] = []
    assigned_idxs = set()
    for idx, player in trace:
        if player is None:
            left_behind.append(items[idx])
        else:
            assignment[player].append(items[idx])
            assigned_idxs.add(idx)

    client_set_completed = (
        bool(full_client_mask)
        and can_complete_original_set
        and all(idx in assigned_idxs for idx in client_target_idxs)
    )
    bonus_applied = client_set_bonus if client_set_completed else 0

    return SolveResult(
        assignment=assignment,
        left_behind=left_behind,
        total_value=round(total_value),
        client_set_completed=client_set_completed,
        bonus_applied=bonus_applied,
    )
