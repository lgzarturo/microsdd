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

REPO = Path(__file__).resolve().parents[1]
SDD = REPO / '.microharness' / 'sdd.py'
SCRIPT = REPO / 'scripts' / 'limpiar_arnes.py'
spec = importlib.util.spec_from_file_location('limpiar_arnes', SCRIPT)
limpiar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(limpiar)

DOCS = ('AGENT.md', 'arquitectura.md', 'convensiones.md', 'specificaciones.md')
GIT_ENV = {k: v for k, v in os.environ.items() if k not in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE')}
MEMORY = {'schema_version': 1, 'project': {'observations': ['dato ficticio'], 'decisions': []},
          'tasks': {'tarea-uno': {'notes': 'uno'}, 'tarea-dos': {'notes': 'dos'}}}


def git(args, cwd):
    return subprocess.run(['git', *args], cwd=cwd, env=GIT_ENV, check=True, capture_output=True,
                          text=True, encoding='utf-8')


def task(state):
    return {'spec.json': json.dumps({'id': 'x', 'state': state}),
            'plan.md': '# CÓMO\nDiseño ficticio.\n', 'tareas.md': '# PASOS\n- [x] T01\n'}


def snapshot(root: Path) -> dict:
    result = {}
    for folder, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not (Path(folder) == root and d == '.git')]
        for name in files:
            path = Path(folder) / name
            result[path.relative_to(root).as_posix()] = path.read_bytes()
    return result


def head_and_index(root: Path):
    return git(['rev-parse', 'HEAD'], root).stdout, git(['diff', '--cached', '--name-only'], root).stdout


class LimpiarArnesTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.root = self.base / 'repo'

    def make_repo(self, tasks=None, extra=None, gitignore=None, memory=MEMORY, sdd_text=None, git_init=True):
        # Repositorio temporal con commit inicial; nunca el repositorio real.
        tasks = {'tarea-uno': task('terminado'), 'tarea-dos': task('terminado')} if tasks is None else tasks
        files = {'.microharness/sdd.py': SDD.read_bytes() if sdd_text is None else sdd_text,
                 'spec/.gitkeep': '', 'src/app.py': 'x = 1\n'}
        if memory is not None:
            files['.microharness/memory.json'] = memory if isinstance(memory, str) else json.dumps(memory, indent=2)
        for doc in DOCS:
            files[f'docs/{doc}'] = f'# {doc}\n\nContenido propio del desarrollo del arnés.\n'
        for slug, content in tasks.items():
            for name, text in content.items():
                files[f'spec/{slug}/{name}'] = text
        if gitignore is not None:
            files['.gitignore'] = gitignore
        files.update(extra or {})
        for name, content in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                path.write_bytes(content)
            else:
                path.write_bytes(content.encode('utf-8'))
        if git_init:
            self.commit_repo(self.root)

    def commit_repo(self, where: Path):
        git(['init', '-q'], where)
        git(['config', 'user.email', 'test@example.com'], where)
        git(['config', 'user.name', 'Test'], where)
        git(['config', 'core.autocrlf', 'false'], where)
        git(['config', 'core.symlinks', 'true'], where)
        git(['add', '-A'], where)
        git(['-c', 'commit.gpgsign=false', 'commit', '-q', '--no-verify', '-m', 'inicial'], where)

    def commit_change(self, message):
        git(['add', '-A'], self.root)
        git(['-c', 'commit.gpgsign=false', 'commit', '-q', '--no-verify', '-m', message], self.root)

    def init_reference(self) -> dict:
        ref = self.base / 'referencia'
        (ref / '.microharness').mkdir(parents=True)
        shutil.copy2(SDD, ref / '.microharness' / 'sdd.py')
        subprocess.run([sys.executable, str(ref / '.microharness' / 'sdd.py'), 'init'], cwd=ref,
                       check=True, capture_output=True)
        result = {f'docs/{doc}': (ref / 'docs' / doc).read_bytes() for doc in DOCS}
        result['.microharness/memory.json'] = (ref / '.microharness' / 'memory.json').read_bytes()
        return result

    def run_tool(self, argv, root=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = limpiar.main(argv, root=self.root if root is None else root)
        return code, out.getvalue(), err.getvalue()

    def assert_rejected(self, argv=('1.2.0',), git_state=True, root=None, contains=()):
        root = self.root if root is None else root
        before = snapshot(root)
        state = head_and_index(root) if git_state else None
        code, out, err = self.run_tool(list(argv), root=root)
        self.assertEqual(code, 1, out + err)
        self.assertEqual(snapshot(root), before)
        if git_state:
            self.assertEqual(head_and_index(root), state)
        for text in contains:
            self.assertIn(text, out + err)
        return out + err

    # AC-01
    def test_archives_byte_for_byte_without_gitkeep(self):
        self.make_repo()
        before = snapshot(self.root)
        code, out, err = self.run_tool(['1.2.0'])
        self.assertEqual(code, 0, out + err)
        archived = {k: v for k, v in before.items()
                    if k == '.microharness/memory.json' or k.startswith(('docs/', 'spec/')) and k != 'spec/.gitkeep'}
        self.assertIn('spec/tarea-uno/plan.md', archived)
        hist = self.root / 'historial' / '1.2.0'
        for name, content in archived.items():
            target = hist / ('memory.json' if name == '.microharness/memory.json' else name)
            self.assertEqual(target.read_bytes(), content, name)
        self.assertEqual(len(snapshot(hist)), len(archived))
        self.assertFalse((hist / 'spec' / '.gitkeep').exists())

    # AC-02
    def test_leaves_initial_state_equal_to_sdd_init(self):
        self.make_repo()
        code, out, err = self.run_tool(['1.2.0'])
        self.assertEqual(code, 0, out + err)
        for name, content in self.init_reference().items():
            self.assertEqual((self.root / name).read_bytes(), content, name)
        self.assertEqual(sorted(p.name for p in (self.root / 'docs').iterdir()), sorted(DOCS))
        self.assertEqual([p.name for p in (self.root / 'spec').iterdir()], ['.gitkeep'])

    # AC-03
    def test_keeps_other_files_head_index_and_prints_next_steps(self):
        self.make_repo()
        def outside(snap):
            return {k: v for k, v in snap.items() if not k.startswith(('historial/1.2.0/', 'docs/', 'spec/'))
                    and k not in ('.microharness/memory.json', '.microharness/memory.lock')}
        before, state = outside(snapshot(self.root)), head_and_index(self.root)
        code, out, err = self.run_tool(['1.2.0'])
        self.assertEqual(code, 0, out + err)
        self.assertEqual(outside(snapshot(self.root)), before)
        self.assertEqual(head_and_index(self.root), state)
        self.assertEqual(state[1], '')
        add_line = next(line for line in out.splitlines() if 'git add --' in line)
        for path in ('historial/1.2.0', 'docs', 'spec', '.microharness/memory.json'):
            self.assertIn(path, add_line.split())
        self.assertNotIn('git add .', out)
        self.assertIn('chore(release): archiva historial 1.2.0', out)

    # AC-04
    def test_dry_run_writes_nothing(self):
        self.make_repo()
        before, state = snapshot(self.root), head_and_index(self.root)
        code, out, err = self.run_tool(['1.2.0', '--dry-run'])
        self.assertEqual(code, 0, out + err)
        self.assertEqual(snapshot(self.root), before)
        self.assertEqual(head_and_index(self.root), state)
        self.assertFalse((self.root / 'historial').exists())
        self.assertIn('historial/1.2.0', out)

    # AC-05
    def test_open_tasks_abort_listing_slugs(self):
        no_spec = task('terminado')
        del no_spec['spec.json']
        memory = json.loads(json.dumps(MEMORY))
        memory['tasks'] = {'tarea-pendiente': {}, 'tarea-fantasma': {}}
        self.make_repo(tasks={'tarea-pendiente': task('pendiente'), 'tarea-proceso': task('proceso'),
                              'tarea-sin-spec': no_spec, 'tarea-ok': task('terminado')}, memory=memory)
        text = self.assert_rejected(contains=('tarea-pendiente', 'tarea-proceso', 'tarea-fantasma', 'tarea-sin-spec'))
        self.assertNotIn('tarea-ok', text)

    # AC-06 (a)
    def test_modified_tracked_file_aborts(self):
        self.make_repo()
        (self.root / 'src' / 'app.py').write_text('x = 2\n', encoding='utf-8')
        self.assert_rejected()

    # AC-06 (b)
    def test_untracked_file_aborts(self):
        self.make_repo()
        (self.root / 'nuevo.txt').write_text('nuevo\n', encoding='utf-8')
        self.assert_rejected()

    # AC-06 (c)
    def test_non_git_directory_aborts(self):
        self.make_repo(git_init=False)
        self.assert_rejected(git_state=False)

    # AC-06 (d)
    def test_root_inside_other_repository_aborts(self):
        self.root = self.base / 'externo' / 'repo'
        self.make_repo(git_init=False)
        self.commit_repo(self.base / 'externo')
        self.assert_rejected()

    # AC-07 (a)-(c)
    def test_existing_history_version_aborts(self):
        self.make_repo(extra={'historial/1.2.0/previo.txt': 'previo\n'})
        self.assert_rejected()

    # AC-07 (d)
    def test_history_as_file_aborts(self):
        self.make_repo(extra={'historial': 'no soy un directorio\n'})
        self.assert_rejected()

    # AC-08
    def test_invalid_versions_return_one(self):
        self.make_repo()
        for version in ('../x', '1.0', '01.2.0', '1.2.0/../x', '1.2.0+build', '1.2.0\n'):
            with self.subTest(version=version):
                self.assert_rejected(argv=(version,))

    # AC-08
    def test_prerelease_version_is_valid(self):
        self.make_repo()
        code, out, err = self.run_tool(['1.2.0-rc.1'])
        self.assertEqual(code, 0, out + err)
        self.assertTrue((self.root / 'historial' / '1.2.0-rc.1' / 'memory.json').is_file())

    # AC-09
    def test_unknown_doc_aborts(self):
        self.make_repo(extra={'docs/extra.md': '# extra\n'})
        self.assert_rejected(contains=('extra.md',))

    # AC-10 (a)
    def test_missing_memory_aborts(self):
        self.make_repo(memory=None)
        self.assert_rejected()

    # AC-10 (b)
    def test_invalid_memory_json_aborts(self):
        self.make_repo(memory='{no es json')
        self.assert_rejected()

    # AC-10 (c)
    def test_missing_sdd_aborts(self):
        self.make_repo()
        (self.root / '.microharness' / 'sdd.py').unlink()
        self.commit_change('sin sdd')
        self.assert_rejected()

    # AC-10 (d)
    def test_memory_tasks_not_object_aborts(self):
        memory = json.loads(json.dumps(MEMORY))
        memory['tasks'] = []
        self.make_repo(memory=memory)
        self.assert_rejected()

    # AC-11
    def test_invalid_arguments_exit_two(self):
        self.make_repo()
        for argv in ([], ['1.2.0', '--desconocida']):
            with self.subTest(argv=argv):
                before, state = snapshot(self.root), head_and_index(self.root)
                with self.assertRaises(SystemExit) as caught:
                    self.run_tool(argv)
                self.assertEqual(caught.exception.code, 2)
                self.assertEqual(snapshot(self.root), before)
                self.assertEqual(head_and_index(self.root), state)

    # AC-12
    def test_failed_init_prints_git_remediation(self):
        self.make_repo(sdd_text='import sys\nsys.exit(1)\n')
        code, out, err = self.run_tool(['1.2.0'])
        self.assertEqual(code, 1, out + err)
        self.assertTrue((self.root / 'historial' / '1.2.0').is_dir())
        self.assertIn('git restore', err)
        self.assertIn('historial/1.2.0', err)

    # AC-14
    def test_ignored_file_in_archived_paths_aborts(self):
        self.make_repo(gitignore='.coverage\n')
        (self.root / 'spec' / 'tarea-uno' / '.coverage').write_text('datos\n', encoding='utf-8')
        self.assertEqual(git(['status', '--porcelain'], self.root).stdout, '')
        self.assert_rejected(contains=('spec/tarea-uno/.coverage',))

    # AC-15
    def test_symlink_in_spec_aborts(self):
        self.make_repo(git_init=False)
        try:
            os.symlink(self.root / 'src' / 'app.py', self.root / 'spec' / 'tarea-uno' / 'enlace')
        except (OSError, NotImplementedError):
            self.skipTest('la plataforma no permite crear enlaces simbólicos')
        self.commit_repo(self.root)
        self.assert_rejected()


if __name__ == '__main__':
    unittest.main()
