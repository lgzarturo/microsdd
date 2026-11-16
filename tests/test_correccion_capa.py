"""Compuertas de corrección: recibo, pases, núcleo, RDD, versión, docs y router."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / '.microharness' / 'sdd.py'
HOOK_PATH = REPO / '.claude' / 'hooks' / 'pretool.py'
BENCH_PATH = REPO / '.microharness' / 'bench.py'

spec = importlib.util.spec_from_file_location('sdd_correccion', SCRIPT)
sdd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdd)


class FakeStdin:
    def __init__(self, tty=True):
        self.tty = tty

    def isatty(self):
        return self.tty


@contextlib.contextmanager
def human_tty():
    old = os.environ.pop('CLAUDECODE', None)
    prev = sys.stdin
    sys.stdin = FakeStdin(True)
    try:
        yield
    finally:
        sys.stdin = prev
        if old is None:
            os.environ.pop('CLAUDECODE', None)
        else:
            os.environ['CLAUDECODE'] = old


class CorreccionCapaTests(unittest.TestCase):
    def setUp(self):
        self._tty = human_tty()
        self._tty.__enter__()
        self.addCleanup(self._tty.__exit__, None, None, None)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.old_root, self.old_memory = sdd.ROOT, sdd.MEMORY
        sdd.ROOT = Path(self.tmp.name)
        sdd.MEMORY = sdd.ROOT / '.microharness' / 'memory.json'
        self.addCleanup(self._restore)
        env = mock.patch.dict(os.environ, {'GIT_CEILING_DIRECTORIES': str(sdd.ROOT.parent)})
        env.start()
        self.addCleanup(env.stop)
        with contextlib.redirect_stdout(io.StringIO()):
            sdd.new('capa')
        self.folder = sdd.ROOT / 'spec' / 'capa'
        data = sdd.load(self.folder / 'spec.json')
        data['title'] = 'Capa'
        data['scope']['allowed_paths'] = ['src/**', 'tests/**', '.microharness/sdd.py']
        (sdd.ROOT / 'pruebas').mkdir()
        (sdd.ROOT / 'pruebas' / 'test_ok.py').write_text(
            'import unittest\n\n\nclass Ok(unittest.TestCase):\n    def test_ok(self):\n        pass\n',
            encoding='utf-8')
        data['testing']['commands'] = [[sys.executable, '-m', 'unittest', 'discover', '-s', 'pruebas']]
        sdd.dump(self.folder / 'spec.json', data)
        (self.folder / 'requerimientos.md').write_text(
            '# QUÉ\nWHEN x, THE y SHALL z.\nAC-01: ok.\n## Fuera\nNada.\n', encoding='utf-8')
        (self.folder / 'plan.md').write_text('# CÓMO\nHacer.\n', encoding='utf-8')
        (self.folder / 'tareas.md').write_text('# PASOS\n- [ ] T01 (AC-01): hacer.\n', encoding='utf-8')

    def _restore(self):
        sdd.ROOT, sdd.MEMORY = self.old_root, self.old_memory

    def git(self, *args):
        subprocess.run(['git', *args], cwd=sdd.ROOT, check=True, capture_output=True)

    def git_repo(self, tracked: dict[str, str]):
        self.git('init', '-q')
        self.git('config', 'user.email', 't@example.com')
        self.git('config', 'user.name', 'T')
        for name, content in tracked.items():
            path = sdd.ROOT / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
            self.git('add', '--', name)
        self.git('-c', 'commit.gpgsign=false', 'commit', '-q', '--no-verify', '--allow-empty', '-m', 'inicial')

    def quiet(self, fn, *args, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return fn(*args, **kwargs)

    # AC-04 ------------------------------------------------------------------

    def test_ac04_pases_reales_y_bench(self):
        self.assertEqual(sdd.tests_ran('Ran 1 test in 0.0s\nOK (skipped=1)\n'), 0)
        self.assertEqual(sdd.tests_ran('Ran 0 tests in 0.0s\nOK\n'), 0)
        self.assertEqual(sdd.tests_ran('Ran 2 tests in 0.0s\nOK\n'), 2)
        bspec = importlib.util.spec_from_file_location('bench_correccion', BENCH_PATH)
        bench = importlib.util.module_from_spec(bspec)
        bspec.loader.exec_module(bench)
        proc = mock.Mock(returncode=0, stdout='', stderr='Ran 1 test in 0.0s\n\nOK (skipped=1)\n')
        with mock.patch('subprocess.run', return_value=proc):
            self.assertEqual(
                bench.evaluate_fixture(['python', '-m', 'unittest', 't'], sdd.ROOT),
                {'ok': False, 'testsRun': 1})

    # AC-01 / AC-02 / AC-03 --------------------------------------------------

    def test_ac01_recibo_antes_de_aprobado(self):
        self.git_repo({'src/a.py': 'x = 1\n'})
        self.quiet(sdd.approve, 'capa', 'spec', 'Humano', 'Sí')
        with self.assertRaises(ValueError) as caught:
            sdd.review('capa', 'APROBADO', 'sin recibo')
        self.assertIn('verificación', str(caught.exception).lower())
        self.quiet(sdd.record_verification, 'capa')
        self.quiet(sdd.review, 'capa', 'APROBADO', 'con recibo')
        (sdd.ROOT / 'src' / 'a.py').write_text('x = 2\n', encoding='utf-8')
        with self.assertRaises(ValueError) as caught:
            sdd.review('capa', 'APROBADO', 'huella vieja')
        self.assertIn('verificación', str(caught.exception).lower())

    def test_ac02_rechazado_sin_recibo(self):
        self.quiet(sdd.approve, 'capa', 'spec', 'Humano', 'Sí')
        self.quiet(sdd.review, 'capa', 'RECHAZADO', 'falta AC')
        self.assertEqual(sdd.load(sdd.MEMORY)['tasks']['capa']['review'], 'RECHAZADO')

    def test_ac03_integridad_y_reset(self):
        self.git_repo({'src/a.py': 'x = 1\n'})
        self.quiet(sdd.approve, 'capa', 'spec', 'Humano', 'Sí')
        self.quiet(sdd.record_verification, 'capa')
        self.assertIsNotNone(sdd.load(sdd.MEMORY)['tasks']['capa'].get('verification'))
        (self.folder / 'plan.md').write_text('# CÓMO\nOtro plan.\n', encoding='utf-8')
        self.quiet(sdd.approve, 'capa', 'spec', 'Humano', 'reapruobo')
        self.assertIsNone(sdd.load(sdd.MEMORY)['tasks']['capa'].get('verification'))
        self.quiet(sdd.record_verification, 'capa')
        self.git('add', '-A')
        self.git('-c', 'commit.gpgsign=false', 'commit', '-q', '--no-verify', '-m', 'base')
        memory = sdd.load(sdd.MEMORY)
        memory['tasks']['capa']['verification'] = {'fingerprint': 'otra', 'at': sdd.now()}
        sdd.dump(sdd.MEMORY, memory)
        errors = sdd.memory_integrity(sdd.load(sdd.MEMORY))
        self.assertTrue(any('verification' in e for e in errors), errors)

    # AC-05 / AC-06 / AC-07 --------------------------------------------------

    def test_ac05_encogimiento_nucleo(self):
        body = 'line\n' * 200
        self.git_repo({'.microharness/sdd.py': body + "__version__ = '1.5.3'\n"})
        # Quitar 150 líneas netas (>100).
        (sdd.ROOT / '.microharness' / 'sdd.py').write_text(
            'line\n' * 50 + "__version__ = '1.5.3'\n", encoding='utf-8')
        self.quiet(sdd.approve, 'capa', 'spec', 'Humano', 'Sí')
        errors = sdd.validate('capa')
        self.assertTrue(any('Encogimiento del núcleo' in e for e in errors), errors)
        # Fix pequeño: −10 líneas.
        (sdd.ROOT / '.microharness' / 'sdd.py').write_text(
            body[:-len('line\n') * 10] + "__version__ = '1.5.3'\n", encoding='utf-8')
        errors = [e for e in sdd.validate('capa') if 'Encogimiento' in e]
        self.assertEqual(errors, [])
        # 770-like shrink with rewrite-core note.
        (sdd.ROOT / '.microharness' / 'sdd.py').write_text("__version__ = '1.5.3'\n", encoding='utf-8')
        self.quiet(
            sdd.note, 'reescribo .microharness/sdd.py', None, None, 'autorizo',
            for_task='capa', for_phase='rewrite-core')
        errors = [e for e in sdd.validate('capa') if 'Encogimiento' in e]
        self.assertEqual(errors, [])
        note_ids = sdd.pending_rewrite_notes('capa')
        self.assertTrue(note_ids)
        self.quiet(sdd.consume_rewrite_notes, 'capa', note_ids)
        mem = sdd.load(sdd.MEMORY)
        obs = mem['project']['observations'][-1]
        self.assertIsNotNone(obs.get('used_at'))

    def test_ac06_rdd_no_negociable(self):
        self.git_repo({'src/a.py': 'x = 1\n'})
        cfg = sdd.ROOT / '.microharness' / 'config.json'
        cfg.write_text(json.dumps({'rdd_max_lines': 50}), encoding='utf-8')
        (sdd.ROOT / 'src' / 'a.py').write_text('x = 1\n' + ('y = 1\n' * 60), encoding='utf-8')
        self.quiet(sdd.approve, 'capa', 'spec', 'Humano', 'Sí')
        errors = sdd.validate('capa')
        self.assertTrue(any('rdd_max_lines' in e for e in errors), errors)
        memory = sdd.load(sdd.MEMORY)
        memory['project']['decisions'].append({
            'at': sdd.now(), 'by': 'Humano',
            'decision': 'Se aceptan 60 líneas sin cambiar la spec',
            'evidence': 'acepto',
        })
        sdd.dump(sdd.MEMORY, memory)
        errors = sdd.validate('capa')
        self.assertTrue(any('rdd_max_lines' in e for e in errors), errors)

    def test_ac07_version_mezclada(self):
        self.git_repo({
            '.microharness/sdd.py': "__version__ = '1.5.3'\n",
            'tests/test_x.py': 'x = 1\n',
            'CHANGELOG.md': '# C\n',
            'pruebas/test_ok.py': (sdd.ROOT / 'pruebas' / 'test_ok.py').read_text(encoding='utf-8'),
        })
        self.quiet(sdd.approve, 'capa', 'spec', 'Humano', 'Sí')
        (sdd.ROOT / '.microharness' / 'sdd.py').write_text("__version__ = '1.5.4'\n", encoding='utf-8')
        (sdd.ROOT / 'tests' / 'test_x.py').write_text('x = 2\n', encoding='utf-8')
        errors = sdd.validate('capa')
        self.assertTrue(any('__version__' in e for e in errors), errors)
        (sdd.ROOT / 'tests' / 'test_x.py').write_text('x = 1\n', encoding='utf-8')
        (sdd.ROOT / 'CHANGELOG.md').write_text('# C\n\n## 1.5.4\n', encoding='utf-8')
        errors = [e for e in sdd.validate('capa') if '__version__' in e]
        self.assertEqual(errors, [])

    # AC-08 ------------------------------------------------------------------

    def test_ac08_docs_placeholder(self):
        for name in sdd.DOCS:
            (sdd.ROOT / 'docs' / name).write_text(
                f'# {name.removesuffix(".md")}\n\nPendiente de inspección.\n', encoding='utf-8')
        errors = sdd.validate('capa', scope=False)
        self.assertTrue(any('placeholder' in e for e in errors), errors)
        for name in sdd.DOCS:
            (sdd.ROOT / 'docs' / name).write_text(
                sdd.DOCS_TABLE_TEMPLATE.format(title=name.removesuffix('.md')), encoding='utf-8')
        errors = [e for e in sdd.validate('capa', scope=False) if 'placeholder' in e]
        self.assertEqual(errors, [])
        dest = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__('shutil').rmtree(dest, ignore_errors=True))
        old_root, old_mem = sdd.ROOT, sdd.MEMORY
        try:
            sdd.ROOT = dest
            sdd.MEMORY = dest / '.microharness' / 'memory.json'
            with contextlib.redirect_stdout(io.StringIO()):
                sdd.ensure_init()
            text = (dest / 'docs' / 'AGENT.md').read_text(encoding='utf-8')
            self.assertNotIn('Pendiente de inspección', text)
            self.assertIn('| Regla |', text)
        finally:
            sdd.ROOT, sdd.MEMORY = old_root, old_mem

    # AC-09 ------------------------------------------------------------------

    def test_ac09_router_y_hook(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            sdd.cmd_correct('Falta recibo de verificación de check --run')
        payload = json.loads(out.getvalue())
        self.assertEqual(payload['layer'], 'verificacion')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            sdd.cmd_correct('algo nunca visto')
        payload = json.loads(out.getvalue())
        self.assertEqual(payload['layer'], 'humano')
        self.assertIsNone(payload['next'])

        fixture = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__('shutil').rmtree(fixture, ignore_errors=True))
        subprocess.run(['git', 'init', '-q'], cwd=fixture, check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 't@example.com'], cwd=fixture, check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'T'], cwd=fixture, check=True, capture_output=True)
        (fixture / 'a.txt').write_text('a\n', encoding='utf-8')
        subprocess.run(['git', 'add', 'a.txt'], cwd=fixture, check=True, capture_output=True)
        subprocess.run(
            ['git', '-c', 'commit.gpgsign=false', 'commit', '-q', '--no-verify', '-m', 'feat: uno'],
            cwd=fixture, check=True, capture_output=True)
        base = subprocess.run(
            ['git', 'rev-parse', 'HEAD'], cwd=fixture, check=True, capture_output=True, text=True
        ).stdout.strip()
        (fixture / 'a.txt').write_text('b\n', encoding='utf-8')
        subprocess.run(['git', 'add', 'a.txt'], cwd=fixture, check=True, capture_output=True)
        subprocess.run(
            ['git', '-c', 'commit.gpgsign=false', 'commit', '-q', '--no-verify',
             '-m', 'fix: restaura sdd.py'],
            cwd=fixture, check=True, capture_output=True)
        old_root = sdd.ROOT
        try:
            sdd.ROOT = fixture
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                sdd.cmd_corrections(base)
            report = json.loads(out.getvalue())
            self.assertGreaterEqual(report['restores'], 1)
        finally:
            sdd.ROOT = old_root

        help_out = subprocess.run(
            [sys.executable, str(SCRIPT), '--help'],
            capture_output=True, text=True, encoding='utf-8', check=True)
        self.assertIn('correct', help_out.stdout)
        self.assertIn('corrections', help_out.stdout)

        hspec = importlib.util.spec_from_file_location('hook_correccion', HOOK_PATH)
        hook = importlib.util.module_from_spec(hspec)
        hspec.loader.exec_module(hook)
        cmd = 'python .microharness/sdd.py correct "x"'
        self.assertIsNone(hook.run({
            'agent_type': 'lider', 'tool_name': 'Bash', 'tool_input': {'command': cmd},
        }))
        cmd2 = 'python .microharness/sdd.py corrections --since HEAD~1'
        self.assertIsNone(hook.run({
            'agent_type': 'lider', 'tool_name': 'Bash', 'tool_input': {'command': cmd2},
        }))


if __name__ == '__main__':
    unittest.main()
