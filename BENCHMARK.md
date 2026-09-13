# Vocabulary scale benchmark

Measured on 2026-09-13 on the current Windows development machine. Inputs are
real quality-filtered Wikidata entities; no duplicated or synthetic terms.

| Terms | JSON | gzip | SQLite | Refresh | Startup | cold p95 | warm p95 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1,000 | 215,429 B | 21,136 B | 185,216 B | 56.99 ms | 3.987 ms | 0.0354 ms | 0.0403 ms |
| 10,000 | 2,184,767 B | 188,544 B | 1,231,696 B | 96.84 ms | 4.945 ms | 0.0320 ms | 0.0411 ms |
| 25,000 | 5,545,459 B | 457,820 B | 3,126,896 B | 206.93 ms | 4.615 ms | 0.0563 ms | 0.0444 ms |
| 50,000 | not run | not run | not run | not run | not run | not run | not run |

Only 26,512 unique candidates passed the current quality filters, so a real 50k
benchmark was deliberately not fabricated. The deterministic production pack
contains 25,008 terms including a small reviewed FlowKit-curated core, is 521,211 bytes
compressed and 5,796,131 bytes unpacked. Aliases are restricted to normalized
equivalents, short uppercase initialisms, and canonical corporate-name bases;
the candidate currently retains 2,032 aliases, including deterministic spoken
forms for punctuation-bearing technical names.

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
