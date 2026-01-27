import os
import json
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
SECRET = SECRET.encode()  # for HMAC


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
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def verify_sig(payload, sig):
    raw = _canonical_json(payload).encode()
    expected = hmac.new(SECRET, raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


# ------------------------------
# License validation (ONLINE ONLY)
# ------------------------------
def ensure_valid(server_url, license_key=None):
    device_id = make_fingerprint()

    if not license_key:
        license_key = input("Enter your license key: ").strip()

    # Always try server verification
    r = requests.post(
        f"{server_url.rstrip('/')}/verify",
        json={"license_key": license_key, "device_id": device_id},
        timeout=5
    )
    if r.status_code != 200:
        print(f"Server verification failed: {r.status_code} {r.text}")
        return False

    data = r.json()
    token = data.get("token")
    sig = data.get("signature")
    if not token or not sig or not verify_sig(token, sig):
        print("Server returned invalid signature.")
        return False

    return True
