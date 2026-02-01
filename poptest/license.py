import json
import hmac
import hashlib
import requests
import platform
import uuid
import time
import base64
from pathlib import Path

LICENSE_SECRET = "bb55f4f433ad5c39042ff80d35431c7355b1a638b4ec8c242779484f9079f37b" 

def get_base_dir():
    base = Path.home() / ".poptest"
    base.mkdir(exist_ok=True)
    return base

def get_device_id():
    base = get_base_dir()
    path = base / "device.id"
    if path.exists():
        return path.read_text().strip()
    raw = f"{uuid.getnode()}|{platform.node()}"
    device_id = hashlib.sha256(raw.encode()).hexdigest()
    path.write_text(device_id)
    return device_id

def verify_signature(payload, signature):
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    ).encode("utf-8")

    expected = hmac.new(
        LICENSE_SECRET.encode(),
        raw,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)

class LicenseCache:
    def __init__(self):
        self.path = get_base_dir() / "license.cache"

    def load(self):
        if not self.path.exists():
            return None
        try:
            data = json.loads(base64.b64decode(self.path.read_text()))
            if time.time() > data["token"]["exp"]:
                return None
            if data["token"]["device"] != get_device_id():
                return None
            if not verify_signature(data["token"], data["signature"]):
                return None
            return data
        except:
            return None

    def save(self, token, signature):
        encoded = base64.b64encode(
            json.dumps({
                "token": token,
                "signature": signature,
            }).encode()
        ).decode()
        self.path.write_text(encoded)

def ensure_valid(server_url, license_key=None):
    device_id = get_device_id()
    cache = LicenseCache()

    if not license_key:
        cached = cache.load()
        return True if cached else False

    try:
        r = requests.post(
            f"{server_url.rstrip('/')}/verify",
            json={
                "license_key": license_key,
                "device_id": device_id,
            },
            timeout=70, # Increased slightly to handle Render cold-starts
        )

        if r.status_code != 200:
            return False

        data = r.json()
        token = data.get("token")
        signature = data.get("signature")

        if not token or not signature:
            return False

        if not verify_signature(token, signature):
            return False

        cache.save(token, signature)
        return True
    except (requests.exceptions.RequestException, Exception):
        # Silently catch timeouts and connection pools
        return False