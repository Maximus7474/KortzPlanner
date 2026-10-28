import json
import sys
import urllib.request
import webbrowser
from packaging.version import Version
import tkinter as tk

from .version import __version__

GITHUB_REPO = "Maximus7474/KortzPlanner"

def show_update_window(root: tk.Tk, current_version: str, latest_tag: str, release_url: str):
    """Opens a custom modal child window with dedicated action buttons."""
    win = tk.Toplevel(root)
    win.title("Update Available")
    win.geometry("400x180")
    win.resizable(False, False)

    # Make it modal so it locks focus to the dialog
    win.transient(root)
    win.grab_set()

    # Center the window relative to the main app
    win.update_idletasks()
    x = root.winfo_x() + (root.winfo_width() // 2) - 200
    y = root.winfo_y() + (root.winfo_height() // 2) - 90
    win.geometry(f"+{x}+{y}")

    # Message text
    msg = (
        f"A new version of KortzHeistOptimizer is available!\n\n"
        f"Current Version: {current_version}\n"
        f"Latest Version:  {latest_tag}"
    )
    tk.Label(win, text=msg, justify="left", font=("Segoe UI", 9)).pack(padx=20, pady=20)

    # Buttons Frame
    btn_frame = tk.Frame(win)
    btn_frame.pack(pady=5)

    def open_browser():
        webbrowser.open(release_url)
        win.destroy()

    def copy_link():
        win.clipboard_clear()
        win.clipboard_append(release_url)

    # Action buttons
    tk.Button(btn_frame, text="Open in Browser", command=open_browser, width=15).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="Close", command=win.destroy, width=8).pack(side=tk.LEFT, padx=5)


def check_for_updates(root: tk.Tk | None = None):
    """
    Queries GitHub releases API to check if a newer version exists.
    Runs quietly if offline or if the API rate limit is hit.
    """
    if __version__ == "dev":
        return

    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "KortzHeistOptimizer-Updater"}
        )

        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode())
            latest_tag = data.get("tag_name")
            release_url = data.get("html_url")

            if not latest_tag:
                return

            if Version(latest_tag) > Version(__version__):
                if root:
                    root.after(50, lambda: show_update_window(root, __version__, latest_tag, release_url))
                else:
                    print(
                        f"\n"
                        f"┌──────────────────────────────────────────────────────────────────┐\n"
                        f"│                         UPDATE AVAILABLE                         │\n"
                        f"├──────────────────────────────────────────────────────────────────┤\n"
                        f"│  Current Version: {__version__:<46} │\n"
                        f"│  Latest Version:  {latest_tag:<46} │\n"
                        f"│                                                                  │\n"
                        f"│  Download:                                                       │\n"
                        f"│  {release_url:<63} │\n"
                        f"└──────────────────────────────────────────────────────────────────┘\n"
                    )
            else:
                if not root:
                    print("You are running the latest version.")

    except Exception as e:
        if not root:
            print(f"Could not check for updates: {e}", file=sys.stderr)
