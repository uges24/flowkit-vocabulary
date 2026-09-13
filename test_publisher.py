import base64
import gzip
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


ROOT = Path(__file__).parent


class PublisherTests(unittest.TestCase):
    def test_committed_snapshot_is_bounded_and_provenanced(self):
        data = json.loads((ROOT / "sources/wikidata-snapshot.json").read_bytes())
        self.assertLessEqual(data["request_budget"]["titles"], 300)
        self.assertLessEqual(data["request_budget"]["http_requests_max"], 12)
        self.assertGreater(len(data["entities"]), 128)
        self.assertTrue(all(item["qid"].startswith("Q") for item in data["entities"]))

    def test_release_signature_hash_schema_and_provenance(self):
        manifest_bytes = (ROOT / "dist/manifest.json").read_bytes()
        manifest = json.loads(manifest_bytes)
        public = Ed25519PublicKey.from_public_bytes(bytes.fromhex((ROOT / "PUBLIC_KEY.hex").read_text().strip()))
        public.verify(base64.b64decode((ROOT / "dist/manifest.sig").read_text()), manifest_bytes)
        artifact = (ROOT / "dist" / manifest["artifact"]).read_bytes()
        import hashlib
        self.assertEqual(hashlib.sha256(artifact).hexdigest(), manifest["sha256"])
        payload = json.loads(gzip.decompress(artifact))
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["pack_version"], manifest["pack_version"])
        self.assertEqual(len(payload["terms"]), manifest["term_count"])
        self.assertTrue(all(term["source_ref"].startswith(("wikidata:Q", "flowkit-curated:")) for term in payload["terms"]))


if __name__ == "__main__":
    unittest.main()
