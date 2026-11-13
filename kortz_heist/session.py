"""Per-heist session data: which catalog artifacts are on offer, their
current prices, and which three are the client's request - the parts that
change heist to heist (unlike catalog.py, which is static).

Also handles saving/loading a session to disk, so a plan can be
reprocessed - e.g. rerun with a different player count - without
re-entering everything.
"""
import json, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, NamedTuple, get_args
from collections.abc import Iterable

from .catalog import CATALOG_BY_NAME
from .models import Artifact, ArtifactLocations, ArtifactType

APP_NAME = "KortzHeistOptimizer"

# project is bundled using pyinstaller
if getattr(sys, 'frozen', False):
    # Store user session in LocalAppData on Windows (~/.config on Linux/Mac)
    if sys.platform == "win32":
        DATA_DIR = Path.home() / "AppData" / "Local" / APP_NAME
    else:
        DATA_DIR = Path.home() / ".config" / APP_NAME
else:
    DATA_DIR = Path(__file__).resolve().parent.parent

DATA_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_SESSION_PATH = DATA_DIR / "session.json"


Difficulty = Literal["Hard", "Normal"]
DIFFICULTIES: list[Difficulty] = list(get_args(Difficulty))


class Session(NamedTuple):
    artifacts: list[Artifact]
    difficulty: Difficulty
    primary_target_value: int = 0
    last_updated: str = ""  # ISO-8601 UTC timestamp of the last save


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def format_last_updated(value: str) -> str:
    """Render a stored ISO timestamp in the machine's local time."""
    if not value:
        return "not saved yet"
    try:
        stamp = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return value
    if stamp.tzinfo is not None:
        stamp = stamp.astimezone()
    return stamp.strftime("%Y-%m-%d %H:%M:%S")


def build_session(
    prices: dict[str, int],
    client_targets: Iterable[str] = (),
    solo_unavailable: Iterable[str] = (),
    difficulty: Difficulty = "Normal",
    primary_target_value: int = 0,
) -> Session:
    """Build this heist's artifact layout from the static catalog plus this
    heist's variable data.

    prices: {catalog name: value}. Only names present here are included -
        leave an artifact out if it isn't on offer this heist.
    client_targets: names of the (up to three) client-request items.
    solo_unavailable: names known to be unobtainable solo this heist.
    difficulty: difficulty of the heist which defines the payout for
        completing the client's three-piece request.
    primary_target_value: value of the primary target, paid in full to the
        planner / owner and excluded from the secondary-loot split.
    """
    if primary_target_value < 0:
        raise ValueError("primary_target_value can't be negative")

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
    return Session(
        artifacts=artifacts,
        difficulty=difficulty,
        primary_target_value=primary_target_value,
    )


def save_session(session: Session, path: Path = DEFAULT_SESSION_PATH) -> str:
    """Persist this heist's artifact layout + payout settings so it can be
    reloaded later (e.g. to rerun the solver with a different player count).

    Writes the current UTC time as ``last_updated`` and returns it.
    """
    last_updated = _utc_now()
    payload = {
        "difficulty": session.difficulty,
        "primary_target_value": session.primary_target_value,
        "last_updated": last_updated,
        "artifacts": [
            {
                "name": a.name,
                "type": a.type.value,
                "value": a.value,
                "is_client_target": a.is_client_target,
                "solo_available": a.solo_available,
                "location": a.location.value if a.location else None,
            }
            for a in session.artifacts
        ],
    }

    print(f'Saving session with {len(session.artifacts)} artifacts to', path)

    path.write_text(json.dumps(payload, indent=2))
    return last_updated


def _load_location(item: dict) -> ArtifactLocations | None:
    """Location stored with a saved artifact.

    Sessions saved before locations were tracked fall back to the catalog
    default instead of showing every row as unknown.
    """
    if "location" in item:
        raw = item["location"]
        return ArtifactLocations(raw) if raw else None

    catalog_entry = CATALOG_BY_NAME.get(item["name"])
    if catalog_entry and catalog_entry.location:
        return ArtifactLocations(catalog_entry.location)

    return None


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
            location=_load_location(item),
        )
        for item in raw["artifacts"]
    ]

    # Mitigates the breaking change by taking into account the prior
    # payload format of the session data
    difficulty: Difficulty = DIFFICULTIES[0]
    if "difficulty" in raw:
        difficulty = raw["difficulty"]
    elif "client_set_bonus" in raw:
        difficulty = "Hard" if raw["client_set_bonus"] == 100_000 else "Normal"

    # Older session files predate the primary target value.
    primary_target_value = int(raw.get("primary_target_value") or 0)

    # Older session files also predate the save timestamp; fall back to the
    # file's own modification time so the GUI still shows something useful.
    last_updated = str(raw.get("last_updated") or "")
    if not last_updated:
        try:
            last_updated = datetime.fromtimestamp(
                path.stat().st_mtime, timezone.utc
            ).isoformat(timespec="seconds")
        except OSError:
            last_updated = ""

    return Session(
        artifacts=artifacts,
        difficulty=difficulty,
        primary_target_value=primary_target_value,
        last_updated=last_updated,
    )
