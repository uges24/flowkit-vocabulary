#!/usr/bin/env python3
"""Discover high-signal public vocabulary from bounded Wikidata SPARQL queries."""

import argparse
import datetime as dt
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ENDPOINT = "https://query.wikidata.org/sparql"
ENTITY_API = "https://www.wikidata.org/w/api.php"
USER_AGENT = "FlowKitVocabularyPublisher/2.0 (https://github.com/uges24/flowkit-vocabulary)"
TYPE_MAP = {
    "Q7397": "software",
    "Q9143": "programming_language",
    "Q8513": "database",
    "Q271680": "framework",
    "Q4830453": "company",
    "Q2424752": "product",
    "Q7406919": "service",
    "Q43229": "public_organization",
    "Q9135": "software",
    "Q189210": "software",
    "Q620615": "software",
    "Q13741": "developer_tool",
    "Q11016": "technology",
    "Q35127": "service",
}
COMMON_AMBIGUOUS = {
    "air", "apple", "base", "basic", "box", "branch", "cloud", "code", "cursor",
    "dart", "edge", "flow", "go", "linear", "notion", "oracle", "power", "react",
    "rust", "signal", "spark", "swift", "teams", "warp", "windsurf", "zoom",
}
UNSAFE_CANONICAL_FORMS = {"goto", "visual basic 6"}
HASHISH = re.compile(r"^(?:[0-9a-f]{12,}|[a-z0-9_-]*[0-9a-f]{20,}[a-z0-9_-]*)$", re.I)
DISALLOWED_PREFIXES = ("template:", "category:", "list of ", "draft:", "portal:", "user:")
CORPORATE_SUFFIXES = {"inc", "incorporated", "corp", "corporation", "company", "ltd", "limited", "llc", "plc", "ag"}


def compact(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def runtime_normalized(value):
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split())


def runtime_acceptable(value):
    normalized = runtime_normalized(value.strip())
    compact = normalized.replace(" ", "")
    digits = sum(ch.isascii() and ch.isdigit() for ch in compact)
    secret_compact = "".join(ch for ch in value if ch.isalnum())
    secret_classes = sum((
        any(ch.isascii() and ch.islower() for ch in secret_compact),
        any(ch.isascii() and ch.isupper() for ch in secret_compact),
        any(ch.isascii() and ch.isdigit() for ch in secret_compact),
    ))
    return (
        bool(normalized)
        and normalized not in {"the", "and", "for", "with", "from", "this", "that"}
        and not (len(compact) >= 20 and digits * 3 > len(compact))
        and not (len(secret_compact) >= 24 and secret_classes >= 3 and " " not in value)
    )


def safe_name(value):
    value = " ".join(value.strip().split())
    if not 2 <= len(value) <= 80 or any(ch in value for ch in "\r\n\t{}[]<>`$@"):
        return None
    if value.startswith(("http://", "https://")) or HASHISH.fullmatch(value):
        return None
    if value.casefold().startswith(DISALLOWED_PREFIXES):
        return None
    if not any(ch.isalpha() for ch in value) or not runtime_acceptable(value) or runtime_normalized(value) in UNSAFE_CANONICAL_FORMS:
        return None
    return value


def quality(label, sitelinks):
    normalized = label.casefold()
    ambiguous = normalized in COMMON_AMBIGUOUS
    if sitelinks < 2 or (ambiguous and sitelinks < 40):
        return None
    score = min(100, 30 + min(60, sitelinks) + (10 if any(ch.isupper() for ch in label[1:]) else 0))
    tier = "core" if sitelinks >= 40 else "extended" if sitelinks >= 10 else "discovered"
    return score, tier, ambiguous


def safe_alias(canonical, alias):
    canonical_words = runtime_normalized(canonical).split()
    alias_words = runtime_normalized(alias).split()
    if not alias_words or runtime_normalized(canonical) == runtime_normalized(alias):
        return True
    letters = "".join(ch for ch in alias if ch.isascii() and ch.isalpha())
    if 2 <= len(letters) <= 8 and letters.isupper() and len(alias_words) <= 2:
        return True
    if len(canonical_words) == len(alias_words) + 1 and canonical_words[:-1] == alias_words and canonical_words[-1] in CORPORATE_SUFFIXES:
        return True
    return False


def query_type(qid, limit, cache_dir, attempts=5):
    cache_path = cache_dir / f"{qid}-{limit}-min2.json"
    if cache_path.exists():
        return json.loads(cache_path.read_bytes())
    query = f'''SELECT ?item ?label ?sitelinks WHERE {{
      ?item wdt:P31 wd:{qid}; rdfs:label ?label; wikibase:sitelinks ?sitelinks.
      FILTER(LANG(?label)="en") FILTER(?sitelinks>=2)
    }} ORDER BY DESC(?sitelinks) ASC(?item) LIMIT {limit}'''
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                if response.length and response.length > 12_000_000:
                    raise RuntimeError("discovery response exceeds 12 MB")
                bindings = json.load(response)["results"]["bindings"]
                cache_dir.mkdir(parents=True, exist_ok=True)
                cache_path.write_bytes(compact(bindings))
                return bindings
        except Exception:
            if attempt + 1 == attempts:
                raise
            time.sleep(2 ** attempt)


def enrich_core_aliases(entities, cache_dir):
    core = [entity for entity in entities if entity["tier"] == "core"]
    for start in range(0, len(core), 50):
        batch = core[start:start + 50]
        cache_path = cache_dir / f"aliases-{batch[0]['qid']}-{batch[-1]['qid']}.json"
        if cache_path.exists():
            data = json.loads(cache_path.read_bytes())
        else:
            params = urllib.parse.urlencode({
                "action": "wbgetentities", "format": "json", "formatversion": 2,
                "props": "aliases", "languages": "en", "ids": "|".join(item["qid"] for item in batch),
            })
            request = urllib.request.Request(ENTITY_API + "?" + params, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.load(response)["entities"]
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(compact(data))
        for entity in batch:
            aliases = []
            for item in data.get(entity["qid"], {}).get("aliases", {}).get("en", []):
                alias = safe_name(item.get("value", ""))
                if not alias or alias.casefold() == entity["canonical"].casefold():
                    continue
                if alias.casefold() in COMMON_AMBIGUOUS or (alias.islower() and " " not in alias and len(alias) < 5):
                    continue
                aliases.append(alias)
            entity["aliases"] = sorted(set(aliases), key=lambda value: (value.casefold(), value))[:4]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("sources/wikidata-discovered.json"))
    parser.add_argument("--limit", type=int, default=25_000)
    parser.add_argument("--per-type", type=int, default=8_000)
    parser.add_argument("--retrieved", default=dt.date.today().isoformat())
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/discovery"))
    parser.add_argument("--seed", type=Path, default=Path("sources/wikidata-snapshot.json"))
    args = parser.parse_args()
    if not 1 <= args.limit <= 60_000 or not 1 <= args.per_type <= 10_000:
        raise SystemExit("discovery bounds exceeded")

    by_qid = {}
    if args.seed.exists():
        seed = json.loads(args.seed.read_bytes())
        for entity in seed["entities"]:
            label = safe_name(entity["canonical"])
            if not label:
                continue
            by_qid[entity["qid"]] = {
                **entity,
                "canonical": label,
                "relevance_score": min(100, 40 + entity["sitelinks"]),
                "tier": "core",
                "ambiguity_risk": "high" if label.casefold() in COMMON_AMBIGUOUS else "low",
                "inclusion_reason": "reviewed-seed;" + f"sitelinks={entity['sitelinks']}",
            }
    for qid, category in TYPE_MAP.items():
        for row in query_type(qid, args.per_type, args.cache_dir):
            entity_qid = row["item"]["value"].rsplit("/", 1)[-1]
            label = safe_name(row["label"]["value"])
            sitelinks = int(row["sitelinks"]["value"])
            assessed = quality(label, sitelinks) if label else None
            if not assessed:
                continue
            score, tier, ambiguous = assessed
            candidate = {
                "qid": entity_qid,
                "canonical": label,
                "aliases": [],
                "category": category,
                "sitelinks": sitelinks,
                "relevance_score": score,
                "tier": tier,
                "ambiguity_risk": "high" if ambiguous else "low",
                "inclusion_reason": f"wikidata:{category};sitelinks={sitelinks}",
            }
            previous = by_qid.get(entity_qid)
            if previous is None or (candidate["relevance_score"], category) > (previous["relevance_score"], previous["category"]):
                by_qid[entity_qid] = candidate

    ranked = sorted(by_qid.values(), key=lambda item: (-item["relevance_score"], -item["sitelinks"], item["canonical"].casefold(), item["qid"]))
    entities = []
    seen_names = set()
    for entity in ranked:
        normalized = runtime_normalized(entity["canonical"])
        if normalized in seen_names:
            continue
        seen_names.add(normalized)
        entities.append(entity)
        if len(entities) == args.limit:
            break
    enrich_core_aliases(entities, args.cache_dir)
    for entity in entities:
        entity["aliases"] = [alias for alias in entity["aliases"] if safe_alias(entity["canonical"], alias)]
    snapshot = {
        "schema_version": 2,
        "retrieved_at": args.retrieved,
        "source": {"name": "Wikidata structured data", "version": args.retrieved, "license": "CC0-1.0", "url": ENDPOINT},
        "discovery": {"types": TYPE_MAP, "per_type_limit": args.per_type, "catalog_limit": args.limit, "minimum_sitelinks": 2},
        "entities": entities,
    }
    if args.output.exists():
        previous = json.loads(args.output.read_bytes())
        if previous.get("discovery") == snapshot["discovery"] and previous.get("entities") == snapshot["entities"]:
            print(json.dumps({"terms": len(entities), "output": str(args.output), "unchanged": True}))
            return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(compact(snapshot))
    print(json.dumps({"terms": len(entities), "output": str(args.output), "types": len(TYPE_MAP)}))


if __name__ == "__main__":
    main()
