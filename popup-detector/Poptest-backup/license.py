import json
import os
import time
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from client import make_fingerprint, verify_license, activate_license

APP_NAME = "popup-detector"


def get_config_path(app_dir: Optional[str] = None) -> Path:
    """Return path to license.json (portable & cross-platform)."""
    if app_dir:
        p = Path(app_dir) / "license.json"
    elif getattr(sys, "frozen", False):
        exe_dir = Path(sys._MEIPASS if hasattr(sys, "_MEIPASS") else os.path.dirname(sys.executable))
        config_dir = exe_dir / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        p = config_dir / "license.json"
    else:
        if os.name == "nt":
            appdata = os.getenv("APPDATA") or str(Path.home())
            config_dir = Path(appdata) / APP_NAME
        else:
            xdg = os.getenv("XDG_CONFIG_HOME") or str(Path.home() / ".config")
            config_dir = Path(xdg) / APP_NAME
        config_dir.mkdir(parents=True, exist_ok=True)
        p = config_dir / "license.json"

    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def save_license(license_key: str, app_dir: Optional[str] = None) -> None:
    cfg = {"license_key": license_key, "last_check": None}
    p = get_config_path(app_dir)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(cfg, f)


def load_license(app_dir: Optional[str] = None) -> Optional[dict]:
    p = get_config_path(app_dir)
    if not p.exists():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def update_last_check(app_dir: Optional[str] = None) -> None:
    data = load_license(app_dir) or {}
    data["last_check"] = time.time()
    p = get_config_path(app_dir)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f)


def prompt_for_license() -> str:
    return input("Enter license key: ").strip()


def ensure_valid(
    server: str,
    app_dir: Optional[str] = None,
    recheck_hours: int = 1,
    offline_days: int = 2,
) -> bool:
    data = load_license(app_dir)
    if data and "license_key" in data:
        license_key = data["license_key"]
    else:
        license_key = prompt_for_license()
        save_license(license_key, app_dir)
        data = load_license(app_dir)

    fingerprint = make_fingerprint()
    now = time.time()
    last_check = data.get("last_check") if data else None

    if last_check and (now - last_check) / 3600.0 < recheck_hours:
        return True

    ok, status, text = verify_license(server, license_key, fingerprint)
    if ok:
        update_last_check(app_dir)
        return True

    if status == 403:
        activate_ok, _, _ = activate_license(server, license_key, fingerprint)
        if activate_ok:
            ok, status, text = verify_license(server, license_key, fingerprint)
            if ok:
                update_last_check(app_dir)
                return True

    max_attempts = 3
    print(f"License invalid: {text}. You have {max_attempts} attempts to enter a new key.")

    for attempt in range(max_attempts):
        new_key = prompt_for_license()
        save_license(new_key, app_dir)
        fingerprint = make_fingerprint()
        ok2, status2, text2 = verify_license(server, new_key, fingerprint)
        if not ok2 and status2 == 403:
            activate_ok, _, _ = activate_license(server, new_key, fingerprint)
            if activate_ok:
                ok2, status2, text2 = verify_license(server, new_key, fingerprint)
        if ok2:
            update_last_check(app_dir)
            return True
        print("License still invalid:", text2)

    return False
