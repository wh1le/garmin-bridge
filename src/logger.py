import logging
import logging.handlers
import os

from rich.logging import RichHandler

LOG_DIR = os.path.expanduser("~/.local/share/garmin-bridge")
LOG_FILE = os.path.join(LOG_DIR, "garmin-bridge.log")

os.makedirs(LOG_DIR, exist_ok=True)

log = logging.getLogger("garmin-bridge")
log.setLevel(logging.DEBUG)

console = RichHandler(
    rich_tracebacks = True,
    show_path       = False,
    markup          = True,
)
console.setFormatter(logging.Formatter("%(message)s"))
log.addHandler(console)

file_handler = logging.handlers.RotatingFileHandler(
    LOG_FILE, maxBytes=5_000_000, backupCount=3,
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    fmt     = "%(asctime)s [garmin-bridge] %(levelname)s %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S",
))
log.addHandler(file_handler)
