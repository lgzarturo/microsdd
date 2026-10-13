import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1]
SCRIPT = SOURCE / 'src' / 'microsdd' / 'installer.py'
spec = importlib.util.spec_from_file_location('microsdd_installer_fusion', SCRIPT)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
HOOK = SOURCE / '.claude' / 'hooks' / 'pretool.py'
hook_spec = importlib.util.spec_from_file_location('microsdd_pretool_fusion', HOOK)
pretool = importlib.util.module_from_spec(hook_spec)
hook_spec.loader.exec_module(pretool)

FAKE_UV = [sys.executable, '-c', 'pass']
PAYLOAD = json.loads((SOURCE / '.claude' / 'settings.json').read_text(encoding='utf-8'))
ENTRY = PAYLOAD['hooks']['PreToolUse'][0]
GRAPHIFY = {'permissions': {'allow': ['Bash(graphify:*)']},
            'hooks': {'PreToolUse': [{'matcher': 'Bash', 'hooks': [{'type': 'command', 'command': 'graphify-guard'}]}],
                      'PostToolUse': [{'matcher': 'Write', 'hooks': [{'type': 'command', 'command': 'graphify-index'}]}]}}


def snapshot(root: Path) -> dict[str, bytes]:
    result = {}
    for path in sorted(root.rglob('*')):
        rel = path.relative_to(root)
        if '.git' in rel.parts:
            continue
        result[rel.as_posix()] = path.read_bytes() if path.is_file() else b'<dir>'
    return result


class FakeStdin(io.StringIO):
    def __init__(self, tty: bool):
        super().__init__('')
        self.tty = tty

    def isatty(self):
        return self.tty


class FusionBase(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.home = self.base / 'home'
        self.home.mkdir()
        self.repo = self.base / 'repo'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        self.settings = self.repo / '.claude' / 'settings.json'

    def write_settings(self, data):
        self.settings.parent.mkdir(parents=True, exist_ok=True)
        self.settings.write_text(json.dumps(data), encoding='utf-8')

    def load(self):
        return json.loads(self.settings.read_text(encoding='utf-8'))

    def record(self):
        return json.loads((self.repo / '.microharness' / 'install.json').read_text(encoding='utf-8'))

    def backups(self):
        return sorted((self.repo / '.claude').glob('settings.json.bak.*'))

    def call(self, func, *args, **kwargs):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = func(*args, **kwargs)
        return code, out.getvalue()

    def install(self, **kwargs):
        return self.call(installer.install, SOURCE, self.repo, uv=FAKE_UV, home=self.home, **kwargs)

    def toggle(self, enable):
        return self.call(installer.toggle, SOURCE, self.repo, enable)

    def status(self):
        return self.call(installer.status, SOURCE, self.repo)

    def uninstall(self, force=False):
        return self.call(installer.uninstall, SOURCE, self.repo, force=force)

    def assert_merged(self, data):
        self.assertEqual(data['agent'], 'lider')
        self.assertEqual(data['model'], 'claude-opus-5-5')
        self.assertEqual(data['effortLevel'], 'medium')
        self.assertEqual(data['permissions'], GRAPHIFY['permissions'])
        self.assertEqual(data['hooks']['PostToolUse'], GRAPHIFY['hooks']['PostToolUse'])
        self.assertEqual(data['hooks']['PreToolUse'], [GRAPHIFY['hooks']['PreToolUse'][0], ENTRY])


class ToggleTests(FusionBase):
    # AC-06
    def test_off_restores_foreign_settings_and_is_idempotent(self):
        self.write_settings(GRAPHIFY)
        self.assertEqual(self.install()[0], 0)
        self.assertEqual(len(self.backups()), 1)
        code, output = self.toggle(False)
        self.assertEqual(code, 0, output)
        self.assertEqual(self.load(), GRAPHIFY)
        self.assertEqual(len(self.backups()), 2)
        self.assertIs(self.record()['settings']['enabled'], False)
        before = snapshot(self.repo)
        code, output = self.toggle(False)
        self.assertEqual(code, 0, output)
        self.assertEqual(snapshot(self.repo), before)

    def test_off_after_clean_install_leaves_empty_object(self):
        self.assertEqual(self.install()[0], 0)
        code, output = self.toggle(False)
        self.assertEqual(code, 0, output)
        self.assertEqual(self.load(), {})

    # AC-03
    def test_off_restores_previous_distinct_values(self):
        self.write_settings({'agent': 'otro', 'model': 'x'})
        self.assertEqual(self.install()[0], 0)
        self.assertEqual(self.load()['agent'], 'lider')
        self.assertEqual(self.load()['model'], 'claude-opus-5-5')
        self.assertEqual(self.toggle(False)[0], 0)
        self.assertEqual(self.load(), {'agent': 'otro', 'model': 'x'})

    # AC-07
    def test_on_after_off_reapplies_and_is_idempotent(self):
        self.write_settings(GRAPHIFY)
        self.assertEqual(self.install()[0], 0)
        self.assertEqual(self.toggle(False)[0], 0)
        code, output = self.toggle(True)
        self.assertEqual(code, 0, output)
        self.assert_merged(self.load())
        self.assertIs(self.record()['settings']['enabled'], True)
        before = snapshot(self.repo)
        code, output = self.toggle(True)
        self.assertEqual(code, 0, output)
        self.assertEqual(snapshot(self.repo), before)
        self.assertEqual(self.toggle(False)[0], 0)
        self.assertEqual(self.load(), GRAPHIFY)

    def test_on_and_off_without_record_fail_without_writing(self):
        self.write_settings(GRAPHIFY)
        before = snapshot(self.repo)
        for enable in (True, False):
            with self.subTest(enable=enable):
                code, output = self.toggle(enable)
                self.assertEqual(code, 1, output)
                self.assertIn('ERROR:', output)
                self.assertEqual(snapshot(self.repo), before)

    # AC-05 (on, off, uninstall)
    def test_invalid_settings_fail_without_writing(self):
        self.assertEqual(self.install()[0], 0)
        for raw in (b'{no json', b'[]', b'{"hooks": []}', b'{"hooks": {"PreToolUse": {}}}'):
            self.settings.write_bytes(raw)
            before = snapshot(self.repo)
            for name, func in (('on', lambda: self.toggle(True)), ('off', lambda: self.toggle(False)),
                               ('uninstall', self.uninstall)):
                with self.subTest(raw=raw, command=name):
                    code, output = func()
                    self.assertEqual(code, 1, output)
                    self.assertIn('.claude/settings.json', output)
                    self.assertEqual(snapshot(self.repo), before)


class StatusTests(FusionBase):
    def state(self):
        before = snapshot(self.repo)
        code, output = self.status()
        self.assertEqual(code, 0, output)
        self.assertEqual(snapshot(self.repo), before)
        return output.splitlines()[0]

    # AC-08
    def test_status_reports_real_state(self):
        self.assertEqual(self.state(), 'estado: inactivo')
        self.write_settings(GRAPHIFY)
        self.assertEqual(self.install()[0], 0)
        self.assertEqual(self.state(), 'estado: activo')
        data = self.load()
        data['hooks']['PreToolUse'].remove(ENTRY)
        self.write_settings(data)
        self.assertEqual(self.state(), 'estado: parcial')
        data['hooks']['PreToolUse'].append(ENTRY)
        del data['agent']
        self.write_settings(data)
        self.assertEqual(self.state(), 'estado: parcial')
        data['agent'] = 'lider'
        self.write_settings(data)
        self.assertEqual(self.toggle(False)[0], 0)
        self.assertEqual(self.state(), 'estado: inactivo')

    def test_status_works_inside_claude_code_without_tty(self):
        self.assertEqual(self.install()[0], 0)
        for stdin in (FakeStdin(False), None):
            with (self.subTest(stdin=stdin), mock.patch.dict(os.environ, {'CLAUDECODE': '1'}),
                  mock.patch.object(sys, 'stdin', stdin), mock.patch.object(installer, 'PAYLOAD', SOURCE)):
                before = snapshot(self.repo)
                code, output = self.call(installer.main, ['status', '--target', str(self.repo)])
                self.assertEqual(code, 0, output)
                self.assertIn('estado: activo', output)
                self.assertEqual(snapshot(self.repo), before)

    def test_status_with_invalid_json_fails(self):
        self.settings.parent.mkdir()
        self.settings.write_bytes(b'{no json')
        code, output = self.status()
        self.assertEqual(code, 1, output)
        self.assertIn('.claude/settings.json', output)


class HumanGateTests(FusionBase):
    # AC-09
    def test_on_off_uninstall_require_human_terminal(self):
        self.write_settings(GRAPHIFY)
        self.assertEqual(self.install()[0], 0)
        env = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}
        cases = {'claudecode-vacio': ({**env, 'CLAUDECODE': ''}, True),
                 'sin-tty': (env, False),
                 'stdin-none': (env, None)}
        for command in ('on', 'off', 'uninstall'):
            for name, (environ, tty) in cases.items():
                stdin = None if tty is None else FakeStdin(tty)
                with self.subTest(command=command, case=name):
                    before = snapshot(self.repo)
                    with mock.patch.dict(os.environ, environ, clear=True), mock.patch.object(sys, 'stdin', stdin):
                        code, output = self.call(installer.main, [command, '--target', str(self.repo)])
                    self.assertEqual(code, 1, output)
                    self.assertIn('ERROR:', output)
                    self.assertEqual(snapshot(self.repo), before)
        with (mock.patch.dict(os.environ, env, clear=True), mock.patch.object(sys, 'stdin', FakeStdin(True)),
              mock.patch.object(installer, 'PAYLOAD', SOURCE)):
            code, output = self.call(installer.main, ['off', '--target', str(self.repo)])
        self.assertEqual(code, 0, output)
        self.assertEqual(self.load(), GRAPHIFY)


class UninstallTests(FusionBase):
    # AC-10
    def test_uninstall_keeps_foreign_content(self):
        self.write_settings(GRAPHIFY)
        (self.repo / 'CLAUDE.md').write_bytes(b'# Mio\nlinea\n')
        (self.repo / 'AGENTS.md').write_bytes(b'# Agentes\n')
        legacy = self.repo / '.claude' / 'settings.microsdd.json'
        legacy.write_bytes(b'{}\n')
        code, output = self.install()
        self.assertEqual(code, 0, output)
        self.assertIn('settings.microsdd.json', output)
        code, output = self.uninstall()
        self.assertEqual(code, 0, output)
        self.assertEqual(self.load(), GRAPHIFY)
        self.assertEqual((self.repo / 'CLAUDE.md').read_bytes(), b'# Mio\nlinea\n')
        self.assertEqual((self.repo / 'AGENTS.md').read_bytes(), b'# Agentes\n')
        self.assertTrue((self.repo / 'docs').is_dir())
        self.assertTrue((self.repo / 'spec').is_dir())
        self.assertTrue((self.repo / '.microharness' / 'memory.json').is_file())
        for dst in installer.MANIFEST.values():
            if dst != installer.SETTINGS:
                self.assertFalse((self.repo / dst).exists(), dst)
        self.assertFalse((self.repo / 'CLAUDE.microsdd.md').exists())
        self.assertFalse((self.repo / '.microharness' / 'install.json').exists())
        self.assertFalse(legacy.exists())

    def test_uninstall_after_clean_install_removes_created_files(self):
        self.assertEqual(self.install()[0], 0)
        code, output = self.uninstall()
        self.assertEqual(code, 0, output)
        self.assertFalse(self.settings.exists())
        self.assertFalse((self.repo / 'CLAUDE.md').exists())
        self.assertTrue((self.repo / '.microharness' / 'memory.json').is_file())

    # AC-03 (uninstall)
    def test_uninstall_restores_previous_distinct_values(self):
        self.write_settings({'agent': 'otro', 'model': 'x'})
        self.assertEqual(self.install()[0], 0)
        self.assertEqual(self.uninstall()[0], 0)
        self.assertEqual(self.load(), {'agent': 'otro', 'model': 'x'})

    # AC-11
    def test_modified_own_file_conflicts_unless_forced(self):
        self.assertEqual(self.install()[0], 0)
        lider = self.repo / '.claude' / 'agents' / 'lider.md'
        lider.write_bytes(b'modificado\n')
        before = snapshot(self.repo)
        code, output = self.uninstall()
        self.assertEqual(code, 1, output)
        self.assertIn('conflicto', output)
        self.assertEqual(snapshot(self.repo), before)
        code, output = self.uninstall(force=True)
        self.assertEqual(code, 0, output)
        self.assertFalse(lider.exists())

    def test_uninstall_without_record_fails_without_writing(self):
        self.assertEqual(self.install()[0], 0)
        (self.repo / '.microharness' / 'install.json').unlink()
        before = snapshot(self.repo)
        code, output = self.uninstall()
        self.assertEqual(code, 1, output)
        self.assertEqual(snapshot(self.repo), before)


DENIED = ['microsdd off', 'microsdd on', 'microsdd uninstall',
          'uvx --from git+https://github.com/lgzarturo/microsdd microsdd off',
          'python src/microsdd/installer.py off', 'python -m microsdd.installer uninstall',
          'sh -c "microsdd off"', 'git -c alias.x=!microsdd x off',
          'sed -i s/a/b/ .claude/settings.json', 'echo {} > .claude/settings.json',
          'rm .claude/settings.local.json', 'cp a.json .claude/settings.json',
          'python -m json.tool .claude/settings.json salida.json']
ALLOWED = ['microsdd status', 'uvx --from git+https://github.com/lgzarturo/microsdd microsdd status',
           'git add .claude/settings.json', 'git diff .claude/settings.json', 'git status',
           'git commit -m "feat(installer): microsdd on y off"',
           'python -m json.tool .claude/settings.json', 'python3 -m json.tool .claude/settings.json',
           'python -m unittest discover -s tests -v',
           'sh .microharness/python.sh .microharness/sdd.py check fusion-settings-toggle']


class HookTests(unittest.TestCase):
    # AC-12
    def test_bash_toggle_and_settings_are_denied_to_writers(self):
        for agent in ('lider', 'autor', 'implementador'):
            for tool in ('Bash', 'PowerShell'):
                for cmd in DENIED:
                    with self.subTest(agent=agent, tool=tool, cmd=cmd):
                        reason = pretool.run({'agent_type': agent, 'tool_name': tool,
                                              'tool_input': {'command': cmd}})
                        self.assertIsNotNone(reason)
                        self.assertIn('humano', reason)
                for cmd in ALLOWED:
                    with self.subTest(agent=agent, tool=tool, cmd=cmd):
                        self.assertIsNone(pretool.run({'agent_type': agent, 'tool_name': tool,
                                                       'tool_input': {'command': cmd}}))

    # AC-13
    def test_native_edits_of_settings_are_denied(self):
        with tempfile.TemporaryDirectory() as cwd:
            for agent in ('lider', 'autor', 'implementador', 'revisor'):
                for tool in ('Write', 'Edit', 'MultiEdit', 'NotebookEdit'):
                    key = 'notebook_path' if tool == 'NotebookEdit' else 'file_path'
                    for rel in ('.claude/settings.json', '.claude/settings.local.json'):
                        with self.subTest(agent=agent, tool=tool, rel=rel):
                            self.assertIsNotNone(pretool.run({'agent_type': agent, 'tool_name': tool, 'cwd': cwd,
                                                              'tool_input': {key: rel}}))

    @unittest.skipUnless(shutil.which('uv'), 'uv no disponible')
    def test_hook_starts_with_uv(self):
        result = subprocess.run(['uv', 'run', '--no-project', '--quiet', '--python', '>=3.10', str(HOOK)],
                                input='{}', capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, '')


class DocsTests(unittest.TestCase):
    # AC-14
    def test_versioning_doc_drops_alternate_settings(self):
        text = (SOURCE / 'assets' / 'proceso-versionado.md').read_text(encoding='utf-8')
        self.assertNotIn('settings.microsdd.json', text)
        self.assertIn('`.microharness/install.json`', text)


if __name__ == '__main__':
    unittest.main()
