# pylint: disable=C0415, C0114, C0115, C0116
import logging
from datetime import datetime, timezone, timedelta


# Create a custom formatter with colored log levels and custom date format
class ColoredFormatter(logging.Formatter):
    # Define colors using ANSI escape codes
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "bg_red": "\033[1;30;41m",
        "reset": "\033[0m",
    }

    def __init__(self, fmt=None, datefmt=None, colored=True):
        super().__init__(fmt, datefmt)
        self.colored = colored

    def format(self, record):
        if self.colored:
            level_color = {
                "DEBUG": self.colors["green"],
                "INFO": self.colors["blue"],
                "WARNING": self.colors["yellow"],
                "ERROR": self.colors["red"],
                "CRITICAL": self.colors["bg_red"],
            }.get(record.levelname, "")

            message = super().format(record)
            return f"{level_color}{message}{self.colors['reset']}"
        return super().format(record)


# Set up logging
log = logging.getLogger()
log.setLevel(logging.INFO)

# Create console handler and set the formatter with color
console_handler = logging.StreamHandler()
console_formatter = ColoredFormatter(
    "[%(asctime)s.%(msecs)03d] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
console_handler.setFormatter(console_formatter)

# Create file handler and set the formatter without color
log_file_name = f"console_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
file_handler = logging.FileHandler(log_file_name, encoding="utf-8")
file_formatter = ColoredFormatter(
    "[%(asctime)s.%(msecs)03d] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    colored=False,
)
file_handler.setFormatter(file_formatter)

# Add both handlers to the logger
log.addHandler(console_handler)
log.addHandler(file_handler)


def get_time(date_type: str = None):
    """Return UTC+0 time now

    Args:
        date_type (str): use "text" for formatting string
        or nothing for datetime object

    Returns:
        (str/obj): string or datetime object
    """
    time_now = datetime.now(timezone.utc)
    if date_type == "text":
        return (
            time_now.strftime("[%I:%M%p %Y/%m/%d] (UTC+0)")
            .replace("PM", "pm")
            .replace("AM", "am")
        )
    return time_now


def server_status():
    import psutil
    import os
    from fortnite import FN_JSON

    cpu_used = psutil.cpu_percent(interval=1)
    cpu_freq = int(psutil.cpu_freq().current)
    cpu_cores = os.cpu_count()

    ram_used = round(psutil.virtual_memory().used // 1000000, 1)
    ram_total = round(psutil.virtual_memory().total // 1000000, 1)
    ram_usedp = psutil.virtual_memory().percent

    disk_used = round(psutil.disk_usage("/")[1] / 1000000000, 1)
    disk_total = round(psutil.disk_usage("/")[0] / 1000000000, 1)
    disk_usedp = psutil.disk_usage("/")[3]

    boot_time_sec = int(datetime.now().timestamp() - psutil.boot_time())
    uptime_timedelta = timedelta(seconds=boot_time_sec)
    uptime_str = (datetime.min + uptime_timedelta).strftime("%Hh%Mm%Ss")

    return FN_JSON["msg"]["en"]["server.status"].format(
        cpu_used,
        cpu_cores,
        cpu_freq,
        ram_usedp,
        ram_used,
        ram_total,
        disk_usedp,
        disk_used,
        disk_total,
        uptime_str,
    )
