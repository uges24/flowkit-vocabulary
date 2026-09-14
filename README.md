# FlowKit public vocabulary

This public, vocabulary-only repository produces signed data packs for FlowKit.
It contains no application source, transcripts, recordings, History, Dictionary
data, project paths, contacts, personal vocabulary, installed-app data, context,
corrections, or user identifiers.

## Discovery

`discover.py` makes bounded, deterministic queries for fourteen explicit
Wikidata entity classes. Wikidata structured data is CC0. Candidates require an
English canonical label, at least two sitelinks, a safe non-hash-like name, and
an approved category. Namespace pages and high-risk names are rejected. Common
speech collisions require at least forty sitelinks. Every retained term records
its QID, inclusion reason, relevance score, ambiguity risk, and tier.

The reviewed legacy catalog is retained as a seed so accepted spellings and
aliases are not lost. The production catalog is capped at 25,000 terms. The
generator can measure up to 60,000, but 50k is not approved without enough
quality-filtered source candidates and another benchmark.

Tiers are `core` (40+ sitelinks), `extended` (10–39), and `discovered` (2–9).
They map to separated rank bands in the signed pack. FlowKit continues to keep
the complete catalog in SQLite and caps the active decoder snapshot at 128.

## Sources

- **Wikidata: enabled.** Structured data is CC0-1.0 and its SPARQL endpoint is
  used with a named user agent, bounded response size, retries, and a local CI
  cache for one run.
- **npm: disabled.** The public APIs may be accessed, but registry package data
  remains publisher-owned under package-specific terms; FlowKit does not
  redistribute a derived name catalog without a clearer grant.
- **PyPI: disabled.** Its APIs are documented and public, but the broad dataset
  license is described only generically as Creative Commons and useful download
  popularity requires a separate BigQuery dependency.
- **crates.io: disabled.** No sufficiently explicit authoritative metadata
  redistribution grant was established in this pass.

See `SOURCES.md` for authoritative links and `BENCHMARK.md` for measurements.

## Publication safety

Weekly publication is discovery → normalized snapshot → provenance → diff →
validation → deterministic gzip → signed manifest → immutable release. More
than 10% removal or 1.75× growth remains blocked. The one transition from v3's
small catalog to v4 is allowed only when the deterministic content hash equals
`APPROVED_BOOTSTRAP_CONTENT_SHA256`; any source drift stops publication for
review. Previous releases remain available for rollback.

Authenticity uses a detached Ed25519 signature over exact manifest bytes. The
private key exists only as the `VOCABULARY_SIGNING_KEY` Actions secret. Workflow
permissions remain `contents: write`.

Discovery and release are separate workflows. Discovery may query Wikidata and
uploads an unsigned future candidate for review. Release accepts only a frozen,
versioned candidate checked into `release-candidates/`; it performs no public-data
discovery, validates exact hashes/schema/counts, signs the frozen manifest, and
publishes those exact bytes.

## Release record

- V4 tag: `v4`
- Published: 2026-09-14T02:49:18Z
- Accepted publisher commit: `179373e8a33586d9c88b22ce4dc390df0a8a451f`
- Content SHA-256: `ce531d2112e8ed6f4a6fefc4e680c4a73fc72b51cfad2cd317c50f08c8b9e31d`
- Artifact SHA-256: `c7f489d19846837ed3a443ba05a5c63ee9ebbb3e970fc322c3786f68b2892603`
- Catalog: 25,008 terms and 2,079 aliases
- Production verification: signed dry run and public-byte verification passed;
  isolated FlowKit V3 activated V4 from the production endpoint and retained V4
  after restart.
- Rollback release: `v3`
