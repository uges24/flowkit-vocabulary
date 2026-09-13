# Vocabulary scale benchmark

Measured on 2026-09-13 on the current Windows development machine. Inputs are
real quality-filtered Wikidata entities; no duplicated or synthetic terms.

| Terms | JSON | gzip | SQLite | Refresh | Startup | cold p95 | warm p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1,000 | 244,763 B | 33,113 B | 185,216 B | 19.94 ms | 3.755 ms | 0.0348 ms | 0.0415 ms |
| 10,000 | 2,216,634 B | 201,933 B | 1,231,696 B | 69.90 ms | 3.613 ms | 0.0330 ms | 0.0435 ms |
| 25,000 | 5,577,622 B | 471,232 B | 3,110,416 B | 165.59 ms | 3.794 ms | 0.0452 ms | 0.0479 ms |
| 50,000 | not run | not run | not run | not run | not run | not run | not run |

Only 26,512 unique candidates passed the current quality filters, so a real 50k
benchmark was deliberately not fabricated. The deterministic production pack
contains 25,002 terms including two FlowKit-curated additions, is 522,785 bytes
compressed and 5,792,680 bytes unpacked. Its 876 core entities retain 1,752
quality-filtered English aliases.

The unchanged FlowKit Rust runtime fixture measured a 128-term active snapshot
at 24,320 bytes owned heap. Its fixture-scale timings were refresh 349.895 ms,
snapshot 13.305 ms, candidates 24.320 ms, and sentence lookup 52.734 ms. The
existing negative test covering `vessel`/`Vercel`, `linear`/`Linear`, ambiguity,
and inactive context passed. These fixture timings are not substituted for the
SQLite measurements above.

The publisher's 2,160-sentence ordinary-English collision corpus also passed:
all catalog entries colliding with its 27 ambiguous forms were marked high risk.
This metadata gate complements, rather than replaces, FlowKit's runtime
abstention test.

Recommendation: 25k. It is the largest measured real catalog and stays small on
disk with sub-0.06 ms exact indexed lookup p95. A 50k release should wait for
enough eligible public candidates and a real benchmark.
