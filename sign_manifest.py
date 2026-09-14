#!/usr/bin/env python3
"""Sign the exact manifest of an already-frozen release candidate."""

import argparse
import base64
import os
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-dir", type=Path, required=True)
    args = parser.parse_args()
    encoded_key = os.environ.get("VOCABULARY_SIGNING_KEY", "")
    if not encoded_key:
        raise SystemExit("VOCABULARY_SIGNING_KEY is required")
    private_key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(encoded_key))
    manifest = (args.candidate_dir / "manifest.json").read_bytes()
    signature = base64.b64encode(private_key.sign(manifest)).decode("ascii") + "\n"
    (args.candidate_dir / "manifest.sig").write_text(signature, encoding="ascii")


if __name__ == "__main__":
    main()

