#!/usr/bin/env python3
"""Validate, diff, deterministically build, and optionally sign a vocabulary release."""

import argparse
import base64
import gzip
import hashlib
import json
import os
from collections import Counter
from pathlib import Path

MAX_TERMS = 60_000
MAX_GROWTH_FACTOR = 1.75
MAX_REMOVAL_FRACTION = 0.10
ALLOWED_CATEGORIES = {
    "technology", "company", "product", "service", "software", "developer_tool",
    "framework", "library", "database", "programming_language", "ai_model",
    "ai_product", "cloud_service", "public_organization",
}


def compact(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def normalized(value):
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split())


def valid_text(value):
    return isinstance(value, str) and 2 <= len(value) <= 80 and not any(ch in value for ch in "\r\n\t{}[]<>`$")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--version", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--previous-pack", type=Path)
    parser.add_argument("--signing-key-base64", default=os.environ.get("VOCABULARY_SIGNING_KEY", ""))
    args = parser.parse_args()
    snapshot_bytes = args.snapshot.read_bytes()
    snapshot = json.loads(snapshot_bytes)
    catalog = json.loads(args.catalog.read_bytes())

    terms = []
    for entity in snapshot["entities"]:
        tier = entity.get("tier", "core")
        tier_base = {"core": 9000, "extended": 7000, "discovered": 5000}.get(tier)
        if tier_base is None:
            raise SystemExit(f"invalid tier: {tier}")
        term = {
            "canonical": entity["canonical"],
            "aliases": entity["aliases"],
            "category": entity["category"],
            "confidence": 45 + min(30, entity["sitelinks"] // 5),
            "rank": tier_base + min(999, entity.get("relevance_score", entity["sitelinks"])),
            "source_ref": "wikidata:" + entity["qid"],
            "tier": tier,
            "relevance_reason": entity.get("inclusion_reason", f"wikidata:sitelinks={entity['sitelinks']}"),
            "ambiguity_risk": entity.get("ambiguity_risk", "low"),
        }
        terms.append(term)
    terms.extend(catalog["flowkit_additions"])
    terms.sort(key=lambda item: (normalized(item["canonical"]), item["canonical"]))

    seen = set()
    for term in terms:
        key = normalized(term["canonical"])
        if key in seen:
            raise SystemExit(f"duplicate normalized term: {term['canonical']}")
        seen.add(key)
        if not valid_text(term["canonical"]) or term["category"] not in ALLOWED_CATEGORIES:
            raise SystemExit(f"malformed term: {term}")
        if not term["source_ref"].startswith(("wikidata:Q", "flowkit-curated:")):
            raise SystemExit(f"unapproved provenance: {term['source_ref']}")
        term["aliases"] = sorted(
            {alias for alias in term["aliases"] if valid_text(alias)},
            key=lambda value: (value.casefold(), value),
        )[:4]
        term.setdefault("tier", "core")
        term.setdefault("relevance_reason", "reviewed-curated-source")
        term.setdefault("ambiguity_risk", "low")
    if not 1 <= len(terms) <= MAX_TERMS:
        raise SystemExit(f"term count outside bounds: {len(terms)}")

    previous_names = set()
    if args.previous_pack and args.previous_pack.exists():
        with gzip.open(args.previous_pack, "rb") as handle:
            previous_names = {normalized(item["canonical"]) for item in json.load(handle)["terms"]}
        removed = previous_names - seen
        if previous_names and len(removed) / len(previous_names) > MAX_REMOVAL_FRACTION:
            raise SystemExit(f"suspicious mass removal: {len(removed)}/{len(previous_names)}")
        if previous_names and len(terms) > len(previous_names) * MAX_GROWTH_FACTOR:
            raise SystemExit(f"abnormal growth: {len(previous_names)} -> {len(terms)}")

    payload = {"schema_version": 1, "pack_version": args.version, "terms": terms}
    payload_hash = hashlib.sha256(compact({"schema_version": 1, "terms": terms})).hexdigest()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    artifact_name = f"global-v{args.version}.json.gz"
    artifact = gzip.compress(compact(payload), compresslevel=9, mtime=0)
    manifest = {
        "schema_version": 1,
        "pack_version": args.version,
        "artifact": artifact_name,
        "sha256": hashlib.sha256(artifact).hexdigest(),
        "content_sha256": payload_hash,
        "source_snapshot_sha256": hashlib.sha256(snapshot_bytes).hexdigest(),
        "retrieved_at": snapshot["retrieved_at"],
        "term_count": len(terms),
        "category_counts": dict(sorted(Counter(term["category"] for term in terms).items())),
        "sources": [snapshot["source"], {"name": "FlowKit curated additions", "version": "1", "license": "MIT", "url": "sources/curated-titles.json"}],
    }
    manifest_bytes = compact(manifest)
    (args.output_dir / artifact_name).write_bytes(artifact)
    (args.output_dir / "manifest.json").write_bytes(manifest_bytes)
    if args.signing_key_base64:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(args.signing_key_base64))
        (args.output_dir / "manifest.sig").write_text(base64.b64encode(key.sign(manifest_bytes)).decode() + "\n", encoding="ascii")
    print(json.dumps({"version": args.version, "terms": len(terms), "categories": manifest["category_counts"], "content_sha256": payload_hash}))


if __name__ == "__main__":
    main()
