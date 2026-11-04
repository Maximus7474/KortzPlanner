"""Tkinter GUI for the Kortz Center heist optimizer.

Layout:
- Setup page: "Add artifact" row (autocomplete name + price), the artifact
  table (newest addition first by default), then the configuration options
  (players, difficulty, primary target value, and the two flags).
- Plan page: shown once a plan is established; hides the setup page and
  lists each player's bag plus their estimated payout.
"""
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from .catalog import CATALOG_BY_NAME, CATALOG_NAMES
from .models import Artifact, ArtifactLocations, price_warning
from .payout import PayoutEstimate, estimate_payouts
from .session import Session, DIFFICULTIES, load_session, save_session
from .updater import check_for_updates
from .solver import solve


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

        # name -> {"type": ArtifactType, "price": int,
        #          "client_target": bool, "solo_available": bool}
        self.items = {}

        self.primary_value = 0

        # Sorting state
        self._sort_column = None
        self._sort_reverse = False

        self._last_estimate: PayoutEstimate | None = None
        self._summary_text = ""

        self.pack(fill="both", expand=True)
        self._build_menu()
        self._build_setup_page()
        self._build_results_page()
        self._show_setup()
        self._maybe_offer_saved_session()

    def _build_menu(self):
        menubar = tk.Menu(self.master)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New session", command=self._on_new_session)
        file_menu.add_command(label="Reload saved session", command=self._reload_from_disk)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.master.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        self.master.config(menu=menubar)

    def _build_setup_page(self):
        self.setup_page = ttk.Frame(self)

        add_frame = ttk.LabelFrame(self.setup_page, text="Add artifact", padding=8)
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

        table_frame = ttk.Frame(self.setup_page)
        table_frame.pack(fill="both", expand=True, pady=(0, 8))

        columns = ("name", "type", "price", "client", "solo")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=10)
        self._headings = {
            "name": "Artifact",
            "type": "Type",
            "price": "Price",
            "client": "Client Target",
            "solo": "Solo OK",
        }
        widths = {"name": 180, "type": 160, "price": 90, "client": 100, "solo": 80}
        for col in columns:
            self.tree.heading(col, text=self._headings[col], command=lambda c=col: self._sort_by_column(c))
            anchor = "center" if col in ("client", "solo") else "w"
            self.tree.column(col, width=widths[col], anchor=anchor)
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        self.tree.tag_configure("outlier", background="#fff3cd")
        self.tree.bind("<Button-1>", self._on_tree_click)
        self.tree.bind("<Double-1>", self._on_tree_double_click)

        # controls / options section
        controls_frame = ttk.LabelFrame(self.setup_page, text="Configuration & Controls", padding=8)
        controls_frame.pack(fill="x", pady=(0, 8))

        # config row: players & toggles
        cfg_row = ttk.Frame(controls_frame)
        cfg_row.pack(fill="x", pady=(0, 6))

        ttk.Label(cfg_row, text="Players:").pack(side="left")
        self.players_var = tk.StringVar(value="2")
        self.players_box = ttk.Combobox(
            cfg_row, textvariable=self.players_var, values=["1", "2", "3", "4"],
            width=3, state="readonly",
        )
        self.players_box.pack(side="left", padx=(4, 16))
        self.players_box.bind("<<ComboboxSelected>>", self._update_solo_options)
        self.players_box.bind("<Return>", lambda e: self._on_solve())

        ttk.Label(cfg_row, text="Difficulty:").pack(side="left")
        self.difficulty_var = tk.StringVar(value="Normal")
        self.difficulty_box = ttk.Combobox(
            cfg_row, textvariable=self.difficulty_var, values=list(DIFFICULTIES),
            width=10, state="readonly",
        )
        self.difficulty_box.pack(side="left", padx=(4, 16))
        self.difficulty_box.bind("<Return>", lambda e: self._on_solve())

        # primary target value
        primary_row = ttk.Frame(controls_frame)
        primary_row.pack(fill="x", pady=(0, 6))

        ttk.Label(primary_row, text="Primary target value: $").pack(side="left")
        self.primary_var = tk.StringVar()
        self.primary_entry = ttk.Entry(primary_row, textvariable=self.primary_var, width=14)
        self.primary_entry.pack(side="left", padx=(4, 8))
        self.primary_entry.bind("<Return>", self._on_primary_enter)
        self.primary_entry.bind("<FocusOut>", self._commit_primary)

        # flags
        flags_row = ttk.Frame(controls_frame)
        flags_row.pack(fill="x", pady=(0, 6))

        self.skip_buyer_var = tk.BooleanVar(value=False)
        self.skip_buyer_check = ttk.Checkbutton(
            flags_row, text="Ignore buyer request", variable=self.skip_buyer_var
        )
        self.skip_buyer_check.pack(side="left", padx=(0, 16))

        self.skip_inaccessible_var = tk.BooleanVar(value=False)
        self.skip_inaccessible_check = ttk.Checkbutton(
            flags_row, text="Skip inaccessible loot (solo)", variable=self.skip_inaccessible_var
        )
        self.skip_inaccessible_check.pack(side="left")

        self.plan_error_var = tk.StringVar()
        ttk.Label(
            controls_frame,
            textvariable=self.plan_error_var,
            foreground="#b00020",
            wraplength=720,
            justify="left",
        ).pack(fill="x", pady=(0, 4))

        # action button row
        btn_row = ttk.Frame(controls_frame)
        btn_row.pack(fill="x")

        self.solve_btn = ttk.Button(btn_row, text="Establish plan (Enter)", command=self._on_solve)
        self.solve_btn.pack(side="left", padx=(0, 12))

        self.clear_btn = ttk.Button(btn_row, text="Clear All", command=self._on_clear_all)
        self.clear_btn.pack(side="left")

        self._update_solo_options()

    def _build_results_page(self):
        self.results_page = ttk.Frame(self)

        header = ttk.Frame(self.results_page)
        header.pack(fill="x", pady=(0, 6))

        ttk.Label(
            header, text="Plan established", font=("Segoe UI", 13, "bold")
        ).pack(anchor="w")

        self.results_summary_var = tk.StringVar()
        ttk.Label(
            header,
            textvariable=self.results_summary_var,
            justify="left",
            wraplength=920,
        ).pack(anchor="w", pady=(2, 2))

        self.results_notes_var = tk.StringVar()
        ttk.Label(
            header,
            textvariable=self.results_notes_var,
            foreground="#a05a00",
            justify="left",
            wraplength=920,
        ).pack(anchor="w")

        scroll_container = ttk.Frame(self.results_page)
        scroll_container.pack(fill="both", expand=True, pady=(0, 6))

        self._results_canvas = tk.Canvas(scroll_container, highlightthickness=0)
        results_scrollbar = ttk.Scrollbar(
            scroll_container, orient="vertical", command=self._results_canvas.yview
        )
        self._results_canvas.configure(yscrollcommand=results_scrollbar.set)
        results_scrollbar.pack(side="right", fill="y")
        self._results_canvas.pack(side="left", fill="both", expand=True)

        self.cards_frame = ttk.Frame(self._results_canvas)
        self._cards_window = self._results_canvas.create_window(
            (0, 0), window=self.cards_frame, anchor="nw"
        )
        self.cards_frame.bind("<Configure>", self._on_cards_configure)
        self._results_canvas.bind("<Configure>", self._on_canvas_configure)
        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self._results_canvas.bind(sequence, self._on_results_wheel)

        footer = ttk.Frame(self.results_page)
        footer.pack(fill="x")

        ttk.Button(footer, text="Back to setup", command=self._show_setup).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(footer, text="Copy summary", command=self._copy_summary).pack(side="left")

        self.copy_status_var = tk.StringVar()
        ttk.Label(
            footer, textvariable=self.copy_status_var, foreground="#2a7f2a"
        ).pack(side="left", padx=8)

    def _on_cards_configure(self, event=None):
        self._results_canvas.configure(scrollregion=self._results_canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._results_canvas.itemconfigure(self._cards_window, width=event.width)

    def _on_results_wheel(self, event):
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            delta = -1 if event.delta > 0 else 1
        self._results_canvas.yview_scroll(delta, "units")
        return "break"

    def _bind_results_wheel(self, widget):
        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            widget.bind(sequence, self._on_results_wheel, add="+")
        for child in widget.winfo_children():
            self._bind_results_wheel(child)

    def _show_setup(self):
        self.results_page.pack_forget()
        self.setup_page.pack(fill="both", expand=True)
        self.name_box.focus_set()

    def _show_results(self):
        self.setup_page.pack_forget()
        self.results_page.pack(fill="both", expand=True)
        self._results_canvas.yview_moveto(0)

    def _on_new_session(self):
        if self.items and not messagebox.askyesno(
            "New session", "Remove every item and start over?"
        ):
            return
        self.items.clear()
        self.primary_value = 0
        self.primary_var.set("")
        self._reset_sort()
        self._refresh_table()
        self._save()
        self._show_setup()

    def _update_solo_options(self, event=None):
        """Enable/disable solo options based on the player count."""
        is_solo = self.players_var.get() == "1"
        if is_solo:
            self.skip_inaccessible_check.configure(state="normal")
        else:
            self.skip_inaccessible_check.configure(state="disabled")
            self.skip_inaccessible_var.set(False)

    # session I/O
    def _maybe_offer_saved_session(self):
        existing = load_session()
        if not existing:
            return
        message = f"Found a saved layout with {len(existing.artifacts)} artifact(s)."
        if existing.primary_target_value:
            message += f"\nPrimary target: ${existing.primary_target_value:,}"
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
        self._show_setup()

    def _load_into_items(self, session: Session):
        self.items.clear()
        for a in session.artifacts:
            self.items[a.name] = {
                "type": a.type,
                "price": a.value,
                "client_target": a.is_client_target,
                "solo_available": a.solo_available,
            }
        self.difficulty_var.set(session.difficulty)
        self.primary_value = session.primary_target_value
        self.primary_var.set(
            f"{session.primary_target_value:,}" if session.primary_target_value else ""
        )
        self._reset_sort()
        self._refresh_table()

    def _save(self):
        value, error = self._parse_primary_amount()
        if error is None:
            self.primary_value = value

        save_session(Session(
            artifacts=self._current_artifacts(),
            difficulty="Hard" if self.difficulty_var.get() == "Hard" else "Normal",
            primary_target_value=self.primary_value,
        ))

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
            if val < 1000:
                val *= 1000

            price = round(val)
        except ValueError:
            self.status_var.set("Enter a valid price (e.g., 115000 or 75.5 for 75000).")
            self.price_entry.focus_set()
            return

        artifact = CATALOG_BY_NAME[match]
        warning = price_warning(artifact.type, price)

        self.items[match] = {
            "type": artifact.type,
            "price": price,
            "client_target": False,
            "solo_available": artifact.location != ArtifactLocations.CRISPGALLERY,
        }

        self._reset_sort()
        self._refresh_table()
        self._save()

        self.status_var.set(f"Added, but flagged: {warning}" if warning else f"Added {match}.")

        self.name_box.set("")
        self.price_var.set("")
        self.name_box.focus_set()

    # primary target
    def _parse_primary_amount(self) -> tuple[int | None, str | None]:
        raw = self.primary_var.get().strip().replace(",", "").replace("$", "")
        if not raw:
            return 0, None
        try:
            value = float(raw)
        except ValueError:
            return None, "Enter the primary target as a number (e.g. 1200000 or 1200)."
        if value < 0:
            return None, "The primary target value can't be negative."
        if value < 1000:
            value *= 1000
        return round(value), None

    def _commit_primary(self, event=None):
        value, error = self._parse_primary_amount()
        if error:
            self.plan_error_var.set(error)
            return "break"
        self.primary_value = value
        self.primary_var.set(f"{value:,}" if value else "")
        self._save()
        return "break"

    def _on_primary_enter(self, event=None):
        self._commit_primary()
        self._on_solve()
        return "break"

    # sorting logic
    def _reset_sort(self):
        self._sort_column = None
        self._sort_reverse = False
        for column_key, base_title in self._headings.items():
            self.tree.heading(column_key, text=base_title)

    def _sort_by_column(self, col):
        if self._sort_column == col:
            if self._sort_reverse:
                self._sort_reverse = False
                self._sort_column = None
            else:
                self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = col
            self._sort_reverse = False

        for column_key, base_title in self._headings.items():
            if column_key == self._sort_column:
                indicator = " ▲" if not self._sort_reverse else " ▼"
                self.tree.heading(column_key, text=base_title + indicator)
            else:
                self.tree.heading(column_key, text=base_title)

        self._refresh_table()

    def _get_sort_key(self, item_entry):
        name, d = item_entry
        if self._sort_column == "name":
            return name.lower()
        elif self._sort_column == "type":
            return d["type"].value.lower()
        elif self._sort_column == "price":
            return d["price"]
        elif self._sort_column == "client":
            return d["client_target"]
        elif self._sort_column == "solo":
            return d["solo_available"]
        return name.lower()

    def _refresh_table(self):
        self.tree.delete(*self.tree.get_children())

        item_entries = list(self.items.items())
        if self._sort_column:
            item_entries.sort(key=self._get_sort_key, reverse=self._sort_reverse)
        else:
            # Default view: most recent addition first.
            item_entries.reverse()

        for name, d in item_entries:
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

        solo_text = f"{"\u2611" if data["solo_available"] else "\u2610"} Solo obtainable"
        ttk.Label(dialog, text=solo_text).grid(
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
        self.plan_error_var.set("")
        if not self.items:
            messagebox.showinfo("Nothing to solve", "Add at least one artifact first.")
            return

        primary_value, error = self._parse_primary_amount()
        if error:
            self.plan_error_var.set(error)
            self.primary_entry.focus_set()
            return

        skip_buyer = self.skip_buyer_var.get()
        client_count = sum(1 for d in self.items.values() if d["client_target"])
        if not skip_buyer and client_count < 2:
            self.plan_error_var.set(
                "Missing artifacts for the buyer's request"
                "or enable 'Ignore buyer request'."
            )
            return

        self.primary_value = primary_value
        self.primary_var.set(f"{primary_value:,}" if primary_value else "")
        self._save()

        self.solve_btn.configure(state="disabled", text="Calculating...")
        self.clear_btn.configure(state="disabled")

        # force redraw prior to heavier computing task
        # (is the case on 2+ players)
        self.update_idletasks()

        num_players = int(self.players_var.get())
        skip_inaccessible = self.skip_inaccessible_var.get()
        artifacts = self._current_artifacts()

        lines = []
        if skip_buyer:
            lines.append("NOTE: Fulfilling buyer request is optional (maximizing profit).")

        if num_players == 1:
            solo_locked = [a for a in artifacts if not a.solo_available]
            if solo_locked:
                if skip_inaccessible:
                    lines.append("NOTE: Skipping inaccessible items for solo run.")
                else:
                    lines.append("NOTE: Running solo - these items require 2+ players:")
                    lines.extend(f"  - {a.name}" for a in solo_locked)
            lines.append("")

        result = None
        try:
            result = solve(
                artifacts,
                num_players,
                difficulty=self.difficulty_var.get(),
                require_client_set=not skip_buyer,
                skip_inaccessible=skip_inaccessible,
            )
        except ValueError as error:
            self.plan_error_var.set(f"Cannot establish plan: {error}")
        finally:
            self.solve_btn.configure(state="normal", text="Solve Plan (Enter)")
            self.clear_btn.configure(state="normal")

        if result:
            self._render_results(result, primary_value, lines)
            self._show_results()

    def _render_results(self, result, primary_value, lines):
        estimate = estimate_payouts(
            result.assignment,
            result.bonus_applied,
            len(result.assignment),
            primary_value,
            left_behind=result.left_behind,
        )
        self._last_estimate = estimate
        num_players = estimate.num_players

        if estimate.buyer_bonus_per_player:
            buyer_text = f"+${estimate.buyer_bonus_per_player:,}"
        else:
            buyer_text = "$0 (request not fulfilled)"

        self.results_summary_var.set(
            f"{num_players} player{"s" if num_players > 1 else ""}\n"
            f"Primary target ${estimate.primary_total:,} - "
            f"Secondary loot ${estimate.loot_total:,}\n"
            f"Buyer request {buyer_text} - "
            f"Estimated crew payout: ${estimate.crew_total:,}"
        )

        notes = list(lines)
        self.results_notes_var.set("\n".join(notes))

        for child in self.cards_frame.winfo_children():
            child.destroy()

        self.cards_frame.columnconfigure(0, weight=1, uniform="card")
        self.cards_frame.columnconfigure(1, weight=1, uniform="card")

        for index, payout in enumerate(estimate.players):
            card = ttk.LabelFrame(
                self.cards_frame,
                text=f"Player {payout.player} — {payout.role}",
                padding=10,
            )
            card.grid(row=index // 2, column=index % 2, sticky="nsew", padx=6, pady=6)

            ttk.Label(
                card,
                text=f"Bag {payout.used_percent}% full · ${payout.bag_value:,} in loot",
            ).pack(anchor="w", pady=(0, 4))

            tree = ttk.Treeview(
                card,
                columns=("space", "value"),
                show="tree headings",
                height=max(1, len(payout.artifacts)),
            )
            tree.heading("#0", text="Artifact")
            tree.heading("space", text="Space")
            tree.heading("value", text="Value")
            tree.column("#0", width=280, anchor="w")
            tree.column("space", width=110, anchor="center")
            tree.column("value", width=110, anchor="e")
            tree.pack(fill="x", expand=True, pady=(0, 6))

            if payout.artifacts:
                for a in payout.artifacts:
                    flags = []
                    if a.is_client_target:
                        flags.append("REQ")
                    if num_players == 1 and not a.solo_available:
                        flags.append("LOCKED")
                    label = a.name + (f" [{'/'.join(flags)}]" if flags else "")
                    tree.insert(
                        "", "end",
                        text=label,
                        values=(f"{a.space_percent}%", f"${a.value:,}"),
                    )
            else:
                tree.insert("", "end", text="(empty bag)", values=("", ""))

            breakdown = ttk.Frame(card)
            breakdown.pack(fill="x")

            rows = [("Secondary loot share", payout.loot_share)]
            if payout.primary_share:
                rows.append(("Primary target (100%)", payout.primary_share))
            if payout.flat_cut:
                rows.append(("Task cut", payout.flat_cut))
            rows.append(("Buyer request bonus", payout.buyer_bonus))

            for row, (label, value) in enumerate(rows):
                ttk.Label(breakdown, text=label).grid(row=row, column=0, sticky="w")
                ttk.Label(breakdown, text=f"${value:,}").grid(row=row, column=1, sticky="e")
            breakdown.columnconfigure(0, weight=1)

            ttk.Separator(card, orient="horizontal").pack(fill="x", pady=(6, 2))
            ttk.Label(
                card,
                text=f"Estimated payout: ${payout.total:,}",
                font=("Segoe UI", 10, "bold"),
            ).pack(anchor="e")

        self._summary_text = self._format_summary(estimate)
        self.copy_status_var.set("")
        self._bind_results_wheel(self.cards_frame)
        self._results_canvas.yview_moveto(0)

    def _format_summary(self, estimate: PayoutEstimate) -> str:
        lines = [
            "```",
            f"Kortz Center Heist — {estimate.num_players} Player{"s" if estimate.num_players > 1 else ""}",
            f"Secondary Loot: ${estimate.loot_total:,} | Primary Target:${estimate.primary_total:,}",
            f"Buyer Bonus:    ${estimate.buyer_bonus_per_player:,} ({'Completed' if estimate.buyer_bonus_per_player else 'Skipped'})\n",
            "",
        ]
        for payout in estimate.players:
            lines.append(f"Player {payout.player} ({payout.role}) — Bag: {payout.used_percent}% | ${payout.bag_value:,}")
            if payout.artifacts:
                for artifact in payout.artifacts:
                    flags = []
                    if artifact.is_client_target:
                        flags.append("REQ")
                    if estimate.num_players == 1 and not artifact.solo_available:
                        flags.append("LOCKED")
                    flag_str = f" [{'/'.join(flags)}]" if flags else ""

                    name_display = artifact.name + flag_str
                    lines.append(f" • {name_display:<26} {artifact.space_percent:>3}%   ${artifact.value:>9,}")
            else:
                lines.append(" • (empty bag)")

            lines.append(f"➔ Player Payout: ${payout.total:,}")
            lines.append("")

        lines.append(f"Estimated Crew Total: ${estimate.crew_total:,}")
        lines.append("```")

        return "\n".join(lines)

    def _copy_summary(self):
        if not self._summary_text:
            return
        self.master.clipboard_clear()
        self.master.clipboard_append(self._summary_text)
        self.copy_status_var.set("Copied to clipboard.")
        self.after(2000, lambda: self.copy_status_var.set(""))


def main():
    root = tk.Tk()
    root.title("Kortz Center Heist Optimizer")
    root.minsize(980, 700)

    threading.Thread(
        target=check_for_updates,
        args=(root,),
        daemon=True
    ).start()

    KortzHeistApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
