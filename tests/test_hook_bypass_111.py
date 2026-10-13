"""Regresión de bypass del hook (MicroSDD 1.1.1)."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
HOOK_PATH = REPO / '.claude' / 'hooks' / 'pretool.py'
SDD = '.microharness/sdd.py'
RESTRICTED = ('lider', 'autor', 'implementador')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def shell_event(agent, command, tool='Bash'):
    return {'agent_type': agent, 'tool_name': tool, 'tool_input': {'command': command}}


class HookBypass111Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hook = load('micro_hook_bypass_111', HOOK_PATH)

    def assert_denied(self, command):
        for agent in RESTRICTED:
            with self.subTest(agent=agent, command=command):
                self.assertIsNotNone(self.hook.run(shell_event(agent, command)))

    def assert_allowed(self, command):
        for agent in RESTRICTED:
            with self.subTest(agent=agent, command=command):
                self.assertIsNone(self.hook.run(shell_event(agent, command)))

    def test_deny_check_and_approve(self):
        cmd = ('sh .microharness/python.sh ' + SDD + ' check x && '
               'python3 ' + SDD + ' approve x spec --by P --evidence ok')
        self.assert_denied(cmd)

    def test_deny_check_semicolon_seal(self):
        cmd = ('sh .microharness/python.sh ' + SDD + ' check x; '
               'python3 ' + SDD + ' seal x --by P')
        self.assert_denied(cmd)

    def test_deny_check_or_approve(self):
        cmd = ('sh .microharness/python.sh ' + SDD + ' check x || '
               'python3 ' + SDD + ' approve x spec --by P --evidence ok')
        self.assert_denied(cmd)

    def test_deny_approve_rare_launchers(self):
        for cmd in (
            'python3 ./' + SDD + ' approve x spec --by P --evidence ok',
            'python3.12 ' + SDD + ' approve x spec --by P --evidence ok',
            SDD + ' seal x --by P',
        ):
            self.assert_denied(cmd)

    def test_allow_cat_and_jq_settings(self):
        self.assert_allowed('cat .claude/settings.json')
        self.assert_allowed('jq . .claude/settings.json')
        self.assert_allowed('cat .claude/settings.local.json')

    def test_allow_git_commit_mentioning_sdd(self):
        self.assert_allowed("git commit -m 'chore: toca sdd.py y memory.json'")
        self.assert_allowed("git commit -m 'fix(hook): menciona sdd.py'")

    def test_allow_write_plans_md_deny_other_claude(self):
        # H3 (1.1.2): solo el líder escribe *.md en la raíz de ~/.claude/plans.
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / 'home'
            plans = home / '.claude' / 'plans'
            plans.mkdir(parents=True)
            (plans / 'foo.md').write_text('x', encoding='utf-8')
            (home / '.claude' / 'other.md').write_text('y', encoding='utf-8')
            cwd = Path(td) / 'proj'
            cwd.mkdir()
            with mock.patch.object(self.hook.Path, 'home', return_value=home):
                for agent in RESTRICTED:
                    result = self.hook.run({
                        'agent_type': agent, 'tool_name': 'Write', 'cwd': str(cwd),
                        'tool_input': {'file_path': str(plans / 'foo.md')},
                    })
                    deny = self.hook.run({
                        'agent_type': agent, 'tool_name': 'Write', 'cwd': str(cwd),
                        'tool_input': {'file_path': str(home / '.claude' / 'other.md')},
                    })
                    with self.subTest(agent=agent):
                        if agent == 'lider':
                            self.assertIsNone(result)
                        else:
                            self.assertIsNotNone(result)
                        self.assertIsNotNone(deny)



if __name__ == '__main__':
    unittest.main()
