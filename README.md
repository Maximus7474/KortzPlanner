# Kortz Center Heist Loot Optimizer

Given a list of lootable artifacts (paintings, cases, etc.) and a crew size
(1-4 players), works out which items each player should carry to maximize
total payout, subject to each player having one bag of fixed capacity.

## How it models the problem

- Each player has **one bag**, treated as 100% capacity.
- Item space cost (as a % of a bag), fixed by type:
  | Type | Space |
  |---|---|
  | Artwork | 50% |
  | Vertical case | 30% |
  | Horizontal case, red cushion | 20% |
  | Horizontal case (plain) | 10% |
- Artifact **names and categories are static** (a fixed roster of ~30,
  `catalog.py`) but **price varies heist to heist**, along with which items
  are on offer, which three make up the client's request, and which are
  solo-obtainable - that variable data is a `Session` (`session.py`).
- Three specific artifacts make up the **client's request**. Securing all
  three - by any combination of players, not necessarily one - earns a
  flat bonus on top of their individual values.
- This is a multiple-knapsack assignment problem: which subset of items to
  take, and which player carries each, to maximize total value + bonus.
  `solver.solve()` finds the exact optimum via memoized search (fine for a
  single heist's item count; not built to scale to huge item lists).
- Solo runs (1 player): items marked `solo_available=False` are **not**
  auto-excluded - the CLI just flags them so you can double-check whether
  they're really reachable before committing to a route.

## Layout

```
kortz_heist/
  models.py   - Artifact / ArtifactType, space-cost table
  catalog.py  - CATALOG: static (name, type) roster - edit to match the
                real full item list, up to ~30 entries
  session.py  - Session: this heist's prices + flags; build/save/load
  solver.py   - solve(artifacts, num_players, ...) -> SolveResult
  cli.py      - bare CLI: builds or reuses a session, prints the plan
session.json  - saved automatically after building a session (gitignore
                this if you don't want it committed)
```

## Running it

```
python3 -m kortz_heist.cli
```

First run: enter a price for each artifact on offer this heist (blank to
skip one that isn't available), which three are the client's request,
which are solo-unavailable, and the client-set bonus payout. This gets
saved to `session.json`.

**Reprocessing after a player-count change**: run it again - it detects
the saved session and asks `Reuse it? [Y/n]`. Say yes, and you're only
asked for the new player count; none of the prices/flags need re-entering.
To start a fresh heist, delete `session.json` (or answer `n`) and enter a
new one.

## Extending

- **Real catalog**: fill in the rest of the roster in `catalog.py` (name +
  type only - no price, since that's per-heist).
- **GUI**: `solver.solve()`, `models`, `catalog`, and `session` have no CLI
  dependency. A GUI just needs to: build a `{name: price}` dict (e.g. from
  a form seeded with `CATALOG`), call `build_session(...)`, `save_session`
  it, then `solve(session.artifacts, num_players, client_set_bonus=...)`
  and render `SolveResult.assignment` / `.left_behind` / `.total_value` /
  `.client_set_completed`. `load_session()` covers reprocessing when the
  player count changes.
- **Bag capacity assumption**: currently one 100%-capacity bag per player.
  If that ever changes (e.g. a player can make multiple trips), adjust
  `bag_capacity_units` per player in `solve()` - the solver already takes
  it as a parameter, it's just uniform across players for now.
