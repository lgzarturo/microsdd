"""Regresión Windows, mensajes OS-aware y worktree sync (MicroSDD 1.1.3)."""
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
HOOK_PATH = REPO / '.claude' / 'hooks' / 'pretool.py'
SDD_REL = '.microharness/sdd.py'


def load_hook():
    spec = importlib.util.spec_from_file_location('pretool_windows_1113', HOOK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_worktree():
    spec = importlib.util.spec_from_file_location(
        'worktree_1113', REPO / 'src' / 'microsdd' / 'worktree.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WindowsHookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hook = load_hook()

    def shell_deny(self, command: str):
        return self.hook.run({'agent_type': 'lider', 'tool_name': 'PowerShell',
                              'tool_input': {'command': command}})

    def test_windows_launchers_deny_approve(self):
        args = 'approve x spec --by P --evidence ok'
        launchers = (
            f'.microharness/python.ps1 {SDD_REL}',
            f'pwsh -File .microharness/python.ps1 {SDD_REL}',
            f'powershell -File .microharness/python.ps1 {SDD_REL}',
            f'cmd /c .microharness/python.cmd {SDD_REL}',
            f'python.exe {SDD_REL}',
            f'& python {SDD_REL}',
            f'py -3 {SDD_REL}',
        )
        for launcher in launchers:
            with self.subTest(launcher=launcher):
                self.assertIsNotNone(self.shell_deny(f'{launcher} {args}'))

    def test_windows_launchers_allow_check(self):
        cmd = f'.microharness/python.ps1 {SDD_REL} check x'
        self.assertIsNone(self.shell_deny(cmd))

    def test_call_operator_allows_check_denies_approve(self):
        self.assertIsNone(self.shell_deny(f'& python {SDD_REL} check x'))
        self.assertIsNotNone(self.shell_deny(f'& python {SDD_REL} approve x spec --by P --evidence ok'))

    @mock.patch('os.name', 'nt')
    def test_msg_approve_mentions_windows_launcher(self):
        self.assertIn('python.ps1', self.hook.msg_approve())
        self.assertNotIn('sh .microharness/python.sh', self.hook.msg_approve())

    @mock.patch('os.name', 'posix')
    def test_msg_approve_unix_no_powershell_hint(self):
        text = self.hook.msg_approve()
        self.assertNotIn('python.ps1', text)


class WorktreeSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worktree = load_worktree()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self._git_repo(self.base / 'principal')
        self._seed_harness(self.source)
        principal_mem = {'schema_version': 1, 'project': {'observations': [], 'decisions': []},
                         'tasks': {'principal-only': {'mark': True}}}
        (self.source / '.microharness' / 'memory.json').write_text(
            json.dumps(principal_mem, indent=2) + '\n', encoding='utf-8')
        self.wt = (self.base / 'wt').resolve()
        subprocess.run(['git', '-C', str(self.source), 'worktree', 'add', '-b', 'wt-1113', str(self.wt)],
                       check=True, capture_output=True)

    def _git_repo(self, path: Path) -> Path:
        path.mkdir(parents=True, exist_ok=True)
        subprocess.run(['git', 'init', '-q', str(path)], check=True)
        subprocess.run(['git', '-C', str(path), 'config', 'user.email', 't@test'], check=True)
        subprocess.run(['git', '-C', str(path), 'config', 'user.name', 't'], check=True)
        subprocess.run(['git', '-C', str(path), 'commit', '--allow-empty', '-m', 'init'], check=True,
                       capture_output=True)
        return path.resolve()

    def _seed_harness(self, root: Path) -> None:
        for rel in self.worktree.WORKTREE_SYNC_FILES:
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f'# {rel}\n', encoding='utf-8')

    def test_sync_scaffolds_memory_without_touching_principal(self):
        before = (self.source / '.microharness' / 'memory.json').read_bytes()
        code = self.worktree.worktree_sync(self.source, self.wt, with_memory=False)
        self.assertEqual(code, 0)
        self.assertEqual((self.source / '.microharness' / 'memory.json').read_bytes(), before)
        wt_mem = json.loads((self.wt / '.microharness' / 'memory.json').read_text(encoding='utf-8'))
        self.assertEqual(wt_mem['tasks'], {})

    def test_sync_preserves_existing_worktree_memory(self):
        existing = {'schema_version': 1, 'project': {'observations': [], 'decisions': []},
                    'tasks': {'local': {'x': 1}}}
        (self.wt / '.microharness').mkdir(parents=True, exist_ok=True)
        (self.wt / '.microharness' / 'memory.json').write_text(json.dumps(existing) + '\n', encoding='utf-8')
        code = self.worktree.worktree_sync(self.source, self.wt, with_memory=False)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads((self.wt / '.microharness' / 'memory.json').read_text(encoding='utf-8')),
                         existing)

    def test_with_memory_copies_explicitly(self):
        code = self.worktree.worktree_sync(self.source, self.wt, with_memory=True)
        self.assertEqual(code, 0)
        self.assertEqual(
            json.loads((self.wt / '.microharness' / 'memory.json').read_text(encoding='utf-8'))['tasks'],
            {'principal-only': {'mark': True}})


if __name__ == '__main__':
    unittest.main()
