import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1]
SCRIPT = SOURCE / 'src' / 'microsdd' / 'installer.py'
spec = importlib.util.spec_from_file_location('microsdd_installer', SCRIPT)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

BEGIN = b'<!-- microsdd:begin -->'
FAKE_UV = [sys.executable, '-c', 'print("uv 0.0.0")']

MIT_LICENSE = '''MIT License

Copyright (c) 2026 Arturo López

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.'''


def snapshot(root: Path) -> dict[str, bytes]:
    # Árbol completo (ruta -> bytes) excluyendo directorios .git.
    result = {}
    for path in sorted(root.rglob('*')):
        rel = path.relative_to(root)
        if '.git' in rel.parts:
            continue
        result[rel.as_posix()] = path.read_bytes() if path.is_file() else b'<dir>'
    return result


class InstallerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.home = self.base / 'home'
        self.home.mkdir()
        self.repo = self.git_repo(self.base / 'repo')

    def git_repo(self, path: Path) -> Path:
        path.mkdir(parents=True, exist_ok=True)
        subprocess.run(['git', 'init', '-q', str(path)], check=True)
        return path

    def run_install(self, target: Path, *, uv=None, force=False, dry_run=False):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = installer.install(SOURCE, target, uv=uv or FAKE_UV,
                                     home=self.home, force=force, dry_run=dry_run)
        return code, out.getvalue()

    def install_with_path(self, path: str, uv=None):
        out = io.StringIO()
        with mock.patch.dict(os.environ, {'PATH': path}), contextlib.redirect_stdout(out):
            code = installer.install(SOURCE, self.repo, uv=uv, home=self.home)
        return code, out.getvalue()

    # AC-01
    def test_clean_install_copies_own_files_and_initializes(self):
        code, output = self.run_install(self.repo)
        self.assertEqual(code, 0, output)
        for src, dst in installer.MANIFEST.items():
            self.assertEqual((self.repo / dst).read_bytes(), (SOURCE / src).read_bytes(), dst)
        claude = (self.repo / 'CLAUDE.md').read_bytes()
        self.assertIn(BEGIN, claude)
        self.assertIn(b'<!-- microsdd:end -->', claude)
        self.assertIn(b'@CLAUDE.microsdd.md', claude)
        docs = sorted(p.name for p in (self.repo / 'docs').iterdir())
        self.assertEqual(docs, ['AGENT.md', 'arquitectura.md', 'convensiones.md', 'specificaciones.md'])
        self.assertTrue((self.repo / 'spec').is_dir())
        self.assertTrue((self.repo / '.microharness' / 'memory.json').is_file())
        self.assertIn('git add ', output)
        self.assertNotIn('git add .\n', output)
        self.assertIn('CLAUDE.microsdd.md', output)

    # AC-02
    def test_second_run_is_idempotent(self):
        self.assertEqual(self.run_install(self.repo)[0], 0)
        before = snapshot(self.repo)
        code, output = self.run_install(self.repo)
        self.assertEqual(code, 0, output)
        self.assertEqual(snapshot(self.repo), before)
        self.assertEqual((self.repo / 'CLAUDE.md').read_bytes().count(BEGIN), 1)

    # AC-03
    def test_existing_claude_md_is_kept_as_prefix(self):
        cases = {'lf': b'# Mio\nlinea\n', 'crlf': b'# Mio\r\nlinea\r\n', 'sin-salto': b'# Mio'}
        for name, original in cases.items():
            with self.subTest(name):
                repo = self.git_repo(self.base / name)
                (repo / 'CLAUDE.md').write_bytes(original)
                code, output = self.run_install(repo)
                self.assertEqual(code, 0, output)
                result = (repo / 'CLAUDE.md').read_bytes()
                self.assertTrue(result.startswith(original))
                suffix = result[len(original):]
                self.assertEqual(result.count(BEGIN), 1)
                self.assertIn(b'\n' + BEGIN, result)
                self.assertTrue(result.endswith(b'\n'))
                if name == 'crlf':
                    self.assertEqual(suffix.count(b'\r\n'), suffix.count(b'\n'))
                else:
                    self.assertNotIn(b'\r', suffix)

    def test_agents_md_is_imported_when_claude_md_is_created(self):
        agents = b'# Agentes\n'
        (self.repo / 'AGENTS.md').write_bytes(agents)
        code, output = self.run_install(self.repo)
        self.assertEqual(code, 0, output)
        self.assertIn(b'@AGENTS.md', (self.repo / 'CLAUDE.md').read_bytes())
        self.assertEqual((self.repo / 'AGENTS.md').read_bytes(), agents)

    # AC-04
    def test_different_settings_is_kept_and_alternate_written(self):
        settings = self.repo / '.claude' / 'settings.json'
        settings.parent.mkdir()
        settings.write_bytes(b'{"agent": "otro"}\n')
        code, output = self.run_install(self.repo)
        self.assertEqual(code, 0, output)
        self.assertEqual(settings.read_bytes(), b'{"agent": "otro"}\n')
        self.assertEqual((self.repo / '.claude' / 'settings.microsdd.json').read_bytes(),
                         (SOURCE / '.claude' / 'settings.json').read_bytes())
        self.assertIn('agent: lider', output)
        self.assertIn('fusionar manualmente', output)

    # AC-05
    def test_modified_own_file_conflicts_without_force_and_updates_with_force(self):
        (self.repo / 'CLAUDE.md').write_bytes(b'# Usuario\n')
        settings = self.repo / '.claude' / 'settings.json'
        settings.parent.mkdir()
        settings.write_bytes(b'{}\n')
        self.assertEqual(self.run_install(self.repo)[0], 0)
        claude_after_first = (self.repo / 'CLAUDE.md').read_bytes()
        lider = self.repo / '.claude' / 'agents' / 'lider.md'
        lider.write_bytes(b'modificado\n')
        before = snapshot(self.repo)
        code, output = self.run_install(self.repo)
        self.assertEqual(code, 1, output)
        self.assertIn('conflicto', output)
        self.assertEqual(snapshot(self.repo), before)
        code, output = self.run_install(self.repo, force=True)
        self.assertEqual(code, 0, output)
        self.assertEqual(lider.read_bytes(), (SOURCE / '.claude' / 'agents' / 'lider.md').read_bytes())
        self.assertEqual((self.repo / 'CLAUDE.md').read_bytes(), claude_after_first)
        self.assertEqual(settings.read_bytes(), b'{}\n')

    # AC-06
    def test_dry_run_prints_plan_without_writing(self):
        (self.repo / 'CLAUDE.md').write_bytes(b'# Usuario\n')
        before = snapshot(self.repo)
        code, output = self.run_install(self.repo, dry_run=True)
        self.assertEqual(code, 0, output)
        self.assertEqual(snapshot(self.repo), before)
        self.assertIn('crear', output)
        self.assertIn('anexar registro', output)

    # AC-07
    def test_invalid_targets_fail_without_writing(self):
        self.git_repo(self.home)
        under_claude = self.git_repo(self.home / '.claude' / 'proyecto')
        not_git = self.base / 'sin-git'
        not_git.mkdir()
        subdir = self.repo / 'sub'
        subdir.mkdir()
        (subdir / 'a.txt').write_text('a', encoding='utf-8')
        for name, target in {'home': self.home, 'claude': under_claude,
                             'no-git': not_git, 'subdir': subdir}.items():
            with self.subTest(name):
                before = snapshot(self.base)
                code, output = self.run_install(target)
                self.assertEqual(code, 1, output)
                self.assertEqual(snapshot(self.base), before)

    # AC-02 (instalador-sin-python3)
    def test_broken_uv_fails_without_writing(self):
        before = snapshot(self.repo)
        code, output = self.run_install(self.repo, uv=[sys.executable, '-c', 'import sys; sys.exit(49)'])
        self.assertEqual(code, 1, output)
        self.assertIn('uv', output)
        self.assertEqual(snapshot(self.repo), before)

    # AC-03 (instalador-sin-python3)
    def test_missing_uv_fails_without_writing(self):
        git_dir = os.path.dirname(shutil.which('git'))
        if shutil.which('uv', path=git_dir) or shutil.which('uv.exe', path=git_dir):
            self.skipTest('el directorio de git contiene uv')
        before = snapshot(self.repo)
        code, output = self.install_with_path(git_dir)
        self.assertEqual(code, 1, output)
        self.assertIn('uv', output)
        self.assertEqual(snapshot(self.repo), before)

    # AC-04 (instalador-sin-python3)
    @unittest.skipUnless(sys.platform == 'win32', 'solo Windows')
    def test_windows_ignores_uv_cmd_shim(self):
        shims = self.base / 'shims'
        shims.mkdir()
        (shims / 'uv.cmd').write_text(f'@echo off\r\n"{sys.executable}" -c "print(1)"\r\n', encoding='utf-8')
        git_dir = os.path.dirname(shutil.which('git'))
        before = snapshot(self.repo)
        code, output = self.install_with_path(os.pathsep.join([str(shims), git_dir]))
        self.assertEqual(code, 1, output)
        self.assertIn('.cmd', output)
        self.assertEqual(snapshot(self.repo), before)

    # AC-05 (instalador-sin-python3)
    def test_install_succeeds_without_python3_in_path(self):
        git_dir = os.path.dirname(shutil.which('git'))
        if shutil.which('python3', path=git_dir):
            self.skipTest('el directorio de git contiene python3')
        code, output = self.install_with_path(git_dir, uv=FAKE_UV)
        self.assertEqual(code, 0, output)
        self.assertNotIn('python3', output)

    # AC-06 (instalador-sin-python3)
    def test_init_and_smoke_run_with_installer_interpreter(self):
        calls = []
        original = subprocess.run

        def record(args, *rest, **kwargs):
            calls.append([str(a) for a in args])
            return original(args, *rest, **kwargs)

        with mock.patch.object(installer.subprocess, 'run', side_effect=record):
            code, output = self.run_install(self.repo)
        self.assertEqual(code, 0, output)
        scripts = [c for c in calls if '.microharness/sdd.py' in c or '.claude/hooks/pretool.py' in c]
        self.assertEqual(len(scripts), 2, calls)
        for argv in scripts:
            self.assertEqual(argv[0], sys.executable, argv)
        for argv in calls:
            if argv[0] != sys.executable:
                self.assertFalse(os.path.basename(argv[0]).startswith('python3'), argv)

    # AC-13
    def test_smoke_requires_reviewer_read_only_reason(self):
        source = self.base / 'origen'
        for rel in installer.MANIFEST:
            (source / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE / rel, source / rel)
        (source / '.claude' / 'hooks' / 'pretool.py').write_text(
            'import json\nprint(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", '
            '"permissionDecision": "deny", "permissionDecisionReason": "Guardia inválida: x"}}))\n',
            encoding='utf-8')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = installer.install(source, self.repo, uv=FAKE_UV, home=self.home)
        self.assertEqual(code, 1, out.getvalue())

    def test_path_filter_excludes_isolated_environment(self):
        prefix = os.path.abspath('uv-entorno')
        base = os.path.abspath('python-base')
        other = os.path.abspath('otro')
        value = os.pathsep.join([os.path.join(prefix, 'bin'), other, os.path.join(prefix, 'Scripts')])
        self.assertEqual(installer.filter_path(value, prefix, base), other)
        self.assertEqual(installer.filter_path(value, prefix, prefix), value)

    # AC-09
    def test_banner_and_usage_errors(self):
        code, output = self.run_install(self.base / 'sin-git-banner')
        self.assertEqual(code, 1)
        self.assertIn('MicroSDD for Claude Opus 5.5', output)
        self.assertIn('no es un arnés global', output)
        empty = self.base / 'vacio'
        empty.mkdir()
        cwd = os.getcwd()
        self.addCleanup(os.chdir, cwd)
        os.chdir(empty)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            installer.main([])
        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(snapshot(empty), {})

    # AC-01 (licencia-mit)
    def test_license_file_is_canonical_mit(self):
        text = (SOURCE / 'LICENSE').read_text(encoding='utf-8')
        self.assertEqual(text.replace('\r\n', '\n').rstrip('\n'), MIT_LICENSE)

    # AC-10; AC-02, AC-03 (licencia-mit)
    @unittest.skipUnless(shutil.which('uv'), 'uv no disponible')
    def test_wheel_from_sdist_contains_payload_without_dependencies(self):
        project = self.base / 'proyecto'
        for rel in ['pyproject.toml', 'README.md', 'LICENSE', *installer.MANIFEST]:
            (project / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE / rel, project / rel)
        shutil.copytree(SOURCE / 'src', project / 'src',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        dist = self.base / 'dist'
        subprocess.run(['uv', 'build', '--sdist', '--out-dir', str(dist), str(project)],
                       check=True, capture_output=True)
        sdist = next(dist.glob('*.tar.gz'))
        with tarfile.open(sdist) as archive:
            members = [m.name for m in archive.getmembers()
                       if m.name.count('/') == 1 and m.name.endswith('/LICENSE')]
            self.assertEqual(len(members), 1, members)
            sdist_license = archive.extractfile(members[0]).read()
        subprocess.run(['uv', 'build', '--wheel', '--out-dir', str(dist), str(sdist)],
                       check=True, capture_output=True)
        wheel = next(dist.glob('*.whl'))
        with zipfile.ZipFile(wheel) as archive:
            names = set(archive.namelist())
            for rel in installer.MANIFEST:
                self.assertIn(f'microsdd/payload/{rel}', names)
            self.assertIn('microsdd/installer.py', names)
            metadata = next(n for n in names if n.endswith('.dist-info/METADATA'))
            self.assertNotIn('Requires-Dist', archive.read(metadata).decode('utf-8'))
            lines = archive.read(metadata).decode('utf-8').splitlines()
            self.assertIn('License-Expression: MIT', lines)
            self.assertIn('License-File: LICENSE', lines)
            licenses = [n for n in names if n.endswith('.dist-info/licenses/LICENSE')]
            self.assertEqual(len(licenses), 1, sorted(names))
            self.assertEqual(archive.read(licenses[0]), sdist_license)


if __name__ == '__main__':
    unittest.main()
