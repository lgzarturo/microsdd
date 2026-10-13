import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
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

    def run_install(self, target: Path, *, python=None, force=False, dry_run=False):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = installer.install(SOURCE, target, python=python or [sys.executable],
                                     home=self.home, force=force, dry_run=dry_run)
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

    # AC-08
    def test_broken_or_old_python3_fails_without_writing(self):
        scripts = self.base / 'falsos'
        scripts.mkdir()
        stub = scripts / 'stub.py'
        stub.write_text('import sys\nsys.exit(9009)\n', encoding='utf-8')
        old = scripts / 'viejo.py'
        old.write_text('print("3.9.18")\n', encoding='utf-8')
        for fake in (stub, old):
            with self.subTest(fake.name):
                before = snapshot(self.repo)
                code, output = self.run_install(self.repo, python=[sys.executable, str(fake)])
                self.assertEqual(code, 1, output)
                self.assertIn('python3', output)
                self.assertEqual(snapshot(self.repo), before)

    @unittest.skipUnless(sys.platform == 'win32', 'solo Windows')
    def test_windows_ignores_python3_cmd_shim(self):
        shims = self.base / 'shims'
        shims.mkdir()
        (shims / 'python3.cmd').write_text(f'@echo off\r\n"{sys.executable}" %*\r\n', encoding='utf-8')
        git_dir = os.path.dirname(shutil.which('git'))
        before = snapshot(self.repo)
        out = io.StringIO()
        with mock.patch.dict(os.environ, {'PATH': os.pathsep.join([str(shims), git_dir])}), \
                contextlib.redirect_stdout(out):
            code = installer.install(SOURCE, self.repo, python=None, home=self.home)
        self.assertEqual(code, 1, out.getvalue())
        self.assertIn('.cmd', out.getvalue())
        self.assertEqual(snapshot(self.repo), before)

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
            code = installer.install(source, self.repo, python=[sys.executable], home=self.home)
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

    # AC-10
    @unittest.skipUnless(shutil.which('uv'), 'uv no disponible')
    def test_wheel_from_sdist_contains_payload_without_dependencies(self):
        project = self.base / 'proyecto'
        for rel in ['pyproject.toml', 'README.md', *installer.MANIFEST]:
            (project / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE / rel, project / rel)
        shutil.copytree(SOURCE / 'src', project / 'src',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        dist = self.base / 'dist'
        subprocess.run(['uv', 'build', '--sdist', '--out-dir', str(dist), str(project)],
                       check=True, capture_output=True)
        sdist = next(dist.glob('*.tar.gz'))
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


if __name__ == '__main__':
    unittest.main()
