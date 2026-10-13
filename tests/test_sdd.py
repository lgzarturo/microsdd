import importlib.util
import json
import os
import shutil
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

    @unittest.skipUnless(shutil.which('git'), 'git no disponible')
    def test_diff_files_returns_literal_non_ascii_paths(self):
        for command in (['git', 'init'], ['git', 'config', 'core.quotePath', 'true']):
            subprocess.run(command, cwd=sdd.ROOT, check=True, capture_output=True)
        (sdd.ROOT / 'fuera').mkdir()
        (sdd.ROOT / 'fuera' / 'configuración.txt').write_text('x', encoding='utf-8')
        self.assertIn('spec/fix-sesiones/diseño.md', sdd.diff_files())
        errors = sdd.validate('fix-sesiones')
        self.assertFalse([x for x in errors if 'diseño.md' in x])
        self.assertIn('Archivo modificado fuera de scope: fuera/configuración.txt', errors)

    def test_run_replaces_python_alias_with_current_interpreter(self):
        # AC-06: "python3"/"python" como primer elemento se ejecutan con sys.executable.
        for alias in ('python3', 'python'):
            with self.subTest(alias=alias):
                out = sdd.ROOT / f'interprete-{alias}.txt'
                code = f'import sys; open({str(out)!r}, "w", encoding="utf-8").write(sys.executable)'
                data = sdd.load(self.folder / 'spec.json')
                data['testing']['commands'] = [[alias, '-c', code]]
                sdd.dump(self.folder / 'spec.json', data)
                self.assertEqual(sdd.validate('fix-sesiones', run=True), [])
                self.assertEqual(out.read_text(encoding='utf-8'), sys.executable)


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


class SettingsTests(unittest.TestCase):
    ROOT = SCRIPT.parents[1]

    def pretool_hook(self):
        settings = json.loads((self.ROOT / '.claude' / 'settings.json').read_text(encoding='utf-8'))
        entries = settings['hooks']['PreToolUse']
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['matcher'], 'Write|Edit|MultiEdit|NotebookEdit|Bash')
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


if __name__ == '__main__':
    unittest.main()
