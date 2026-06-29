"""
Config Bridge — reads/writes INI config files ↔ GUI.
Wraps configparser to provide a simple key/value interface for the launcher pages.
All writes go to config/custom.ini (which overrides params.ini at runtime).
"""
import configparser
import os
from pathlib import Path
from typing import Any


# Root of the botty project (two levels up from this file: src/launcher/config_bridge.py)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PARAMS_INI   = _PROJECT_ROOT / "config" / "params.ini"
_CUSTOM_INI   = _PROJECT_ROOT / "config" / "custom.ini"
_SHOP_INI     = _PROJECT_ROOT / "config" / "shop.ini"


class ConfigBridge:
    """
    Thin facade over the INI files.
    - load()  → populate internal cache from params.ini + custom.ini
    - get(section, key) → str value
    - set(section, key, value) → mark as pending
    - save() → write pending changes to custom.ini
    - discard() → discard pending changes
    """

    def __init__(self):
        self._base = configparser.ConfigParser()
        self._custom = configparser.ConfigParser()
        self._pending: dict[tuple[str, str], str] = {}
        self.load()

    # ------------------------------------------------------------------ #
    #  Load                                                                #
    # ------------------------------------------------------------------ #
    def load(self):
        self._base = configparser.ConfigParser()
        self._base.read(str(_PARAMS_INI))
        self._base.read(str(_SHOP_INI))

        self._custom = configparser.ConfigParser()
        if _CUSTOM_INI.exists():
            self._custom.read(str(_CUSTOM_INI))

        self._pending.clear()

    # ------------------------------------------------------------------ #
    #  Read                                                                #
    # ------------------------------------------------------------------ #
    def get(self, section: str, key: str, fallback: str = "") -> str:
        """Return value: pending > custom.ini > params.ini > fallback."""
        if (section, key) in self._pending:
            return self._pending[(section, key)]
        if self._custom.has_option(section, key):
            return self._custom.get(section, key)
        return self._base.get(section, key, fallback=fallback)

    def get_bool(self, section: str, key: str, fallback: bool = False) -> bool:
        val = self.get(section, key, "1" if fallback else "0").strip()
        return val in ("1", "true", "yes", "on")

    def get_float(self, section: str, key: str, fallback: float = 0.0) -> float:
        try:
            return float(self.get(section, key, str(fallback)))
        except ValueError:
            return fallback

    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        try:
            return int(self.get(section, key, str(fallback)))
        except ValueError:
            return fallback

    def get_list(self, section: str, key: str) -> list[str]:
        raw = self.get(section, key, "")
        return [x.strip() for x in raw.split(",") if x.strip()]

    def sections(self, base_only=False) -> list[str]:
        if base_only:
            return self._base.sections()
        secs = set(self._base.sections()) | set(self._custom.sections())
        return sorted(secs)

    def options(self, section: str) -> list[str]:
        opts = set()
        if self._base.has_section(section):
            opts.update(self._base.options(section))
        if self._custom.has_section(section):
            opts.update(self._custom.options(section))
        return sorted(opts)

    # ------------------------------------------------------------------ #
    #  Write (pending)                                                     #
    # ------------------------------------------------------------------ #
    def set(self, section: str, key: str, value: Any):
        self._pending[(section, key)] = str(value)

    def set_bool(self, section: str, key: str, value: bool):
        self.set(section, key, "1" if value else "0")

    def set_list(self, section: str, key: str, values: list[str]):
        self.set(section, key, ", ".join(values))

    @property
    def has_changes(self) -> bool:
        return bool(self._pending)

    def discard(self):
        self._pending.clear()

    # ------------------------------------------------------------------ #
    #  Persist to custom.ini                                               #
    # ------------------------------------------------------------------ #
    def save(self):
        """Merge pending changes into custom.ini and write to disk."""
        if not self._pending:
            return

        # Re-read current custom.ini to avoid overwriting unrelated settings
        merged = configparser.ConfigParser()
        if _CUSTOM_INI.exists():
            merged.read(str(_CUSTOM_INI))

        for (section, key), value in self._pending.items():
            if not merged.has_section(section):
                merged.add_section(section)
            merged.set(section, key, value)

        with open(str(_CUSTOM_INI), "w") as f:
            merged.write(f)

        # Reload after save
        self._pending.clear()
        self._custom = configparser.ConfigParser()
        self._custom.read(str(_CUSTOM_INI))


# Singleton instance shared across all pages
_bridge_instance: ConfigBridge | None = None


def get_bridge() -> ConfigBridge:
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = ConfigBridge()
    return _bridge_instance


def reset_bridge():
    """Force reload (e.g. after external file change)."""
    global _bridge_instance
    _bridge_instance = None
