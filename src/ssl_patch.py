import os
import sys

# Windows Python 3.8+ DLL loading workaround for Conda DLLs
if sys.platform == "win32":
    _conda_env_path = os.path.dirname(sys.executable)
    _library_bin_path = os.path.join(_conda_env_path, "Library", "bin")
    if os.path.exists(_library_bin_path):
        os.add_dll_directory(_library_bin_path)

import ssl
import certifi

_orig_load_default_certs = ssl.SSLContext.load_default_certs

def _patched_load_default_certs(self, purpose=ssl.Purpose.SERVER_AUTH):
    try:
        _orig_load_default_certs(self, purpose)
    except Exception:
        # Fallback to certifi CA bundle if Windows cert store has corrupt certificates
        self.load_verify_locations(cafile=certifi.where())

ssl.SSLContext.load_default_certs = _patched_load_default_certs
