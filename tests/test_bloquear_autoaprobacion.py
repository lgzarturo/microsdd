"""Pruebas del bloqueo de autoaprobación (spec bloquear-autoaprobacion)."""
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

RESTRICTED = ('lider', 'autor', 'implementador')
SHELLS = ('Bash', 'PowerShell')
EDIT_TOOLS = ('Write', 'Edit', 'MultiEdit', 'NotebookEdit')
SDD = '.microharness/sdd.py'
LAUNCHERS = (
    'sh .microharness/python.sh', 'python', 'python3', 'python.exe', 'py -3', 'uv run --no-project',
    '.microharness/python.ps1', 'cmd /c .microharness/python.cmd',
    'pwsh -File .microharness/python.ps1', 'powershell -File .microharness/python.ps1',
    '& python',
)
UV_VARIANTS = ("uv run --no-project --quiet --python '>=3.10'",
               'uv run --no-project --python ">=3.10"',
               'uv run --no-project --python 3.12')
APPROVE_ARGS = ('approve x spec --by P --evidence ok', 'approve x close --by P --evidence ok',
                'seal x --by P --evidence ok', 'allow-test-command custom --evidence ok')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def shell_event(agent, tool, command):
    return {'agent_type': agent, 'tool_name': tool, 'tool_input': {'command': command}}


def bypass_commands():
    commands = []
    for args in ('approve x spec --by P --evidence ok', 'seal x --by P --evidence ok'):
        commands += [
            f'python3 ./{SDD} {args}',
            f'python3 {REPO / SDD} {args}',
            f'python3.12 {SDD} {args}',
            f'{SDD} {args}',
            f'python3 -m microharness.sdd {args}',
            f'cd .microharness && python3 sdd.py {args}',
            f'F={SDD}; python3 $F {args}',
            f'python3 "$PWD/{SDD}" {args}',
            f'uv run {SDD} {args}',
            f'python3 .microharness\\sdd.py {args}',
            f'python3 .MicroHarness/sdd.py {args}',
            f'python3 .microharness/SDD.PY {args}',
            f'.microharness/python.ps1 {SDD} {args}',
            f'cmd /c .microharness/python.cmd {SDD} {args}',
        ]
    check = f'sh .microharness/python.sh {SDD} check x'
    commands += [f'{check} && rm -rf src', f'{check}; rm -rf src', f'{check};rm -rf src',
                 f'{check}#;rm -rf src', f'{check} #; rm -rf src',
                 f'{check} | tee salida', f'{check} || rm -rf src', f'{check} & rm -rf src',
                 f'{check}\nrm -rf src', f'{check}\rrm -rf src']
    note = f'sh .microharness/python.sh {SDD} note --fact F --evidence'
    commands += [f'{note} "$(rm -rf src)"', f'{note} "`rm -rf src`"']
    sdd_note = f'python3 {SDD} note --fact'
    commands += [f"{sdd_note} 'a’; Set-Content .microharness/memory.json x; echo ‘b' --evidence E"]
    commands += [f"{sdd_note} 'a{quote}; rm -rf src' --evidence E" for quote in '‘’‚‛']
    commands += [f'{sdd_note} "a{quote}; rm -rf src" --evidence E' for quote in '“”„']
    commands += [
        'echo {} > .microharness/memory.json',
        'echo {} >> .microharness/memory.json',
        'echo {} | tee .microharness/memory.json',
        'cp /tmp/m.json .microharness/memory.json',
        'mv /tmp/m.json .microharness/memory.json',
        'sed -i s/a/b/ .microharness/memory.json',
        'python3 -c "open(\'.microharness/memory.json\',\'w\')"',
        'cat .microharness/memory.json',
        'echo {} > .microharness/config.json',
        'sh .microharness/python.sh -c "print(1)"',
        'git checkout -- .microharness/memory.json',
        'git diff --output=.microharness/memory.json',
        'git diff --ext-diff -- .microharness/sdd.py',
        'cat .MicroHarness/otro',
        'cat Memory.JSON',
        'cat SDD.PY',
    ]
    return commands


class ShellPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hook = load('micro_hook_autoaprobacion', HOOK_PATH)

    def assert_denied(self, commands):
        for agent in RESTRICTED:
            for tool in SHELLS:
                for command in commands:
                    with self.subTest(agent=agent, tool=tool, command=command):
                        self.assertIsNotNone(self.hook.run(shell_event(agent, tool, command)))

    def assert_allowed(self, commands):
        for agent in RESTRICTED:
            for tool in SHELLS:
                for command in commands:
                    with self.subTest(agent=agent, tool=tool, command=command):
                        self.assertIsNone(self.hook.run(shell_event(agent, tool, command)))

    def test_ac01_bypass_variants_denied(self):
        self.assert_denied(bypass_commands())

    def test_ac02_approve_and_seal_denied_with_every_launcher(self):
        self.assert_denied([f'{launcher} {SDD} {args}'
                            for launcher in LAUNCHERS + UV_VARIANTS for args in APPROVE_ARGS])

    def test_ac03_allowed_subcommands_with_every_launcher(self):
        allowed = ('init', 'new fix-x', 'check fix-x', 'check fix-x --run', 'check fix-x --no-scope',
                   'review fix-x APROBADO --evidence "diff; pruebas > ok"',
                   'note --fact "F" --evidence "E"',
                   'note --decision "D" --by Programador --evidence "E"',
                   "commit-check 'fix(x): corrige y'", 'release propose', '--version', '--help')
        self.assert_allowed([f'{launcher} {SDD} {args}'
                             for launcher in LAUNCHERS + UV_VARIANTS for args in allowed])

    def test_ac04_legitimate_exceptions_allowed(self):
        self.assert_allowed([
            'sh .microharness/python.sh -m unittest discover -s tests -v',
            'sh .microharness/python.sh --version',
            '.microharness/python.ps1 -m unittest discover -s tests -v',
            'pwsh -File .microharness/python.ps1 -m unittest discover -s tests -v',
            'git add .microharness/memory.json spec/x/plan.md',
            'git diff -- .microharness/sdd.py',
            'git log --oneline -- .microharness/memory.json',
            'git show HEAD:.microharness/sdd.py',
            'git status',
            'python -m unittest discover -s tests -v',
            "git commit -m 'fix(hook)!: impide que los agentes aprueben, sellen o editen la memoria'",
            "git commit -m 'fix(hook): menciona sdd.py'",
        ])

    def test_ac04_unittest_exception_rejects_protected_arguments(self):
        self.assert_denied(['sh .microharness/python.sh -m unittest .microharness/sdd.py',
                            'sh .microharness/python.sh --version --help',
                            '.microharness/python.ps1 -m unittest .microharness/sdd.py'])

    def test_ac05_reviewer_cannot_approve_seal_review_or_note(self):
        launcher = f'sh .microharness/python.sh {SDD}'
        for args in ('approve x spec --by P --evidence ok', 'seal x --by P --evidence ok',
                     'review x APROBADO --evidence ok', 'note --fact F --evidence E'):
            for tool in SHELLS:
                with self.subTest(tool=tool, args=args):
                    self.assertIsNotNone(self.hook.run(shell_event('revisor', tool, f'{launcher} {args}')))


class EditPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hook = load('micro_hook_autoaprobacion_edit', HOOK_PATH)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = Path(self.tmp.name).resolve()

    def edit(self, agent, tool, path):
        key = 'notebook_path' if tool == 'NotebookEdit' else 'file_path'
        return self.hook.run({'agent_type': agent, 'tool_name': tool, 'cwd': str(self.cwd),
                              'tool_input': {key: str(path)}})

    def test_ac06_lider_and_autor_cannot_edit_microharness(self):
        paths = ('.microharness/memory.json', '.microharness/config.json', '.microharness/sdd.py',
                 '.microharness/python.sh', '.microharness/python.ps1', '.microharness/python.cmd',
                 self.cwd / 'docs' / '..' / '.microharness' / 'memory.json',
                 self.cwd / '.MicroHarness' / 'memory.json', self.cwd / '.microharness')
        for agent in ('lider', 'autor'):
            for tool in EDIT_TOOLS:
                for path in paths:
                    with self.subTest(agent=agent, tool=tool, path=str(path)):
                        self.assertIsNotNone(self.edit(agent, tool, path))

    def test_ac06_ac08_lider_edits_docs_and_spec_relative_to_event_cwd(self):
        self.assertNotEqual(Path.cwd().resolve(), self.cwd)
        for path in ('docs/AGENT.md', 'spec/x/plan.md'):
            with self.subTest(path=path):
                self.assertIsNone(self.edit('lider', 'Write', path))
        self.assertIsNotNone(self.edit('lider', 'Write', '.microharness/memory.json'))

    def test_ac09_reviewer_read_only_without_path(self):
        reason = self.hook.run({'agent_type': 'revisor', 'tool_name': 'Edit', 'tool_input': {}})
        self.assertIsNotNone(reason)
        self.assertIn('solo lectura', reason)

    def make_task(self, allowed, approved=True):
        (self.cwd / 'spec' / 't').mkdir(parents=True)
        (self.cwd / '.microharness').mkdir()
        spec = {'id': 't', 'state': 'proceso', 'scope': {'allowed_paths': allowed}}
        (self.cwd / 'spec' / 't' / 'spec.json').write_text(json.dumps(spec), encoding='utf-8')
        approval = {'by': 'P', 'evidence': 'ok'} if approved else None
        memory = {'tasks': {'t': {'approvals': {'spec': approval, 'close': None}, 'sealed_tests': {}}}}
        (self.cwd / '.microharness' / 'memory.json').write_text(json.dumps(memory), encoding='utf-8')

    def test_ac07_implementer_edits_only_harness_files_in_scope(self):
        self.make_task(['.microharness/sdd.py', '.microharness/python.sh',
                        '.microharness/python.ps1', '.microharness/python.cmd', 'src/**'])
        for tool in EDIT_TOOLS:
            for path in ('.microharness/sdd.py', self.cwd / '.microharness' / 'python.sh',
                         self.cwd / '.microharness' / 'python.ps1',
                         self.cwd / '.microharness' / 'python.cmd'):
                with self.subTest(tool=tool, permitido=str(path)):
                    self.assertIsNone(self.edit('implementador', tool, path))
            for path in ('.microharness/memory.json', '.microharness/config.json',
                         '.microharness/memory.lock', '.microharness/otro.py', '.MicroHarness/sdd.py'):
                with self.subTest(tool=tool, denegado=path):
                    self.assertIsNotNone(self.edit('implementador', tool, path))

    def test_ac07_implementer_denied_without_scope(self):
        self.make_task(['src/**'])
        for path in ('.microharness/sdd.py', '.microharness/python.sh',
                     '.microharness/python.ps1', '.microharness/python.cmd'):
            with self.subTest(path=path):
                self.assertIsNotNone(self.edit('implementador', 'Write', path))

    def test_ac07_implementer_denied_without_approval(self):
        self.make_task(['.microharness/sdd.py', '.microharness/python.sh',
                        '.microharness/python.ps1', '.microharness/python.cmd'], approved=False)
        for path in ('.microharness/sdd.py', '.microharness/python.sh'):
            with self.subTest(path=path):
                self.assertIsNotNone(self.edit('implementador', 'Write', path))


class FakeStdin:
    def __init__(self, tty):
        self.tty = tty

    def isatty(self):
        return self.tty


class MainTtyTests(unittest.TestCase):
    CASES = ((['approve', 'x', 'spec', '--by', 'P', '--evidence', 'ok'], 'approve', ('x', 'spec', 'P', 'ok')),
             (['seal', 'x', '--by', 'P', '--evidence', 'ok'], 'seal', ('x', 'P', 'ok')))

    def setUp(self):
        self.sdd = load('micro_sdd_autoaprobacion', SCRIPT)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        (root / '.microharness').mkdir()
        self.sdd.ROOT = root
        self.sdd.MEMORY = root / '.microharness' / 'memory.json'
        self.sdd.MEMORY.write_text('{"version": 1, "tasks": {}}\n', encoding='utf-8')
        self.before = self.sdd.MEMORY.read_bytes()

    def run_main(self, argv, env, stdin):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, env), mock.patch.object(sys, 'argv', ['sdd.py', *argv]), \
                mock.patch.object(sys, 'stdin', stdin), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            if 'CLAUDECODE' not in env:
                os.environ.pop('CLAUDECODE', None)
            try:
                code = self.sdd.main()
            except SystemExit as e:
                code = e.code
        return code, err.getvalue()

    def assert_rejected(self, env, stdin):
        for argv, name, _ in self.CASES:
            with self.subTest(argv=argv, env=env, stdin=stdin), mock.patch.object(self.sdd, name) as fn:
                code, err = self.run_main(argv, env, stdin)
                self.assertEqual(code, 1)
                self.assertIn('ERROR:', err)
                fn.assert_not_called()
                self.assertEqual(self.sdd.MEMORY.read_bytes(), self.before)

    def test_ac10_rejected_with_claudecode_defined(self):
        for value in ('1', ''):
            self.assert_rejected({'CLAUDECODE': value}, FakeStdin(True))

    def test_ac11_rejected_without_tty(self):
        self.assert_rejected({}, FakeStdin(False))
        self.assert_rejected({}, None)

    def test_ac12_allowed_with_tty_outside_claude_code(self):
        for argv, name, expected in self.CASES:
            with self.subTest(argv=argv), mock.patch.object(self.sdd, name) as fn:
                code, err = self.run_main(argv, {}, FakeStdin(True))
                self.assertEqual(code, 0, err)
                fn.assert_called_once_with(*expected)

    def test_ac12_note_and_check_unchanged_inside_claude_code(self):
        env, stdin = {'CLAUDECODE': '1'}, FakeStdin(False)
        with mock.patch.object(self.sdd, 'note') as fn:
            code, err = self.run_main(['note', '--fact', 'F', '--evidence', 'E'], env, stdin)
            self.assertEqual(code, 0, err)
            fn.assert_called_once_with('F', None, None, 'E', None, None, progress=None, discovery=None)
        with mock.patch.object(self.sdd, 'validate', return_value=[]) as fn:
            code, err = self.run_main(['check', 'x'], env, stdin)
            self.assertEqual(code, 0, err)
            fn.assert_called_once_with('x', run=False, scope=True)


if __name__ == '__main__':
    unittest.main()
