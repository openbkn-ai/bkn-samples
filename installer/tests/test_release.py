import unittest

from installer.contract import OFFICIAL_SOURCE_REPO
from installer.release import ReleaseError, assert_release_tag, assert_same_digest, image_refs, main_build_version, merge_catalog

DIGEST = "sha256:" + "ab" * 32


def index(version: str, name: str, digest: str, repo: str = OFFICIAL_SOURCE_REPO) -> dict:
    return {
        "sourceRepo": repo,
        "version": version,
        "samples": [{"name": name, "manifestSha256": digest, "displayName": name}],
    }


class ReleasePinTest(unittest.TestCase):
    def test_tag_must_equal_version_and_cannot_be_latest(self):
        self.assertEqual(assert_release_tag("0.1.0", "0.1.0"), "0.1.0")
        self.assertEqual(assert_release_tag("v0.1.0", "0.1.0"), "0.1.0")
        with self.assertRaises(ReleaseError):
            assert_release_tag("latest", "0.1.0")
        with self.assertRaises(ReleaseError):
            assert_release_tag("0.2.0", "0.1.0")

    def test_main_build_uses_the_platform_version_shape(self):
        self.assertEqual(
            main_build_version("0.1.0", "20260925010000", "abcdef1"),
            "0.1.0-main.20260925010000.shaabcdef1",
        )
        with self.assertRaises(ReleaseError):
            main_build_version("0.1.0", "2026", "abcdef1")

    def test_image_refs_use_the_pinned_version(self):
        swr, ghcr = image_refs("0.1.0")
        self.assertTrue(swr.endswith(":0.1.0"))
        self.assertTrue(ghcr.endswith(":0.1.0"))
        self.assertNotIn("latest", swr + ghcr)

    def test_registry_digests_must_match(self):
        self.assertEqual(assert_same_digest(DIGEST, DIGEST), DIGEST)
        with self.assertRaises(ReleaseError):
            assert_same_digest(DIGEST, "sha256:" + "cd" * 32)

    def test_sha_mismatch_makes_that_sample_unavailable(self):
        image = index("0.1.0", "supply-chain", "a" * 64)
        repo = index("0.1.0", "supply-chain", "b" * 64)
        merged = merge_catalog("0.1.0", image, repo)
        self.assertFalse(merged["sourceRejected"])
        self.assertEqual(merged["samples"][0]["status"], "unavailable")
        self.assertFalse(merged["samples"][0]["installable"])
        self.assertEqual(merged["samples"][0]["code"], "source_rejected")

    def test_other_repository_rejects_the_catalog(self):
        image = index("0.1.0", "supply-chain", "a" * 64, repo="https://github.com/example/samples")
        repo = index("0.1.0", "supply-chain", "a" * 64)
        merged = merge_catalog("0.1.0", image, repo)
        self.assertTrue(merged["sourceRejected"])
        self.assertFalse(merged["samples"][0]["installable"])


if __name__ == "__main__":
    unittest.main()
