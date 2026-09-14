#!/usr/bin/env python3
"""Verify exact frozen vocabulary bytes, metadata, counts, and signature."""

import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


ROOT = Path(__file__).parent


def require(actual, expected, label):
    if actual != expected:
        raise SystemExit(f"{label} mismatch: expected {expected}, got {actual}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--version", type=int, required=True)
    parser.add_argument("--content-sha256", required=True)
    parser.add_argument("--artifact-sha256", required=True)
    parser.add_argument("--terms", type=int, required=True)
    parser.add_argument("--aliases", type=int, required=True)
    parser.add_argument("--signature", type=Path)
    args = parser.parse_args()

    manifest_bytes = (args.candidate_dir / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    require(manifest["schema_version"], 1, "manifest schema")
    require(manifest["pack_version"], args.version, "manifest version")
    require(manifest["content_sha256"], args.content_sha256, "content hash")
    require(manifest["sha256"], args.artifact_sha256, "manifest artifact hash")
    require(manifest["term_count"], args.terms, "manifest term count")

    artifact = (args.candidate_dir / manifest["artifact"]).read_bytes()
    require(hashlib.sha256(artifact).hexdigest(), args.artifact_sha256, "artifact hash")
    payload = json.loads(gzip.decompress(artifact))
    require(payload["schema_version"], 1, "payload schema")
    require(payload["pack_version"], args.version, "payload version")
    require(len(payload["terms"]), args.terms, "payload term count")
    require(sum(len(term.get("aliases", [])) for term in payload["terms"]), args.aliases, "payload alias count")

    if args.signature:
        public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex((ROOT / "PUBLIC_KEY.hex").read_text().strip()))
        public_key.verify(base64.b64decode(args.signature.read_text()), manifest_bytes)
    print(json.dumps({"version": args.version, "content_sha256": args.content_sha256, "artifact_sha256": args.artifact_sha256, "terms": args.terms, "aliases": args.aliases, "signature_verified": bool(args.signature)}, sort_keys=True))


if __name__ == "__main__":
    main()
