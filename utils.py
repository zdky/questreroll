"""Logging setup and small helpers."""

import logging
import os
from datetime import datetime, timedelta, timezone

import psutil

from config import create_log_file
from constants import BASE_DIR, text

LOG_FORMAT = "[%(asctime)s.%(msecs)03d] %(levelname)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class ColoredFormatter(logging.Formatter):
    """Formatter that paints the whole record by its log level."""

    level_colors = {
        "DEBUG": "\033[92m",
        "INFO": "\033[94m",
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "CRITICAL": "\033[1;30;41m",
    }
    reset = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        color = self.level_colors.get(record.levelname)
        return f"{color}{message}{self.reset}" if color else message


def setup_logging() -> logging.Logger:
    root = logging.getLogger()
    if not root.handlers:
        root.setLevel(logging.INFO)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(ColoredFormatter(LOG_FORMAT, LOG_DATE_FORMAT))
        root.addHandler(console_handler)

        if create_log_file:
            log_name = f"console_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
            file_handler = logging.FileHandler(BASE_DIR / log_name, encoding="utf-8")
            file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
            root.addHandler(file_handler)

        # aiogram logs every handled update at INFO level
        logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    return logging.getLogger("questreroll")


log = setup_logging()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def time_text() -> str:
    """UTC time now as text, e.g. [09:15pm 2023/08/25] (UTC+0)"""
    return (
        utc_now()
        .strftime("[%I:%M%p %Y/%m/%d] (UTC+0)")
        .replace("PM", "pm")
        .replace("AM", "am")
    )


def seconds_until_daily_reset(hour: int = 0, minute: int = 5) -> float:
    """Seconds until the next hh:mm UTC (daily quests reset at 00:00 UTC)."""
    now = utc_now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def server_status() -> str:
    """Server load message (blocking for ~1 second, run it in a thread)."""
    cpu_used = psutil.cpu_percent(interval=1)
    cpu_freq = psutil.cpu_freq()
    cpu_freq = int(cpu_freq.current) if cpu_freq else 0
    cpu_cores = os.cpu_count()

    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    uptime = int(datetime.now().timestamp() - psutil.boot_time())
    days, rest = divmod(uptime, 86400)
    hours, rest = divmod(rest, 3600)
    minutes, seconds = divmod(rest, 60)
    uptime_str = f"{hours}h{minutes:02d}m{seconds:02d}s"
    if days:
        uptime_str = f"{days}d {uptime_str}"

    return text(
        "server.status",
        cpu_used,
        cpu_cores,
        cpu_freq,
        ram.percent,
        ram.used // 1_000_000,
        ram.total // 1_000_000,
        disk.percent,
        round(disk.used / 1_000_000_000, 1),
        round(disk.total / 1_000_000_000, 1),
        uptime_str,
    )
