"""Pruebas ODD (reintentos, Write, progress) y RDD (recibo, kill switch) — MicroSDD 1.3.0."""
from __future__ import annotations

import contextlib
import hashlib
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
    def __init__(self, tty=True):
        self.tty = tty

    def isatty(self):
        return self.tty


class OddRddBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hook = load('hook_odd_rdd', HOOK_PATH)
        cls.sdd = load('sdd_odd_rdd', SCRIPT)

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
        self._stdin_cm = mock.patch.object(sys, 'stdin', FakeStdin(True))
        self._stdin_cm.start()
        self.addCleanup(self._stdin_cm.stop)
        subprocess.run(['git', 'init'], cwd=self.root, check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 't@example.com'], cwd=self.root, check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 't'], cwd=self.root, check=True, capture_output=True)

    def _restore(self):
        self.sdd.ROOT, self.sdd.MEMORY = self.old_root, self.old_memory

    def write_config(self, **kwargs):
        path = self.root / '.microharness' / 'config.json'
        path.write_text(json.dumps(kwargs), encoding='utf-8')

    def git_add_commit(self, message='init'):
        subprocess.run(['git', 'add', '-A'], cwd=self.root, check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', message], cwd=self.root, check=True, capture_output=True)

    def seed_task(self, slug='tarea', paths=None):
        with contextlib.redirect_stdout(io.StringIO()):
            self.sdd.new(slug)
        folder = self.root / 'spec' / slug
        data = self.sdd.load(folder / 'spec.json')
        data['title'] = 'T'
        data['scope']['allowed_paths'] = paths or ['src/**']
        data['testing']['protected_tests'] = ['tests/t.py']
        data['testing']['commands'] = [[sys.executable, '-m', 'unittest', 'discover', '-s', 'pruebas']]
        data['method'] = {'primary': 'SDD', 'optional': ['ODD', 'RDD'],
                          'notes': 'ODD reintentos; RDD recibo y kill switch'}
        self.sdd.dump(folder / 'spec.json', data)
        (folder / 'requerimientos.md').write_text(
            '# QUÉ\nWHEN x, THE y SHALL z.\nAC-01: ok.\n## Fuera de alcance\nNada.\n',
            encoding='utf-8')
        (folder / 'plan.md').write_text('# CÓMO\nHacer.\n', encoding='utf-8')
        (folder / 'tareas.md').write_text('# PASOS\n- [ ] T01 (AC-01): hacer.\n', encoding='utf-8')
        (self.root / 'src').mkdir(exist_ok=True)
        # Contenido con varias líneas para que un Edit acotado no dispare odd_rewrite_percent.
        (self.root / 'src' / 'a.py').write_text('a = 1\n# keep\n# more\n# lines\n# here\n', encoding='utf-8')
        (self.root / 'src' / 'b.py').write_text('b = 1\n# keep\n# more\n# lines\n# here\n', encoding='utf-8')
        (self.root / 'tests').mkdir(exist_ok=True)
        (self.root / 'tests' / 't.py').write_text('x = 1\n', encoding='utf-8')
        self.git_add_commit('seed')
        return folder

    def approve_spec(self, slug='tarea'):
        with contextlib.redirect_stdout(io.StringIO()):
            self.sdd.approve(slug, 'spec', 'Humano', 'apruebo')

    def impl_edit(self, rel, tool='Edit', **extra):
        path = self.root / rel
        inputs = {'file_path': str(path)}
        inputs.update(extra)
        return self.hook.run({
            'agent_type': 'implementador',
            'tool_name': tool,
            'cwd': str(self.root),
            'tool_input': inputs,
        })


class OddRetriesTests(OddRddBase):
    def test_default_odd_max_retries_is_3(self):
        self.assertEqual(self.sdd.config()['odd_max_retries'], 3)

    def test_config_odd_max_retries(self):
        self.write_config(odd_max_retries=2)
        self.assertEqual(self.sdd.config()['odd_max_retries'], 2)

    def test_record_retries_until_limit(self):
        self.write_config(odd_max_retries=2)
        self.seed_task()
        self.approve_spec()
        with contextlib.redirect_stdout(io.StringIO()):
            self.sdd.note('fallo 1', None, None, 'Traceback: boom', for_task='tarea', for_phase='odd-retry')
        mem = self.sdd.load(self.sdd.MEMORY)
        self.assertEqual(mem['tasks']['tarea']['odd_retries'], 1)
        events = [e['event'] for e in mem['tasks']['tarea']['events']]
        self.assertIn('reintento_odd', events)
        with self.assertRaises(ValueError) as ctx:
            with contextlib.redirect_stdout(io.StringIO()):
                self.sdd.note('fallo 2', None, None, 'Traceback: boom2', for_task='tarea', for_phase='odd-retry')
        self.assertIn('Límite de reintentos ODD agotado', str(ctx.exception))
        mem = self.sdd.load(self.sdd.MEMORY)
        self.assertEqual(mem['tasks']['tarea']['odd_retries'], 2)
        events = [e['event'] for e in mem['tasks']['tarea']['events']]
        self.assertIn('reintentos_agotados', events)

    def test_approve_resets_odd_retries(self):
        self.write_config(odd_max_retries=5)
        self.seed_task()
        self.approve_spec()
        with contextlib.redirect_stdout(io.StringIO()):
            self.sdd.note('fallo', None, None, 'stack', for_task='tarea', for_phase='odd-retry')
        self.assertEqual(self.sdd.load(self.sdd.MEMORY)['tasks']['tarea']['odd_retries'], 1)
        # Cambiar fingerprint exige rellenar docs; re-approve tras reset manual de state.
        folder = self.root / 'spec' / 'tarea'
        data = self.sdd.load(folder / 'spec.json')
        data['state'] = 'pendiente'
        self.sdd.dump(folder / 'spec.json', data)
        mem = self.sdd.load(self.sdd.MEMORY)
        mem['tasks']['tarea']['approvals']['spec'] = None
        self.sdd.dump(self.sdd.MEMORY, mem)
        self.approve_spec()
        self.assertEqual(self.sdd.load(self.sdd.MEMORY)['tasks']['tarea']['odd_retries'], 0)


class OddWriteBlockTests(OddRddBase):
    def test_write_existing_blocked_for_implementador(self):
        self.seed_task()
        self.approve_spec()
        reason = self.impl_edit('src/a.py', tool='Write', content='a = 2\n')
        self.assertIsNotNone(reason)
        self.assertIn('Reescritura completa bloqueada', reason)
        self.assertIn('Edit', reason)

    def test_write_new_file_allowed(self):
        self.seed_task()
        self.approve_spec()
        reason = self.impl_edit('src/nuevo.py', tool='Write', content='n = 1\n')
        self.assertIsNone(reason)

    def test_edit_existing_allowed(self):
        self.write_config(odd_rewrite_percent=80, rdd_max_lines=10000)
        self.seed_task()
        self.approve_spec()
        reason = self.impl_edit('src/a.py', tool='Edit', old_string='a = 1', new_string='a = 2')
        self.assertIsNone(reason)


class ProgressDiscoveriesTests(OddRddBase):
    def test_init_schema_has_empty_progress(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.sdd.ensure_init()
        mem = self.sdd.load(self.sdd.MEMORY)
        self.assertEqual(mem['project']['progress'], [])
        self.assertEqual(mem['project']['discoveries'], [])

    def test_note_progress_and_discovery(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.sdd.ensure_init()
            self.sdd.note(None, None, None, 'ev-p', progress='paso 1 listo')
            self.sdd.note(None, None, None, 'ev-d', discovery='hallazgo X')
        mem = self.sdd.load(self.sdd.MEMORY)
        self.assertEqual(mem['project']['progress'][0]['text'], 'paso 1 listo')
        self.assertEqual(mem['project']['progress'][0]['evidence'], 'ev-p')
        self.assertEqual(mem['project']['discoveries'][0]['text'], 'hallazgo X')
        self.assertEqual(mem['project']['discoveries'][0]['evidence'], 'ev-d')

    def test_note_progress_exclusive(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.sdd.ensure_init()
        with self.assertRaises(ValueError):
            self.sdd.note('fact', None, None, 'e', progress='p')


class RddReceiptTests(OddRddBase):
    def test_approve_creates_receipt_with_digest(self):
        self.seed_task()
        self.approve_spec()
        mem = self.sdd.load(self.sdd.MEMORY)
        receipt = mem['tasks']['tarea']['receipt']
        self.assertIsInstance(receipt, dict)
        self.assertEqual(receipt['allowed_paths'], ['src/**'])
        self.assertIn('src/a.py', receipt['files'])
        self.assertIn('src/b.py', receipt['files'])
        expected = hashlib.sha256(
            (self.root / 'src' / 'a.py').read_bytes().replace(b'\r\n', b'\n')).hexdigest()
        self.assertEqual(receipt['files']['src/a.py'], expected)
        self.assertTrue(isinstance(receipt['digest'], str) and len(receipt['digest']) == 64)

    def test_hook_rejects_outside_receipt(self):
        self.seed_task()
        self.approve_spec()
        # Ampliar spec live no debe ampliar el recibo.
        folder = self.root / 'spec' / 'tarea'
        data = self.sdd.load(folder / 'spec.json')
        data['scope']['allowed_paths'] = ['src/**', 'extra/**']
        self.sdd.dump(folder / 'spec.json', data)
        (self.root / 'extra').mkdir()
        reason = self.impl_edit('extra/x.py', tool='Write', content='x=1\n')
        self.assertIsNotNone(reason)
        self.assertIn('Fuera del recibo RDD', reason)


class RddKillSwitchTests(OddRddBase):
    def test_kill_switch_lines(self):
        self.write_config(rdd_max_lines=3, odd_rewrite_percent=100)
        self.seed_task()
        self.approve_spec()
        reason = self.impl_edit(
            'src/a.py', tool='Edit', old_string='a = 1',
            new_string='a = 1\n' + 'x\n' * 5)
        self.assertIsNotNone(reason)
        self.assertIn('Kill switch RDD', reason)
        self.assertIn('rdd_max_lines', reason)

    def test_kill_switch_files(self):
        self.write_config(rdd_max_files=1, odd_rewrite_percent=100, rdd_max_lines=10000)
        self.seed_task()
        self.approve_spec()
        # Primer archivo OK (aún coincide con el recibo → suma 1).
        self.assertIsNone(self.impl_edit('src/a.py', tool='Edit', old_string='a = 1', new_string='a = 2'))
        (self.root / 'src' / 'a.py').write_text('a = 2\n# keep\n# more\n# lines\n# here\n', encoding='utf-8')
        # Segundo archivo distinto del recibo → kill.
        reason = self.impl_edit('src/b.py', tool='Edit', old_string='b = 1', new_string='b = 2')
        self.assertIsNotNone(reason)
        self.assertIn('Kill switch RDD', reason)
        self.assertIn('rdd_max_files', reason)

    def test_defaults_documented_in_config(self):
        cfg = self.sdd.config()
        self.assertEqual(cfg['rdd_max_files'], 20)
        self.assertEqual(cfg['rdd_max_lines'], 500)
        self.assertEqual(cfg['odd_max_retries'], 3)
        self.assertEqual(cfg['odd_rewrite_percent'], 80)

    def test_kill_switch_lines_accumulates_across_calls(self):
        self.write_config(rdd_max_lines=5, odd_rewrite_percent=100)
        self.seed_task()
        self.approve_spec()
        body = 'line0\nline1\nline2\nline3\nline4\nline5\n'
        (self.root / 'src' / 'a.py').write_text(body, encoding='utf-8')
        # Tres edits de ~2 líneas: el tercero debe superar el acumulado.
        self.assertIsNone(self.impl_edit(
            'src/a.py', tool='Edit', old_string='line0', new_string='line0\nx'))
        self.assertIsNone(self.impl_edit(
            'src/a.py', tool='Edit', old_string='line1', new_string='line1\ny'))
        reason = self.impl_edit(
            'src/a.py', tool='Edit', old_string='line2', new_string='line2\nz')
        self.assertIsNotNone(reason)
        self.assertIn('Kill switch RDD', reason)
        self.assertIn('acumulado', reason)
        runtime = self.root / '.microharness' / 'rdd_runtime.json'
        self.assertTrue(runtime.is_file())
        data = json.loads(runtime.read_text(encoding='utf-8'))
        self.assertIn('tarea', data['tasks'])


class OddRewriteEditTests(OddRddBase):
    def test_edit_near_full_rewrite_blocked(self):
        self.write_config(odd_rewrite_percent=80, rdd_max_lines=10000)
        self.seed_task()
        self.approve_spec()
        content = 'alpha\nbeta\ngamma\ndelta\nepsilon\n'
        path = self.root / 'src' / 'a.py'
        path.write_text(content, encoding='utf-8')
        reason = self.impl_edit(
            'src/a.py', tool='Edit', old_string=content, new_string='reescrito\npor\ncompleto\n')
        self.assertIsNotNone(reason)
        self.assertIn('Reescritura completa bloqueada', reason)

    def test_multiedit_near_full_rewrite_blocked(self):
        self.write_config(odd_rewrite_percent=80, rdd_max_lines=10000)
        self.seed_task()
        self.approve_spec()
        content = 'one\ntwo\nthree\nfour\nfive\n'
        path = self.root / 'src' / 'a.py'
        path.write_text(content, encoding='utf-8')
        reason = self.impl_edit(
            'src/a.py', tool='MultiEdit',
            edits=[
                {'old_string': 'one\ntwo\nthree\n', 'new_string': 'A\nB\nC\n'},
                {'old_string': 'four\nfive\n', 'new_string': 'D\nE\n'},
            ])
        self.assertIsNotNone(reason)
        self.assertIn('Reescritura completa bloqueada', reason)

    def test_small_edit_allowed(self):
        self.write_config(odd_rewrite_percent=80, rdd_max_lines=10000)
        self.seed_task()
        self.approve_spec()
        path = self.root / 'src' / 'a.py'
        path.write_text('one\ntwo\nthree\nfour\nfive\n', encoding='utf-8')
        reason = self.impl_edit('src/a.py', tool='Edit', old_string='two', new_string='TWO')
        self.assertIsNone(reason)


class RddPathCaseAndSymlinkTests(OddRddBase):
    def test_path_in_patterns_casefold(self):
        self.assertTrue(self.hook.path_in_patterns('Src/A.py', ['src/**'], casefold=True))
        self.assertFalse(self.hook.path_in_patterns('Src/A.py', ['src/**'], casefold=False))

    def test_receipt_allows_case_variant_when_windows(self):
        self.write_config(odd_rewrite_percent=100, rdd_max_lines=10000)
        self.seed_task()
        self.approve_spec()
        with mock.patch.object(self.hook, 'paths_casefold', return_value=True), \
                mock.patch.object(self.hook, 'resolve_edit_rel', return_value=('Src/A.py', None)):
            reason = self.impl_edit('src/a.py', tool='Edit', old_string='a = 1', new_string='a = 2')
        self.assertIsNone(reason)

    def test_receipt_rejects_outside_case_variant_when_windows(self):
        self.write_config(odd_rewrite_percent=100, rdd_max_lines=10000)
        self.seed_task()
        self.approve_spec()
        with mock.patch.object(self.hook, 'paths_casefold', return_value=True), \
                mock.patch.object(self.hook, 'resolve_edit_rel', return_value=('Extra/X.py', None)):
            reason = self.impl_edit('src/a.py', tool='Edit', old_string='a = 1', new_string='a = 2')
        self.assertIsNotNone(reason)
        self.assertIn('Fuera del recibo RDD', reason)

    def test_symlink_real_destination_outside_receipt(self):
        self.write_config(odd_rewrite_percent=100, rdd_max_lines=10000)
        self.seed_task()
        self.approve_spec()
        other = self.root / 'other'
        other.mkdir()
        (other / 'x.py').write_text('x = 1\n', encoding='utf-8')
        link = self.root / 'src' / 'link.py'
        try:
            link.symlink_to(other / 'x.py')
        except OSError:
            with mock.patch.object(self.hook, 'resolve_edit_rel', return_value=('other/x.py', None)):
                reason = self.impl_edit('src/link.py', tool='Edit', old_string='x = 1', new_string='x = 2')
            self.assertIsNotNone(reason)
            self.assertIn('Fuera del recibo RDD', reason)
            return
        reason = self.impl_edit('src/link.py', tool='Edit', old_string='x = 1', new_string='x = 2')
        self.assertIsNotNone(reason)
        self.assertTrue(
            'Fuera del recibo RDD' in reason or 'Symlinks' in reason or 'fuera del proyecto' in reason,
            reason)


class CompatibilityTests(OddRddBase):
    def test_agent_may_approve_still_works(self):
        self.write_config(agent_may_approve=True, odd_max_retries=3)
        self.seed_task()
        with contextlib.redirect_stdout(io.StringIO()):
            self.sdd.note('apruebo', None, None, 'cita', for_task='tarea', for_phase='spec')
        mem = self.sdd.load(self.sdd.MEMORY)
        nid = mem['project']['observations'][-1]['id']
        with mock.patch.object(sys, 'stdin', FakeStdin(False)):
            with contextlib.redirect_stdout(io.StringIO()):
                self.sdd.approve('tarea', 'spec', 'Agente', '@note:' + nid)
        mem = self.sdd.load(self.sdd.MEMORY)
        self.assertIsNotNone(mem['tasks']['tarea']['approvals']['spec'])
        self.assertIsNotNone(mem['tasks']['tarea']['receipt'])


if __name__ == '__main__':
    unittest.main()
