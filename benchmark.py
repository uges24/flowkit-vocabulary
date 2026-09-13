#!/usr/bin/env python3
"""Measure deterministic pack/SQLite/lookup scaling without loading the catalog."""

import argparse
import gzip
import json
import sqlite3
import statistics
import tempfile
import time
import tracemalloc
from pathlib import Path


def percentile(values, fraction):
    return sorted(values)[min(len(values) - 1, int(len(values) * fraction))]


def measure(entities, size):
    rows = entities[:size]
    payload = json.dumps({"schema_version": 1, "pack_version": 0, "terms": rows}, ensure_ascii=False, separators=(",", ":")).encode()
    compressed = gzip.compress(payload, compresslevel=9, mtime=0)
    with tempfile.TemporaryDirectory() as directory:
        db_path = Path(directory) / "vocabulary.db"
        start = time.perf_counter()
        connection = sqlite3.connect(db_path)
        try:
            connection.executescript("""
              PRAGMA journal_mode=WAL;
              CREATE TABLE terms(id INTEGER PRIMARY KEY, canonical TEXT NOT NULL, normalized TEXT NOT NULL UNIQUE, category TEXT NOT NULL, rank INTEGER NOT NULL, tier TEXT NOT NULL);
              CREATE INDEX idx_terms_category_rank ON terms(category, rank DESC);
            """)
            connection.executemany("INSERT INTO terms(canonical,normalized,category,rank,tier) VALUES(?,?,?,?,?)", [
                (row["canonical"], row["canonical"].casefold(), row["category"], row.get("relevance_score", row.get("sitelinks", 0)), row.get("tier", "core")) for row in rows
            ])
            connection.commit()
            refresh_ms = (time.perf_counter() - start) * 1000
            db_bytes = db_path.stat().st_size + sum(path.stat().st_size for path in Path(directory).glob("vocabulary.db-*") if path.is_file())
            cold = []
            warm = []
            probes = [row["canonical"].casefold() for row in rows[::max(1, len(rows) // 100)][:100]]
            for probe in probes:
                before = time.perf_counter_ns(); connection.execute("SELECT canonical FROM terms WHERE normalized=?", (probe,)).fetchone(); cold.append((time.perf_counter_ns()-before)/1e6)
            for _ in range(10):
                for probe in probes:
                    before = time.perf_counter_ns(); connection.execute("SELECT canonical FROM terms WHERE normalized=?", (probe,)).fetchone(); warm.append((time.perf_counter_ns()-before)/1e6)
        finally:
            connection.close()
        before = time.perf_counter(); connection = sqlite3.connect(db_path); connection.execute("SELECT count(*) FROM terms").fetchone(); startup_ms = (time.perf_counter()-before)*1000; connection.close()
    return {"terms": len(rows), "json_bytes": len(payload), "gzip_bytes": len(compressed), "db_bytes": db_bytes, "refresh_ms": round(refresh_ms, 2), "startup_ms": round(startup_ms, 3), "cold_lookup_p50_ms": round(statistics.median(cold), 4), "cold_lookup_p95_ms": round(percentile(cold, .95), 4), "warm_lookup_p50_ms": round(statistics.median(warm), 4), "warm_lookup_p95_ms": round(percentile(warm, .95), 4)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--sizes", default="1000,10000,25000,50000")
    args = parser.parse_args()
    entities = json.loads(args.snapshot.read_bytes())["entities"]
    tracemalloc.start()
    results = [measure(entities, size) for size in map(int, args.sizes.split(",")) if size <= len(entities)]
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(json.dumps({"available_terms": len(entities), "benchmark_peak_python_bytes": peak, "results": results}, indent=2))


if __name__ == "__main__":
    main()
