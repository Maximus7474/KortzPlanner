"""Optimizer: assign artifacts to players' bags to maximize total payout."""
from dataclasses import dataclass
from functools import lru_cache
tuple
from .models import Artifact, BAG_CAPACITY_UNITS


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

    items = list(artifacts)
    n = len(items)
    client_target_idxs = [i for i, a in enumerate(items) if a.is_client_target]
    client_bit = {idx: 1 << pos for pos, idx in enumerate(client_target_idxs)}
    full_client_mask = (1 << len(client_target_idxs)) - 1

    @lru_cache(maxsize=None)
    def best(i: int, caps: tuple[int, ...], collected_mask: int) -> tuple[int, tuple]:
        """Returns (best_value_from_here_on, decisions) where decisions is a
        tuple of (item_index, player_index_or_None)."""
        if i == n:
            bonus = client_set_bonus if full_client_mask and collected_mask == full_client_mask else 0
            return bonus, ()

        item = items[i]
        cost = item.space_units

        # Option: leave this item behind.
        best_value, best_trace = best(i + 1, caps, collected_mask)
        best_choice = None

        # Option: give it to whichever player yields the best outcome.
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
    best.cache_clear()  # this solve's cache is only useful within this call

    assignment: list[list[Artifact]] = [[] for _ in range(num_players)]
    left_behind: list[Artifact] = []
    assigned_idxs = set()
    for idx, player in trace:
        if player is None:
            left_behind.append(items[idx])
        else:
            assignment[player].append(items[idx])
            assigned_idxs.add(idx)

    client_set_completed = bool(full_client_mask) and all(
        idx in assigned_idxs for idx in client_target_idxs
    )
    bonus_applied = client_set_bonus if client_set_completed else 0

    return SolveResult(
        assignment=assignment,
        left_behind=left_behind,
        total_value=total_value,
        client_set_completed=client_set_completed,
        bonus_applied=bonus_applied,
    )
