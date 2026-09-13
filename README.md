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
