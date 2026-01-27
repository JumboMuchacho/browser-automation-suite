import os
import json
import hmac
import hashlib
import requests
import platform
import uuid
import time  # Added for retries
from dotenv import load_dotenv

# Load LICENSE_SECRET from .env
load_dotenv()
SECRET = os.getenv("LICENSE_SECRET")
if not SECRET:
    raise RuntimeError("LICENSE_SECRET not set in .env or environment variables")

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
# Signature verification (Matches Server security.py)
# ------------------------------
def verify_sig(payload, sig):
    """Re-creates the signature locally to verify the server's response."""
    # Ensure JSON format matches server exactly: no spaces, sorted keys
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    expected = hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)

# ------------------------------
# License validation
# ------------------------------
def ensure_valid(server_url, license_key=None):
    device_id = make_fingerprint()

    if not license_key:
        license_key = input("Enter your license key: ").strip()

    max_retries = 3  # Limit retries to prevent infinite loops
    for attempt in range(max_retries):
        try:
            r = requests.post(
                f"{server_url.rstrip('/')}/verify",
                json={
                    "license_key": license_key,
                    "device_id": device_id,
                    "client_version": "1.0.0"  # Added to fix 422 error
                },
                timeout=60  # Increased for Render wake-up
            )
            
            if r.status_code == 200:
                data = r.json()
                token = data.get("token")
                sig = data.get("signature")

                if not token or not sig or not verify_sig(token, sig):
                    print("Security Error: Signature invalid or tampered with.")
                    return False
                return True
            else:
                print(f"Server verification failed: {r.status_code} - {r.text}")
                if r.status_code == 422:  # Specific handling for field errors
                    print("Check if client_version or other fields are correct.")
                return False

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                print(f"Connection timed out. Retrying in 10s... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(10)
            else:
                print("Max retries reached due to timeouts.")
                return False
        except requests.exceptions.RequestException as e:
            print(f"Connection error: {e}")
            return False

    return False