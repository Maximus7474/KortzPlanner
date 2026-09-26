"""Per-heist session data: which catalog artifacts are on offer, their
current prices, and which three are the client's request - the parts that
change heist to heist (unlike catalog.py, which is static).

Also handles saving/loading a session to disk, so a plan can be
reprocessed - e.g. rerun with a different player count - without
re-entering everything.
"""
import json
from pathlib import Path
from typing import NamedTuple
from collections.abc import Iterable

from .catalog import CATALOG_BY_NAME
from .models import CLIENT_SET_BONUS, Artifact, ArtifactType

DEFAULT_SESSION_PATH = Path(__file__).resolve().parent.parent / "session.json"


class Session(NamedTuple):
    artifacts: list[Artifact]
    client_set_bonus: int


def build_session(
    prices: dict[str, int],
    client_targets: Iterable[str] = (),
    solo_unavailable: Iterable[str] = (),
    client_set_bonus: int = CLIENT_SET_BONUS,
) -> Session:
    """Build this heist's artifact layout from the static catalog plus this
    heist's variable data.

    prices: {catalog name: value}. Only names present here are included -
        leave an artifact out if it isn't on offer this heist.
    client_targets: names of the (up to three) client-request items.
    solo_unavailable: names known to be unobtainable solo this heist.
    client_set_bonus: payout for completing the client's three-piece
        request. Fixed at CLIENT_SET_BONUS unless overridden.
    """
    client_targets = set(client_targets)
    solo_unavailable = set(solo_unavailable)

    unknown = (client_targets | solo_unavailable | set(prices)) - set(CATALOG_BY_NAME)
    if unknown:
        raise ValueError(f"Not in the catalog: {sorted(unknown)}")

    artifacts = [
        Artifact(
            name=name,
            type=CATALOG_BY_NAME[name],
            value=price,
            is_client_target=name in client_targets,
            solo_available=name not in solo_unavailable,
        )
        for name, price in prices.items()
    ]
    return Session(artifacts=artifacts, client_set_bonus=client_set_bonus)


def save_session(session: Session, path: Path = DEFAULT_SESSION_PATH) -> None:
    """Persist this heist's artifact layout + bonus so it can be reloaded
    later (e.g. to rerun the solver with a different player count)."""
    payload = {
        "client_set_bonus": session.client_set_bonus,
        "artifacts": [
            {
                "name": a.name,
                "type": a.type.value,
                "value": a.value,
                "is_client_target": a.is_client_target,
                "solo_available": a.solo_available,
            }
            for a in session.artifacts
        ],
    }
    path.write_text(json.dumps(payload, indent=2))


def load_session(path: Path = DEFAULT_SESSION_PATH) -> Session | None:
    """Reload a previously saved layout, or None if none exists yet."""
    if not path.exists():
        return None
    raw = json.loads(path.read_text())
    artifacts = [
        Artifact(
            name=item["name"],
            type=ArtifactType(item["type"]),
            value=item["value"],
            is_client_target=item["is_client_target"],
            solo_available=item["solo_available"],
        )
        for item in raw["artifacts"]
    ]
    return Session(artifacts=artifacts, client_set_bonus=raw["client_set_bonus"])
