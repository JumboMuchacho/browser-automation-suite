import time
import json
import os
import hmac
import hashlib
import requests

CACHE = ".license_token.json"
SECRET = b"CHANGE_ME_NOW"
CLIENT_VERSION = "1.0.0"

def verify_sig(payload, sig):
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    expected = hmac.new(SECRET, raw.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)

def ensure_valid(server, license_key, device_id, offline_days=2, recheck_hours=1):
    """Check license validity with offline grace and HMAC"""
    now = int(time.time())
    cached = None

    # Try reading cached token
    if os.path.exists(CACHE):
        with open(CACHE, "r") as f:
            try:
                cached = json.load(f)
            except Exception:
                cached = None

    # Decide if we need a server check
    last_check = cached.get("last_check", 0) if cached else 0
    need_server = (now - last_check) > recheck_hours * 3600

    if need_server:
        try:
            r = requests.post(
                f"{server}/verify",
                json={
                    "license_key": license_key,
                    "device_id": device_id,
                    "client_version": CLIENT_VERSION,
                },
                timeout=5,
            )
            if r.status_code != 200:
                raise Exception("Server rejected license")
            data = r.json()
            data["last_check"] = now
            with open(CACHE, "w") as f:
                json.dump(data, f)
            return True

        except Exception:
            # If server unavailable, fallback to cached
            pass

    # Offline verification
    if cached:
        token = cached.get("token")
        sig = cached.get("signature")
        if token and sig and verify_sig(token, sig):
            if token.get("device") != device_id:
                return False
            # Allow offline grace period
            if token.get("exp", 0) + offline_days * 86400 >= now:
                return True

    return False
