"""Pruebas de agent_may_approve y evidencia @note (MicroSDD 1.2.0)."""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
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


class AgentMayApproveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hook = load('hook_ama', HOOK_PATH)
        cls.sdd = load('sdd_ama', SCRIPT)

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
            '# QUE\nWHEN x, THE y SHALL z.\nAC-01: ok.\n## Fuera de alcance\nNada.\n'.replace('QUE', 'QUÉ'),
            encoding='utf-8')
        (folder / 'plan.md').write_text('# COMO\nHacer.\n'.replace('COMO', 'CÓMO'), encoding='utf-8')
        (folder / 'tareas.md').write_text('# PASOS\n- [ ] T01 (AC-01): hacer.\n', encoding='utf-8')
        (self.root / 'tests').mkdir(exist_ok=True)
        (self.root / 'tests' / 't.py').write_text('x = 1\n', encoding='utf-8')
        return folder

    def make_note(self, fact, for_task, for_phase, age_s=0):
        with contextlib.redirect_stdout(io.StringIO()):
            self.sdd.note(fact, None, None, 'cita literal', for_task=for_task, for_phase=for_phase)
        mem = self.sdd.load(self.sdd.MEMORY)
        obs = mem['project']['observations'][-1]
        if age_s:
            old = datetime.now(timezone.utc) - timedelta(seconds=age_s)
            obs['at'] = old.isoformat(timespec='seconds')
            self.sdd.dump(self.sdd.MEMORY, mem)
        return obs['id']

    def test_default_config_true(self):
        self.assertTrue(self.sdd.agent_may_approve_enabled())

    def test_config_false(self):
        self.write_config(agent_may_approve=False)
        self.assertFalse(self.sdd.agent_may_approve_enabled())

    def test_approve_with_note_without_tty(self):
        self.write_config(agent_may_approve=True)
        self.seed_task()
        nid = self.make_note('apruebo la spec', 'tarea', 'spec')
        with contextlib.redirect_stdout(io.StringIO()):
            self.sdd.approve('tarea', 'spec', 'Agente', '@note:' + nid)
        mem = self.sdd.load(self.sdd.MEMORY)
        self.assertIsNotNone(mem['tasks']['tarea']['approvals']['spec'])
        self.assertIsNotNone(mem['project']['observations'][0]['used_at'])

    def test_seal_with_note_without_tty(self):
        self.write_config(agent_may_approve=True)
        self.seed_task()
        nid = self.make_note('sello tests', 'tarea', 'seal')
        with contextlib.redirect_stdout(io.StringIO()):
            self.sdd.seal('tarea', 'Agente', '@note:' + nid)
        mem = self.sdd.load(self.sdd.MEMORY)
        self.assertIn('tests/t.py', mem['tasks']['tarea']['sealed_tests'])

    def test_false_blocked_without_tty(self):
        self.write_config(agent_may_approve=False)
        self.seed_task()
        nid = self.make_note('apruebo', 'tarea', 'spec')
        with self.assertRaises(ValueError):
            self.sdd.approve('tarea', 'spec', 'Agente', '@note:' + nid)

    def test_invalid_note_id(self):
        self.write_config(agent_may_approve=True)
        self.seed_task()
        with self.assertRaises(ValueError):
            self.sdd.approve('tarea', 'spec', 'Agente', '@note:n999')

    def test_expired_note(self):
        self.write_config(agent_may_approve=True)
        self.seed_task()
        nid = self.make_note('apruebo', 'tarea', 'spec', age_s=1801)
        with self.assertRaises(ValueError):
            self.sdd.approve('tarea', 'spec', 'Agente', '@note:' + nid)

    def test_reused_note(self):
        self.write_config(agent_may_approve=True)
        self.seed_task()
        nid = self.make_note('apruebo', 'tarea', 'spec')
        with contextlib.redirect_stdout(io.StringIO()):
            self.sdd.approve('tarea', 'spec', 'Agente', '@note:' + nid)
        # reopen for reapprove path needs new fingerprint - just try consume again via seal wrong phase
        with self.assertRaises(ValueError):
            self.sdd.seal('tarea', 'Agente', '@note:' + nid)

    def test_wrong_phase(self):
        self.write_config(agent_may_approve=True)
        self.seed_task()
        nid = self.make_note('apruebo', 'tarea', 'close')
        with self.assertRaises(ValueError):
            self.sdd.approve('tarea', 'spec', 'Agente', '@note:' + nid)

    def test_wrong_task(self):
        self.write_config(agent_may_approve=True)
        self.seed_task('tarea')
        self.seed_task('otra')
        nid = self.make_note('apruebo', 'otra', 'spec')
        with self.assertRaises(ValueError):
            self.sdd.approve('tarea', 'spec', 'Agente', '@note:' + nid)

    def test_plain_evidence_still_needs_tty(self):
        self.write_config(agent_may_approve=True)
        self.seed_task()
        with self.assertRaises(ValueError):
            self.sdd.approve('tarea', 'spec', 'Agente', 'texto plano')

    def test_allow_test_command(self):
        self.write_config(agent_may_approve=True)
        self.seed_task()
        nid = self.make_note('permito runner', 'tarea', 'allow-test')
        with contextlib.redirect_stdout(io.StringIO()):
            self.sdd.allow_test_command(['custom-runner', 'test'], '@note:' + nid)
        mem = self.sdd.load(self.sdd.MEMORY)
        self.assertIn(['custom-runner', 'test'], mem['project']['allowed_test_commands'])

    def test_allow_test_rejects_empty(self):
        self.write_config(agent_may_approve=True)
        with contextlib.redirect_stdout(io.StringIO()):
            self.sdd.ensure_init()
        with self.assertRaises(ValueError):
            self.sdd.allow_test_command(['  '], '@note:n1')

    def _hook_gated(self, agent, subcmd, may_approve=True, tool='Bash'):
        cfg = self.root / '.microharness' / 'config.json'
        cfg.write_text(json.dumps({'agent_may_approve': may_approve}), encoding='utf-8')
        if subcmd == 'approve':
            cmd = 'python3 .microharness/sdd.py approve x spec --by P --evidence @note:n1'
        elif subcmd == 'seal':
            cmd = 'python3 .microharness/sdd.py seal x --by P --evidence @note:n1'
        elif subcmd == 'allow-test-command':
            cmd = 'python3 .microharness/sdd.py allow-test-command custom --evidence @note:n1'
        else:
            raise AssertionError(subcmd)
        event = {
            'tool_name': tool, 'cwd': str(self.root),
            'tool_input': {'command': cmd},
        }
        if agent is not None:
            event['agent_type'] = agent
        return self.hook.run(event)

    def test_hook_allows_with_note_when_on(self):
        reason = self._hook_gated('lider', 'approve', may_approve=True)
        self.assertIsNone(reason)

    def test_hook_lider_allowed_seal_and_allow_test(self):
        self.assertIsNone(self._hook_gated('lider', 'seal'))
        self.assertIsNone(self._hook_gated('lider', 'allow-test-command'))

    def test_hook_denies_autor_and_implementador_gated(self):
        for agent in ('autor', 'implementador'):
            for sub in ('approve', 'seal', 'allow-test-command'):
                with self.subTest(agent=agent, sub=sub):
                    reason = self._hook_gated(agent, sub)
                    self.assertIsNotNone(reason)
                    self.assertIn('Solo el líder', reason)

    def test_hook_denies_absent_or_unknown_role(self):
        for agent in (None, '', 'desconocido'):
            with self.subTest(agent=agent):
                reason = self._hook_gated(agent, 'approve')
                self.assertIsNotNone(reason)

    def test_hook_denies_without_note_when_on(self):
        cfg = self.root / '.microharness' / 'config.json'
        cfg.write_text(json.dumps({'agent_may_approve': True}), encoding='utf-8')
        cmd = 'python3 .microharness/sdd.py approve x spec --by P --evidence ok'
        reason = self.hook.run({
            'agent_type': 'lider', 'tool_name': 'Bash', 'cwd': str(self.root),
            'tool_input': {'command': cmd},
        })
        self.assertIsNotNone(reason)

    def test_hook_denies_when_off(self):
        reason = self._hook_gated('lider', 'approve', may_approve=False)
        self.assertIsNotNone(reason)
        # Modo estricto: mensaje de TTY/humano, no el de solo-líder.
        self.assertNotIn('Solo el líder', reason or '')

    def test_note_prints_id(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.sdd.ensure_init()
        self.seed_task()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.sdd.note('apruebo la spec', None, None, 'cita', for_task='tarea', for_phase='spec')
        self.assertIn('Nota registrada: n1', buf.getvalue())


if __name__ == '__main__':
    unittest.main()
