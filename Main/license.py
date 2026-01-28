import os
import json
import hmac
import hashlib
import requests
import platform
import uuid
import time
import sys
import base64
from pathlib import Path
from dotenv import load_dotenv

# Load environment (license key only, NO SECRET)
load_dotenv()

# ------------------------------
# Hardware fingerprint
# ------------------------------
def get_hardware_id():
    """Generate stable hardware identifier."""
    identifiers = []
    
    # 1. MAC address (most stable)
    try:
        mac = uuid.getnode()
        if mac != 0:  # Valid MAC
            mac_str = ':'.join(['{:02x}'.format((mac >> ele) & 0xff) 
                               for ele in range(0, 8*6, 8)][::-1])
            identifiers.append(f"MAC:{mac_str}")
    except:
        pass
    
    # 2. Computer name
    try:
        hostname = platform.node()
        if hostname:
            identifiers.append(f"HOST:{hostname}")
    except:
        pass
    
    # 3. Windows-specific (if available)
    if platform.system() == "Windows":
        try:
            import subprocess
            
            # Get computer name via WMI (more stable)
            result = subprocess.run(
                'wmic computersystem get name',
                shell=True,
                capture_output=True,
                text=True,
                timeout=2
            )
            lines = result.stdout.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.isspace() and line.lower() != "name":
                    identifiers.append(f"WMI:{line}")
                    break
                    
        except:
            pass
    
    # Fallback
    if not identifiers:
        identifiers = [
            platform.node(),
            platform.machine(),
            str(uuid.getnode())
        ]
    
    # Create fingerprint
    fingerprint_str = "|".join(sorted(set(identifiers)))
    return hashlib.sha256(fingerprint_str.encode()).hexdigest()

# Keep original function name
make_fingerprint = get_hardware_id

# ------------------------------
# Client Secret Generation (NO .env SECRET!)
# ------------------------------
def get_client_secret(device_id=None):
    """
    Generate client-specific secret from hardware.
    This matches what the server expects.
    """
    if not device_id:
        device_id = get_hardware_id()
    
    # IMPORTANT: This SALT must match what the server uses
    # It's embedded in code, not in .env
    SALT = "popup_detector_v2_secure_salt_2024"
    
    # Derive secret using PBKDF2 (slow hashing)
    secret = hashlib.pbkdf2_hmac(
        'sha256',
        device_id.encode(),  # Hardware ID as password
        SALT.encode(),       # Constant salt
        100000,              # High iteration count
        dklen=32             # 32 bytes = 256 bits
    )
    
    return secret.hex()

# ------------------------------
# Signature verification
# ------------------------------
def verify_signature(payload, signature, device_id=None):
    """Verify HMAC signature using derived secret."""
    if not device_id:
        device_id = get_hardware_id()
    
    # Get client-specific secret
    secret = get_client_secret(device_id)
    
    # Create signature same way server does
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    expected = hmac.new(
        secret.encode(),
        raw,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)

# ------------------------------
# License Cache Manager
# ------------------------------
class LicenseCache:
    def __init__(self):
        self.cache_file = ".license_cache"
        self.max_cache_age = 3600  # 1 hour cache
    
    def save(self, token, signature):
        """Save successful license validation."""
        cache_data = {
            "token": token,
            "signature": signature,
            "device_id": token.get("device"),
            "cached_at": int(time.time())
        }
        
        try:
            # Simple obfuscation
            encoded = base64.b64encode(
                json.dumps(cache_data).encode()
            ).decode()
            
            with open(self.cache_file, "w") as f:
                f.write(encoded)
                
            # Hide on Windows
            if platform.system() == "Windows":
                import ctypes
                ctypes.windll.kernel32.SetFileAttributesW(self.cache_file, 2)
                
            return True
        except Exception as e:
            return False
    
    def load(self):
        """Load and validate cached license."""
        if not os.path.exists(self.cache_file):
            return None
        
        try:
            with open(self.cache_file, "r") as f:
                encoded = f.read().strip()
            
            cache_data = json.loads(base64.b64decode(encoded.encode()).decode())
            
            # Check cache age
            if time.time() - cache_data.get("cached_at", 0) > self.max_cache_age:
                self.clear()
                return None
            
            # Get current device ID
            current_device_id = get_hardware_id()
            
            # Verify device matches
            if cache_data.get("device_id") != current_device_id:
                self.clear()
                return None
            
            # Verify signature
            token = cache_data.get("token")
            signature = cache_data.get("signature")
            
            if not verify_signature(token, signature, current_device_id):
                self.clear()
                return None
            
            # Check token expiration
            expires_at = token.get("exp", 0)
            if time.time() > expires_at:
                self.clear()
                return None
            
            return token
        except:
            self.clear()
            return None
    
    def clear(self):
        """Clear cache file."""
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
        except:
            pass

# ------------------------------
# Main License Validation
# ------------------------------
def ensure_valid(server_url, license_key=None):
    """
    Validate license with server.
    Returns True if valid, False otherwise.
    """
    cache = LicenseCache()
    
    # Try cached license first
    cached = cache.load()
    if cached:
        print("✓ Using cached license (fast startup)")
        return True
    
    # Get device ID
    device_id = get_hardware_id()
    
    # Get license key
    if not license_key:
        license_key = os.getenv("LICENSE_KEY")
        if not license_key:
            license_key = input("Enter license key: ").strip()
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{server_url.rstrip('/')}/verify",
                json={
                    "license_key": license_key,
                    "device_id": device_id,
                    "client_version": "2.0.0",
                    "timestamp": int(time.time())
                },
                timeout=30,
                headers={"User-Agent": "PopupDetector/2.0"}
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("token")
                signature = data.get("signature")
                
                # Validate response
                if not token or not signature:
                    print("Invalid server response")
                    return False
                
                # Verify signature
                if not verify_signature(token, signature, device_id):
                    print("Security error: Invalid signature")
                    return False
                
                # Check expiration
                expires_at = token.get("exp", 0)
                if time.time() > expires_at:
                    print("License token expired")
                    return False
                
                # Verify device matches
                if token.get("device") != device_id:
                    print("Security error: Device mismatch")
                    return False
                
                # Cache successful validation
                cache.save(token, signature)
                
                return True
                
            elif response.status_code == 404:
                print("License not found or inactive")
                return False
            elif response.status_code == 410:
                print("License has expired")
                return False
            elif response.status_code == 429:
                print("Device limit reached")
                return False
            elif response.status_code == 422:
                print("Invalid request format")
                return False
            else:
                print(f"Server error: {response.status_code}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                
        except requests.exceptions.Timeout:
            print(f"Connection timeout (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(10)
        except requests.exceptions.ConnectionError:
            print("Cannot connect to license server")
            if attempt < max_retries - 1:
                time.sleep(10)
        except requests.exceptions.RequestException as e:
            print(f"Network error: {e}")
            return False
    
    print("Failed to validate license")
    return False