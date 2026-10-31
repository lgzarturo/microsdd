"""Señal de éxito del bench y aviso de invalidez del baseline, sin red."""

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
BENCH_PATH = ROOT / '.microharness' / 'bench.py'
MODEL = 'deepseek/deepseek-v4-flash'
CMD = ['python', '-m', 'unittest', 'test_fixture']
PAYLOAD = json.dumps({'is_error': False, 'subtype': 'success', 'num_turns': 1, 'usage': {'input_tokens': 1}})
TRIVIAL = 'import unittest\n\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n'
CORREGIDO = {
    '01-correccion-localizada': 'def add(a, b):\n    return a + b\n',
    '02-regla-nueva': 'def eligible(age):\n    return age >= 18\n',
    '03-refactor': 'def total(xs):\n    return sum(xs)\n',
    '04-config-docs': "VERSION = '0.1.0'\n",
    '05-prueba-regresion': 'def clamp(x, lo, hi):\n    return max(lo, min(hi, x))\n',
}
FILAS = (
    (0, 'Ran 0 tests in 0.000s\n\nOK\n', False, 0),
    (5, 'Ran 0 tests in 0.000s\n\nNO TESTS RAN\n', False, 0),
    (0, 'Ran 1 test in 0.000s\n\nOK (skipped=1)\n', False, 1),
    (0, 'Ran 1 test in 0.000s\n\nOK (expected failures=1)\n', False, 1),
    (0, 'Ran 2 tests in 0.000s\n\nOK (skipped=1, expected failures=1)\n', False, 2),
    (0, 'Ran 2 tests in 0.000s\n\nOK (skipped=1)\n', True, 2),
    (0, 'Ran 1 test in 0.000s\n\nOK\n', True, 1),
    (1, 'Ran 1 test in 0.000s\n\nFAILED (failures=1)\n', False, 1),
    (0, '', False, 0),
)


class BenchSenalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('microsdd_bench_senal_ut', BENCH_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cls.b = mod
        cls.tasks = mod.list_tasks()

    def setUp(self):
        mock.patch('urllib.request.urlopen', side_effect=AssertionError('red prohibida')).start()
        self.addCleanup(mock.patch.stopall)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def _workdir(self, task, variant='base'):
        work = self.tmp / f"{task['id']}-{variant}"
        self.b.prepare_cell_workdir(Path(task['_dir']), work, variant, model_id=MODEL)
        return work

    def _simulado(self, cmd=CMD, **patch_kw):
        with mock.patch('subprocess.run', **patch_kw) as run:
            return self.b.evaluate_fixture(list(cmd), self.tmp), run

    def _run_cell(self, task, work, agent=None):
        real_run = subprocess.run
        def fake_run(cmd, *args, **kwargs):
            if cmd[0] != 'claude':
                return real_run(cmd, *args, **kwargs)
            if '--version' in cmd:
                return mock.Mock(returncode=0, stdout='2.1.197', stderr='')
            self.prompt = cmd[cmd.index('-p') + 1]
            for name, text in (agent or {}).items():
                (Path(kwargs['cwd']) / name).write_text(text, encoding='utf-8')
            return mock.Mock(returncode=0, stdout=PAYLOAD, stderr='')
        proxy = mock.Mock(LOCAL_TOKEN='local', unsafe=True, **{
            'server.aborted': False, 'assert_readable.return_value': {'count': 0},
            'client_env.return_value': {'ANTHROPIC_AUTH_TOKEN': 'local'}})
        with mock.patch('subprocess.run', side_effect=fake_run):
            return self.b.ClaudeCodeProvider(MODEL, proxy=proxy).run_cell(task, 'base', 0, workdir=work)

    def test_resumen_unittest(self):
        for code, stderr, ok, n in FILAS:
            for exe in ('python', 'python3'):
                with self.subTest(code=code, stderr=stderr, exe=exe):
                    proc = mock.Mock(returncode=code, stdout='', stderr=stderr)
                    res, run = self._simulado([exe, *CMD[1:]], return_value=proc)
                    self.assertEqual(res, {'ok': ok, 'testsRun': n})
                    self.assertEqual(run.call_args.args[0][0], sys.executable)
        for exc in (OSError('x'), subprocess.TimeoutExpired('python', 60)):
            self.assertEqual(self._simulado(side_effect=exc)[0], {'ok': False, 'testsRun': 0})

    def test_cero_pruebas_real(self):
        (self.tmp / 'test_fixture.py').write_text('def test_x():\n    assert False\n', encoding='utf-8')
        self.assertEqual(self.b.evaluate_fixture(list(CMD), self.tmp), {'ok': False, 'testsRun': 0})

    def test_rojo_y_verde(self):
        for task in self.tasks:
            for variant in ('base', 'treatment'):
                with self.subTest(task=task['id'], variant=variant):
                    work = self._workdir(task, variant)
                    rojo = self.b.evaluate_fixture(task['testCommand'], work)
                    self.assertEqual((rojo['ok'], rojo['testsRun'] >= 1), (False, True))
                    (work / 'fixture_mod.py').write_text(CORREGIDO[task['id']], encoding='utf-8')
                    verde = self.b.evaluate_fixture(task['testCommand'], work)
                    self.assertEqual((verde['ok'], verde['testsRun'] >= 1), (True, True))

    def test_run_cell_usa_senal(self):
        for task in self.tasks:
            with self.subTest(task=task['id']):
                sin = self._run_cell(task, self._workdir(task))
                self.assertEqual((sin['success'], sin['status'], sin['testsRun'] >= 1), (False, 'fail', True))
                con = self._run_cell(task, self._workdir(task), {'fixture_mod.py': CORREGIDO[task['id']]})
                self.assertEqual((con['success'], con['status'], con['testsRun'] >= 1), (True, 'ok', True))
                self.assertEqual(self.b.sanitize_report({'cells': [con]})['cells'][0]['testsRun'], con['testsRun'])

    def test_prueba_manipulada_se_restaura(self):
        for task in self.tasks:
            with self.subTest(task=task['id']):
                work = self._workdir(task)
                cell = self._run_cell(task, work, {'test_fixture.py': TRIVIAL})
                self.assertFalse(cell['success'])
                self.assertEqual((work / 'test_fixture.py').read_bytes(),
                                 (Path(task['_dir']) / 'fixture' / 'test_fixture.py').read_bytes())
                self.assertIn('Do not edit test_fixture.py: it is restored before evaluation.', self.prompt)

    def test_entorno_de_evaluacion(self):
        secretos = {k: 'sk-no-debe-llegar' for k in self.b.SECRET_ENV_KEYS}
        with mock.patch.dict(os.environ, secretos):
            _, run = self._simulado(return_value=mock.Mock(returncode=0, stdout='', stderr=''))
        env = run.call_args.kwargs['env']
        self.assertEqual(sorted(set(secretos) & set(env)), [])
        self.assertEqual(env['PYTHONDONTWRITEBYTECODE'], '1')

    def test_huella_fixture(self):
        for task in self.tasks:
            fx = Path(task['_dir']) / 'fixture'
            data = ((fx / 'fixture_mod.py').read_bytes() + (fx / 'test_fixture.py').read_bytes()).replace(b'\r\n', b'\n')
            with self.subTest(task=task['id']):
                self.assertEqual(hashlib.sha256(data).hexdigest(), task['fixtureSha256'])

    def test_aviso_baseline(self):
        titulo, cuerpo = (ROOT / 'bench' / 'baseline' / 'README.md').read_text(encoding='utf-8').split('\n', 1)
        self.assertEqual(titulo, '# Línea base')
        aviso = cuerpo.lstrip().split('\n\n', 1)[0]
        self.assertTrue(aviso.startswith('> **AVISO: este baseline no es evidencia sobre MicroSDD.**'))
        notes = '\n'.join(json.loads((ROOT / 'bench' / 'config.json').read_text(encoding='utf-8'))['notes'])
        for token in ('1f3a731', 'eb3d43e', 'ef3955f', 'no es evidencia sobre MicroSDD'):
            self.assertIn(token, aviso)
            self.assertIn(token, notes)
