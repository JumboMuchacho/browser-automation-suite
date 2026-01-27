import time
import json
import os
import hmac
import hashlib
import requests
import platform
import uuid
from dotenv import load_dotenv

# Load LICENSE_SECRET from .env
load_dotenv()
SECRET = os.getenv("LICENSE_SECRET")
if not SECRET:
    raise RuntimeError("LICENSE_SECRET not set in .env or environment variables")
SECRET = SECRET.encode()  # convert to bytes for HMAC

CACHE = ".license_token.json"
OFFLINE_GRACE_DAYS = 2  # Grace period if offline


# ------------------------------
# Hardware fingerprint
# ------------------------------
def get_cpu_id():
    if platform.system() == "Windows":
        try:
            import subprocess
            out = subprocess.check_output("wmic cpu get ProcessorId", shell=True, text=True)
            for line in out.splitlines():
                line = line.strip()
                if line and line.lower() != "processorid":
                    return line
        except Exception:
            pass
    return platform.processor() or ""


def get_disk_serial():
    if platform.system() == "Windows":
        try:
            import subprocess
            out = subprocess.check_output("wmic diskdrive get SerialNumber", shell=True, text=True)
            for line in out.splitlines():
                line = line.strip()
                if line and not line.lower().startswith("serialnumber"):
                    return line
        except Exception:
            pass
    return ""


def get_mac():
    node = uuid.getnode()
    return ":".join([f"{(node >> ele) & 0xFF:02x}" for ele in range(0, 8 * 6, 8)][::-1])


def make_fingerprint():
    cpu = get_cpu_id()
    disk = get_disk_serial()
    mac = get_mac()
    seed = "|".join([cpu, disk, mac])
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


# ------------------------------
# Signature verification
# ------------------------------
def _canonical_json(payload):
    """Produce deterministic JSON for HMAC"""
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def verify_sig(payload, sig):
    raw = _canonical_json(payload).encode()
    expected = hmac.new(SECRET, raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


# ------------------------------
# License validation
# ------------------------------
def ensure_valid(server_url, license_key=None):
    device_id = make_fingerprint()
    now = int(time.time())

    # Prompt license if not provided
    if not license_key:
        license_key = input("Enter your license key: ").strip()

    # Attempt server verification
    try:
        r = requests.post(
            f"{server_url.rstrip('/')}/verify",
            json={"license_key": license_key, "device_id": device_id},
            timeout=5
        )
        if r.status_code != 200:
            print(f"Server verification failed: {r.status_code} {r.text}")
            raise Exception("Server rejected license")

        data = r.json()
        # Save cached token locally
        with open(CACHE, "w") as f:
            json.dump(data, f)
        return True

    except Exception:
        # Offline handling
        if not os.path.exists(CACHE):
            print("No cached license found and server unreachable.")
            return False

        with open(CACHE) as f:
            data = json.load(f)

        token = data.get("token")
        sig = data.get("signature")
        if not token or not sig or not verify_sig(token, sig):
            print("Cached token invalid or tampered.")
            return False

        if token.get("device") != device_id:
            print("License not valid for this device.")
            return False

        if token.get("exp", 0) < now and now - token.get("exp", 0) > OFFLINE_GRACE_DAYS * 86400:
            print("Offline grace expired.")
            return False

        print("Using offline cached license.")
        return True
