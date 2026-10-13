"""Regresión de seguridad H1–H5 (MicroSDD 1.1.2)."""
import contextlib
import importlib.util
import io
import json
import os
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


class Security1112Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hook = load('micro_hook_security_1112', HOOK_PATH)
        cls.sdd = load('micro_sdd_security_1112', SCRIPT)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / '.microharness').mkdir()
        self.old_root, self.old_memory = self.sdd.ROOT, self.sdd.MEMORY
        self.sdd.ROOT = self.root
        self.sdd.MEMORY = self.root / '.microharness' / 'memory.json'
        self.addCleanup(self._restore)

    def _restore(self):
        self.sdd.ROOT, self.sdd.MEMORY = self.old_root, self.old_memory

    def _seed_task(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.sdd.new('tarea')
        folder = self.root / 'spec' / 'tarea'
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
        return folder

    def test_h1_approve_seal_denied_under_claudecode(self):
        self._seed_task()
        before = self.sdd.MEMORY.read_bytes()
        with mock.patch.dict(os.environ, {'CLAUDECODE': '1'}), \
                mock.patch.object(sys, 'stdin', FakeStdin(True)), \
                self.assertRaises(ValueError):
            self.sdd.approve('tarea', 'spec', 'P', 'ok')
        self.assertEqual(self.sdd.MEMORY.read_bytes(), before)
        with mock.patch.dict(os.environ, {'CLAUDECODE': '1'}), \
                mock.patch.object(sys, 'stdin', FakeStdin(True)), \
                self.assertRaises(ValueError):
            self.sdd.seal('tarea', 'P')
        self.assertEqual(self.sdd.MEMORY.read_bytes(), before)

    def test_h1_approve_seal_denied_without_tty(self):
        self._seed_task()
        before = self.sdd.MEMORY.read_bytes()
        env = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(sys, 'stdin', FakeStdin(False)), \
                self.assertRaises(ValueError):
            self.sdd.approve('tarea', 'spec', 'P', 'ok')
        self.assertEqual(self.sdd.MEMORY.read_bytes(), before)

    def test_h1_approve_works_with_tty(self):
        self._seed_task()
        env = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(sys, 'stdin', FakeStdin(True)), \
                contextlib.redirect_stdout(io.StringIO()):
            self.sdd.approve('tarea', 'spec', 'P', 'evidencia explícita')
        mem = self.sdd.load(self.sdd.MEMORY)
        self.assertIsNotNone(mem['tasks']['tarea']['approvals']['spec'])

    def test_h1b_lider_write_docs_py_denied(self):
        reason = self.hook.run({
            'agent_type': 'lider', 'tool_name': 'Write', 'cwd': str(self.root),
            'tool_input': {'file_path': 'docs/evil.py', 'content': 'print(1)\n'},
        })
        self.assertIsNotNone(reason)
        self.assertIn('ejecutables', reason)

    def test_h1b_lider_write_docs_shebang_denied(self):
        reason = self.hook.run({
            'agent_type': 'lider', 'tool_name': 'Write', 'cwd': str(self.root),
            'tool_input': {'file_path': 'docs/x.md', 'content': '#!/bin/sh\necho hi\n'},
        })
        self.assertIsNotNone(reason)
        self.assertIn('ejecutables', reason)

    def test_h1c_python_docs_py_denied(self):
        for cmd in ('python docs/evil.py', 'python3 docs/x.py', 'py -3 spec/t/hack.py'):
            with self.subTest(cmd=cmd):
                reason = self.hook.run({
                    'agent_type': 'lider', 'tool_name': 'Bash',
                    'tool_input': {'command': cmd},
                })
                self.assertIsNotNone(reason)

    def test_h3_plans_only_lider_root_md(self):
        home = self.root / 'home'
        plans = home / '.claude' / 'plans'
        plans.mkdir(parents=True)
        (plans / 'sub').mkdir()
        cwd = self.root / 'proj'
        cwd.mkdir()
        with mock.patch.object(self.hook.Path, 'home', return_value=home):
            allow = self.hook.run({
                'agent_type': 'lider', 'tool_name': 'Write', 'cwd': str(cwd),
                'tool_input': {'file_path': str(plans / 'a.md'), 'content': 'x'},
            })
            deny_sub = self.hook.run({
                'agent_type': 'lider', 'tool_name': 'Write', 'cwd': str(cwd),
                'tool_input': {'file_path': str(plans / 'sub' / 'a.md'), 'content': 'x'},
            })
            deny_autor = self.hook.run({
                'agent_type': 'autor', 'tool_name': 'Write', 'cwd': str(cwd),
                'tool_input': {'file_path': str(plans / 'a.md'), 'content': 'x'},
            })
        self.assertIsNone(allow)
        self.assertIsNotNone(deny_sub)
        self.assertIsNotNone(deny_autor)

    def test_h4_jq_inplace_denied(self):
        reason = self.hook.run({
            'agent_type': 'lider', 'tool_name': 'Bash',
            'tool_input': {'command': 'jq -i . .claude/settings.json'},
        })
        self.assertIsNotNone(reason)

    def test_h5_cat_settings_and_rm_denied(self):
        reason = self.hook.run({
            'agent_type': 'lider', 'tool_name': 'Bash',
            'tool_input': {'command': 'cat .claude/settings.json && rm -rf src'},
        })
        self.assertIsNotNone(reason)
        self.assertIn('encadenado', reason.lower())

    def test_settings_read_head_grep_tail_rg_allowed(self):
        for cmd in (
            'head .claude/settings.json',
            'grep agent .claude/settings.json',
            'tail .claude/settings.local.json',
            'rg effortLevel .claude/settings.json',
        ):
            with self.subTest(cmd=cmd):
                reason = self.hook.run({
                    'agent_type': 'lider', 'tool_name': 'Bash',
                    'tool_input': {'command': cmd},
                })
                self.assertIsNone(reason, cmd)


if __name__ == '__main__':
    unittest.main()
