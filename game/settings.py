"""Persistent user settings for Repair Terminal.

Source checkouts keep settings in ``game/settings.json`` for backwards
compatibility. Frozen executables and installed Linux packages keep mutable
settings in the user's config directory instead of trying to write beside
read-only application files or inside PyInstaller's temporary extraction dir.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

BUNDLED_SETTINGS_FILE = Path(__file__).resolve().parent / "settings.json"


def _user_settings_path() -> Path:
    """Return a per-user writable config path for installed/package builds."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "repair-terminal" / "settings.json"


_USE_USER_CONFIG = bool(getattr(sys, "frozen", False)) or os.environ.get("REPAIR_USER_CONFIG") == "1"
SETTINGS_FILE = _user_settings_path() if _USE_USER_CONFIG else BUNDLED_SETTINGS_FILE

DEFAULT_SKILL_SLOT_KEYS = {
    "slot_1": "q",
    "slot_2": "e",
    "slot_3": "r",
    "slot_4": "f",
    "slot_5": "c",
}
DEFAULT_SKILL_SET_TOGGLE_KEY = "x"
_RESERVED_KEYBINDINGS = frozenset("wasdpmn")


def _valid_skill_key(value):
    return (isinstance(value, str) and len(value) == 1 and value.isascii()
            and value.isalpha() and value.lower() not in _RESERVED_KEYBINDINGS)


DEFAULT_SETTINGS = {
    "master_volume": 1.0,
    "music_volume": 1.0,
    "sfx_volume": 1.0,
    "mute_audio": False,
    "vfx_quality": 2,
    "auto_quality": True,
    "screen_shake": True,
    "damage_numbers": True,
    "fullscreen": False,
    "fps_cap": 60,
    "skill_slot_keys": dict(DEFAULT_SKILL_SLOT_KEYS),
    "skill_set_toggle_key": DEFAULT_SKILL_SET_TOGGLE_KEY,
}


def _read_settings(path: Path) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def load_settings():
    data = dict(DEFAULT_SETTINGS)
    # Do not share the mutable default key map between settings instances.
    data["skill_slot_keys"] = dict(DEFAULT_SKILL_SLOT_KEYS)
    if SETTINGS_FILE.exists():
        data.update({k: v for k, v in _read_settings(SETTINGS_FILE).items() if k in DEFAULT_SETTINGS})
    elif SETTINGS_FILE != BUNDLED_SETTINGS_FILE:
        # Preserve settings from the old source-tree location on first packaged run.
        data.update({k: v for k, v in _read_settings(BUNDLED_SETTINGS_FILE).items() if k in DEFAULT_SETTINGS})

    for key in ("master_volume", "music_volume", "sfx_volume"):
        try:
            data[key] = max(0.0, min(1.0, float(data[key])))
        except (TypeError, ValueError):
            data[key] = DEFAULT_SETTINGS[key]

    try:
        data["vfx_quality"] = max(0, min(2, int(data.get("vfx_quality", 2))))
    except (TypeError, ValueError):
        data["vfx_quality"] = DEFAULT_SETTINGS["vfx_quality"]

    try:
        data["fps_cap"] = int(data.get("fps_cap", 60))
    except (TypeError, ValueError):
        data["fps_cap"] = 60
    if data["fps_cap"] not in (30, 60, 90, 120, 0):
        data["fps_cap"] = 60

    for key in ("mute_audio", "auto_quality", "screen_shake", "damage_numbers", "fullscreen"):
        data[key] = bool(data.get(key, DEFAULT_SETTINGS[key]))

    # Validate rebinding data from older, edited, or partially corrupted settings.
    raw_slots = data.get("skill_slot_keys", {})
    if not isinstance(raw_slots, dict):
        raw_slots = {}
    clean_slots = {}
    used = set()
    allowed_keys = "qwertyuiopfg h j l z c v b".replace(" ", "")
    for slot, default in DEFAULT_SKILL_SLOT_KEYS.items():
        candidate = raw_slots.get(slot, default)
        candidate = candidate.lower() if isinstance(candidate, str) else default
        if not _valid_skill_key(candidate) or candidate in used:
            candidate = default
        if candidate in used:
            candidate = next(k for k in allowed_keys if _valid_skill_key(k) and k not in used)
        clean_slots[slot] = candidate
        used.add(candidate)
    data["skill_slot_keys"] = clean_slots

    toggle = data.get("skill_set_toggle_key", DEFAULT_SKILL_SET_TOGGLE_KEY)
    toggle = toggle.lower() if isinstance(toggle, str) else DEFAULT_SKILL_SET_TOGGLE_KEY
    if not _valid_skill_key(toggle) or toggle in used:
        toggle = DEFAULT_SKILL_SET_TOGGLE_KEY
    if toggle in used:
        toggle = next(k for k in allowed_keys if _valid_skill_key(k) and k not in used)
    data["skill_set_toggle_key"] = toggle
    return data


def save_settings(data):
    """Save known keys atomically; do not fail the game if the disk is read-only."""
    safe_data = {key: data[key] for key in DEFAULT_SETTINGS if key in data}
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        temp_path = SETTINGS_FILE.with_suffix(".json.tmp")
        temp_path.write_text(json.dumps(safe_data, indent=2), encoding="utf-8")
        temp_path.replace(SETTINGS_FILE)
    except (OSError, TypeError, ValueError):
        # Settings should never prevent the game from closing or continuing.
        try:
            temp_path.unlink(missing_ok=True)
        except (OSError, UnboundLocalError):
            pass
