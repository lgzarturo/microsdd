import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / '.microharness' / 'sdd.py'
spec = importlib.util.spec_from_file_location('micro_sdd_integridad_utf8', SCRIPT)
sdd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdd)

SLUG = 'fix-sesiones'


@unittest.skipUnless(shutil.which('git'), 'git no disponible')
class InvalidUtf8BaseMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.old_root, self.old_memory = sdd.ROOT, sdd.MEMORY
        sdd.ROOT = Path(self.temporary.name)
        sdd.MEMORY = sdd.ROOT / '.microharness' / 'memory.json'
        self.addCleanup(self.restore)
        env = mock.patch.dict(os.environ, {'GIT_CEILING_DIRECTORIES': str(sdd.ROOT.parent)})
        env.start()
        self.addCleanup(env.stop)
        with contextlib.redirect_stdout(io.StringIO()):
            sdd.new(SLUG)

    def restore(self):
        sdd.ROOT, sdd.MEMORY = self.old_root, self.old_memory

    def git(self, *args):
        subprocess.run(['git', *args], cwd=sdd.ROOT, check=True, capture_output=True)

    def test_invalid_utf8_base_memory_is_unreadable_not_skipped(self):
        # REQ-02 / Q-02: bytes UTF-8 inválidos en HEAD fallan cerrado, con una sola lectura de git.
        self.git('init', '-q')
        self.git('config', 'user.email', 'test@example.com')
        self.git('config', 'user.name', 'Test')
        good = sdd.MEMORY.read_bytes()
        sdd.MEMORY.write_bytes(b'{"tasks": {"\xff\xfe": {}}}\n')
        self.git('add', '-A')
        self.git('-c', 'commit.gpgsign=false', 'commit', '-q', '--no-verify', '-m', 'utf8 inválido')
        sdd.MEMORY.write_bytes(good)
        real = subprocess.run
        calls = []

        def spy(*args, **kwargs):
            calls.append(list(args[0] if args else kwargs['args']))
            return real(*args, **kwargs)

        with mock.patch.object(sdd.subprocess, 'run', spy):
            errors = sdd.validate(SLUG, scope=False)
        integrity = [e for e in errors if e.startswith('Integridad de memoria')]
        self.assertTrue([e for e in integrity if 'HEAD ilegible' in e], errors)
        reads = [c for c in calls if any('HEAD:.microharness/memory.json' in str(a) for a in c)]
        self.assertEqual(len(reads), 1, calls)


if __name__ == '__main__':
    unittest.main()
