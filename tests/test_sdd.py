import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
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
        data['testing']['commands'] = [[sys.executable, '-c', 'print("tests ok")']]
        sdd.dump(self.folder / 'spec.json', data)
        (self.folder / 'requerimientos.md').write_text(
            '# QUÉ\nWHEN expire una sesión, THE sistema SHALL rechazar credenciales vencidas.\n'
            'AC-01: token vencido produce 401.\n## Fuera de alcance\nNo renovar tokens.\n', encoding='utf-8')
        (self.folder / 'diseño.md').write_text('# CÓMO\nComprobar expiración en validador existente.\n', encoding='utf-8')
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
        (sdd.ROOT / 'spec' / 'x' / 'diseño.md').write_text('# CÓMO\n', encoding='utf-8')
        files = [f for f in sdd.diff_files() if f.startswith(('spec/x/', 'src/'))]
        self.assertEqual(files, ['spec/x/diseño.md', 'src/módulo.py'])
        for name in files:
            self.assertTrue((sdd.ROOT / name).is_file(), name)

    def test_scope_ignores_uncommitted_task_design(self):
        self.git_repo({'src/app.py': 'x = 1\n'})
        errors = sdd.validate('fix-sesiones')
        self.assertFalse([e for e in errors if 'fuera de scope' in e and 'fix-sesiones/dise' in e], errors)

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

    def test_slug_traversal_rejected(self):
        with self.assertRaises(ValueError):
            sdd.task_dir('../secret')

    def test_spec_approval_and_fingerprint(self):
        sdd.approve('fix-sesiones', 'spec', 'Humano', 'Aprobado textualmente en la sesión')
        self.assertEqual(sdd.validate('fix-sesiones'), [])
        (self.folder / 'diseño.md').write_text('CAMBIO SIN APROBACIÓN', encoding='utf-8')
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

    def test_conventional_commit_message(self):
        sdd.commit_check('fix(auth): valida expiración de sesión')
        with self.assertRaises(ValueError):
            sdd.commit_check('arreglos')

    def test_testing_failure_is_reported(self):
        data = sdd.load(self.folder / 'spec.json')
        data['testing']['commands'] = [[sys.executable, '-c', 'raise SystemExit(1)']]
        sdd.dump(self.folder / 'spec.json', data)
        self.assertTrue(any('Comando falló' in x for x in sdd.validate('fix-sesiones', run=True)))


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


if __name__ == '__main__':
    unittest.main()
