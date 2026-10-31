import ast
import unittest
from pathlib import Path

from fixture_mod import total


class TotalTests(unittest.TestCase):
    def test_total(self):
        self.assertEqual(total([1, 2, 3]), 6)

    def test_sin_bucle_manual(self):
        source = Path(__file__).with_name('fixture_mod.py').read_text(encoding='utf-8')
        loops = [n for n in ast.walk(ast.parse(source)) if isinstance(n, (ast.For, ast.While))]
        self.assertEqual(loops, [], 'refactoriza total sin bucle manual')
