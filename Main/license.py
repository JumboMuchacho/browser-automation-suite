import json
import hmac
import hashlib
import requests
import platform
import uuid
import time
import base64
from pathlib import Path

# ------------------------------
# Device ID (persistent)
# ------------------------------
def get_device_id():
    base = Path.home() / ".popup_detector"
    base.mkdir(exist_ok=True)
    path = base / "device.id"

    if path.exists():
        return path.read_text().strip()

    parts = []

    try:
        mac = uuid.getnode()
        if mac:
            parts.append(str(mac))
    except:
        pass

    parts.append(platform.node())

    raw = "|".join(sorted(parts))
    device_id = hashlib.sha256(raw.encode()).hexdigest()
    path.write_text(device_id)
    return device_id

# ------------------------------
# Client secret derivation
# ------------------------------
def get_client_secret(device_id: str):
    SALT = b"popup_detector_v2_secure_salt_2024"
    return hashlib.pbkdf2_hmac(
        "sha256",
        device_id.encode(),
        SALT,
        100_000,
        dklen=32,
    )

# ------------------------------
# Signature verification
# ------------------------------
def verify_signature(payload, signature, device_id):
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    ).encode("utf-8")

    expected = hmac.new(
        get_client_secret(device_id),
        raw,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)

# ------------------------------
# Cache
# ------------------------------
class LicenseCache:
    def __init__(self):
        self.path = Path.home() / ".popup_detector" / "license.cache"
        self.ttl = 3600

    def load(self):
        if not self.path.exists():
            return None

        try:
            data = json.loads(base64.b64decode(self.path.read_text()))
            if time.time() - data["cached_at"] > self.ttl:
                return None
            if data["device"] != get_device_id():
                return None
            if time.time() > data["token"]["exp"]:
                return None
            if not verify_signature(data["token"], data["signature"], data["device"]):
                return None
            return data
        except:
            return None

    def save(self, token, signature, device):
        data = {
            "token": token,
            "signature": signature,
            "device": device,
            "cached_at": int(time.time()),
        }
        encoded = base64.b64encode(json.dumps(data).encode()).decode()
        self.path.write_text(encoded)

# ------------------------------
# Validation
# ------------------------------
def ensure_valid(server_url, license_key=None):
    device_id = get_device_id()
    cache = LicenseCache()

    if cache.load():
        return True

    if not license_key:
        return False

    r = requests.post(
        f"{server_url.rstrip('/')}/verify",
        json={
            "license_key": license_key,
            "device_id": device_id,
            "timestamp": int(time.time()),
        },
        timeout=20,
    )

    if r.status_code != 200:
        return False

    data = r.json()
    token = data["token"]
    signature = data["signature"]

    if token["device"] != device_id:
        return False

    if not verify_signature(token, signature, device_id):
        return False

    cache.save(token, signature, device_id)
    return True
