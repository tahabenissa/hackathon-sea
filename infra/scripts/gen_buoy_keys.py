"""Generate one random HMAC key per buoy listed in config/buoys.yaml.

Usage:  python infra/scripts/gen_buoy_keys.py [--force]
Output: secrets/buoy_keys.json  (git-ignored, never commit it)
"""

import argparse
import json
import secrets
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
BUOYS = ROOT / "config" / "buoys.yaml"
OUT = ROOT / "secrets" / "buoy_keys.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="overwrite (rotate) existing keys")
    args = parser.parse_args()

    if OUT.exists() and not args.force:
        sys.exit(f"{OUT} already exists. Use --force to rotate all keys.")

    buoys = yaml.safe_load(BUOYS.read_text(encoding="utf-8"))["buoys"]
    keys = {b["buoy_id"]: secrets.token_hex(32) for b in buoys}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(keys, indent=2), encoding="utf-8")
    print(f"Wrote {len(keys)} keys to {OUT}")


if __name__ == "__main__":
    main()
