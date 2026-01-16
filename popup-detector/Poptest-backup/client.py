import hashlib
import subprocess
import uuid
import platform
import argparse
import sys
from typing import Tuple, Optional

import requests


def run_cmd(cmd: str) -> str:
    try:
        out = subprocess.check_output(
            cmd,
            shell=True,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return out.strip()
    except Exception:
        return ""


def get_cpu_id() -> str:
    if platform.system() == "Windows":
        out = run_cmd("wmic cpu get ProcessorId")
        for line in out.splitlines():
            line = line.strip()
            if line and line.lower() != "processorid":
                return line
    return platform.processor() or ""


def get_disk_serial() -> str:
    if platform.system() == "Windows":
        out = run_cmd("wmic diskdrive get SerialNumber")
        for line in out.splitlines():
            line = line.strip()
            if line and not line.lower().startswith("serialnumber"):
                return line
    return ""


def get_mac() -> str:
    node = uuid.getnode()
    mac = ":".join([f"{(node >> ele) & 0xFF:02x}" for ele in range(0, 8 * 6, 8)][::-1])
    return mac


def make_fingerprint() -> str:
    cpu = get_cpu_id()
    disk = get_disk_serial()
    mac = get_mac()
    seed = "|".join([cpu, disk, mac])
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def activate_license(server_url: str, license_key: str, fingerprint: str, timeout: float = 5.0) -> Tuple[bool, Optional[int], str]:
    payload = {"license_key": license_key, "device_id": fingerprint}
    url = server_url.rstrip("/") + "/activate"
    try:
        r = requests.post(url, json=payload, timeout=timeout)
    except requests.RequestException as e:
        return False, None, f"Error contacting server: {e}"
    return r.status_code == 200, r.status_code, r.text


def verify_license(server_url: str, license_key: str, fingerprint: str, timeout: float = 5.0) -> Tuple[bool, Optional[int], str]:
    payload = {"license_key": license_key, "device_id": fingerprint}
    url = server_url.rstrip("/") + "/verify"
    try:
        r = requests.post(url, json=payload, timeout=timeout)
    except requests.RequestException as e:
        return False, None, f"Error contacting server: {e}"
    return r.status_code == 200, r.status_code, r.text


def _main_cli() -> None:
    parser = argparse.ArgumentParser(description="Collect machine fingerprint and verify license")
    parser.add_argument("--server", default="http://127.0.0.1:8000", help="License server base URL")
    parser.add_argument("--license", required=True, help="License key to verify")
    args = parser.parse_args()

    fingerprint = make_fingerprint()
    print(f"Fingerprint: {fingerprint}")

    ok, status, text = verify_license(args.server, args.license, fingerprint)
    if ok:
        print("Verified: OK")
    else:
        print(f"Verification failed: {status} {text}")
        sys.exit(1)


if __name__ == "__main__":
    _main_cli()
