import base64
import gzip
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from build_pack import compact_punctuation_alias, identity_normalized, preferred_surface, spoken_punctuation_aliases
from discover import quality, runtime_normalized, safe_alias, safe_name


ROOT = Path(__file__).parent


class PublisherTests(unittest.TestCase):
    def test_preferred_surface_and_spoken_punctuation_are_deterministic(self):
        self.assertEqual(preferred_surface("Vercel Inc.", ["Vercel"]), "Vercel")
        self.assertEqual(
            preferred_surface("Hudson's Bay Company", ["The Bay"]),
            "Hudson's Bay Company",
        )
        self.assertEqual(spoken_punctuation_aliases("ASP.NET"), ["ASP NET"])
        self.assertEqual(spoken_punctuation_aliases("C++"), ["C plus plus"])
        self.assertEqual(spoken_punctuation_aliases("C#"), ["C sharp"])
        self.assertEqual(identity_normalized("C++"), "c plus plus")
        self.assertEqual(identity_normalized("C#"), "c sharp")
        self.assertEqual(identity_normalized(".NET"), "dot net")

    def test_compact_punctuation_aliases_are_bounded(self):
        self.assertEqual(compact_punctuation_alias("ASP.NET"), "aspnet")
        self.assertEqual(compact_punctuation_alias("Node.js"), "nodejs")
        self.assertEqual(compact_punctuation_alias("Next.js"), "nextjs")
        self.assertEqual(compact_punctuation_alias("llama.cpp"), "llamacpp")
        self.assertEqual(compact_punctuation_alias("Objective-C"), "objectivec")
        self.assertIsNone(compact_punctuation_alias("C++"))
        self.assertIsNone(compact_punctuation_alias("C#"))
        self.assertIsNone(compact_punctuation_alias(".NET"))

    def test_approved_large_bootstrap_build_is_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            subprocess.run([
                "python", str(ROOT / "build_pack.py"),
                "--snapshot", str(ROOT / "sources/wikidata-discovered.json"),
                "--catalog", str(ROOT / "sources/curated-titles.json"),
                "--version", "4", "--output-dir", str(output),
            ], check=True, capture_output=True, text=True)
            manifest = json.loads((output / "manifest.json").read_bytes())
            approved = (ROOT / "APPROVED_BOOTSTRAP_CONTENT_SHA256").read_text().strip()
            self.assertEqual(manifest["content_sha256"], approved)
            self.assertEqual(manifest["term_count"], 25_008)

    def test_discovered_snapshot_is_large_unique_tiered_and_provenanced(self):
        data = json.loads((ROOT / "sources/wikidata-discovered.json").read_bytes())
        self.assertEqual(len(data["entities"]), 25_000)
        names = [item["canonical"].casefold() for item in data["entities"]]
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(all(item["qid"].startswith("Q") for item in data["entities"]))
        self.assertTrue(all(item["tier"] in {"core", "extended", "discovered"} for item in data["entities"]))
        self.assertTrue(all(item["inclusion_reason"].startswith(("wikidata:", "reviewed-seed;")) for item in data["entities"]))

    def test_discovery_rejects_noise_and_downranks_ambiguity(self):
        self.assertIsNone(safe_name("Template:Infobox organization"))
        self.assertIsNone(safe_name("0123456789abcdef0123456789abcdef"))
        self.assertIsNone(safe_name("GoTo"))
        self.assertIsNone(safe_name("Visual Basic 6"))
        self.assertIsNone(quality("Linear", 20))
        self.assertEqual(quality("Linear", 40)[1:], ("core", True))
        self.assertEqual(runtime_normalized("ESPN+"), runtime_normalized("ESPN"))
        self.assertFalse(safe_alias("Hudson's Bay Company", "The Bay"))
        self.assertTrue(safe_alias("Vercel Inc.", "Vercel"))
        self.assertTrue(safe_alias("International Business Machines", "IBM"))

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
