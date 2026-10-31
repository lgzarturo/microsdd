import unittest

from fixture_mod import VERSION


class VersionTests(unittest.TestCase):
    def test_version_semver(self):
        parts = VERSION.split('.')
        self.assertEqual(len(parts), 3)
        self.assertTrue(all(p.isdigit() for p in parts))
