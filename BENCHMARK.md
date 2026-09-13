# Vocabulary scale benchmark

Measured on 2026-09-13 on the current Windows development machine. Inputs are
real quality-filtered Wikidata entities; no duplicated or synthetic terms.

| Terms | JSON | gzip | SQLite | Refresh | Startup | cold p95 | warm p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1,000 | 215,429 B | 21,136 B | 185,216 B | 50.63 ms | 3.555 ms | 0.0335 ms | 0.0422 ms |
| 10,000 | 2,184,767 B | 188,544 B | 1,231,696 B | 90.17 ms | 3.781 ms | 0.0385 ms | 0.0473 ms |
| 25,000 | 5,545,459 B | 457,820 B | 3,126,896 B | 206.63 ms | 4.825 ms | 0.0394 ms | 0.0434 ms |
| 50,000 | not run | not run | not run | not run | not run | not run | not run |

Only 26,512 unique candidates passed the current quality filters, so a real 50k
benchmark was deliberately not fabricated. The deterministic production pack
contains 25,002 terms including two FlowKit-curated additions, is 506,667 bytes
compressed and 5,760,519 bytes unpacked. Aliases are restricted to normalized
equivalents, short uppercase initialisms, and canonical corporate-name bases;
the candidate currently retains 251 such aliases.

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
