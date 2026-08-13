"""Ensure Appwrite indexes exist. Delegates to reconcile_appwrite_schema --apply."""

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    script = Path(__file__).with_name("reconcile_appwrite_schema.py")
    raise SystemExit(subprocess.call([sys.executable, str(script), "--apply"]))
