import contextlib
import importlib.util
import io
import json
import re
import subprocess
import sys
import tempfile
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
        data['testing']['commands'] = [[sys.executable, '-c', 'print("tests ok")']]
        sdd.dump(self.folder / 'spec.json', data)
        (self.folder / 'requerimientos.md').write_text(
            '# QUÉ\nWHEN expire una sesión, THE sistema SHALL rechazar credenciales vencidas.\n'
            'AC-01: token vencido produce 401.\n## Fuera de alcance\nNo renovar tokens.\n', encoding='utf-8')
        (self.folder / 'diseño.md').write_text('# CÓMO\nComprobar expiración en validador existente.\n', encoding='utf-8')
        (self.folder / 'tareas.md').write_text('# PASOS\n- [ ] T01 (AC-01): prueba de expiración.\n', encoding='utf-8')

    def restore(self):
        sdd.ROOT, sdd.MEMORY = self.old_root, self.old_memory

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
        (sdd.ROOT / 'spec' / 'release-v0-1-1' / 'diseño.md').write_text('# CÓMO\nSin commit.\n', encoding='utf-8')
        (sdd.ROOT / 'spec' / 'release-v0-1-1' / 'notas-año.md').write_text('nuevo\n', encoding='utf-8')
        memory = sdd.load(sdd.MEMORY)
        memory['project']['observations'].append('cambio sin commit')
        sdd.dump(sdd.MEMORY, memory)
        status = self.git('status', '--porcelain', '--untracked-files=all')
        self.assertIn(' M spec/release-v0-1-1/diseño.md', status)
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

    # AC-07.
    def test_release_without_action_is_usage_error(self):
        code, out, err = self.run_main('release')
        self.assertEqual(code, 2)
        self.assertIn('propose', err)


if __name__ == '__main__':
    unittest.main()
