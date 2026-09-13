#!/usr/bin/env python3
"""Refresh a bounded, deterministic Wikidata vocabulary snapshot."""

import argparse
import datetime as dt
import hashlib
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT = "FlowKitVocabularyPublisher/1.0 (https://github.com/uges24/flowkit-vocabulary)"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
MAX_TITLES = 300
MAX_ALIASES = 4


def compact(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def get_json(base, params, attempts=3):
    url = base + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                if response.length and response.length > 4_000_000:
                    raise RuntimeError("source response exceeds 4 MB")
                return json.load(response)
        except Exception:
            if attempt + 1 == attempts:
                raise
            time.sleep(2 ** attempt)


def batches(values, size=50):
    for start in range(0, len(values), size):
        yield values[start:start + size]


def safe_name(value):
    value = " ".join(value.strip().split())
    if not (2 <= len(value) <= 80) or any(ch in value for ch in "\r\n\t{}[]<>`$"):
        return None
    if value.startswith(("http://", "https://")) or "@" in value:
        return None
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=Path("sources/curated-titles.json"))
    parser.add_argument("--output", type=Path, default=Path("sources/wikidata-snapshot.json"))
    parser.add_argument("--retrieved", default=dt.date.today().isoformat())
    args = parser.parse_args()
    catalog_bytes = args.catalog.read_bytes()
    catalog = json.loads(catalog_bytes)
    title_category = {}
    for category, titles in catalog["categories"].items():
        for title in titles:
            title_category.setdefault(title, category)
    titles = sorted(title_category)
    if len(titles) > MAX_TITLES:
        raise SystemExit(f"bounded title budget exceeded: {len(titles)} > {MAX_TITLES}")

    qids = {}
    for batch in batches(titles):
        data = get_json(WIKIPEDIA_API, {
            "action": "query", "format": "json", "formatversion": 2,
            "prop": "pageprops", "ppprop": "wikibase_item", "redirects": 1,
            "titles": "|".join(batch),
        })
        for page in data["query"]["pages"]:
            qid = page.get("pageprops", {}).get("wikibase_item")
            if qid:
                qids[qid] = title_category.get(page.get("title"), title_category.get(batch[0], "product"))

    entities = []
    for batch in batches(sorted(qids)):
        data = get_json(WIKIDATA_API, {
            "action": "wbgetentities", "format": "json", "formatversion": 2,
            "props": "labels|aliases|sitelinks", "languages": "en", "sitefilter": "enwiki",
            "ids": "|".join(batch),
        })
        for entity in data["entities"].values():
            label = safe_name(entity.get("labels", {}).get("en", {}).get("value", ""))
            if not label or entity.get("missing"):
                continue
            aliases = []
            for item in entity.get("aliases", {}).get("en", []):
                alias = safe_name(item.get("value", ""))
                if alias and alias.casefold() != label.casefold() and alias not in aliases:
                    aliases.append(alias)
            sitelinks = len(entity.get("sitelinks", {}))
            entities.append({
                "qid": entity["id"], "canonical": label, "aliases": sorted(aliases, key=str.casefold)[:MAX_ALIASES],
                "category": qids[entity["id"]], "sitelinks": sitelinks,
            })

    entities.sort(key=lambda item: (item["canonical"].casefold(), item["qid"]))
    snapshot = {
        "schema_version": 1,
        "retrieved_at": args.retrieved,
        "catalog_sha256": hashlib.sha256(catalog_bytes).hexdigest(),
        "source": {"name": "Wikidata structured data", "license": "CC0-1.0", "url": WIKIDATA_API},
        "request_budget": {"titles": len(titles), "http_requests_max": 12, "response_bytes_each_max": 4_000_000},
        "entities": entities,
    }
    if args.output.exists():
        previous = json.loads(args.output.read_bytes())
        comparable = ("catalog_sha256", "source", "request_budget", "entities")
        if all(previous.get(key) == snapshot.get(key) for key in comparable):
            print(f"unchanged: {len(entities)} entities")
            return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(compact(snapshot))
    print(f"wrote {len(entities)} entities to {args.output}")


if __name__ == "__main__":
    main()
