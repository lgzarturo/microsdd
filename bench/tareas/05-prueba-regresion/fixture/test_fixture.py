import unittest

from fixture_mod import clamp


class ClampTests(unittest.TestCase):
    def test_clamp_bounds(self):
        self.assertEqual(clamp(-1, 0, 10), 0)
        self.assertEqual(clamp(11, 0, 10), 10)
        self.assertEqual(clamp(5, 0, 10), 5)
