<h1 align="center">Kortz Center Heist Loot Optimizer</h1>

<p align="center">
  <a href="https://github.com/Maximus7474/KortzPlanner/releases/latest/download/KortzHeistOptimizer-windows.exe">
    <img src="https://img.shields.io/badge/Download-Windows-blue?style=for-the-badge&logo=windows" alt="Download Windows" />
  </a>
  <a href="https://github.com/Maximus7474/KortzPlanner/releases/latest/download/KortzHeistOptimizer-macos">
    <img src="https://img.shields.io/badge/Download-macOS-black?style=for-the-badge&logo=apple" alt="Download macOS" />
  </a>
  <a href="https://github.com/Maximus7474/KortzPlanner/releases/latest/download/KortzHeistOptimizer-linux">
    <img src="https://img.shields.io/badge/Download-Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black" alt="Download Linux" />
  </a>
</p>

Given a list of lootable artifacts (paintings, cases, etc.) and a crew size
(1-4 players), works out which items each player should carry to maximize
total payout, subject to each player having one bag of fixed capacity.

> [!NOTE]
> Still needs further evaluation to adapt for second runs in a given week, so I can add further settings to properly estimate revenue of a given run.

<details>
  <summary>GUI Preview</summary>
  <img width="873" height="696" alt="image" src="https://github.com/user-attachments/assets/4f65840b-b817-44f2-ba20-02e4728d54f5" />
</details>

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
  flat, fixed **$100,000 bonus** (`CLIENT_SET_BONUS` in `models.py`) on
  top of their individual values.
- Each type has a typical price range, used only to flag likely typos or
  unusual values as you enter them - it never blocks or clamps a price:
  | Type | Typical range |
  |---|---|
  | Artwork | $70,000 - $155,000 |
  | Vertical case | $80,000 - $100,000 |
  | Horizontal case, cushion | $30,000 - $40,000 |
  | Horizontal case (plain) | $20,000 - $50,000 |
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
  gui.py      - Tkinter GUI: same workflow, point-and-click
run_gui.py    - PyInstaller entry point for the GUI (see "Packaging" below)
session.json  - saved automatically after building a session (gitignore
                this if you don't want it committed)
```

## Running it

CLI:
```
python -m kortz_heist.cli
```

GUI:
```
python -m kortz_heist.gui
```

First run (either one): enter a price for each artifact on offer this
heist (out-of-range prices get flagged inline but are still accepted),
which three are the client's request, and which are solo-unavailable.
This gets saved to `session.json`. (The client-set bonus is fixed, so it
isn't asked for.)

**Reprocessing after a player-count change**: run it again (CLI or GUI) -
it detects the saved session and offers to reuse it. Accept, and you're
only asked for the new player count; none of the prices/flags need
re-entering. To start a fresh heist, delete `session.json` (or decline the
reuse prompt / use File > New session in the GUI) and enter a new one.

### CLI Output

```
Player 1 bag (100% full, $ 330,500):
  - Byzantine Hoops                     [ 10% |  32,000$ ]
  - Oeuf de Coquard de Vouivre          [ 20% |  60,000$ ]
  - Memento Non Mori (Diamond)          [ 30% |  97,500$ ]
  - Art Deco Rings                      [ 10% |  31,000$ ]
  - Pharaonic Bangles                   [ 10% |  31,000$ ]
  - Coquard Rings                       [ 10% |  33,000$ ]
  - Art Deco Circlets                   [ 10% |  46,000$ ]

Player 2 bag (100% full, $ 307,000):
  - Fertility Statue (Ivory)            [ 20% |  62,000$ ]
  - Don't Forgo These Blueprints        [ 50% | 152,500$ ]
  - Coquard Carcanet (Yellow Diamond)   [ 30% |  92,500$ ]

Client set completed: True (bonus: $100,000)
TOTAL PAYOUT: $737,500
```

## Using the GUI

- **Add an artifact**: type its name into the Name field - matching
  catalog entries appear as you type. Press **Enter** (or Tab) once the
  name is filled in to jump to the Price field; type the price and press
  **Enter** to add it to the table below. Focus returns to Name so you can
  keep adding items back-to-back without touching the mouse.
- **Client Target / Solo OK**: click either cell in an item's row to
  toggle it (☐/☑). Only three items can be marked as the client's request
  at once - the app will tell you if you try a fourth.
- **Fix a mistake**: double-click a row to open an edit dialog (change
  price, toggle flags, or remove the item entirely); Enter saves, Esc
  cancels. Or select a row and click "Remove selected" / press Delete.
- **File menu**: "New session" clears everything, "Reload saved session"
  reverts to what's on disk, discarding unsaved changes.
- Every add/edit/remove/toggle auto-saves to `session.json`.
- Pick the player count and click "Solve" (or press Enter with focus on
  the player-count box) to see the bag assignment in the Plan panel.

## Packaging the GUI with PyInstaller

From the project root (same folder as `run_gui.py`):
```
pip install pyinstaller
pyinstaller --onefile --windowed --name KortzHeistOptimizer run_gui.py
```
The executable lands in `dist/`. Notes:
- `--windowed` suppresses the console window (drop it if you want the
  console visible for debugging).
- Tkinter is part of the standard library, so there's nothing extra to
  bundle for the GUI itself; on Linux, make sure the *build* machine has
  `python3-tk` installed (e.g. `apt install python3-tk`) since PyInstaller
  needs it present to bundle Tcl/Tk - end users don't need it installed.
- The bundled executable writes/reads `session.json` next to itself only
  if run from a writable location; if you hit permission errors when
  running from somewhere like `Program Files`, move the executable to a
  writable folder or adjust `DEFAULT_SESSION_PATH` in `session.py`.

## Extending

- **Real catalog**: fill in the rest of the roster in `catalog.py` (name +
  type only - no price, since that's per-heist).
- **A different GUI**: `solver.solve()`, `models`, `catalog`, and
  `session` have no UI dependency - `gui.py` is just one consumer of them.
  Any other frontend can build a `{name: price}` dict, call
  `build_session(...)`, `save_session` it, then
  `solve(session.artifacts, num_players, client_set_bonus=...)` and render
  `SolveResult.assignment` / `.left_behind` / `.total_value` /
  `.client_set_completed`. `load_session()` covers reprocessing when the
  player count changes.
- **Bag capacity assumption**: currently one 100%-capacity bag per player.
  If that ever changes (e.g. a player can make multiple trips), adjust
  `bag_capacity_units` per player in `solve()` - the solver already takes
  it as a parameter, it's just uniform across players for now.
