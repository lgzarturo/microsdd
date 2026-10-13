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

SCRIPT = Path(__file__).resolve().parents[1] / '.microharness' / 'sdd.py'
spec = importlib.util.spec_from_file_location('micro_sdd_integridad', SCRIPT)
sdd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdd)

PREFIX = 'Integridad de memoria'
SLUG = 'fix-sesiones'
CLOSED = 'cerrada'



class FakeStdin:
    def __init__(self, tty=True):
        self.tty = tty

    def isatty(self):
        return self.tty


@contextlib.contextmanager
def human_tty():
    old = os.environ.pop("CLAUDECODE", None)
    prev = sys.stdin
    sys.stdin = FakeStdin(True)
    try:
        yield
    finally:
        sys.stdin = prev
        if old is None:
            os.environ.pop("CLAUDECODE", None)
        else:
            os.environ["CLAUDECODE"] = old


@unittest.skipUnless(shutil.which('git'), 'git no disponible')
class MemoryIntegrityTests(unittest.TestCase):
    def setUp(self):
        self._human_tty_cm = human_tty()
        self._human_tty_cm.__enter__()
        self.addCleanup(self._human_tty_cm.__exit__, None, None, None)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.old_root, self.old_memory = sdd.ROOT, sdd.MEMORY
        sdd.ROOT = Path(self.temporary.name)
        sdd.MEMORY = sdd.ROOT / '.microharness' / 'memory.json'
        self.addCleanup(self.restore)
        # Evita que git suba a un repositorio que contenga el directorio temporal.
        env = mock.patch.dict(os.environ, {'GIT_CEILING_DIRECTORIES': str(sdd.ROOT.parent)})
        env.start()
        self.addCleanup(env.stop)
        (sdd.ROOT / 'tests').mkdir()
        (sdd.ROOT / 'tests' / 'test_ok.py').write_text(
            'import unittest\n\n\nclass Ok(unittest.TestCase):\n    def test_ok(self):\n        pass\n',
            encoding='utf-8')
        self.make_task(SLUG)

    def restore(self):
        sdd.ROOT, sdd.MEMORY = self.old_root, self.old_memory

    # Utilidades -----------------------------------------------------------

    def quiet(self, fn, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return fn(*args)

    def folder(self, slug):
        return sdd.ROOT / 'spec' / slug

    def make_task(self, slug):
        self.quiet(sdd.new, slug)
        folder = self.folder(slug)
        data = sdd.load(folder / 'spec.json')
        data['title'] = 'Corregir la sesión'
        data['scope']['allowed_paths'] = ['src/**', 'tests/**']
        data['testing']['commands'] = [[sys.executable, '-m', 'unittest', 'discover', '-s', 'tests']]
        sdd.dump(folder / 'spec.json', data)
        (folder / 'requerimientos.md').write_text(
            '# QUÉ\nWHEN expire una sesión, THE sistema SHALL rechazar credenciales vencidas.\n'
            'AC-01: token vencido produce 401.\n## Fuera de alcance\nNo renovar tokens.\n', encoding='utf-8')
        (folder / 'plan.md').write_text('# CÓMO\nComprobar expiración en validador existente.\n', encoding='utf-8')
        (folder / 'tareas.md').write_text('# PASOS\n- [ ] T01 (AC-01): prueba de expiración.\n', encoding='utf-8')

    def close_task(self, slug):
        self.quiet(sdd.approve, slug, 'spec', 'Humano', 'Sí, aprobada')
        self.quiet(sdd.review, slug, 'APROBADO', 'Comparados diff y pruebas')
        self.quiet(sdd.approve, slug, 'close', 'Humano', 'Sí, cerrar tarea')
        self.assertEqual(sdd.load(self.folder(slug) / 'spec.json')['state'], 'terminado')

    def git(self, *args):
        subprocess.run(['git', *args], cwd=sdd.ROOT, check=True, capture_output=True)

    def init_repo(self):
        self.git('init', '-q')
        self.git('config', 'user.email', 'test@example.com')
        self.git('config', 'user.name', 'Test')

    def commit_all(self, message='base'):
        self.git('add', '-A')
        self.git('-c', 'commit.gpgsign=false', 'commit', '-q', '--no-verify', '--allow-empty', '-m', message)

    def repo_with_base(self):
        self.init_repo()
        self.commit_all()

    def edit_memory(self, change):
        memory = sdd.load(sdd.MEMORY)
        change(memory)
        sdd.dump(sdd.MEMORY, memory)

    def integrity(self, slug=SLUG, **kwargs):
        return [e for e in sdd.validate(slug, **kwargs) if e.startswith(PREFIX)]

    def assertIntegrityError(self, errors, *parts):
        self.assertTrue([e for e in errors if all(p in e for p in parts)],
                        f'Falta error de integridad con {parts}: {errors}')

    # AC-01 -----------------------------------------------------------------

    def test_ac01_not_applicable_without_repo_commits_or_memory_in_head(self):
        with self.subTest('sin repositorio'):
            self.assertEqual(self.integrity(), [])
        self.init_repo()
        with self.subTest('repositorio sin commits'):
            self.assertEqual(self.integrity(), [])
        (sdd.ROOT / 'src').mkdir()
        (sdd.ROOT / 'src' / 'app.py').write_text('x = 1\n', encoding='utf-8')
        self.git('add', '--', 'src/app.py')
        self.git('-c', 'commit.gpgsign=false', 'commit', '-q', '--no-verify', '-m', 'sin memoria')
        with self.subTest('HEAD sin memory.json'):
            self.assertEqual(self.integrity(), [])

    # AC-02 -----------------------------------------------------------------

    def test_ac02_unreadable_base_memory_fails_closed(self):
        self.init_repo()
        good = sdd.MEMORY.read_bytes()
        bad_contents = {
            'texto no JSON': 'esto no es JSON\n',
            'tasks como lista': json.dumps({'schema_version': 1, 'project': {}, 'tasks': []}),
        }
        for name, content in bad_contents.items():
            with self.subTest(name):
                sdd.MEMORY.write_text(content, encoding='utf-8')
                self.commit_all(name)
                sdd.MEMORY.write_bytes(good)
                errors = self.integrity()
                self.assertTrue([e for e in errors if 'HEAD ilegible' in e], errors)

    # AC-03 -----------------------------------------------------------------

    def test_ac03_events_must_keep_committed_prefix(self):
        self.quiet(sdd.approve, SLUG, 'spec', 'Humano', 'Sí, aprobada')
        self.repo_with_base()
        base = sdd.MEMORY.read_bytes()
        events = sdd.load(sdd.MEMORY)['tasks'][SLUG]['events']
        self.assertEqual([e['event'] for e in events], ['creada', 'aprobación_spec'])

        def delete_created(m):
            m['tasks'][SLUG]['events'].pop(0)

        def change_at(m):
            m['tasks'][SLUG]['events'][0]['at'] = '2000-01-01T00:00:00+00:00'

        def insert_before_last(m):
            m['tasks'][SLUG]['events'].insert(1, {'at': sdd.now(), 'event': 'revisión'})

        for name, change in (('borrar creada', delete_created), ('cambiar at', change_at),
                             ('insertar antes del último', insert_before_last)):
            with self.subTest(name):
                sdd.MEMORY.write_bytes(base)
                self.edit_memory(change)
                self.assertIntegrityError(self.integrity(), SLUG, 'events')
        with self.subTest('añadir al final'):
            sdd.MEMORY.write_bytes(base)
            self.edit_memory(lambda m: m['tasks'][SLUG]['events'].append({'at': sdd.now(), 'event': 'otro'}))
            self.assertFalse([e for e in self.integrity() if 'events' in e])

    # AC-04 -----------------------------------------------------------------

    def test_ac04_watched_fields_require_justifying_event(self):
        self.quiet(sdd.approve, SLUG, 'spec', 'Humano', 'Sí, aprobada')
        self.repo_with_base()
        base = sdd.MEMORY.read_bytes()

        def setter(field, value):
            def change(m):
                task = m['tasks'][SLUG]
                if field.startswith('approvals.'):
                    task['approvals'][field.split('.', 1)[1]] = value
                else:
                    task[field] = value
            return change

        cases = (
            ('approvals.spec', {'by': 'Otro', 'evidence': 'falsa', 'at': sdd.now(), 'fingerprint': 'f'},
             ('aprobación_spec',), 'revisión'),
            ('approvals.close', {'by': 'Otro', 'evidence': 'falsa', 'at': sdd.now()},
             ('aprobación_close', 'aprobación_spec'), 'sellado_tests'),
            ('sealed_tests', {'tests/test_ok.py': 'abc'}, ('sellado_tests',), 'revisión'),
            ('review', 'APROBADO', ('revisión', 'aprobación_spec'), 'sellado_tests'),
            ('review_fingerprint', 'abc', ('revisión', 'aprobación_spec'), 'sellado_tests'),
            ('iterations', 2, ('revisión', 'aprobación_spec'), 'sellado_tests'),
        )
        for field, value, justifying, unrelated in cases:
            change = setter(field, value)
            with self.subTest(field=field, evento='ninguno'):
                sdd.MEMORY.write_bytes(base)
                self.edit_memory(change)
                self.assertIntegrityError(self.integrity(), SLUG, field)
            for event in justifying:
                with self.subTest(field=field, evento=event):
                    sdd.MEMORY.write_bytes(base)
                    self.edit_memory(change)
                    self.edit_memory(lambda m: m['tasks'][SLUG]['events'].append({'at': sdd.now(), 'event': event}))
                    self.assertEqual(self.integrity(), [])
            with self.subTest(field=field, evento=unrelated):
                sdd.MEMORY.write_bytes(base)
                self.edit_memory(change)
                self.edit_memory(lambda m: m['tasks'][SLUG]['events'].append({'at': sdd.now(), 'event': unrelated}))
                self.assertIntegrityError(self.integrity(), SLUG, field)

    # AC-05 -----------------------------------------------------------------

    def test_ac05_real_operations_produce_no_integrity_errors(self):
        self.repo_with_base()
        folder = self.folder(SLUG)

        def no_errors(step):
            self.assertEqual(self.integrity(), [], step)

        self.quiet(sdd.approve, SLUG, 'spec', 'Humano', 'Sí, aprobada')
        no_errors('approve spec')
        (sdd.ROOT / 'tests' / 'test_auth.py').write_text(
            'import unittest\n\n\nclass Auth(unittest.TestCase):\n    def test_auth(self):\n        pass\n',
            encoding='utf-8')
        data = sdd.load(folder / 'spec.json')
        data['testing']['protected_tests'] = ['tests/test_auth.py']
        sdd.dump(folder / 'spec.json', data)
        (folder / 'plan.md').write_text('# CÓMO\nComprobar expiración y proteger la prueba.\n', encoding='utf-8')
        self.quiet(sdd.approve, SLUG, 'spec', 'Humano', 'Aprobé la nueva spec')
        no_errors('reaprobación approve spec')
        self.quiet(sdd.seal, SLUG, 'Humano')
        no_errors('seal')
        self.quiet(sdd.review, SLUG, 'RECHAZADO', 'Falta AC-01')
        no_errors('review RECHAZADO')
        self.quiet(sdd.review, SLUG, 'APROBADO', 'Comparados diff y pruebas')
        no_errors('review APROBADO')
        self.quiet(sdd.approve, SLUG, 'close', 'Humano', 'Sí, cerrar tarea')
        self.assertEqual(sdd.load(folder / 'spec.json')['state'], 'terminado')
        no_errors('approve close')
        # Control: la comprobación está activa en este mismo escenario.
        self.edit_memory(lambda m: m['tasks'][SLUG]['events'].pop(0))
        self.assertIntegrityError(self.integrity(), SLUG, 'events')

    # AC-06 -----------------------------------------------------------------

    def closed_base(self):
        self.make_task(CLOSED)
        self.close_task(CLOSED)
        self.repo_with_base()
        return sdd.MEMORY.read_bytes()

    def test_ac06_closed_task_is_immutable(self):
        base = self.closed_base()
        spec_path = self.folder(CLOSED) / 'spec.json'
        spec_base = spec_path.read_bytes()
        with self.subTest('sin cambios'):
            self.assertEqual(self.integrity(), [])

        def set_close(value):
            def change(m):
                m['tasks'][CLOSED]['approvals']['close'] = value
            return change

        def change_evidence(m):
            m['tasks'][CLOSED]['approvals']['close']['evidence'] = 'otra evidencia'

        changes = (
            ('añadir evento', lambda m: m['tasks'][CLOSED]['events'].append({'at': sdd.now(), 'event': 'revisión'})),
            ('cambiar evidence', change_evidence),
            ('close a null', set_close(None)),
        )
        for name, change in changes:
            with self.subTest(name):
                sdd.MEMORY.write_bytes(base)
                self.edit_memory(change)
                self.assertIntegrityError(self.integrity(), CLOSED, 'tarea cerrada modificada')
        with self.subTest('spec.json reabierto'):
            sdd.MEMORY.write_bytes(base)
            data = sdd.load(spec_path)
            data['state'] = 'proceso'
            sdd.dump(spec_path, data)
            self.assertIntegrityError(self.integrity(), CLOSED, 'tarea cerrada reabierta')
            spec_path.write_bytes(spec_base)

    # AC-07 -----------------------------------------------------------------

    def test_ac07_removed_task_with_spec_folder_is_error(self):
        self.closed_base()
        self.edit_memory(lambda m: m['tasks'].pop(CLOSED))
        self.assertIntegrityError(self.integrity(), CLOSED, 'tarea eliminada de la memoria')

    def test_ac07_release_cleanup_is_not_an_error(self):
        self.closed_base()
        self.edit_memory(lambda m: m.__setitem__('tasks', {}))
        shutil.rmtree(self.folder(SLUG))
        shutil.rmtree(self.folder(CLOSED))
        self.make_task('nueva')
        self.assertEqual(self.integrity('nueva'), [])

    # AC-08 -----------------------------------------------------------------

    def test_ac08_uncommitted_task_and_project_are_not_compared(self):
        self.repo_with_base()
        self.make_task('nueva')

        def tamper_new(m):
            task = m['tasks']['nueva']
            task['approvals'] = {'spec': {'by': 'X', 'evidence': 'y', 'at': sdd.now(), 'fingerprint': 'f'},
                                 'close': {'by': 'X', 'evidence': 'y', 'at': sdd.now()}}
            task['sealed_tests'] = {'tests/test_ok.py': 'abc'}
            task['review'] = 'APROBADO'
            task['review_fingerprint'] = 'abc'
            task['iterations'] = 3
            task['events'] = []

        self.edit_memory(tamper_new)
        self.edit_memory(lambda m: m['project'].setdefault('observations', []).append(
            {'at': sdd.now(), 'fact': 'nuevo hecho', 'evidence': 'prueba'}))
        self.assertEqual(self.integrity(), [])
        # Control: la comprobación está activa sobre las tareas confirmadas.
        self.edit_memory(lambda m: m['tasks'][SLUG]['events'].pop(0))
        self.assertIntegrityError(self.integrity(), SLUG, 'events')

    # AC-09 -----------------------------------------------------------------

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, 'argv', ['sdd.py', *argv]), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = sdd.main()
            except SystemExit as e:
                code = e.code
        return code, err.getvalue()

    def test_ac09_errors_in_other_tasks_are_reported_with_and_without_scope(self):
        self.closed_base()
        self.edit_memory(lambda m: m['tasks'][CLOSED]['events'].append({'at': sdd.now(), 'event': 'revisión'}))
        self.assertIntegrityError(self.integrity(SLUG), CLOSED)
        self.assertIntegrityError(self.integrity(SLUG, scope=False), CLOSED)
        code, err = self.run_main('check', SLUG, '--no-scope')
        self.assertEqual(code, 1, err)
        self.assertIn('ERROR: Integridad de memoria', err)

    # AC-10 -----------------------------------------------------------------

    def test_ac10_integrity_error_blocks_approve_and_run(self):
        self.closed_base()
        self.edit_memory(lambda m: m['tasks'][CLOSED]['events'].append({'at': sdd.now(), 'event': 'revisión'}))
        spec_path = self.folder(SLUG) / 'spec.json'
        memory_before, spec_before = sdd.MEMORY.read_bytes(), spec_path.read_bytes()
        with self.assertRaisesRegex(ValueError, PREFIX):
            self.quiet(sdd.approve, SLUG, 'spec', 'Humano', 'Sí, aprobada')
        self.assertEqual(sdd.MEMORY.read_bytes(), memory_before)
        self.assertEqual(spec_path.read_bytes(), spec_before)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            errors = sdd.validate(SLUG, run=True)
        self.assertIntegrityError(errors, CLOSED)
        self.assertNotIn('EJECUTANDO:', out.getvalue())

    # AC-11 -----------------------------------------------------------------

    def test_ac11_single_git_invocation_reads_head_memory(self):
        self.repo_with_base()
        real = subprocess.run
        calls = []

        def spy(*args, **kwargs):
            calls.append(list(args[0] if args else kwargs['args']))
            return real(*args, **kwargs)

        with mock.patch.object(sdd.subprocess, 'run', spy):
            sdd.validate(SLUG)
        reads = [c for c in calls if c and c[0] == 'git'
                 and any('HEAD:.microharness/memory.json' in str(a) for a in c)]
        self.assertEqual(len(reads), 1, calls)


if __name__ == '__main__':
    unittest.main()
