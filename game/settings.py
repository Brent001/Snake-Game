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
}


def _read_settings(path: Path) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def load_settings():
    data = dict(DEFAULT_SETTINGS)
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
