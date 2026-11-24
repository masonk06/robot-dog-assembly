"""Focused, telemetry-only screen for manual conservative joint-limit capture."""
import argparse
from pathlib import Path
import tkinter as tk
from tkinter import ttk

from esp32_joint_check_view import JointCheckView


class LimitFocus(JointCheckView):
    """Reuse the guarded capture logic while presenting one joint at a time."""

    def __init__(self, root, zero_path, checks_path):
        super().__init__(root, zero_path, checks_path)
        root.title('Luca • one-joint conservative limit capture • READ ONLY')
        root.geometry('1280x780')
        self.mode.set('Limits')
        self.select_joint()
        # The full grid is useful for a summary, but obscures the selected
        # joint during manual endpoint work.  The selector remains above it.
        self.table.configure(height=1)
        ttk.Label(root, text=(
            'LIMIT FOCUS: select one joint, capture neutral, then choose two comfortable '
            'backed-off endpoints. The screen is a reference only; never seek a hard stop.'
        ), foreground='#9a3e10').pack(anchor='w', padx=10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zeros', type=Path, required=True)
    parser.add_argument('--checks', type=Path, required=True,
                        help='Completed direction session for the same zero capture.')
    args = parser.parse_args()
    root = tk.Tk()
    LimitFocus(root, args.zeros, args.checks)
    root.mainloop()


if __name__ == '__main__':
    main()
