# FlowKit public vocabulary

This public, vocabulary-only repository produces signed data packs for FlowKit. It contains no application source, transcripts, recordings, History, Dictionary data, project paths, contacts, personal vocabulary, or user identifiers.

The source is a bounded allowlist resolved through Wikidata structured-data APIs. Wikidata structured data is CC0. Two explicitly identified FlowKit terms are curated additions under MIT.

Selection is deliberately allowlist-based: at most 300 reviewed English Wikipedia titles covering software, technologies, products, companies, and services are resolved to stable Wikidata QIDs. The publisher retains the canonical English label and at most four bounded English aliases. Rank is `5000 + min(5000, sitelinks × 25)` and confidence is `45 + min(30, sitelinks ÷ 5)`. These aliases remain scored vocabulary candidates in FlowKit; they are not unconditional replacement rules.

The weekly workflow makes at most twelve bounded source requests, validates schema/provenance/content, rejects more than 10% removals or 1.75× growth, shows the diff, and skips publication when content is unchanged. Releases contain only `manifest.json`, `manifest.sig`, and one immutable `global-vN.json.gz` artifact.

Authenticity uses a detached Ed25519 signature over the exact manifest bytes. The private key exists only as the `VOCABULARY_SIGNING_KEY` Actions secret; FlowKit pins only its public key. SHA-256 then binds the signed manifest to the compressed artifact.
