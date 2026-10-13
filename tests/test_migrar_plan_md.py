import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / 'scripts' / 'migrar_plan_md.py'
SDD = REPO / '.microharness' / 'sdd.py'
spec = importlib.util.spec_from_file_location('micro_sdd_migracion', SDD)
sdd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdd)

REQS = '# QUÉ: requisitos\nWHEN se migre la tarea, THE script SHALL conservar la aprobación.\nAC-01: la huella migrada valida.\n'
PLAN = '# CÓMO: diseño mínimo\nRecalcular la huella con el nombre nuevo.\n'
TAREAS = '# PASOS\n- [x] T01 (AC-01): migrar la huella.\n'

# Huellas del esquema antiguo (nombre diseño.md). Origen: spec_fingerprint de .microharness/sdd.py
# en el commit 61bd1ee (`git show 61bd1ee:.microharness/sdd.py`), calculada antes de cambiar sdd.py
# sobre spec_data(slug) y REQS, PLAN y TAREAS escritos en LF, con PLAN guardado como diseño.md.
OLD = {'tarea-uno': '0a076e8005a91b0a8f545df8523f795e8102883f1983f130871982d6ae104ffe',
       'tarea-dos': 'ccd0fb89ccba75db4a5aab00ddc7b060fd21a9a346a23620cfcf87f3f48111f6'}
APPROVED = tuple(OLD)
PENDING = 'tarea-tres'
EVENT = 'migración_plan_md'


def spec_data(slug, state='terminado'):
    return {'schema_version': 1, 'id': slug, 'title': 'Tarea ficticia', 'state': state,
            'model': 'claude-opus-5-5', 'effort': 'medium', 'max_iterations': 3,
            'method': {'primary': 'SDD', 'optional': [], 'notes': ''},
            'scope': {'allowed_paths': ['src/**'], 'excluded': []},
            'requirements': {'acceptance_ids': ['AC-01'], 'preconditions': []},
            'testing': {'strategy': 'tdd', 'commands': [['python', '-m', 'unittest']], 'protected_tests': [],
                        'mutation': {'enabled': False, 'command': [], 'reason': 'No aplica.'}}}


def approved_memory(slug):
    return {'approvals': {'spec': {'by': 'Humano', 'evidence': 'Aprobada en la sesión',
                                   'at': '2026-01-01T00:00:00+00:00', 'fingerprint': OLD[slug]},
                          'close': {'by': 'Humano', 'evidence': 'Cerrar', 'at': '2026-01-02T00:00:00+00:00'}},
            'sealed_tests': {'tests/test_x.py': 'a' * 64}, 'review': 'APROBADO', 'review_fingerprint': 'b' * 64,
            'iterations': 1, 'events': [{'at': '2026-01-01T00:00:00+00:00', 'event': 'creada'}]}


def snapshot(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}


class MigrarPlanMdTests(unittest.TestCase):
    def setUp(self):
        self.old_root, self.old_memory = sdd.ROOT, sdd.MEMORY
        self.addCleanup(self.restore)

    def restore(self):
        sdd.ROOT, sdd.MEMORY = self.old_root, self.old_memory

    def make_repo(self):
        # Repositorio temporal: dos tareas aprobadas con huella del esquema antiguo y una sin aprobación.
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        sdd.ROOT = Path(temporary.name).resolve()
        sdd.MEMORY = sdd.ROOT / '.microharness' / 'memory.json'
        tasks = {slug: approved_memory(slug) for slug in APPROVED}
        tasks[PENDING] = {'approvals': {'spec': None, 'close': None}, 'sealed_tests': {}, 'review': None,
                          'review_fingerprint': None, 'iterations': 0,
                          'events': [{'at': '2026-01-01T00:00:00+00:00', 'event': 'creada'}]}
        for slug in (*APPROVED, PENDING):
            folder = sdd.ROOT / 'spec' / slug
            folder.mkdir(parents=True)
            sdd.dump(folder / 'spec.json', spec_data(slug, 'pendiente' if slug == PENDING else 'terminado'))
            for name, text in (('requerimientos.md', REQS), ('diseño.md', PLAN), ('tareas.md', TAREAS)):
                (folder / name).write_bytes(text.encode('utf-8'))
            (folder / 'diseño.md').rename(folder / 'plan.md')  # Renombrado previo del líder.
        sdd.dump(sdd.MEMORY, {'schema_version': 1, 'project': {'observations': [], 'decisions': []}, 'tasks': tasks})
        return sdd.ROOT

    def run_script(self, root):
        result = subprocess.run([sys.executable, str(SCRIPT), str(root)], capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=60)
        return result.returncode, result.stdout + result.stderr

    def new_fingerprint(self, slug):
        folder = sdd.ROOT / 'spec' / slug
        return sdd.spec_fingerprint(folder, sdd.load(folder / 'spec.json'))

    # AC-07
    def test_migrates_old_fingerprints_and_records_event(self):
        root = self.make_repo()
        before = sdd.load(sdd.MEMORY)
        spec_before = {k: v for k, v in snapshot(root).items() if k.startswith('spec/')}
        code, out = self.run_script(root)
        self.assertEqual(code, 0, out)
        after = sdd.load(sdd.MEMORY)
        for slug in APPROVED:
            with self.subTest(tarea=slug):
                task = after['tasks'][slug]
                new = self.new_fingerprint(slug)
                self.assertNotEqual(new, OLD[slug])
                self.assertEqual(task['approvals']['spec']['fingerprint'], new)
                self.assertFalse([e for e in sdd.validate(slug, scope=False) if 'alterada' in e])
                events = [e for e in task['events'] if e.get('event') == EVENT]
                self.assertEqual(len(events), 1, task['events'])
                self.assertEqual((events[0].get('old'), events[0].get('new')), (OLD[slug], new))
                # Fuera de la huella y del evento añadido, la tarea no cambia (by, evidence, at, close,
                # review, review_fingerprint, sealed_tests, iterations y eventos previos).
                task['approvals']['spec']['fingerprint'] = OLD[slug]
                task['events'] = [e for e in task['events'] if e.get('event') != EVENT]
                self.assertEqual(task, before['tasks'][slug])
        self.assertEqual(after['tasks'][PENDING], before['tasks'][PENDING])
        self.assertEqual(after['project'], before['project'])
        self.assertEqual(set(after['tasks']), set(before['tasks']))
        self.assertEqual({k: v for k, v in snapshot(root).items() if k.startswith('spec/')}, spec_before)

    # AC-08
    def test_aborts_without_writing(self):
        def altered_plan(root):
            (root / 'spec' / 'tarea-dos' / 'plan.md').write_bytes(b'# CAMBIO SIN APROBAR\n')
            return 'tarea-dos'

        def leftover_diseno(root):
            (root / 'spec' / 'tarea-uno' / 'diseño.md').write_bytes(PLAN.encode('utf-8'))
            return 'tarea-uno'

        def missing_plan(root):
            (root / 'spec' / 'tarea-dos' / 'plan.md').unlink()
            return 'tarea-dos'

        for case in (altered_plan, leftover_diseno, missing_plan):
            with self.subTest(caso=case.__name__):
                root = self.make_repo()
                slug = case(root)
                memory_before = sdd.MEMORY.read_bytes()
                code, out = self.run_script(root)
                self.assertEqual(code, 1, out)
                self.assertIn(slug, out)
                self.assertEqual(sdd.MEMORY.read_bytes(), memory_before)

    # AC-09
    def test_second_run_is_noop(self):
        root = self.make_repo()
        code, out = self.run_script(root)
        self.assertEqual(code, 0, out)
        memory_before = sdd.MEMORY.read_bytes()
        code, out = self.run_script(root)
        self.assertEqual(code, 0, out)
        self.assertEqual(sdd.MEMORY.read_bytes(), memory_before)


if __name__ == '__main__':
    unittest.main()
