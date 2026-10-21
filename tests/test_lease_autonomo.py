"""Lease de autonomía del líder y testigo quirúrgico (loop-autonomo-testigo)."""
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
HOOK_PATH = REPO / '.claude' / 'hooks' / 'pretool.py'
SCRIPT = REPO / '.microharness' / 'sdd.py'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeStdin:
    def __init__(self, tty=False):
        self.tty = tty

    def isatty(self):
        return self.tty


class LeaseAutonomoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hook = load('hook_lease', HOOK_PATH)
        cls.sdd = load('sdd_lease', SCRIPT)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / '.microharness').mkdir()
        self.old_root, self.old_memory = self.sdd.ROOT, self.sdd.MEMORY
        self.sdd.ROOT = self.root
        self.sdd.MEMORY = self.root / '.microharness' / 'memory.json'
        self.addCleanup(self._restore)
        env = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}
        self._env_cm = mock.patch.dict(os.environ, env, clear=True)
        self._env_cm.start()
        self.addCleanup(self._env_cm.stop)
        self._stdin_cm = mock.patch.object(sys, 'stdin', FakeStdin(False))
        self._stdin_cm.start()
        self.addCleanup(self._stdin_cm.stop)

    def _restore(self):
        self.sdd.ROOT, self.sdd.MEMORY = self.old_root, self.old_memory

    def write_config(self, **kwargs):
        path = self.root / '.microharness' / 'config.json'
        path.write_text(json.dumps(kwargs), encoding='utf-8')

    def seed_task(self, slug='tarea'):
        with contextlib.redirect_stdout(io.StringIO()):
            self.sdd.new(slug)
        folder = self.root / 'spec' / slug
        data = self.sdd.load(folder / 'spec.json')
        data['title'] = 'T'
        data['scope']['allowed_paths'] = ['src/**']
        data['testing']['protected_tests'] = ['tests/t.py']
        data['testing']['commands'] = [[sys.executable, '-m', 'unittest', 'discover', '-s', 'pruebas']]
        self.sdd.dump(folder / 'spec.json', data)
        (folder / 'requerimientos.md').write_text(
            '# QUÉ\nWHEN x, THE y SHALL z.\nAC-01: ok.\n## Fuera de alcance\nNada.\n',
            encoding='utf-8')
        (folder / 'plan.md').write_text('# CÓMO\nHacer.\n', encoding='utf-8')
        (folder / 'tareas.md').write_text('# PASOS\n- [ ] T01 (AC-01): hacer.\n', encoding='utf-8')
        (self.root / 'tests').mkdir(exist_ok=True)
        (self.root / 'tests' / 't.py').write_text('x = 1\n', encoding='utf-8')
        (self.root / 'pruebas').mkdir(exist_ok=True)
        (self.root / 'pruebas' / 'test_ok.py').write_text(
            'import unittest\n\n\nclass Ok(unittest.TestCase):\n    def test_ok(self):\n        pass\n',
            encoding='utf-8')
        return folder

    def make_note(self, fact, for_task, for_phase):
        with contextlib.redirect_stdout(io.StringIO()):
            self.sdd.note(fact, None, None, 'cita literal', for_task=for_task, for_phase=for_phase)
        mem = self.sdd.load(self.sdd.MEMORY)
        return mem['project']['observations'][-1]['id']

    def approve_spec(self, slug='tarea'):
        nid = self.make_note('apruebo la spec', slug, 'spec')
        with contextlib.redirect_stdout(io.StringIO()):
            self.sdd.approve(slug, 'spec', 'Humano', '@note:' + nid)

    # T01 (AC-01): seal autónomo del líder con lease activo.
    def test_seal_autonomo_con_lease_activo(self):
        self.write_config(agent_may_approve=True)
        self.seed_task()
        self.approve_spec()
        with contextlib.redirect_stdout(io.StringIO()):
            self.sdd.seal('tarea', 'lider', 'Pruebas de aceptación verificadas y congeladas')
        mem = self.sdd.load(self.sdd.MEMORY)
        self.assertIn('tests/t.py', mem['tasks']['tarea']['sealed_tests'])

    # T01 (AC-04): approve spec sin @note sigue exigiendo terminal humana.
    def test_approve_spec_sin_nota_sigue_bloqueado(self):
        self.write_config(agent_may_approve=True)
        self.seed_task()
        with self.assertRaises(ValueError):
            self.sdd.approve('tarea', 'spec', 'lider', 'texto plano sin nota')

    # T02 (AC-02): approve close autónomo con gates en verde.
    def test_approve_close_autonomo_en_verde(self):
        self.write_config(agent_may_approve=True)
        self.seed_task()
        self.approve_spec()
        with contextlib.redirect_stdout(io.StringIO()):
            self.sdd.seal('tarea', 'lider', 'Pruebas verificadas y congeladas')
            self.sdd.review('tarea', 'APROBADO', 'Autor: diff mínimo, AC-01 cubierto')
            self.sdd.approve('tarea', 'close', 'lider', 'Loop autónomo completado')
        mem = self.sdd.load(self.sdd.MEMORY)
        self.assertIsNotNone(mem['tasks']['tarea']['approvals']['close'])
        spec = self.sdd.load(self.root / 'spec' / 'tarea' / 'spec.json')
        self.assertEqual(spec['state'], 'terminado')

    # T02 (AC-03): la deriva de alcance revoca el lease.
    def test_deriva_revoca_lease(self):
        self.write_config(agent_may_approve=True)
        self.seed_task()
        self.approve_spec()
        self.assertTrue(self.sdd.has_active_spec_lease('tarea'))
        (self.root / 'spec' / 'tarea' / 'plan.md').write_text(
            '# CÓMO\nCambiado tras aprobar.\n', encoding='utf-8')
        self.assertFalse(self.sdd.has_active_spec_lease('tarea'))
        with self.assertRaises(ValueError):
            self.sdd.seal('tarea', 'lider', 'texto plano')
        with self.assertRaises(ValueError):
            self.sdd.approve('tarea', 'close', 'lider', 'texto plano')

    # T03 (AC-05): approve close genera spec/<slug>/testigo.md sellado.
    def test_approve_close_genera_testigo(self):
        self.write_config(agent_may_approve=True)
        self.seed_task()
        self.approve_spec()
        with contextlib.redirect_stdout(io.StringIO()):
            self.sdd.seal('tarea', 'lider', 'Pruebas verificadas y congeladas')
            self.sdd.review('tarea', 'APROBADO', 'Autor: diff mínimo, AC-01 cubierto')
            self.sdd.approve('tarea', 'close', 'lider', 'Loop autónomo completado')
        witness_path = self.root / 'spec' / 'tarea' / 'testigo.md'
        self.assertTrue(witness_path.is_file())
        content = witness_path.read_text(encoding='utf-8')
        task = self.sdd.load(self.sdd.MEMORY)['tasks']['tarea']
        self.assertIn(task['approvals']['spec']['fingerprint'], content)
        self.assertIn(task['receipt']['digest'], content)
        self.assertIn('tests/t.py', content)
        self.assertIn('AC-01', content)
        seal = task.get('witness')
        self.assertIsNotNone(seal)
        self.assertEqual(seal['path'], 'spec/tarea/testigo.md')
        self.assertEqual(seal['sha256'], self.sdd.hash_file(witness_path))

    # ---- T04 (AC-06): hook ----
    def hook_run(self, agent, cmd, may_approve=True):
        cfg = self.root / '.microharness' / 'config.json'
        cfg.write_text(json.dumps({'agent_may_approve': may_approve}), encoding='utf-8')
        return self.hook.run({'tool_name': 'Bash', 'cwd': str(self.root),
                              'agent_type': agent, 'tool_input': {'command': cmd}})

    def hook_main(self, agent, cmd):
        event = {'agent_type': agent, 'tool_name': 'Bash', 'cwd': str(self.root),
                 'tool_input': {'command': cmd}}
        proc = subprocess.run([sys.executable, str(HOOK_PATH)], input=json.dumps(event),
                              capture_output=True, text=True, cwd=self.root)
        self.assertEqual(proc.returncode, 0)
        return json.loads(proc.stdout)

    def test_hook_permite_seal_lider_sin_nota(self):
        reason = self.hook_run(
            'lider', 'python3 .microharness/sdd.py seal x --by lider --evidence texto')
        self.assertIsNone(reason)

    def test_hook_permite_approve_close_lider_sin_nota(self):
        reason = self.hook_run(
            'lider', 'python3 .microharness/sdd.py approve x close --by lider --evidence texto')
        self.assertIsNone(reason)

    def test_hook_exige_nota_en_approve_spec_y_allow_test(self):
        for cmd in ('python3 .microharness/sdd.py approve x spec --by lider --evidence texto',
                    'python3 .microharness/sdd.py allow-test-command custom --evidence texto'):
            with self.subTest(cmd=cmd):
                self.assertIsNotNone(self.hook_run('lider', cmd))

    def test_hook_sigue_denegando_no_lider_sin_nota(self):
        for agent in ('autor', 'implementador'):
            with self.subTest(agent=agent):
                reason = self.hook_run(
                    agent, 'python3 .microharness/sdd.py seal x --by lider --evidence texto')
                self.assertIsNotNone(reason)

    def test_main_emite_allow_explicito(self):
        payload = self.hook_main('lider', 'python3 .microharness/sdd.py check x')
        self.assertEqual(payload['hookSpecificOutput']['permissionDecision'], 'allow')

    def test_main_emite_deny_al_bloquear(self):
        payload = self.hook_main(
            'lider', 'python3 .microharness/sdd.py approve x spec --by P --evidence texto')
        self.assertEqual(payload['hookSpecificOutput']['permissionDecision'], 'deny')


if __name__ == '__main__':
    unittest.main()
