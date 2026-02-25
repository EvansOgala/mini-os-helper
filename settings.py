import json
from pathlib import Path

APP_DIR = Path.home() / ".config" / "mini_os_helper"
SETTINGS_PATH = APP_DIR / "settings.json"
NOTES_PATH = APP_DIR / "notes.txt"

DEFAULT_SETTINGS = {
    "theme": "dark",
    "refresh_interval_ms": 1000,
    "auto_refresh": True,
    "favorites": {
        "Documents": str(Path.home() / "Documents"),
        "Downloads": str(Path.home() / "Downloads"),
        "Projects": str(Path.home() / "Documents"),
    },
    "web_shortcuts": {
        "YouTube": "https://www.youtube.com",
        "GitHub": "https://github.com",
    },
}


def load_settings() -> dict:
    if not SETTINGS_PATH.exists():
        return DEFAULT_SETTINGS.copy()

    try:
        with SETTINGS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return DEFAULT_SETTINGS.copy()

    merged = DEFAULT_SETTINGS.copy()
    merged.update(data)

    interval = merged.get("refresh_interval_ms", DEFAULT_SETTINGS["refresh_interval_ms"])
    if not isinstance(interval, int):
        interval = DEFAULT_SETTINGS["refresh_interval_ms"]
    merged["refresh_interval_ms"] = max(100, min(2000, interval))

    auto = merged.get("auto_refresh", DEFAULT_SETTINGS["auto_refresh"])
    merged["auto_refresh"] = bool(auto)

    if not isinstance(merged.get("favorites"), dict):
        merged["favorites"] = DEFAULT_SETTINGS["favorites"]
    if not isinstance(merged.get("web_shortcuts"), dict):
        merged["web_shortcuts"] = DEFAULT_SETTINGS["web_shortcuts"]

    return merged


def save_settings(data: dict) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    with SETTINGS_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_notes() -> str:
    if not NOTES_PATH.exists():
        return ""
    try:
        return NOTES_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""


def save_notes(content: str) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    NOTES_PATH.write_text(content, encoding="utf-8")
