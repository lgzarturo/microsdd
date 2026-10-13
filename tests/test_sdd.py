import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / '.microharness' / 'sdd.py'
spec = importlib.util.spec_from_file_location('micro_sdd', SCRIPT)
sdd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdd)


class MicroSDDTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.old_root, self.old_memory = sdd.ROOT, sdd.MEMORY
        sdd.ROOT = Path(self.temporary.name)
        sdd.MEMORY = sdd.ROOT / '.microharness' / 'memory.json'
        self.addCleanup(self.restore)
        sdd.new('fix-sesiones')
        self.folder = sdd.ROOT / 'spec' / 'fix-sesiones'
        data = sdd.load(self.folder / 'spec.json')
        data['title'] = 'Corregir la sesión'
        data['scope']['allowed_paths'] = ['src/**', 'tests/**']
        (sdd.ROOT / 'pruebas').mkdir()
        (sdd.ROOT / 'pruebas' / 'test_ok.py').write_text(
            'import unittest\n\n\nclass Ok(unittest.TestCase):\n    def test_ok(self):\n        pass\n',
            encoding='utf-8')
        data['testing']['commands'] = [[sys.executable, '-m', 'unittest', 'discover', '-s', 'pruebas']]
        sdd.dump(self.folder / 'spec.json', data)
        (self.folder / 'requerimientos.md').write_text(
            '# QUÉ\nWHEN expire una sesión, THE sistema SHALL rechazar credenciales vencidas.\n'
            'AC-01: token vencido produce 401.\n## Fuera de alcance\nNo renovar tokens.\n', encoding='utf-8')
        (self.folder / 'plan.md').write_text('# CÓMO\nComprobar expiración en validador existente.\n', encoding='utf-8')
        (self.folder / 'tareas.md').write_text('# PASOS\n- [ ] T01 (AC-01): prueba de expiración.\n', encoding='utf-8')

    def restore(self):
        sdd.ROOT, sdd.MEMORY = self.old_root, self.old_memory

    def git_repo(self, tracked: dict[str, str]):
        # Repositorio con commit inicial que no incluye spec/fix-sesiones/.
        def git(*args):
            subprocess.run(['git', *args], cwd=sdd.ROOT, check=True, capture_output=True)
        git('init', '-q')
        git('config', 'user.email', 'test@example.com')
        git('config', 'user.name', 'Test')
        for name, content in tracked.items():
            path = sdd.ROOT / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
            git('add', '--', name)
        git('-c', 'commit.gpgsign=false', 'commit', '-q', '--no-verify', '--allow-empty', '-m', 'inicial')

    def test_diff_files_non_ascii_paths(self):
        self.git_repo({'src/módulo.py': 'x = 1\n'})
        (sdd.ROOT / 'src' / 'módulo.py').write_text('x = 2\n', encoding='utf-8')
        (sdd.ROOT / 'spec' / 'x').mkdir(parents=True)
        (sdd.ROOT / 'spec' / 'x' / 'plan.md').write_text('# CÓMO\n', encoding='utf-8')
        files = [f for f in sdd.diff_files() if f.startswith(('spec/x/', 'src/'))]
        self.assertEqual(files, ['spec/x/plan.md', 'src/módulo.py'])
        for name in files:
            self.assertTrue((sdd.ROOT / name).is_file(), name)

    def test_scope_ignores_uncommitted_task_design(self):
        self.git_repo({'src/app.py': 'x = 1\n'})
        errors = sdd.validate('fix-sesiones')
        self.assertFalse([e for e in errors if 'fuera de scope' in e and 'fix-sesiones/' in e], errors)

    def test_fingerprint_reads_non_ascii_file(self):
        self.git_repo({'src/módulo.py': 'x = 1\n'})
        path = sdd.ROOT / 'src' / 'módulo.py'
        path.write_text('x = 2\n', encoding='utf-8')
        before = sdd.code_fingerprint(['src/**'])
        path.write_text('x = 3\n', encoding='utf-8')
        self.assertNotEqual(before, sdd.code_fingerprint(['src/**']))

    def test_diff_files_path_with_spaces(self):
        self.git_repo({'src/app.py': 'x = 1\n'})
        (sdd.ROOT / 'src' / 'con espacio.py').write_text('y = 1\n', encoding='utf-8')
        self.assertIn('src/con espacio.py', sdd.diff_files())
        self.assertTrue((sdd.ROOT / 'src' / 'con espacio.py').is_file())

    def test_structure_and_validation(self):
        self.assertEqual({x.name for x in self.folder.iterdir()}, set(sdd.TASK_FILES))
        self.assertEqual(sdd.validate('fix-sesiones'), [])

    def test_new_creates_exactly_four_ascii_files(self):
        # AC-01: conjunto literal, sin derivarlo de TASK_FILES.
        with contextlib.redirect_stdout(io.StringIO()):
            sdd.new('otra-tarea')
        names = {x.name for x in (sdd.ROOT / 'spec' / 'otra-tarea').iterdir()}
        self.assertEqual(names, {'spec.json', 'requerimientos.md', 'plan.md', 'tareas.md'})

    def test_check_requires_plan_md(self):
        # AC-02: un diseño.md en lugar de plan.md no satisface la tarea.
        (self.folder / 'plan.md').replace(self.folder / 'diseño.md')
        self.assertIn('Falta spec/fix-sesiones/plan.md', sdd.validate('fix-sesiones'))

    def test_check_detects_template_markers_in_plan_md(self):
        # AC-02: el marcador que escribe new se detecta en plan.md.
        (self.folder / 'plan.md').write_text('# CÓMO\n[PENDIENTE]\n', encoding='utf-8')
        self.assertIn('plan.md conserva marcadores de plantilla', sdd.validate('fix-sesiones'))

    def test_check_rejects_non_ascii_file_name(self):
        # AC-03: el error nombra la entrada no ASCII.
        (self.folder / 'notas-año.md').write_text('nota\n', encoding='utf-8')
        errors = sdd.validate('fix-sesiones')
        self.assertTrue([x for x in errors if 'notas-año.md' in x and 'ASCII' in x], errors)

    def test_check_tolerates_extra_ascii_file(self):
        # AC-03: los archivos extra con nombre ASCII se siguen tolerando.
        (self.folder / 'notas.md').write_text('nota\n', encoding='utf-8')
        self.assertEqual(sdd.validate('fix-sesiones'), [])

    def test_slug_traversal_rejected(self):
        with self.assertRaises(ValueError):
            sdd.task_dir('../secret')

    def test_spec_approval_and_fingerprint(self):
        sdd.approve('fix-sesiones', 'spec', 'Humano', 'Aprobado textualmente en la sesión')
        self.assertEqual(sdd.validate('fix-sesiones'), [])
        (self.folder / 'plan.md').write_text('CAMBIO SIN APROBACIÓN', encoding='utf-8')
        self.assertTrue(any('alterada' in x for x in sdd.validate('fix-sesiones')))

    def test_lifecycle_review_close(self):
        sdd.approve('fix-sesiones', 'spec', 'Humano', 'Sí, aprobada')
        sdd.review('fix-sesiones', 'APROBADO', 'Comparados diff y pruebas')
        sdd.approve('fix-sesiones', 'close', 'Humano', 'Sí, cerrar tarea')
        self.assertEqual(sdd.load(self.folder / 'spec.json')['state'], 'terminado')
        self.assertEqual(sdd.validate('fix-sesiones'), [])

    def test_requires_review_for_close(self):
        sdd.approve('fix-sesiones', 'spec', 'Humano', 'Sí')
        with self.assertRaises(ValueError):
            sdd.approve('fix-sesiones', 'close', 'Humano', 'Sí')

    def test_rejection_exhaustion(self):
        sdd.approve('fix-sesiones', 'spec', 'Humano', 'Sí')
        for _ in range(3):
            sdd.review('fix-sesiones', 'RECHAZADO', 'Falló requisito AC-01')
        self.assertEqual(sdd.load(self.folder / 'spec.json')['state'], 'pendiente')

    def test_sealed_tests_detect_changes(self):
        sdd.approve('fix-sesiones', 'spec', 'Humano', 'Sí')
        path = sdd.ROOT / 'tests' / 'test_auth.py'
        path.parent.mkdir(parents=True)
        path.write_text('assert 1 == 1\n', encoding='utf-8')
        data = sdd.load(self.folder / 'spec.json')
        data['testing']['protected_tests'] = ['tests/test_auth.py']
        sdd.dump(self.folder / 'spec.json', data)
        # Proteger tests y pasar por nueva aprobación del contrato.
        sdd.approve('fix-sesiones', 'spec', 'Humano', 'Aprobé la nueva spec')
        sdd.seal('fix-sesiones', 'Humano')
        self.assertEqual(sdd.validate('fix-sesiones'), [])
        path.write_text('assert 2 == 2\n', encoding='utf-8')
        self.assertTrue(any('sellado' in x for x in sdd.validate('fix-sesiones')))

    def test_sealed_test_ignores_crlf_conversion(self):
        # AC-01, AC-02: convertir LF a CRLF no rompe el sello; un cambio real sí.
        sdd.approve('fix-sesiones', 'spec', 'Humano', 'Sí')
        path = sdd.ROOT / 'tests' / 'test_auth.py'
        path.parent.mkdir(parents=True)
        path.write_bytes(b'import os\nassert 1 == 1\n')
        data = sdd.load(self.folder / 'spec.json')
        data['testing']['protected_tests'] = ['tests/test_auth.py']
        sdd.dump(self.folder / 'spec.json', data)
        sdd.approve('fix-sesiones', 'spec', 'Humano', 'Aprobé la nueva spec')
        sdd.seal('fix-sesiones', 'Humano')
        path.write_bytes(path.read_bytes().replace(b'\n', b'\r\n'))
        self.assertFalse([x for x in sdd.validate('fix-sesiones') if 'sellado' in x])
        path.write_bytes(b'import os\r\nassert 2 == 2\r\n')
        self.assertTrue(any('sellado' in x for x in sdd.validate('fix-sesiones')))

    def _seal_auth_test(self):
        sdd.approve('fix-sesiones', 'spec', 'Humano', 'Sí')
        path = sdd.ROOT / 'tests' / 'test_auth.py'
        path.parent.mkdir(parents=True)
        path.write_text('assert 1 == 1\n', encoding='utf-8')
        data = sdd.load(self.folder / 'spec.json')
        data['testing']['protected_tests'] = ['tests/test_auth.py']
        sdd.dump(self.folder / 'spec.json', data)
        sdd.approve('fix-sesiones', 'spec', 'Humano', 'Aprobé la nueva spec')
        sdd.seal('fix-sesiones', 'Humano')
        return path

    def test_sealed_tests_ignored_after_close(self):
        # AC-01, AC-04: tras el cierre el sello no se compara y queda intacto en memoria.
        path = self._seal_auth_test()
        sealed = dict(sdd.load(sdd.MEMORY)['tasks']['fix-sesiones']['sealed_tests'])
        self.assertIn('tests/test_auth.py', sealed)
        sdd.review('fix-sesiones', 'APROBADO', 'Comparados diff y pruebas')
        sdd.approve('fix-sesiones', 'close', 'Humano', 'Sí, cerrar tarea')
        path.write_text('assert 2 == 2\n', encoding='utf-8')
        self.assertFalse([x for x in sdd.validate('fix-sesiones') if 'sellado' in x])
        self.assertEqual(sdd.load(sdd.MEMORY)['tasks']['fix-sesiones']['sealed_tests'], sealed)

    def test_sealed_tests_checked_when_escalated_pending(self):
        # AC-03: una tarea escalada a pendiente conserva la comparación del sello.
        path = self._seal_auth_test()
        for _ in range(3):
            sdd.review('fix-sesiones', 'RECHAZADO', 'Falló requisito AC-01')
        self.assertEqual(sdd.load(self.folder / 'spec.json')['state'], 'pendiente')
        path.write_text('assert 2 == 2\n', encoding='utf-8')
        self.assertTrue(any('sellado' in x for x in sdd.validate('fix-sesiones')))

    def test_spec_fingerprint_ignores_crlf_conversion(self):
        # AC-03: la huella aprobada sobrevive a LF->CRLF; un cambio real en plan.md no.
        names = ('requerimientos.md', 'plan.md', 'tareas.md')
        for name in names:  # Partir de LF explícito: write_text en Windows ya escribe CRLF.
            p = self.folder / name
            p.write_bytes(p.read_bytes().replace(b'\r\n', b'\n'))
        sdd.approve('fix-sesiones', 'spec', 'Humano', 'Sí')
        for name in names:
            p = self.folder / name
            p.write_bytes(p.read_bytes().replace(b'\n', b'\r\n'))
        self.assertFalse([x for x in sdd.validate('fix-sesiones') if 'alterada' in x])
        (self.folder / 'plan.md').write_bytes('# CÓMO\r\nOtro diseño.\r\n'.encode('utf-8'))
        self.assertTrue(any('alterada' in x for x in sdd.validate('fix-sesiones')))

    def test_hash_file_unchanged_for_lf_content(self):
        # AC-04: compatibilidad con hashes ya registrados sobre LF.
        p = sdd.ROOT / 'lf.txt'
        p.write_bytes('línea uno\nlínea dos\n'.encode('utf-8'))
        self.assertEqual(sdd.hash_file(p), hashlib.sha256(p.read_bytes()).hexdigest())

    def test_conventional_commit_message(self):
        sdd.commit_check('fix(auth): valida expiración de sesión')
        with self.assertRaises(ValueError):
            sdd.commit_check('arreglos')

    def _failing_suite(self):
        # Runner permitido por la lista blanca que sale con código 1.
        (sdd.ROOT / 'pruebas_fallo').mkdir(exist_ok=True)
        (sdd.ROOT / 'pruebas_fallo' / 'test_falla.py').write_text(
            'import unittest\n\n\nclass Falla(unittest.TestCase):\n    def test_falla(self):\n'
            '        self.fail()\n', encoding='utf-8')
        return [sys.executable, '-m', 'unittest', 'discover', '-s', 'pruebas_fallo']

    def test_testing_failure_is_reported(self):
        data = sdd.load(self.folder / 'spec.json')
        data['testing']['commands'] = [self._failing_suite()]
        sdd.dump(self.folder / 'spec.json', data)
        self.assertTrue(any('Comando falló' in x for x in sdd.validate('fix-sesiones', run=True)))

    @unittest.skipUnless(shutil.which('git'), 'git no disponible')
    def test_diff_files_returns_literal_non_ascii_paths(self):
        for command in (['git', 'init'], ['git', 'config', 'core.quotePath', 'true']):
            subprocess.run(command, cwd=sdd.ROOT, check=True, capture_output=True)
        (sdd.ROOT / 'fuera').mkdir()
        (sdd.ROOT / 'fuera' / 'configuración.txt').write_text('x', encoding='utf-8')
        self.assertIn('spec/fix-sesiones/plan.md', sdd.diff_files())
        errors = sdd.validate('fix-sesiones')
        self.assertFalse([x for x in errors if 'plan.md' in x])
        self.assertIn('Archivo modificado fuera de scope: fuera/configuración.txt', errors)

    def test_run_replaces_python_alias_with_current_interpreter(self):
        # AC-06: "python3"/"python" como primer elemento se ejecutan con sys.executable.
        for alias in ('python3', 'python'):
            with self.subTest(alias=alias):
                out = sdd.ROOT / f'interprete-{alias}.txt'
                (sdd.ROOT / 'pruebas' / 'test_alias.py').write_text(
                    'import sys\nimport unittest\n\n\nclass Alias(unittest.TestCase):\n'
                    '    def test_alias(self):\n'
                    f'        open({str(out)!r}, "w", encoding="utf-8").write(sys.executable)\n',
                    encoding='utf-8')
                data = sdd.load(self.folder / 'spec.json')
                data['testing']['commands'] = [[alias, '-m', 'unittest', 'discover', '-s', 'pruebas']]
                sdd.dump(self.folder / 'spec.json', data)
                self.assertEqual(sdd.validate('fix-sesiones', run=True), [])
                self.assertEqual(out.read_text(encoding='utf-8'), sys.executable)

    def _set_testing(self, commands=None, **extra):
        data = sdd.load(self.folder / 'spec.json')
        if commands is not None:
            data['testing']['commands'] = commands
        data['testing'].update(extra)
        sdd.dump(self.folder / 'spec.json', data)

    def _run_captured(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            errors = sdd.validate('fix-sesiones', run=True)
        return errors, out.getvalue(), err.getvalue()

    SUITE = [sys.executable, '-m', 'unittest', 'discover', '-s', 'pruebas']
    NO_TESTS = [sys.executable, '-m', 'unittest', '--help']

    def test_run_counts_and_echoes_suite_output(self):
        # AC-02: suite real con una prueba pasa la puerta y su salida se reproduce.
        errors, out, err = self._run_captured()
        self.assertEqual(errors, [])
        self.assertIn('Ran 1 test', err)
        self.assertIn('EJECUTANDO:', out)

    def test_run_without_test_count_fails(self):
        # AC-03: salir con 0 sin recuento reconocible no pasa la puerta.
        self._set_testing([self.NO_TESTS])
        errors, _, _ = self._run_captured()
        self.assertTrue(any('al menos 1' in e and 'ninguna' in e for e in errors), errors)

    def test_run_enforces_min_tests_threshold(self):
        # AC-04: el recuento debe alcanzar testing.min_tests.
        self._set_testing(min_tests=2)
        errors, _, _ = self._run_captured()
        self.assertTrue(any('al menos 2' in e and 'detectadas: 1' in e for e in errors), errors)
        self._set_testing(min_tests=1)
        errors, _, _ = self._run_captured()
        self.assertEqual(errors, [])

    def test_min_tests_type_is_validated(self):
        # AC-05: min_tests debe ser int (no bool) >= 1; ausente equivale a 1.
        message = 'testing.min_tests debe ser un entero mayor o igual a 1'
        for value in (0, -1, '2', 1.5, True, None):
            with self.subTest(value=value):
                self._set_testing(min_tests=value)
                self.assertIn(message, sdd.validate('fix-sesiones'))
        for value in (1, 5):
            with self.subTest(value=value):
                self._set_testing(min_tests=value)
                self.assertNotIn(message, sdd.validate('fix-sesiones'))
        data = sdd.load(self.folder / 'spec.json')
        data['testing'].pop('min_tests')
        sdd.dump(self.folder / 'spec.json', data)
        self.assertNotIn(message, sdd.validate('fix-sesiones'))

    def test_min_tests_applies_per_command(self):
        # AC-06: un comando con recuento no compensa a otro sin recuento.
        self._set_testing([self.SUITE, self.NO_TESTS])
        errors, _, _ = self._run_captured()
        count_errors = [e for e in errors if 'al menos' in e]
        self.assertEqual(len(count_errors), 1, errors)
        self.assertIn('--help', count_errors[0])

    def test_mutation_command_is_not_counted(self):
        # AC-07: mutation.command se ejecuta sin exigir recuento.
        self._set_testing(mutation={'enabled': True, 'command': self.NO_TESTS, 'reason': 'prueba'})
        errors, out, _ = self._run_captured()
        self.assertEqual(errors, [])
        self.assertIn('--help', out)

    def test_failed_command_has_no_count_error(self):
        # AC-08: un comando que falla solo produce 'Comando falló'.
        self._set_testing([self._failing_suite()])
        errors, _, _ = self._run_captured()
        self.assertTrue(any('Comando falló' in e for e in errors), errors)
        self.assertFalse([e for e in errors if 'al menos' in e], errors)

    def test_count_not_required_after_close(self):
        # AC-09: en proceso se exige el recuento; tras el cierre normal ya no.
        sdd.approve('fix-sesiones', 'spec', 'Humano', 'Sí, aprobada')
        with mock.patch.object(sdd, 'tests_ran', return_value=None):
            errors, _, _ = self._run_captured()
        self.assertTrue(any('al menos 1' in e and 'ninguna' in e for e in errors), errors)
        sdd.review('fix-sesiones', 'APROBADO', 'Comparados diff y pruebas')
        sdd.approve('fix-sesiones', 'close', 'Humano', 'Sí, cerrar tarea')
        self.assertEqual(sdd.load(self.folder / 'spec.json')['state'], 'terminado')
        with mock.patch.object(sdd, 'tests_ran', return_value=None):
            errors, _, _ = self._run_captured()
        self.assertEqual(errors, [])

    DEFAULT_PREFIXES = (
        ['python', '-m', 'unittest'], ['python3', '-m', 'unittest'], ['python', '-m', 'pytest'],
        ['python3', '-m', 'pytest'], ['pytest'], ['npm', 'test'], ['pnpm', 'test'], ['yarn', 'test'],
        ['bun', 'test'], ['go', 'test'], ['cargo', 'test'], ['mvn', 'test'], ['./mvnw', 'test'],
        ['gradle', 'test'], ['./gradlew', 'test'], ['mutmut', 'run'])

    def _whitelist_errors(self, commands=None, **extra):
        self._set_testing(commands, **extra)
        return [e for e in sdd.validate('fix-sesiones') if 'lista blanca' in e or 'allowed_test_commands' in e]

    def _set_allowed(self, value):
        memory = sdd.load(sdd.MEMORY)
        memory['project']['allowed_test_commands'] = value
        sdd.dump(sdd.MEMORY, memory)

    def test_whitelist_accepts_default_prefixes(self):
        # AC-01: los 16 prefijos, con y sin argumentos extra, no generan error de lista blanca.
        self.assertEqual(len(self.DEFAULT_PREFIXES), 16)
        for prefix in self.DEFAULT_PREFIXES:
            for command in (prefix, [*prefix, '-q', './...']):
                with self.subTest(command=command):
                    self.assertEqual(self._whitelist_errors([command]), [])

    def test_whitelist_treats_current_interpreter_as_python(self):
        # AC-02: sys.executable equivale a python; -c sigue rechazado.
        for command in ([sys.executable, '-m', 'unittest', 'discover'], [sys.executable, '-m', 'pytest']):
            with self.subTest(command=command):
                self.assertEqual(self._whitelist_errors([command]), [])
        command = [sys.executable, '-c', 'print(1)']
        self.assertEqual(self._whitelist_errors([command]),
                         [f'Comando de pruebas fuera de la lista blanca: {command}'])

    def test_whitelist_rejects_other_commands(self):
        # AC-03: ejecutables arbitrarios, rutas, mayúsculas y prefijos incompletos se rechazan.
        rejected = (['python', '-c', 'print(1)'], ['python3', '.microharness/sdd.py', '--version'],
                    ['sh', '-c', 'echo x'], ['bash', '-c', 'x'], ['/tmp/evil/python3', '-m', 'unittest'],
                    ['curl', 'https://example.com'], ['py', '-3', '-m', 'unittest'], ['uv', 'run', 'pytest'],
                    ['npm', 'run', 'test'], ['Python', '-m', 'unittest'], ['python', '-m'],
                    ['python', '-m', 'unittestx'])
        for command in rejected:
            with self.subTest(command=command):
                self.assertEqual(self._whitelist_errors([command]),
                                 [f'Comando de pruebas fuera de la lista blanca: {command}'])
        bad = ['sh', '-c', 'echo x']
        self.assertEqual(self._whitelist_errors([self.SUITE, bad, ['pytest']]),
                         [f'Comando de pruebas fuera de la lista blanca: {bad}'])

    def test_whitelist_applies_to_enabled_mutation(self):
        # AC-04: mutation.command se valida solo si está activado.
        bad = ['sh', '-c', 'echo']
        self.assertEqual(self._whitelist_errors(mutation={'enabled': True, 'command': bad, 'reason': 'x'}),
                         [f'Comando de mutación fuera de la lista blanca: {bad}'])
        self.assertEqual(self._whitelist_errors(
            mutation={'enabled': True, 'command': ['mutmut', 'run'], 'reason': 'x'}), [])
        self.assertEqual(self._whitelist_errors(mutation={'enabled': False, 'command': bad, 'reason': 'x'}), [])

    def test_whitelist_project_extension(self):
        # AC-05: la ampliación de memory.json se suma a los predeterminados por prefijo.
        self.assertEqual(self._whitelist_errors([['make', 'test']]),
                         ["Comando de pruebas fuera de la lista blanca: ['make', 'test']"])
        self._set_allowed([['make', 'test']])
        self.assertEqual(self._whitelist_errors([['make', 'test'], ['make', 'test', '-j2'], self.SUITE]), [])
        self.assertEqual(self._whitelist_errors([['make', 'install']]),
                         ["Comando de pruebas fuera de la lista blanca: ['make', 'install']"])

    def test_whitelist_reports_invalid_extension_entries(self):
        # AC-06: cada entrada inválida se reporta y las válidas siguen aplicando.
        self._set_allowed('make test')
        self.assertEqual(self._whitelist_errors([self.SUITE]),
                         ['project.allowed_test_commands inválido: make test'])
        self._set_allowed(['make test', [], [''], [1], ['make', 'test']])
        self.assertEqual(self._whitelist_errors([['make', 'test']]), [
            'project.allowed_test_commands inválido: make test',
            'project.allowed_test_commands inválido: []',
            "project.allowed_test_commands inválido: ['']",
            'project.allowed_test_commands inválido: [1]'])

    def test_whitelist_skipped_after_close(self):
        # AC-07: las tareas terminadas no se validan contra la lista blanca.
        self._set_allowed('x')
        data = sdd.load(self.folder / 'spec.json')
        data['state'] = 'terminado'
        sdd.dump(self.folder / 'spec.json', data)
        self.assertEqual(self._whitelist_errors(
            [['python', '-c', 'print(1)']],
            mutation={'enabled': True, 'command': ['sh', '-c', 'echo'], 'reason': 'x'}), [])

    def test_whitelist_blocks_execution(self):
        # AC-08: un comando fuera de la lista no se ejecuta con --run.
        marker = sdd.ROOT / 'marca.txt'
        command = [sys.executable, '-c', "open('marca.txt','w')"]
        self._set_testing([self.SUITE, command])
        errors, out, _ = self._run_captured()
        self.assertIn(f'Comando de pruebas fuera de la lista blanca: {command}', errors)
        self.assertNotIn('EJECUTANDO:', out)
        self.assertFalse(marker.exists())

    def _write_config(self, text):
        (sdd.MEMORY.parent / 'config.json').write_text(text, encoding='utf-8')

    def _new_spec(self, slug='x'):
        with contextlib.redirect_stdout(io.StringIO()):
            sdd.new(slug)
        return sdd.load(sdd.ROOT / 'spec' / slug / 'spec.json')

    def _set_spec(self, **values):
        data = sdd.load(self.folder / 'spec.json')
        data.update(values)
        sdd.dump(self.folder / 'spec.json', data)

    def _model_errors(self):
        return [e for e in sdd.validate('fix-sesiones') if 'modelo' in e.lower()]

    def _effort_errors(self):
        return [e for e in sdd.validate('fix-sesiones') if 'effort' in e.lower()]

    def test_new_uses_defaults_without_config(self):
        # AC-01: sin config.json se mantienen claude-opus-5-5 y medium.
        self.assertFalse((sdd.MEMORY.parent / 'config.json').exists())
        data = self._new_spec()
        self.assertEqual((data['model'], data['effort']), ('claude-opus-5-5', 'medium'))

    def test_new_uses_configured_values(self):
        # AC-02: valores configurados y, para cada clave ausente, el valor por defecto.
        cases = (('{"model": "claude-prueba-1", "effort": "high"}', ('claude-prueba-1', 'high')),
                 ('{"model": "claude-prueba-1"}', ('claude-prueba-1', 'medium')),
                 ('{"effort": "low"}', ('claude-opus-5-5', 'low')))
        for index, (text, expected) in enumerate(cases):
            with self.subTest(config=text):
                self._write_config(text)
                data = self._new_spec(f'x{index}')
                self.assertEqual((data['model'], data['effort']), expected)

    def test_check_compares_model_with_config(self):
        # AC-03: en pendiente y proceso, spec.model debe coincidir con el configurado.
        self._write_config('{"model": "claude-prueba-1"}')
        for state in ('pendiente', 'proceso'):
            with self.subTest(state=state):
                self._set_spec(state=state, model='claude-opus-5-5')
                errors = self._model_errors()
                self.assertEqual(len(errors), 1, errors)
                for text in ('claude-opus-5-5', 'claude-prueba-1', '.microharness/config.json'):
                    self.assertIn(text, errors[0])
                self._set_spec(model='claude-prueba-1')
                self.assertEqual(self._model_errors(), [])

    def test_check_model_defaults_without_config(self):
        # AC-03: sin config.json el modelo esperado es claude-opus-5-5.
        self._set_spec(model='claude-otro')
        errors = self._model_errors()
        self.assertEqual(len(errors), 1, errors)
        self.assertIn('claude-otro', errors[0])
        self._set_spec(model='claude-opus-5-5')
        self.assertEqual(self._model_errors(), [])

    def test_check_effort_levels(self):
        # AC-04: effort inválido enumera los niveles; uno válido distinto del configurado no es error.
        self._set_spec(effort='ultra')
        errors = self._effort_errors()
        self.assertEqual(len(errors), 1, errors)
        self.assertIn('low, medium, high, xhigh, max', errors[0])
        self._write_config('{"effort": "medium"}')
        self._set_spec(effort='max')
        self.assertEqual(self._effort_errors(), [])

    def test_check_skips_model_for_closed_task(self):
        # AC-05: una tarea terminado no se compara con el modelo configurado.
        sdd.approve('fix-sesiones', 'spec', 'Humano', 'Sí, aprobada')
        sdd.review('fix-sesiones', 'APROBADO', 'Comparados diff y pruebas')
        sdd.approve('fix-sesiones', 'close', 'Humano', 'Sí, cerrar tarea')
        self.assertEqual(sdd.load(self.folder / 'spec.json')['state'], 'terminado')
        self._write_config('{"model": "claude-prueba-1"}')
        self.assertEqual(self._model_errors(), [])

    def _run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, 'argv', ['sdd.py', *argv]), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = sdd.main()
            except SystemExit as e:
                code = e.code
        return code, err.getvalue()

    def test_invalid_config_aborts_new_and_check(self):
        # AC-06: config.json inválido termina con código 1 y ERROR: sin escrituras parciales.
        invalid = ('{', '[]', '{"model": ""}', '{"model": 5}', '{"effort": "ultra"}', '{"efort": "high"}')
        for text in invalid:
            with self.subTest(config=text):
                self._write_config(text)
                before = sdd.MEMORY.read_bytes()
                code, err = self._run_main('new', 'y')
                self.assertEqual(code, 1)
                self.assertRegex(err, r'ERROR: .*config\.json')
                self.assertFalse((sdd.ROOT / 'spec' / 'y').exists())
                self.assertEqual(sdd.MEMORY.read_bytes(), before)
                code, err = self._run_main('check', 'fix-sesiones', '--no-scope')
                self.assertEqual(code, 1)
                self.assertRegex(err, r'ERROR: .*config\.json')


class TestsRanTests(unittest.TestCase):
    def test_recognized_summaries(self):
        # AC-01: casos literales de unittest, pytest, bun, Maven, Go y salidas sin recuento.
        cases = [
            ('Ran 12 tests in 0.1s\nOK\n', 12),
            ('Ran 1 test in 0.0s\n', 1),
            ('Ran 0 tests in 0.000s\n', 0),
            ('==== 5 passed, 1 skipped in 0.2s ====', 5),
            (' 7 pass\n 0 fail\n', 7),
            ('Tests run: 3, Failures: 0\n...\nResults:\nTests run: 9, Failures: 0', 9),
            ('ok  \tej/a\t0.01s\nok  \tej/b\t(cached)\n?   \tej/c\t[no test files]\n', 2),
            ('Ran 1 test in 0.0s\n...\nRan 40 tests in 3.0s\n', 40),
            ('tests ok', None),
            ('', None),
        ]
        for output, expected in cases:
            with self.subTest(output=output):
                self.assertEqual(sdd.tests_ran(output), expected)


class HookTests(unittest.TestCase):
    def test_reviewer_edits_blocked(self):
        hook_path = SCRIPT.parents[1] / '.claude' / 'hooks' / 'pretool.py'
        spec = importlib.util.spec_from_file_location('micro_hook', hook_path)
        hook = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hook)
        self.assertIn('solo lectura', hook.run({'agent_type': 'revisor', 'tool_name': 'Edit', 'tool_input': {}}))
        self.assertIsNone(hook.run({'agent_type': 'revisor', 'tool_name': 'Bash',
                                    'tool_input': {'command': 'python3 .microharness/sdd.py check fix-sesiones --run'}}))
        self.assertIsNotNone(hook.run({'agent_type': 'revisor', 'tool_name': 'Bash',
                                       'tool_input': {'command': 'rm -rf src'}}))

    def test_reviewer_checker_prefixes(self):
        # AC-07: prefijos portables permitidos; encadenamientos y variantes inseguras denegados.
        hook_path = SCRIPT.parents[1] / '.claude' / 'hooks' / 'pretool.py'
        spec = importlib.util.spec_from_file_location('micro_hook', hook_path)
        hook = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hook)
        check = '.microharness/sdd.py check fix-a --run'
        allowed = [
            f'python {check}',
            f'python3 {check}',
            f'py -3 {check}',
            f'sh .microharness/python.sh {check}',
            f"uv run --no-project --quiet --python '>=3.10' {check}",
            f'uv run --no-project {check}',
        ]
        denied = [
            f'sh .microharness/python.sh {check}; rm -rf src',
            f'uv run --no-project --python >=3.10 {check}',
            f'uv run {check}',
            f'sh other.sh {check}',
            'rm -rf src',
            f'sh .microharness/python.sh {check} && rm -rf src',
            f'sh .microharness/python.sh {check}\nrm -rf src',
            f'sh .microharness/python.sh $(rm -rf src) {check}',
            f'uv run --no-project --python `rm -rf src` {check}',
        ]
        for command in allowed:
            with self.subTest(permitido=command):
                self.assertIsNone(hook.run({'agent_type': 'revisor', 'tool_name': 'Bash',
                                            'tool_input': {'command': command}}))
        for command in denied:
            with self.subTest(denegado=command):
                self.assertIsNotNone(hook.run({'agent_type': 'revisor', 'tool_name': 'Bash',
                                               'tool_input': {'command': command}}))

    def test_reviewer_powershell_uses_allowlist(self):
        # AC-01, AC-02: PowerShell aplica la misma allowlist del revisor que Bash.
        hook_path = SCRIPT.parents[1] / '.claude' / 'hooks' / 'pretool.py'
        spec = importlib.util.spec_from_file_location('micro_hook', hook_path)
        hook = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hook)
        self.assertIsNotNone(hook.run({'agent_type': 'revisor', 'tool_name': 'PowerShell',
                                       'tool_input': {'command': 'rm -rf src'}}))
        for command in ('python .microharness/sdd.py check fix-a --run', 'git status'):
            with self.subTest(permitido=command):
                self.assertIsNone(hook.run({'agent_type': 'revisor', 'tool_name': 'PowerShell',
                                            'tool_input': {'command': command}}))

    def test_reviewer_git_allowlist(self):
        # AC-01, AC-02: tokens seguros de git diff/status permitidos; expansión, redirección y escritura denegadas.
        hook_path = SCRIPT.parents[1] / '.claude' / 'hooks' / 'pretool.py'
        spec = importlib.util.spec_from_file_location('micro_hook', hook_path)
        hook = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hook)
        allowed = [
            'git diff',
            'git status',
            'git status --short',
            'git diff --stat',
            'git diff -w -- .microharness/sdd.py',
            'git diff -U0 -- README.md',
            'git diff HEAD~1 -- .claude/hooks/pretool.py',
            'git diff -- spec/x/plan.md',
        ]
        denied = [
            'git diff $(rm -rf src)',
            'git diff `rm -rf src`',
            'git diff > README.md',
            'git status < x',
            'git diff --output=README.md',
            'git diff --output README.md',
            'git diff --ext-diff',
        ]
        for tool in ('Bash', 'PowerShell'):
            for command in allowed:
                with self.subTest(herramienta=tool, comando=command):
                    self.assertIsNone(hook.run({'agent_type': 'revisor', 'tool_name': tool,
                                                'tool_input': {'command': command}}))
            for command in denied:
                with self.subTest(herramienta=tool, comando=command):
                    self.assertIsNotNone(hook.run({'agent_type': 'revisor', 'tool_name': tool,
                                                   'tool_input': {'command': command}}))

    def test_reviewer_git_extra_options(self):
        # AC-01, AC-02: --textconv, -O (también agrupado) y --open-files-in-pager denegados.
        hook_path = SCRIPT.parents[1] / '.claude' / 'hooks' / 'pretool.py'
        spec = importlib.util.spec_from_file_location('micro_hook', hook_path)
        hook = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hook)
        denied = [
            'git diff --textconv',
            'git diff --stat --textconv',
            'git diff -O/tmp/o',
            'git diff -O /tmp/o',
            'git diff -O',
            'git diff -pO/tmp/o',
            'git diff -wO/tmp/o',
            'git diff -U0 -O/tmp/o',
            'git diff --open-files-in-pager',
            'git diff --open-files-in-pager=less',
        ]
        allowed = [
            'git diff',
            'git diff --stat HEAD~1 -- src/app.py',
            'git diff --name-only HEAD',
            'git status --short',
            'git diff --no-textconv',
            'git diff -U0 -- README.md',
            'git diff -- Old.txt',
        ]
        for tool in ('Bash', 'PowerShell'):
            for command in denied:
                with self.subTest(herramienta=tool, comando=command):
                    self.assertIsNotNone(hook.run({'agent_type': 'revisor', 'tool_name': tool,
                                                   'tool_input': {'command': command}}))
            for command in allowed:
                with self.subTest(herramienta=tool, comando=command):
                    self.assertIsNone(hook.run({'agent_type': 'revisor', 'tool_name': tool,
                                                'tool_input': {'command': command}}))

    def test_author_edits_plan_md_not_diseno_md(self):
        # AC-06: el autor escribe plan.md; diseño.md queda denegado.
        hook_path = SCRIPT.parents[1] / '.claude' / 'hooks' / 'pretool.py'
        spec = importlib.util.spec_from_file_location('micro_hook', hook_path)
        hook = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hook)
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)

            def write(name):
                return hook.run({'agent_type': 'autor', 'tool_name': 'Write', 'cwd': str(base),
                                 'tool_input': {'file_path': str(base / 'spec' / 'x' / name)}})
            self.assertIsNone(write('plan.md'))
            self.assertIsNotNone(write('diseño.md'))

    def test_reviewer_checker_ascii_digits(self):
        # AC-03: la versión de Python del checker solo admite dígitos ASCII.
        hook_path = SCRIPT.parents[1] / '.claude' / 'hooks' / 'pretool.py'
        spec = importlib.util.spec_from_file_location('micro_hook', hook_path)
        hook = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hook)
        check = '.microharness/sdd.py check fix-a --run'
        for command in (f'uv run --no-project --python 3.١٠ {check}',
                        f"uv run --no-project --python '>=3.١٠' {check}"):
            with self.subTest(denegado=command):
                self.assertIsNotNone(hook.run({'agent_type': 'revisor', 'tool_name': 'Bash',
                                               'tool_input': {'command': command}}))


@unittest.skipUnless(shutil.which('git'), 'git no disponible')
class GitAttributesTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]

    def test_shell_scripts_checkout_with_lf(self):
        # AC-05: raíz real del repo, no sdd.ROOT (redirigido en MicroSDDTests).
        self.assertTrue((self.ROOT / '.gitattributes').is_file())
        result = subprocess.run(['git', 'check-attr', 'eol', '--', '.microharness/python.sh'],
                                cwd=self.ROOT, capture_output=True, text=True, check=True)
        self.assertTrue(result.stdout.strip().endswith('eol: lf'), result.stdout)

    def test_memory_lock_is_ignored(self):
        # memoria-atomica-lock AC-12: raíz real del repo.
        result = subprocess.run(['git', 'check-ignore', '-q', '.microharness/memory.lock'],
                                cwd=self.ROOT, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0)


class SettingsTests(unittest.TestCase):
    ROOT = SCRIPT.parents[1]

    def pretool_hook(self):
        settings = json.loads((self.ROOT / '.claude' / 'settings.json').read_text(encoding='utf-8'))
        entries = settings['hooks']['PreToolUse']
        self.assertEqual(len(entries), 1)
        self.assertEqual(set(entries[0]['matcher'].split('|')),
                         {'Write', 'Edit', 'MultiEdit', 'NotebookEdit', 'Bash', 'PowerShell'})
        self.assertEqual(len(entries[0]['hooks']), 1)
        return entries[0]['hooks'][0]

    def test_pretool_hook_exec_form_with_uv(self):
        # AC-01: forma exec con uv, sin shell ni python3, y fallo bloqueante.
        hook = self.pretool_hook()
        self.assertEqual(hook['type'], 'command')
        self.assertEqual(hook['command'], 'uv')
        self.assertEqual(hook.get('args'), ['run', '--no-project', '--quiet', '--python', '>=3.10',
                                            '${CLAUDE_PROJECT_DIR}/.claude/hooks/pretool.py'])
        self.assertEqual(hook.get('onFailure'), 'block')

    @unittest.skipUnless(shutil.which('uv'), 'uv no disponible')
    def test_pretool_hook_runs_and_denies_reviewer_edit(self):
        # AC-01 (integración): el comando configurado arranca la guardia y emite la decisión.
        hook = self.pretool_hook()
        project = self.ROOT.as_posix()
        command = [hook['command']] + [a.replace('${CLAUDE_PROJECT_DIR}', project) for a in hook.get('args', [])]
        event = {'agent_type': 'revisor', 'tool_name': 'Edit', 'tool_input': {}}
        result = subprocess.run(command, input=json.dumps(event), capture_output=True, text=True,
                                cwd=self.ROOT, timeout=180)
        self.assertEqual(result.returncode, 0, result.stderr)
        decision = json.loads(result.stdout)
        self.assertEqual(decision['hookSpecificOutput']['permissionDecision'], 'deny')


@unittest.skipUnless(shutil.which('sh'), 'sh no disponible')
class LauncherTests(unittest.TestCase):
    """AC-02..AC-05 y AC-09: lanzador POSIX con PATH controlado, sin uv."""
    LAUNCHER = (SCRIPT.parent / 'python.sh').as_posix()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        self.fake('python3', 'exit 49')  # Simula el stub de Microsoft Store.

    def fake(self, name, body, folder=None):
        path = (folder or self.bin) / name
        path.write_text(f'#!/bin/sh\n{body}\n', encoding='utf-8', newline='\n')
        path.chmod(0o755)
        return path

    def forwarder(self, name='python', folder=None):
        return self.fake(name, f'exec "{Path(sys.executable).as_posix()}" "$@"', folder)

    def launch(self, *args, stdin='', microsdd_python=None):
        env = {k: v for k, v in os.environ.items() if k != 'MICROSDD_PYTHON'}
        env['PATH'] = str(self.bin)
        if microsdd_python is not None:
            env['MICROSDD_PYTHON'] = microsdd_python
        return subprocess.run([shutil.which('sh'), self.LAUNCHER, *args], input=stdin, env=env,
                              capture_output=True, text=True, timeout=60)

    def test_skips_store_stub_and_preserves_streams_and_exit_code(self):
        # AC-02
        self.forwarder()
        result = self.launch('-c', 'import sys; sys.stdout.write(sys.stdin.read().upper()); sys.exit(7)',
                             stdin='hola')
        self.assertEqual(result.stdout, 'HOLA', result.stderr)
        self.assertEqual(result.returncode, 7)

    def test_microsdd_python_has_priority(self):
        # AC-03
        self.fake('python', 'echo MARCADOR-FALSO')
        result = self.launch('-c', 'import sys; print("REAL")', microsdd_python=Path(sys.executable).as_posix())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('REAL', result.stdout)
        self.assertNotIn('MARCADOR-FALSO', result.stdout)

    def test_invalid_microsdd_python_fails_closed(self):
        # AC-04: sin degradar a otro candidato válido.
        self.forwarder()
        other = self.base / 'otro'
        other.mkdir()
        broken = self.fake('python-roto', 'exit 49', other).as_posix()
        for value in (broken, (other / 'inexistente').as_posix()):
            with self.subTest(MICROSDD_PYTHON=value):
                result = self.launch('-c', 'import sys; print("EJECUTADO")', microsdd_python=value)
                self.assertEqual(result.returncode, 2)
                self.assertIn('MICROSDD_PYTHON', result.stderr)
                self.assertNotIn('EJECUTADO', result.stdout)

    def test_no_valid_interpreter_fails_closed(self):
        # AC-05: solo existe el stub de python3.
        result = self.launch('-c', 'import sys; print("EJECUTADO")')
        self.assertEqual(result.returncode, 2)
        self.assertIn('uv', result.stderr)
        self.assertIn('Python', result.stderr)
        self.assertNotIn('EJECUTADO', result.stdout)


class VersionTests(unittest.TestCase):
    def test_version_flag_prints_microsdd_version(self):
        # AC-01: solo lectura del script real.
        result = subprocess.run([sys.executable, str(SCRIPT), '--version'], capture_output=True, text=True,
                                encoding='utf-8', check=False)
        self.assertEqual((result.returncode, result.stdout.strip()), (0, 'MicroSDD 0.1.0'))
        source = SCRIPT.read_text(encoding='utf-8')
        self.assertEqual(len(re.findall(r"^__version__ = '0\.1\.0'\r?$", source, flags=re.M)), 1)


class ReleaseProposeTests(unittest.TestCase):
    def setUp(self):
        self.old_root, self.old_memory = sdd.ROOT, sdd.MEMORY
        self.addCleanup(self.restore)
        self.make_repo()

    def restore(self):
        sdd.ROOT, sdd.MEMORY = self.old_root, self.old_memory

    def make_repo(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        sdd.ROOT = Path(temporary.name).resolve()
        sdd.MEMORY = sdd.ROOT / '.microharness' / 'memory.json'
        self.git('init', '-b', 'main')
        # Aislamiento: nunca operar sobre el repositorio real.
        self.assertEqual(Path(self.git('rev-parse', '--show-toplevel').strip()).resolve(), sdd.ROOT)
        for key, value in (('user.name', 'Prueba'), ('user.email', 'prueba@example.com'),
                           ('commit.gpgsign', 'false'), ('tag.gpgsign', 'false')):
            self.git('config', '--local', key, value)
        self.write_version('0.1.0')
        (sdd.ROOT / 'README.md').write_text('# Proyecto\n', encoding='utf-8')
        with contextlib.redirect_stdout(io.StringIO()):
            sdd.ensure_init()
        self.git('add', '-A')
        self.git('commit', '-m', 'chore: inicial')

    def git(self, *args):
        result = subprocess.run(['git', '-c', 'core.quotePath=false', *args], cwd=sdd.ROOT, capture_output=True,
                                text=True, encoding='utf-8', check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def write_version(self, version):
        path = sdd.ROOT / '.microharness' / 'sdd.py'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"__version__ = '{version}'\n", encoding='utf-8')

    def commit(self, *subjects):
        for subject in subjects:
            self.git('commit', '--allow-empty', '-m', subject)

    def new_task(self, slug, state='pendiente'):
        with contextlib.redirect_stdout(io.StringIO()):
            sdd.new(slug)
        path = sdd.ROOT / 'spec' / slug / 'spec.json'
        data = sdd.load(path)
        data['state'] = state
        sdd.dump(path, data)

    def snapshot(self):
        return (self.git('status', '--porcelain', '--untracked-files=all'), self.git('tag'),
                self.git('rev-parse', 'HEAD'))

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, 'argv', ['sdd.py', *argv]), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = sdd.main()
            except SystemExit as e:
                code = e.code
        return code, out.getvalue(), err.getvalue()

    def propose(self):
        # AC-07: ninguna ejecución altera estado, tags ni HEAD.
        before = self.snapshot()
        result = self.run_main('release', 'propose')
        self.assertEqual(self.snapshot(), before)
        return result

    def assert_proposed(self, expected):
        code, out, err = self.propose()
        self.assertEqual(code, 0, err)
        self.assertIn(f'Versión propuesta: {expected}', out.splitlines())
        return out.splitlines()

    def assert_rejected(self):
        code, out, err = self.propose()
        self.assertEqual(code, 1, out + err)
        self.assertIn('ERROR', err)
        self.assertNotIn('Versión propuesta', out)
        return err

    # AC-02: fase 0.y.z.
    def test_zero_major_fix_feat_perf_bump_patch(self):
        for subject in ('fix: corrige x', 'feat: añade x', 'perf: acelera x'):
            with self.subTest(subject=subject):
                self.make_repo()
                self.git('tag', 'v0.1.0')
                self.commit(subject)
                self.assertIn('Último tag: v0.1.0', self.assert_proposed('0.1.1'))

    def test_zero_major_breaking_bumps_minor(self):
        self.git('tag', 'v0.1.0')
        self.commit('fix: corrige x', 'feat: añade y', 'docs!: x')
        lines = self.assert_proposed('0.2.0')
        self.assertIn('Incompatible: docs!: x', lines)
        self.assertIn('Añadido: feat: añade y', lines)
        self.assertIn('Corregido: fix: corrige x', lines)

    def test_rc_tag_is_not_base(self):
        self.git('tag', 'v0.1.0')
        self.commit('fix: corrige x')
        self.git('tag', 'v0.2.0-rc.1')
        self.commit('fix: corrige y')
        self.assertIn('Último tag: v0.1.0', self.assert_proposed('0.1.1'))

    def test_other_types_grouped_as_otros(self):
        self.git('tag', 'v0.1.0')
        others = ('docs: guía', 'test: casos', 'refactor: limpia', 'chore: tareas', 'arreglos varios')
        self.commit(*others, 'fix: corrige x')
        lines = self.assert_proposed('0.1.1')
        for subject in others:
            self.assertIn(f'Otros: {subject}', lines)

    def test_subject_with_enye_printed_unchanged(self):
        self.git('tag', 'v0.1.0')
        self.commit('fix: corrige la contraseña del año')
        self.assertIn('Corregido: fix: corrige la contraseña del año', self.assert_proposed('0.1.1'))

    # AC-03: fase >= 1.0.0.
    def test_stable_increments(self):
        cases = ((('fix: x',), '1.2.4'), (('perf: x',), '1.2.4'), (('feat: x',), '1.3.0'),
                 (('refactor!: x',), '2.0.0'), (('fix: a', 'feat: b'), '1.3.0'),
                 (('feat: a', 'refactor!: b', 'fix: c'), '2.0.0'))
        for subjects, expected in cases:
            with self.subTest(subjects=subjects):
                self.make_repo()
                self.git('tag', 'v1.2.3')
                self.commit(*subjects)
                self.assert_proposed(expected)

    def test_highest_final_tag_is_base(self):
        self.git('tag', 'v1.2.3')
        self.commit('fix: a')
        self.git('tag', 'v1.10.0')
        self.commit('fix: b')
        self.assertIn('Último tag: v1.10.0', self.assert_proposed('1.10.1'))

    # AC-04: sin tags.
    def test_without_tags_uses_version_constant(self):
        self.commit('feat: a', 'feat: b')
        self.assertIn('Último tag: (ninguno)', self.assert_proposed('0.1.0'))

    def test_without_tags_strips_rc_suffix(self):
        self.write_version('0.1.0-rc.1')
        self.git('add', '-A')
        self.commit('feat: candidata')
        self.assertIn('Último tag: (ninguno)', self.assert_proposed('0.1.0'))

    # AC-05.
    def test_no_increment_fails(self):
        self.git('tag', 'v0.1.0')
        self.commit('docs: a', 'test: b', 'refactor: c', 'chore: d', 'arreglos')
        self.assertIn('sin incremento', self.assert_rejected())

    # AC-06.
    def test_rejects_branch_other_than_main(self):
        self.git('tag', 'v0.1.0')
        self.commit('fix: a')
        self.git('checkout', '-b', 'otra')
        self.assertIn('main', self.assert_rejected())

    def test_rejects_task_in_proceso(self):
        self.git('tag', 'v0.1.0')
        self.commit('fix: a')
        self.new_task('otra-tarea', 'proceso')
        self.assertIn('proceso', self.assert_rejected())

    def test_rejects_modified_tracked_file(self):
        self.git('tag', 'v0.1.0')
        self.commit('fix: a')
        (sdd.ROOT / 'README.md').write_text('# Cambiado\n', encoding='utf-8')
        self.assert_rejected()

    def test_rejects_untracked_file(self):
        self.git('tag', 'v0.1.0')
        self.commit('fix: a')
        (sdd.ROOT / 'nuevo.txt').write_text('x\n', encoding='utf-8')
        self.assert_rejected()

    def test_allows_changes_in_spec_and_memory(self):
        self.git('tag', 'v0.1.0')
        self.commit('fix: a')
        self.new_task('release-v0-1-1')
        self.git('add', '-A')
        self.git('commit', '-m', 'chore: specs')
        (sdd.ROOT / 'spec' / 'release-v0-1-1' / 'plan.md').write_text('# CÓMO\nSin commit.\n', encoding='utf-8')
        (sdd.ROOT / 'spec' / 'release-v0-1-1' / 'notas-año.md').write_text('nuevo\n', encoding='utf-8')
        memory = sdd.load(sdd.MEMORY)
        memory['project']['observations'].append('cambio sin commit')
        sdd.dump(sdd.MEMORY, memory)
        status = self.git('status', '--porcelain', '--untracked-files=all')
        self.assertIn(' M spec/release-v0-1-1/plan.md', status)
        self.assertIn(' M .microharness/memory.json', status)
        self.assertIn('?? spec/release-v0-1-1/notas-año.md', status)
        self.assert_proposed('0.1.1')

    def test_rejects_rename_from_outside_into_spec(self):
        self.git('tag', 'v0.1.0')
        self.commit('fix: a')
        self.git('mv', 'README.md', 'spec/README.md')
        self.assertIn('R  README.md -> spec/README.md', self.git('status', '--porcelain'))
        self.assert_rejected()

    def test_allows_new_file_with_spaces_in_spec(self):
        self.git('tag', 'v0.1.0')
        self.commit('fix: a')
        self.new_task('release-v0-1-1')
        self.git('add', '-A')
        self.git('commit', '-m', 'chore: specs')
        (sdd.ROOT / 'spec' / 'release-v0-1-1' / 'nota con espacios.md').write_text('nuevo\n', encoding='utf-8')
        self.assertIn('spec/release-v0-1-1/nota con espacios.md', self.git('status', '--porcelain', '--untracked-files=all'))
        self.assert_proposed('0.1.1')

    # memoria-atomica-lock AC-13.
    def test_tolerates_untracked_memory_lock(self):
        self.git('tag', 'v0.1.0')
        self.git('rm', '--cached', '-q', '--ignore-unmatch', '.microharness/memory.lock')
        self.commit('fix: a')
        (sdd.ROOT / '.microharness' / 'memory.lock').touch()
        self.assertIn('?? .microharness/memory.lock', self.git('status', '--porcelain', '--untracked-files=all'))
        self.assert_proposed('0.1.1')

    def test_rejects_other_untracked_file_in_microharness(self):
        self.git('tag', 'v0.1.0')
        self.commit('fix: a')
        (sdd.ROOT / '.microharness' / 'otro.txt').write_text('x\n', encoding='utf-8')
        self.assertIn('.microharness/otro.txt', self.assert_rejected())

    # AC-07.
    def test_release_without_action_is_usage_error(self):
        code, out, err = self.run_main('release')
        self.assertEqual(code, 2)
        self.assertIn('propose', err)


class NoteTests(unittest.TestCase):
    FIXED = '2026-01-02T03:04:05+00:00'

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.old_root, self.old_memory = sdd.ROOT, sdd.MEMORY
        self.addCleanup(self.restore)
        sdd.ROOT = Path(temporary.name)
        sdd.MEMORY = sdd.ROOT / '.microharness' / 'memory.json'
        self.initial = {
            'schema_version': 1,
            'project': {
                'observations': [{'at': '2025-01-01T00:00:00+00:00', 'fact': 'previo', 'evidence': 'x'}],
                'decisions': [{'at': '2025-01-01T00:00:00+00:00', 'by': 'H', 'decision': 'previa', 'evidence': 'y'}],
            },
            'tasks': {'demo': {'review': None, 'events': []}},
        }
        sdd.dump(sdd.MEMORY, self.initial)
        patcher = mock.patch.object(sdd, 'now', return_value=self.FIXED)
        patcher.start()
        self.addCleanup(patcher.stop)

    def restore(self):
        sdd.ROOT, sdd.MEMORY = self.old_root, self.old_memory

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, 'argv', ['sdd.py', 'note', *argv]), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = sdd.main()
            except SystemExit as e:
                code = e.code
        return code, out.getvalue(), err.getvalue()

    # AC-01, AC-03, AC-04.
    def test_fact_appends_observation(self):
        code, out, err = self.run_main('--fact', 'F', '--evidence', 'E')
        self.assertEqual(code, 0, err)
        self.assertTrue(out.strip())
        data = sdd.load(sdd.MEMORY)
        self.assertEqual(data['project']['observations'][-1], {'at': self.FIXED, 'fact': 'F', 'evidence': 'E'})
        self.assertRegex(data['project']['observations'][-1]['at'], r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$')
        self.assertEqual(data['project']['observations'][:-1], self.initial['project']['observations'])
        self.assertEqual(data['project']['decisions'], self.initial['project']['decisions'])
        self.assertEqual((data['tasks'], data['schema_version']), (self.initial['tasks'], 1))

    # AC-02, AC-03, AC-04.
    def test_decision_appends_decision(self):
        code, out, err = self.run_main('--decision', 'D', '--by', 'Programador', '--evidence', 'E')
        self.assertEqual(code, 0, err)
        self.assertTrue(out.strip())
        data = sdd.load(sdd.MEMORY)
        self.assertEqual(data['project']['decisions'][-1],
                         {'at': self.FIXED, 'by': 'Programador', 'decision': 'D', 'evidence': 'E'})
        self.assertEqual(data['project']['decisions'][:-1], self.initial['project']['decisions'])
        self.assertEqual(data['project']['observations'], self.initial['project']['observations'])
        self.assertEqual((data['tasks'], data['schema_version']), (self.initial['tasks'], 1))

    def assert_rejected(self, *argv):
        before = sdd.MEMORY.read_bytes()
        code, out, err = self.run_main(*argv)
        self.assertEqual(code, 1, (argv, out, err))
        self.assertIn('ERROR:', err)
        self.assertEqual(sdd.MEMORY.read_bytes(), before)

    # AC-05.
    def test_rejects_both_or_neither(self):
        self.assert_rejected('--fact', 'F', '--decision', 'D', '--by', 'P', '--evidence', 'E')
        self.assert_rejected('--evidence', 'E')

    # AC-06.
    def test_rejects_blank_texts(self):
        self.assert_rejected('--fact', '  ', '--evidence', 'E')
        self.assert_rejected('--decision', '', '--by', 'P', '--evidence', 'E')
        self.assert_rejected('--decision', 'D', '--by', '  ', '--evidence', 'E')
        self.assert_rejected('--fact', 'F', '--evidence', ' ')

    # AC-07.
    def test_rejects_missing_or_extra_by(self):
        self.assert_rejected('--decision', 'D', '--evidence', 'E')
        self.assert_rejected('--fact', 'F', '--by', 'X', '--evidence', 'E')

    # AC-08.
    def test_creates_memory_when_missing(self):
        sdd.MEMORY.unlink()
        code, out, err = self.run_main('--fact', 'F', '--evidence', 'E')
        self.assertEqual(code, 0, err)
        data = sdd.load(sdd.MEMORY)
        self.assertEqual(data['tasks'], {})
        self.assertEqual(data['project']['decisions'], [])
        self.assertEqual(data['project']['observations'], [{'at': self.FIXED, 'fact': 'F', 'evidence': 'E'}])

    # AC-08.
    def test_creates_missing_project_structure(self):
        for broken in ({'schema_version': 1, 'project': {'observations': []}, 'tasks': self.initial['tasks']},
                       {'schema_version': 1, 'tasks': self.initial['tasks']}):
            sdd.dump(sdd.MEMORY, broken)
            code, out, err = self.run_main('--decision', 'D', '--by', 'P', '--evidence', 'E')
            self.assertEqual(code, 0, err)
            data = sdd.load(sdd.MEMORY)
            self.assertEqual(data['project']['decisions'], [{'at': self.FIXED, 'by': 'P', 'decision': 'D', 'evidence': 'E'}])
            self.assertEqual(data['tasks'], self.initial['tasks'])

    # AC-09.
    def test_invalid_json_unchanged(self):
        sdd.MEMORY.write_text('no es json {', encoding='utf-8')
        self.assert_rejected('--fact', 'F', '--evidence', 'E')


class MemoryAtomicLockTests(unittest.TestCase):
    """memoria-atomica-lock: dump atómico y lock de las mutaciones de memoria."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.old_root, self.old_memory = sdd.ROOT, sdd.MEMORY
        self.addCleanup(self.restore)
        sdd.ROOT = Path(temporary.name).resolve()
        sdd.MEMORY = sdd.ROOT / '.microharness' / 'memory.json'
        self.lock_path = sdd.MEMORY.parent / 'memory.lock'

    def restore(self):
        sdd.ROOT, sdd.MEMORY = self.old_root, self.old_memory

    def quiet(self, func, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            return func(*args)

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, 'argv', ['sdd.py', *argv]), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = sdd.main()
            except SystemExit as e:
                code = e.code
        return code, out.getvalue(), err.getvalue()

    def set_timeout(self, value):
        missing = object()
        old = getattr(sdd, 'LOCK_TIMEOUT', missing)
        sdd.LOCK_TIMEOUT = value
        self.addCleanup(lambda: delattr(sdd, 'LOCK_TIMEOUT') if old is missing else setattr(sdd, 'LOCK_TIMEOUT', old))

    def hold_lock(self):
        import fcntl
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = open(self.lock_path, 'a+b')
        self.addCleanup(handle.close)
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        return handle

    def assert_lock_free(self):
        import fcntl
        with open(self.lock_path, 'a+b') as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)  # lanza si sigue retenido
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def make_task(self, slug='tarea'):
        self.quiet(sdd.new, slug)
        path = sdd.ROOT / 'spec' / slug / 'spec.json'
        data = sdd.load(path)
        data['testing']['protected_tests'] = ['tests/t.py']
        sdd.dump(path, data)
        (sdd.ROOT / 'tests').mkdir(exist_ok=True)
        (sdd.ROOT / 'tests' / 't.py').write_text('x = 1\n', encoding='utf-8')
        return path

    @staticmethod
    def expected_bytes(data):
        # Bytes de la implementación anterior (write_text), con la traducción de saltos de la plataforma.
        with tempfile.TemporaryDirectory() as folder:
            control = Path(folder) / 'control.json'
            control.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            return control.read_bytes()

    # AC-01.
    def test_dump_replaces_atomically_with_same_bytes(self):
        folder = sdd.ROOT / 'd'
        folder.mkdir()
        target = folder / 'm.json'
        target.write_text('{"viejo": 1}\n', encoding='utf-8')
        data = {'nuevo': True, 'texto': 'año ñ'}
        with mock.patch.object(os, 'replace', side_effect=os.replace) as replace, \
                mock.patch.object(os, 'fsync', side_effect=os.fsync) as fsync:
            sdd.dump(target, data)
        self.assertEqual(replace.call_count, 1)
        source, destination = replace.call_args.args
        self.assertEqual(Path(source).parent, folder)
        self.assertEqual(Path(destination), target)
        self.assertGreaterEqual(fsync.call_count, 1)
        self.assertEqual(target.read_bytes(), self.expected_bytes(data))
        self.assertEqual(os.listdir(folder), ['m.json'])

    # AC-02.
    def test_dump_failure_keeps_previous_content(self):
        for name in ('replace', 'fsync'):
            for existed in (True, False):
                with self.subTest(fails=name, existed=existed):
                    folder = sdd.ROOT / f'{name}-{existed}'
                    folder.mkdir()
                    target = folder / 'm.json'
                    if existed:
                        target.write_text('{"viejo": 1}\n', encoding='utf-8')
                        before = target.read_bytes()
                    with mock.patch.object(os, name, side_effect=OSError('simulado')), \
                            self.assertRaises(OSError):
                        sdd.dump(target, {'nuevo': True})
                    if existed:
                        self.assertEqual(target.read_bytes(), before)
                        self.assertEqual(os.listdir(folder), ['m.json'])
                    else:
                        self.assertFalse(target.exists())
                        self.assertEqual(os.listdir(folder), [])

    # AC-03.
    def test_cli_note_with_failing_replace(self):
        self.quiet(sdd.ensure_init)
        before = sdd.MEMORY.read_bytes()
        with mock.patch.object(os, 'replace', side_effect=OSError('simulado')):
            code, out, err = self.run_main('note', '--fact', 'x', '--evidence', 'y')
        self.assertEqual(code, 1, out + err)
        self.assertIn('ERROR:', err)
        self.assertEqual(sdd.MEMORY.read_bytes(), before)
        self.assertEqual([n for n in os.listdir(sdd.MEMORY.parent) if n.endswith('.tmp')], [])

    # AC-04.
    @unittest.skipIf(os.name == 'nt', 'permisos POSIX')
    def test_dump_preserves_existing_mode(self):
        target = sdd.ROOT / 'm.json'
        target.write_text('{}\n', encoding='utf-8')
        os.chmod(target, 0o640)
        sdd.dump(target, {'nuevo': True})
        self.assertEqual(target.stat().st_mode & 0o777, 0o640)

    @unittest.skipIf(os.name == 'nt', 'permisos POSIX')
    def test_dump_new_file_uses_umask(self):
        for mask, expected in ((0o022, 0o644), (0o027, 0o640)):
            with self.subTest(umask=oct(mask)):
                old = os.umask(mask)
                try:
                    target = sdd.ROOT / f'nuevo-{mask:o}.json'
                    sdd.dump(target, {'nuevo': True})
                finally:
                    os.umask(old)
                self.assertEqual(target.stat().st_mode & 0o777, expected)

    # AC-05.
    def test_dump_ignores_directory_fsync_error(self):
        folder = sdd.ROOT / 'd'
        folder.mkdir()
        target = folder / 'm.json'
        real_open, attempts = os.open, []

        def fake_open(path, *args, **kwargs):
            # R-09: solo falla la apertura del directorio; mkstemp usa el os.open real.
            if os.fspath(path) == os.fspath(folder):
                attempts.append(path)
                raise OSError('simulado')
            return real_open(path, *args, **kwargs)

        with mock.patch.object(os, 'open', side_effect=fake_open):
            sdd.dump(target, {'nuevo': True})
        self.assertEqual(sdd.load(target), {'nuevo': True})
        if os.name != 'nt':
            self.assertEqual(len(attempts), 1)

    # AC-06.
    @unittest.skipIf(os.name == 'nt', 'fcntl solo en POSIX')
    def test_held_lock_blocks_mutations(self):
        spec_path = self.make_task()
        self.hold_lock()
        self.set_timeout(0.2)
        operations = {
            'ensure_init': lambda: sdd.ensure_init(),
            'new': lambda: sdd.new('otra'),
            'approve': lambda: sdd.approve('tarea', 'spec', 'P', 'ok'),
            'review': lambda: sdd.review('tarea', 'RECHAZADO', 'ev'),
            'seal': lambda: sdd.seal('tarea', 'P'),
            'note': lambda: sdd.note('f', None, None, 'e'),
        }
        for name, operation in operations.items():
            with self.subTest(operation=name):
                memory, spec_bytes = sdd.MEMORY.read_bytes(), spec_path.read_bytes()
                with contextlib.redirect_stdout(io.StringIO()), \
                        self.assertRaisesRegex(ValueError, r'memory\.lock'):
                    operation()
                self.assertEqual(sdd.MEMORY.read_bytes(), memory)
                self.assertEqual(spec_path.read_bytes(), spec_bytes)
                self.assertFalse((sdd.ROOT / 'spec' / 'otra').exists())
        code, out, err = self.run_main('note', '--fact', 'f', '--evidence', 'e')
        self.assertEqual(code, 1, out + err)
        self.assertIn('ERROR:', err)
        self.assertIn('memory.lock', err)

    # AC-07.
    @unittest.skipIf(os.name == 'nt', 'fcntl solo en POSIX')
    def test_waits_until_lock_released(self):
        import fcntl
        self.quiet(sdd.ensure_init)
        handle = self.hold_lock()
        self.set_timeout(5)
        timer = threading.Timer(0.2, fcntl.flock, (handle.fileno(), fcntl.LOCK_UN))
        self.addCleanup(timer.cancel)
        start = time.monotonic()
        timer.start()
        code, out, err = self.run_main('note', '--fact', 'esperada', '--evidence', 'e')
        elapsed = time.monotonic() - start
        timer.join()
        self.assertEqual(code, 0, err)
        self.assertGreaterEqual(elapsed, 0.15)
        self.assertEqual(sdd.load(sdd.MEMORY)['project']['observations'][-1]['fact'], 'esperada')

    # AC-08.
    def test_lock_is_reentrant(self):
        self.set_timeout(0.2)
        with sdd.memory_lock():
            self.quiet(sdd.note, 'f', None, None, 'e')
            self.quiet(sdd.new, 'anidada')
        self.assertTrue((sdd.ROOT / 'spec' / 'anidada' / 'spec.json').is_file())
        self.assertEqual(sdd.load(sdd.MEMORY)['project']['observations'][-1]['fact'], 'f')

    # AC-09.
    @unittest.skipIf(os.name == 'nt', 'fcntl solo en POSIX')
    def test_lock_released_after_error_and_success(self):
        self.make_task()
        self.set_timeout(0.2)
        with self.assertRaises(ValueError):
            sdd.approve('tarea', 'spec', 'P', '  ')
        self.assert_lock_free()
        self.quiet(sdd.note, 'f', None, None, 'e')
        self.assert_lock_free()
        self.hold_lock()
        with self.assertRaisesRegex(ValueError, r'memory\.lock'):
            sdd.note('g', None, None, 'e')

    # AC-10.
    def test_lock_file_follows_redirected_memory(self):
        self.quiet(sdd.ensure_init)
        self.assertTrue(self.lock_path.is_file())
        self.assertTrue(self.lock_path.resolve().is_relative_to(sdd.ROOT))

    # AC-11.
    @unittest.skipIf(os.name == 'nt', 'fcntl solo en POSIX')
    def test_check_does_not_wait_for_lock(self):
        self.make_task()
        expected = self.run_main('check', 'tarea', '--no-scope')[0]
        self.hold_lock()
        self.set_timeout(5)
        start = time.monotonic()
        code, out, err = self.run_main('check', 'tarea', '--no-scope')
        self.assertLess(time.monotonic() - start, 2)
        self.assertEqual(code, expected, err)


if __name__ == '__main__':
    unittest.main()
