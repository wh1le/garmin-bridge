import signal
import sys

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.style import Style
from rich import box
from readchar import readkey, key

SELECTED = Style(color="blue", bgcolor="white", bold=True)

console = Console()

signal.signal(signal.SIGINT, lambda *_: sys.exit(0))


def spinner(message):
    return console.status(message)


def pick_device(devices):
    if not devices:
        return None

    headers = ["Name", "Address"]
    rows = [(d.name, d.address) for d in devices]

    selected = 0
    with Live(
        _build_table(headers, rows, selected), auto_refresh=False, console=console
    ) as live:
        while True:
            ch = readkey()
            if ch == key.UP or ch == "k":
                selected = max(0, selected - 1)
            elif ch == key.DOWN or ch == "j":
                selected = min(len(rows) - 1, selected + 1)
            elif ch == key.ENTER:
                live.stop()
                return selected
            elif ch == key.ESC or ch == "q":
                live.stop()
                return None
            live.update(_build_table(headers, rows, selected), refresh=True)


HELP = "[dim]↑/↓/j/k navigate  enter select  q quit[/dim]"


def _build_table(headers, rows, selected):
    table = Table(box=box.MINIMAL, caption=HELP)
    for h in headers:
        table.add_column(h)
    for i, row in enumerate(rows):
        table.add_row(*row, style=SELECTED if i == selected else None)
    return table