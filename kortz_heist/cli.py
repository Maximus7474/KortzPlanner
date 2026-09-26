"""Minimal command-line entry point for the Kortz Center loot optimizer.

Bare on purpose - swap for a GUI later. The reusable core is
`solver.solve()` plus `models` / `catalog` / `session` (see README.md).
"""
from .catalog import CATALOG
from .models import Artifact, price_warning
from .session import DEFAULT_SESSION_PATH, Session, build_session, load_session, save_session
from .solver import solve


def warn_price_outliers(artifacts: list[Artifact]) -> None:
    """Print a flag for any artifact whose price falls outside the
    typical range for its type. Informational only - doesn't change
    anything about how the plan is solved."""
    for a in artifacts:
        warning = price_warning(a.type, a.value)
        if warning:
            print(f"  ! {a.name}: {warning} - double check this value")


def prompt_new_session() -> Session:
    print("Enter this heist's price for each artifact on offer.")
    print("Leave blank and press enter to skip an item that isn't available.\n")

    prices = {}
    for name, art_type in CATALOG:
        raw = input(f"  {name}: $").strip().replace(",", "")
        if not raw:
            continue
        if not raw.isdigit():
            print("    (not a number, skipping)")
            continue
        price = int(raw)
        warning = price_warning(art_type, price)
        if warning:
            print(f"    ! {warning} - double check this value")
        prices[name] = price

    print("\nWhich of those are the client's three-piece request?")
    print("(comma-separated names, exactly as entered above, or blank for none)")
    raw = input("  Client targets: ").strip()
    client_targets = [n.strip() for n in raw.split(",") if n.strip()] if raw else []

    print("\nAny of those NOT obtainable solo this heist?")
    raw = input("  Solo-unavailable: ").strip()
    solo_unavailable = [n.strip() for n in raw.split(",") if n.strip()] if raw else []

    return build_session(prices, client_targets, solo_unavailable)


def get_session() -> Session:
    existing = load_session()
    if existing:
        print(f"Found a saved layout ({len(existing.artifacts)} artifacts) at {DEFAULT_SESSION_PATH}.")
        warn_price_outliers(existing.artifacts)
        use_saved = input("Reuse it? [Y/n]: ").strip().lower()
        if use_saved in ("", "y", "yes"):
            return existing

    session = prompt_new_session()
    save_session(session)
    print(f"\nSaved this layout to {DEFAULT_SESSION_PATH} - rerun to reprocess with a different player count.\n")
    return session


def run(num_players: int, artifacts: list[Artifact], client_set_bonus: int) -> None:
    if num_players == 1:
        solo_locked = [a for a in artifacts if not a.solo_available]
        if solo_locked:
            print("NOTE: running solo - the following items may not actually be")
            print("obtainable without a crew. Double check before you commit:")
            for a in solo_locked:
                print(f"  - {a.name}")
            print()

    result = solve(artifacts, num_players, client_set_bonus=client_set_bonus)

    for i, bag in enumerate(result.assignment, start=1):
        bag_value = sum(a.value for a in bag)
        used_percent = sum(a.space_percent for a in bag)
        print(f"Player {i} bag ({used_percent}% full, ${bag_value:,}):")
        for a in bag:
            print(f"  - {a.name} [{a.type.value}, {a.space_percent}%, ${a.value:,}]")
        print()

    print(
        f"Client set completed: {result.client_set_completed} "
        f"(bonus: ${result.bonus_applied:,})"
    )
    print(f"TOTAL PAYOUT: ${result.total_value:,}")


def main() -> None:
    session = get_session()

    while True:
        raw = input("How many players (1-4)? ").strip()
        if raw.isdigit() and 1 <= int(raw) <= 4:
            num_players = int(raw)
            break
        print("Enter a number from 1 to 4.")

    run(num_players, session.artifacts, session.client_set_bonus)


if __name__ == "__main__":
    main()
