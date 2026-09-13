# Source decisions

Checked 2026-09-13.

| Source | Decision | Authoritative basis |
|---|---|---|
| Wikidata structured data | Enabled | CC0 structured data: https://www.wikidata.org/wiki/Wikidata:Licensing ; SPARQL access: https://query.wikidata.org/ |
| npm registry metadata | Disabled | Public API access is permitted, but registry data belongs to publishers and packages retain independent licenses: https://docs.npmjs.com/policies/open-source-terms/ |
| PyPI metadata | Disabled | API/caching guidance: https://docs.pypi.org/api/ ; public BigQuery tables describe only a generic Creative Commons license: https://docs.pypi.org/api/bigquery/ |
| crates.io metadata | Disabled | An explicit authoritative redistribution license suitable for this derived public catalog was not established. |

Disabled sources are not fetched by CI and contribute zero terms.
