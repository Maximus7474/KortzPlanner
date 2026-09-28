"""Tkinter GUI for the Kortz Center heist optimizer.

Layout:
- "Add artifact" row: type a name (autocomplete against the static
  catalog), Tab/Enter to the price field, Enter to add it to the table.
- Table: one row per added artifact. Click the "Client Target" or
  "Solo OK" cell to toggle it. Double-click a row to edit its price or
  remove it.
- Bottom: player count + Skip buyer request toggle + Solve.
- Results panel: the resulting bag assignment, same info the CLI prints.
"""
import tkinter as tk
from tkinter import messagebox, ttk

from .catalog import CATALOG, CATALOG_BY_NAME
from .models import Artifact, CLIENT_SET_BONUS, price_warning
from .session import Session, load_session, save_session
from .solver import solve

CATALOG_NAMES = [name for name, _ in CATALOG]


class AutocompleteEntry(ttk.Entry):
    """
    A ttk.Entry with a lightweight autocomplete popup.
    """

    ROW_HEIGHT = 18
    MAX_VISIBLE_ROWS = 6

    def __init__(self, master=None, values=(), on_return=None, on_accept=None, **kwargs):
        super().__init__(master, **kwargs)
        self._all_values = list(values)
        self._on_return_cb = on_return
        self._on_accept_cb = on_accept
        self._popup = None
        self._listbox = None

        self.bind("<KeyRelease>", self._on_keyrelease)
        self.bind("<Down>", self._on_down)
        self.bind("<Up>", self._on_up)
        self.bind("<Return>", self._on_enter_key)
        self.bind("<Escape>", self._close_popup)
        self.bind("<FocusOut>", self._on_focus_out)

    # -- Entry-like API used elsewhere in the app --
    def set(self, value):
        self.delete(0, tk.END)
        self.insert(0, value)

    # -- filtering / popup lifecycle --
    def _matches(self, typed):
        if not typed:
            return ['No results']

        values = [v for v in self._all_values if typed.lower() in v.lower()]
        return values if len(values) > 0 else ['No results']

    def _on_keyrelease(self, event):
        if event.keysym in ("Up", "Down", "Return", "Escape", "Tab"):
            return
        matches = self._matches(self.get())
        if matches:
            self._show_popup(matches)
        else:
            self._close_popup()

    def _show_popup(self, matches):
        if self._popup is None:
            self._popup = tk.Toplevel(self)
            self._popup.wm_overrideredirect(True)
            try:
                self._popup.wm_attributes("-topmost", True)
            except tk.TclError:
                pass
            self._listbox = tk.Listbox(self._popup, activestyle="dotbox", exportselection=False)
            self._listbox.pack(fill="both", expand=True)
            self._listbox.bind("<ButtonRelease-1>", self._on_listbox_click)

        if self._listbox is None:
            return

        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        width = max(self.winfo_width(), 160)
        visible_rows = min(self.MAX_VISIBLE_ROWS, len(matches))
        height = visible_rows * self.ROW_HEIGHT + 4
        self._popup.wm_geometry(f"{width}x{height}+{x}+{y}")

        self._listbox.delete(0, tk.END)
        for m in matches:
            self._listbox.insert(tk.END, m)
        self._listbox.selection_clear(0, tk.END)
        self._listbox.selection_set(0)

        # Keep keyboard focus on the entry - the popup is purely visual
        # (and mouse-clickable) until Enter/Down explicitly engages it.
        self.focus_set()

    def _close_popup(self, event=None):
        if self._popup is not None:
            self._popup.destroy()
            self._popup = None
            self._listbox = None

    def _on_focus_out(self, event):
        # A click on the popup fires FocusOut just before the click itself
        # registers - give it a moment before deciding to close.
        self.after(150, self._close_if_focus_elsewhere)

    def _close_if_focus_elsewhere(self):
        focused = self.focus_get()
        if focused is self or focused is self._listbox:
            return
        self._close_popup()

    # -- keyboard navigation (focus stays on the entry throughout) --
    def _on_down(self, event):
        if self._listbox is None:
            return
        self._move_selection(1)
        return "break"

    def _on_up(self, event):
        if self._listbox is None:
            return

        self._move_selection(-1)
        return "break"

    def _move_selection(self, delta):
        if self._listbox is None:
            return

        size = self._listbox.size()
        if size == 0:
            return
        current = self._listbox.curselection()
        idx = current[0] if current else -1
        idx = max(0, min(size - 1, idx + delta))
        self._listbox.selection_clear(0, tk.END)
        self._listbox.selection_set(idx)
        self._listbox.see(idx)

    def _on_enter_key(self, event):
        if self._listbox is not None:
            sel = self._listbox.curselection()
            if sel:
                self._accept(self._listbox.get(sel[0]))
                return "break"
            self._close_popup()
        if self._on_return_cb:
            return self._on_return_cb(event)
        return None

    def _on_listbox_click(self, event):
        if self._listbox is None:
            return
        sel = self._listbox.curselection()
        if sel:
            self._accept(self._listbox.get(sel[0]))

    def _accept(self, value):
        self.set(value)
        self.icursor(tk.END)
        self._close_popup()
        self.focus_set()
        if self._on_accept_cb:
            self._on_accept_cb(value)


class KortzHeistApp(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.master = master
        master.title("Kortz Center Heist Optimizer")

        # name -> {"type": ArtifactType, "price": int,
        #          "client_target": bool, "solo_available": bool}
        self.items = {}

        self.pack(fill="both", expand=True)
        self._build_menu()
        self._build_widgets()
        self._maybe_offer_saved_session()

    def _build_menu(self):
        menubar = tk.Menu(self.master)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New session", command=self._on_clear_all)
        file_menu.add_command(label="Reload saved session", command=self._reload_from_disk)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.master.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        self.master.config(menu=menubar)

    def _build_widgets(self):
        add_frame = ttk.LabelFrame(self, text="Add artifact", padding=8)
        add_frame.pack(fill="x", pady=(0, 8))

        ttk.Label(add_frame, text="Name:").grid(row=0, column=0, sticky="w")
        self.name_box = AutocompleteEntry(
            add_frame, values=CATALOG_NAMES, width=28,
            on_return=self._on_name_enter, on_accept=self._on_name_enter,
        )
        self.name_box.grid(row=0, column=1, padx=4)

        ttk.Label(add_frame, text="Price: $").grid(row=0, column=2, sticky="w")
        self.price_var = tk.StringVar()
        self.price_entry = ttk.Entry(add_frame, textvariable=self.price_var, width=12)
        self.price_entry.grid(row=0, column=3, padx=4)
        self.price_entry.bind("<Return>", self._on_add)

        self.add_btn = ttk.Button(add_frame, text="Add (Enter)", command=self._on_add)
        self.add_btn.grid(row=0, column=4, padx=4)

        self.status_var = tk.StringVar()
        ttk.Label(add_frame, textvariable=self.status_var, foreground="#a05a00").grid(
            row=1, column=0, columnspan=5, sticky="w", pady=(4, 0)
        )

        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, pady=(0, 8))

        columns = ("name", "type", "price", "client", "solo")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=10)
        headings = {
            "name": "Artifact",
            "type": "Type",
            "price": "Price",
            "client": "Client Target",
            "solo": "Solo OK",
        }
        widths = {"name": 180, "type": 160, "price": 90, "client": 100, "solo": 80}
        for col in columns:
            self.tree.heading(col, text=headings[col])
            anchor = "center" if col in ("client", "solo") else "w"
            self.tree.column(col, width=widths[col], anchor=anchor)
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        self.tree.tag_configure("outlier", background="#fff3cd")
        self.tree.bind("<Button-1>", self._on_tree_click)
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<Delete>", self._on_tree_delete)

        bottom = ttk.Frame(self)
        bottom.pack(fill="x")

        ttk.Label(bottom, text="Players:").pack(side="left")
        self.players_var = tk.StringVar(value="2")
        self.players_box = ttk.Combobox(
            bottom, textvariable=self.players_var, values=["1", "2", "3", "4"],
            width=3, state="readonly",
        )
        self.players_box.pack(side="left", padx=(4, 12))
        self.players_box.bind("<Return>", lambda e: self._on_solve())

        # Toggle to ignore/skip buyer requirements
        self.skip_buyer_var = tk.BooleanVar(value=False)
        self.skip_buyer_check = ttk.Checkbutton(
            bottom, text="Skip buyer request", variable=self.skip_buyer_var
        )
        self.skip_buyer_check.pack(side="left", padx=(0, 12))

        self.solve_btn = ttk.Button(bottom, text="Solve (Enter)", command=self._on_solve)
        self.solve_btn.pack(side="left")

        ttk.Button(bottom, text="Remove selected", command=self._on_remove_selected).pack(
            side="left", padx=(12, 0)
        )
        ttk.Button(bottom, text="Clear all", command=self._on_clear_all).pack(side="left", padx=(6, 0))

        results_frame = ttk.LabelFrame(self, text="Plan", padding=8)
        results_frame.pack(fill="both", expand=True, pady=(8, 0))
        self.results_text = tk.Text(results_frame, height=14, wrap="word", state="disabled")
        self.results_text.pack(fill="both", expand=True)

        self.name_box.focus_set()

    # session I/O
    def _maybe_offer_saved_session(self):
        existing = load_session()
        if not existing:
            return
        message = f"Found a saved layout with {len(existing.artifacts)} artifact(s)."
        outliers = [a for a in existing.artifacts if price_warning(a.type, a.value)]
        if outliers:
            message += "\n\nFlagged prices:\n" + "\n".join(
                f"  - {a.name}: {price_warning(a.type, a.value)}" for a in outliers
            )
        message += "\n\nReuse it?"
        if messagebox.askyesno("Saved layout found", message, default="yes"):
            self._load_into_items(existing)

    def _reload_from_disk(self):
        existing = load_session()
        if not existing:
            messagebox.showinfo("No saved session", "There's no saved session to reload.")
            return
        self._load_into_items(existing)

    def _load_into_items(self, session: Session):
        self.items.clear()
        for a in session.artifacts:
            self.items[a.name] = {
                "type": a.type,
                "price": a.value,
                "client_target": a.is_client_target,
                "solo_available": a.solo_available,
            }
        self._refresh_table()

    def _save(self):
        save_session(Session(artifacts=self._current_artifacts(), client_set_bonus=CLIENT_SET_BONUS))

    def _current_artifacts(self):
        return [
            Artifact(
                name=name,
                type=d["type"],
                value=d["price"],
                is_client_target=d["client_target"],
                solo_available=d["solo_available"],
            )
            for name, d in self.items.items()
        ]

    # add flow
    def _match_catalog_name(self, typed: str):
        typed = typed.strip()
        return next((n for n in CATALOG_NAMES if n.lower() == typed.lower()), None)

    def _on_name_enter(self, event=None):
        match = self._match_catalog_name(self.name_box.get())
        if match is None:
            self.status_var.set(
                f"'{self.name_box.get()}' isn't in the catalog - pick a suggestion or check spelling."
            )
            return "break"
        self.name_box.set(match)
        self.status_var.set("")
        self.price_entry.focus_set()
        self.price_entry.select_range(0, tk.END)
        return "break"

    def _on_add(self, event=None):
        match = self._match_catalog_name(self.name_box.get())
        if match is None:
            self.status_var.set(
                f"'{self.name_box.get()}' isn't in the catalog - pick a suggestion or check spelling."
            )
            self.name_box.focus_set()
            return

        if match in self.items:
            self.status_var.set(f"'{match}' is already in the list - edit or remove that row instead.")
            return

        raw_price = self.price_var.get().strip().replace(",", "").replace("$", "")

        try:
            val = float(raw_price)
            if val <= 0:
                raise ValueError
            # If input is under 1,000, assume it is shorthand for thousands (e.g., 115 -> 115000, 75.5 -> 75500)
            if val < 1000:
                val *= 1000

            price = round(val)
        except ValueError:
            self.status_var.set("Enter a valid price (e.g., 115000 or 75.5 for 75000).")
            self.price_entry.focus_set()
            return

        art_type = CATALOG_BY_NAME[match]
        warning = price_warning(art_type, price)

        self.items[match] = {
            "type": art_type,
            "price": price,
            "client_target": False,
            "solo_available": True,
        }
        self._refresh_table()
        self._save()

        self.status_var.set(f"Added, but flagged: {warning}" if warning else f"Added {match}.")

        self.name_box.set("")
        self.price_var.set("")
        self.name_box.focus_set()

    def _refresh_table(self):
        self.tree.delete(*self.tree.get_children())
        for name, d in self.items.items():
            warning = price_warning(d["type"], d["price"])
            tags = ("outlier",) if warning else ()
            self.tree.insert(
                "", "end", iid=name,
                values=(
                    name,
                    d["type"].value,
                    f"${d['price']:,}",
                    "\u2611" if d["client_target"] else "\u2610",
                    "\u2611" if d["solo_available"] else "\u2610",
                ),
                tags=tags,
            )

    def _on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        row = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not row:
            return
        if col == "#4":
            self._toggle_client_target(row)
        elif col == "#5":
            self.items[row]["solo_available"] = not self.items[row]["solo_available"]
            self._refresh_table()
            self._save()

    def _toggle_client_target(self, name):
        data = self.items[name]
        currently_on = sum(1 for d in self.items.values() if d["client_target"])
        if not data["client_target"] and currently_on >= 3:
            messagebox.showinfo("Client set", "Only three items can be marked as the client's request.")
            return
        data["client_target"] = not data["client_target"]
        self._refresh_table()
        self._save()

    def _on_tree_double_click(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            self._open_edit_dialog(row)

    def _on_tree_delete(self, event):
        for row in self.tree.selection():
            self.items.pop(row, None)
        self._refresh_table()
        self._save()

    def _on_remove_selected(self):
        self._on_tree_delete(None)

    def _on_clear_all(self):
        if self.items and not messagebox.askyesno("Clear all", "Remove every item from the plan?"):
            return
        self.items.clear()
        self._refresh_table()
        self._save()

    def _open_edit_dialog(self, name):
        data = self.items[name]
        dialog = tk.Toplevel(self)
        dialog.title(f"Edit {name}")
        dialog.transient(self.master)
        dialog.grab_set()

        ttk.Label(dialog, text=f"{name} ({data['type'].value})").grid(
            row=0, column=0, columnspan=2, padx=8, pady=(8, 4), sticky="w"
        )

        ttk.Label(dialog, text="Price: $").grid(row=1, column=0, padx=8, sticky="e")
        price_var = tk.StringVar(value=str(data["price"]))
        price_entry = ttk.Entry(dialog, textvariable=price_var, width=12)
        price_entry.grid(row=1, column=1, padx=8, pady=4, sticky="w")
        price_entry.focus_set()
        price_entry.select_range(0, tk.END)

        client_var = tk.BooleanVar(value=data["client_target"])
        ttk.Checkbutton(dialog, text="Client target", variable=client_var).grid(
            row=2, column=0, columnspan=2, padx=8, sticky="w"
        )
        solo_var = tk.BooleanVar(value=data["solo_available"])
        ttk.Checkbutton(dialog, text="Solo obtainable", variable=solo_var).grid(
            row=3, column=0, columnspan=2, padx=8, sticky="w"
        )

        warn_var = tk.StringVar()
        ttk.Label(dialog, textvariable=warn_var, foreground="#a05a00", wraplength=260).grid(
            row=4, column=0, columnspan=2, padx=8, sticky="w"
        )

        def save_and_close(event=None):
            raw = price_var.get().strip().replace(",", "").replace("$", "")
            if not raw.isdigit():
                warn_var.set("Enter a whole-number price.")
                return
            new_price = int(raw)
            if client_var.get() and not data["client_target"]:
                currently_on = sum(1 for d in self.items.values() if d["client_target"])
                if currently_on >= 3:
                    warn_var.set("Only three items can be the client's request.")
                    return
            data["price"] = new_price
            data["client_target"] = client_var.get()
            data["solo_available"] = solo_var.get()
            self._refresh_table()
            self._save()
            dialog.destroy()

        def remove_and_close():
            self.items.pop(name, None)
            self._refresh_table()
            self._save()
            dialog.destroy()

        btns = ttk.Frame(dialog)
        btns.grid(row=5, column=0, columnspan=2, pady=8)
        ttk.Button(btns, text="Save (Enter)", command=save_and_close).pack(side="left", padx=4)
        ttk.Button(btns, text="Remove item", command=remove_and_close).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel (Esc)", command=dialog.destroy).pack(side="left", padx=4)

        dialog.bind("<Return>", save_and_close)
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    def _on_solve(self):
        if not self.items:
            messagebox.showinfo("Nothing to solve", "Add at least one artifact first.")
            return
        num_players = int(self.players_var.get())
        skip_buyer = self.skip_buyer_var.get()
        artifacts = self._current_artifacts()

        lines = []
        if skip_buyer:
            lines.append("NOTE: Ignoring buyer/client set requirements.")

        if num_players == 1:
            solo_locked = [a for a in artifacts if not a.solo_available]
            if solo_locked:
                lines.append("NOTE: running solo - these may not actually be obtainable:")
                lines.extend(f"  - {a.name}" for a in solo_locked)
                lines.append("")

        result = None
        try:
            result = solve(
                artifacts,
                num_players,
                client_set_bonus=CLIENT_SET_BONUS,
                require_client_set=not self.skip_buyer_var.get()
            )
        except (ValueError, RuntimeError, KeyError) as error:
            print('Failed to solve the task')
            print(error)
            lines.append(f"ERROR: {error}")

        if result:
            for i, bag in enumerate(result.assignment, start=1):
                bag_value = sum(a.value for a in bag)
                used_percent = sum(a.space_percent for a in bag)
                lines.append(f"Player {i} bag ({used_percent}% full, ${bag_value:,}):")
                for a in bag:
                    lines.append(f"  - {a.name:<35} [ {a.space_percent:>}% | {a.value:>7,}$ ] {"BR" if a.is_client_target else ""}")
                lines.append("")

            lines.append(f"Client set completed:  {result.client_set_completed} (bonus: ${result.bonus_applied:,})")
            lines.append(f"TOTAL PAYOUT:          ${result.total_value:,}")

        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", tk.END)
        self.results_text.insert("1.0", "\n".join(lines))
        self.results_text.configure(state="disabled")


def main():
    root = tk.Tk()
    KortzHeistApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
