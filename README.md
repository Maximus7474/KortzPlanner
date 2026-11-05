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
  flat, fixed **$100,000 bonus per participant** (`CLIENT_SET_BONUS` in
  `models.py`) on
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
  take, and which player carries each, to maximize total crew payout (loot
  value plus the bonus paid to every participant). `solver.solve()` finds
  the exact optimum via memoized search (fine for a single heist's item
  count; not built to scale to huge item lists).
- Solo runs (1 player): items marked `solo_available=False` are **not**
  auto-excluded.

## Estimated per-player payout

After a plan is established, the app reports what each participant actually
receives:

| Component | Owner (P1) | Each accomplice (P2-P4) |
|---|---|---|
| Primary target | 100% of the entered value | $0 |
| Task cut | - | $100,000 |
| Secondary loot (every artifact in a bag) | even split (+ remainder) | even split |
| Buyer request bonus (50k Normal / 100k Hard) | paid in full | paid in full |

The buyer-request bonus is paid individually on top of everything and is
never split. Left-behind loot is not counted. If the secondary split does
not divide evenly, the remainder goes to the owner so the totals reconcile
exactly. The primary target value is a separate input, not an artifact: it
does not consume bag space.

## Layout

```
kortz_heist/
  models.py   - Artifact / ArtifactType, space-cost table
  catalog.py  - CATALOG: static (name, type) roster - edit to match the
                real full item list, up to ~30 entries
  session.py  - Session: this heist's prices + flags + primary target;
                build/save/load
  payout.py   - per-player payout estimate (owner/accomplice split)
  solver.py   - solve(artifacts, num_players, ...) -> SolveResult
  gui.py      - Tkinter GUI: same workflow, point-and-click
run_gui.py    - PyInstaller entry point for the GUI (see "Packaging" below)
session.json  - saved automatically after building a session (gitignore
                this if you don't want it committed)
```

## Running it

Launch the graphical interface:
```
python -m kortz_heist.gui
```

The GUI provides a point-and-click workflow for artifact entry, flagging, and solving. It is ideal for interactive use, visual verification, and managing the client target / solo availability flags.

### Difficulty Bonuses
- **Normal difficulty**: $50,000 flat bonus per participant for completing the client's three-piece request.
- **Hard difficulty**: $100,000 flat bonus per participant for completing the client's three-piece request.

These values are defined in `models.py` `CLIENT_SET_BONUS` and are paid individually on top of each participant's share when all three client-target items are secured.

First run (either one): enter a price for each artifact on offer this
heist (out-of-range prices get flagged inline but are still accepted),
which three are the client's request, and which are solo-unavailable.
This gets saved to `session.json`. (The client-set bonus is fixed, so it
isn't asked for.)

**Reprocessing after a player-count change**: run it again (GUI) -
it detects the saved session and offers to reuse it. Accept, and you're
only asked for the new player count; none of the prices/flags need
re-entering. To start a fresh heist, delete `session.json` (or decline the
reuse prompt / use File > New session in the GUI) and enter a new one.

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
- **File menu**: "New session" clears everything, "Reload saved session" reverts to what's on disk, discarding unsaved changes.
- **Primary target value**: enter the value of the primary target in the
  configuration section. It is paid in full to you (P1) and is never part
  of the secondary-loot split. Blank means $0.
- **Establish plan**: hides the setup page and opens a plan page listing
  each player's artifacts plus their estimated payout. "Back to setup"
  returns without losing what you entered.
- Every add/edit/remove/toggle auto-saves to `session.json`.
- Set the player count, difficulty and primary target value, then click "Establish plan" (or press Enter
  with focus on the player-count or primary-target box). The setup page is hidden and a plan page shows each player's loot and estimated payout.

### GUI Checkbox Behaviors
- **Ignore buyer request**: When checked, the solver maximizes profit without requiring the client's three-piece set. The client-set bonus is still available if all three targets are collected incidentally, but it's not required for a valid solution. This is useful when you only care about total value rather than fulfilling the client's specific request.
- **Skip inaccessible loot (solo)**: When running with 1 player, checking this flag automatically excludes artifacts marked `solo_available=False` from the solving process. Unchecking it (the default) will include those items in the plan but flag them with a "LOCKED" warning so you can decide if they're actually reachable with crew members.

These two flags interact: with solo mode + skip inaccessible enabled + ignore buyer unchecked, you get the strictest validation; with ignore buyer checked, the client-set requirement is waived regardless of solo/squad mode.

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
  type only - no price, since that's per-heist) - Note: it should be already complete.
- **A different GUI**: `solver.solve()`, `models`, `catalog`, and
  `session` have no UI dependency - `gui.py` is just one consumer of them.
  Any other frontend can build a `{name: price}` dict, call
  `build_session(...)`, `save_session` it, then
  `solve(session.artifacts, num_players, difficulty=...)`, call
  `payout.estimate_payouts(...)` for per-player cuts, and render
  `SolveResult.assignment` / `.left_behind` / `.total_value` /
  `.client_set_completed`. `load_session()` covers reprocessing when the
  player count changes.
- **Bag capacity assumption**: currently one 100%-capacity bag per player.
  If that ever changes (e.g. a player can make multiple trips), adjust
  `bag_capacity_units` per player in `solve()` - the solver already takes
  it as a parameter, it's just uniform across players for now.
