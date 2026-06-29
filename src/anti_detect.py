"""
anti_detect.py – Anti-detection measures to reduce Warden checks and ban risk.

Features:
  - between_game_delay(): Random pause between games (5-20s configurable)
  - daily_session_guard(): Enforce max play hours per day, stop bot gracefully when limit hit
  - randomize_break_duration(): Add ±jitter% variance to configured break durations
  - ensure_randomize_runs(): Force run-order randomization every game cycle

All settings are controlled via [anti_detect] section in config/params.ini.
"""

import time
import math
import random
import datetime
from logger import Logger


# ---------------------------------------------------------------------------
# Module-level session tracking (persists for the lifetime of the process)
# ---------------------------------------------------------------------------
_session_start: float = time.time()        # when the bot first started today
_session_day: int = datetime.date.today().toordinal()  # calendar day of session start


def _get_config():
    """Lazy import to avoid circular dependency at module load time."""
    from config import Config
    return Config()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def between_game_delay():
    """
    Sleep a random amount of time between ending one game and starting another.
    Mimics natural human pause behaviour (afk, reading chat, grabbing a drink…).

    Reads:  anti_detect.enabled
            anti_detect.between_game_delay_min
            anti_detect.between_game_delay_max
    """
    cfg = _get_config().anti_detect
    if not cfg["enabled"]:
        return

    min_s = cfg["between_game_delay_min"]
    max_s = cfg["between_game_delay_max"]
    delay = random.uniform(min_s, max_s)

    Logger.info(f"[Anti-Detect] Waiting {delay:.1f}s before starting next game "
                f"(range: {min_s}-{max_s}s)")
    time.sleep(delay)


def daily_session_guard():
    """
    Track cumulative bot-play time within a single calendar day.
    If the elapsed time exceeds max_hours_per_day, perform a clean shutdown.

    The session counter resets automatically at midnight (new calendar day).

    Reads:  anti_detect.enabled
            anti_detect.max_hours_per_day  (0 = unlimited)
    """
    global _session_start, _session_day

    cfg = _get_config().anti_detect
    if not cfg["enabled"]:
        return

    max_hours = cfg["max_hours_per_day"]
    if max_hours <= 0:
        return  # unlimited

    # Reset counter if we've crossed midnight
    today = datetime.date.today().toordinal()
    if today != _session_day:
        Logger.info("[Anti-Detect] New calendar day – session timer reset.")
        _session_start = time.time()
        _session_day = today

    elapsed_h = (time.time() - _session_start) / 3600.0
    remaining_h = max_hours - elapsed_h

    Logger.debug(f"[Anti-Detect] Session elapsed: {elapsed_h:.2f}h / {max_hours}h limit "
                 f"({remaining_h:.2f}h remaining)")

    if elapsed_h >= max_hours:
        Logger.info(
            f"[Anti-Detect] Daily limit of {max_hours}h reached "
            f"(ran {elapsed_h:.2f}h). Stopping bot to avoid detection."
        )
        from utils.restart import safe_exit
        safe_exit()


def randomize_break_duration(base_minutes: float) -> float:
    """
    Return a jittered version of *base_minutes* to prevent a predictable
    break pattern being detectable.

    Example: base=60min, jitter=20%  →  result in [48, 72] minutes

    Reads:  anti_detect.enabled
            anti_detect.break_jitter_pct
    """
    cfg = _get_config().anti_detect
    if not cfg["enabled"] or base_minutes <= 0:
        return base_minutes

    jitter_pct = cfg["break_jitter_pct"] / 100.0
    low  = base_minutes * (1.0 - jitter_pct)
    high = base_minutes * (1.0 + jitter_pct)
    result = random.uniform(low, high)

    Logger.info(f"[Anti-Detect] Break duration jittered: "
                f"{base_minutes:.1f}min → {result:.1f}min "
                f"(±{cfg['break_jitter_pct']}%)")
    return result


def ensure_randomize_runs(bot) -> None:
    """
    Force-shuffle the run order every game cycle when auto_randomize is on,
    regardless of the main randomize_runs config flag.

    Reads:  anti_detect.enabled
            anti_detect.auto_randomize
    """
    cfg = _get_config().anti_detect
    if cfg["enabled"] and cfg["auto_randomize"]:
        bot.shuffle_runs()
        Logger.debug("[Anti-Detect] Run order randomized automatically.")
