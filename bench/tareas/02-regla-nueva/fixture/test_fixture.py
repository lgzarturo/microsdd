import unittest

from fixture_mod import eligible


class EligibleTests(unittest.TestCase):
    def test_eligible(self):
        self.assertIs(eligible(18), True)
        self.assertIs(eligible(17), False)
