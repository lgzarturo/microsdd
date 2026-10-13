#!/usr/bin/env python3
"""MicroSDD: validaciones locales sin dependencias. No ejecuta Claude ni autentica al humano."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
MEMORY = ROOT / '.microharness' / 'memory.json'
DOCS = ('AGENT.md', 'arquitectura.md', 'convenciones.md', 'especificaciones.md')
# Nombres antiguos (compatibilidad): init avisa y no duplica ni mueve archivos del usuario.
LEGACY_DOCS = {'convenciones.md': 'convensiones.md', 'especificaciones.md': 'specificaciones.md'}
TASK_FILES = ('spec.json', 'requerimientos.md', 'plan.md', 'tareas.md')
STATES = ('pendiente', 'proceso', 'terminado')
SLUG_RE = re.compile(r'^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$')
COMMIT_RE = re.compile(r'^(feat|fix|docs|test|refactor|perf|chore)(\([a-z0-9][a-z0-9-]*\))?(!)?: [^\n]{1,72}$')
__version__ = '1.1.1'
SUBJECT_RE = re.compile(r'^([a-z]+)(\([^)]*\))?(!)?: ')
FINAL_TAG_RE = re.compile(r'^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$')
LOCK_TIMEOUT = 10.0
DEFAULT_MODEL = 'claude-opus-5-5'
DEFAULT_EFFORT = 'medium'
EFFORTS = ('low', 'medium', 'high', 'xhigh', 'max')
_LOCK_DEPTH = 0
# Resúmenes de runners: unittest, pytest, bun y Maven (se usa la última coincidencia de cada uno).
TEST_COUNT_RES = (
    re.compile(r'^Ran (\d+) tests? in', re.M),
    re.compile(r'\b(\d+) passed\b'),
    re.compile(r'^[ \t]*(\d+) pass\b', re.M),
    re.compile(r'Tests run: (\d+)'),
)
GO_OK_RE = re.compile(r'^ok[ \t]+\S+', re.M)
# Lista blanca de prefijos de argv para testing.commands y mutation.command (comparación exacta de tokens).
TEST_COMMANDS = (
    ('python', '-m', 'unittest'), ('python3', '-m', 'unittest'), ('python', '-m', 'pytest'),
    ('python3', '-m', 'pytest'), ('pytest',), ('npm', 'test'), ('pnpm', 'test'), ('yarn', 'test'),
    ('bun', 'test'), ('go', 'test'), ('cargo', 'test'), ('mvn', 'test'), ('./mvnw', 'test'),
    ('gradle', 'test'), ('./gradlew', 'test'), ('mutmut', 'run'),
)
# Campos vigilados de cada tarea abierta en HEAD y tipos de evento nuevo que justifican su cambio.
INTEGRITY_FIELDS = (
    (('approvals', 'spec'), ('aprobación_spec',)),
    (('approvals', 'close'), ('aprobación_close', 'aprobación_spec')),
    (('sealed_tests',), ('sellado_tests',)),
    (('review',), ('revisión', 'aprobación_spec')),
    (('review_fingerprint',), ('revisión', 'aprobación_spec')),
    (('iterations',), ('revisión', 'aprobación_spec')),
)


def dump(path: Path, data: dict) -> None:
    # Escritura atómica: temporal en el mismo directorio, fsync y os.replace.
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f'.{path.name}.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            mode = stat.S_IMODE(path.stat().st_mode)
        else:
            umask = os.umask(0)
            os.umask(umask)
            mode = 0o666 & ~umask
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise
    if os.name != 'nt':
        with contextlib.suppress(OSError):
            dir_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


@contextlib.contextmanager
def memory_lock():
    # Lock exclusivo y reentrante sobre <directorio de MEMORY>/memory.lock para las mutaciones de memoria.
    global _LOCK_DEPTH
    if _LOCK_DEPTH > 0:
        _LOCK_DEPTH += 1
        try:
            yield
        finally:
            _LOCK_DEPTH -= 1
        return
    lock = MEMORY.parent / 'memory.lock'
    lock.parent.mkdir(parents=True, exist_ok=True)
    with open(lock, 'a+b') as handle:
        deadline = time.monotonic() + LOCK_TIMEOUT
        while True:
            try:
                if os.name == 'nt':
                    import msvcrt
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise ValueError(f'No se pudo obtener {lock} en {LOCK_TIMEOUT:g} s: otro proceso de sdd.py '
                                     'está modificando la memoria; reintenta.')
                time.sleep(0.05)
        _LOCK_DEPTH = 1
        try:
            yield
        finally:
            _LOCK_DEPTH = 0
            if os.name == 'nt':
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def task_dir(slug: str) -> Path:
    if not SLUG_RE.fullmatch(slug):
        raise ValueError('Slug inválido: usa minúsculas, números y guiones; empieza con letra.')
    return ROOT / 'spec' / slug


def task_files(slug: str) -> tuple[Path, dict, dict]:
    path = task_dir(slug)
    return path, load(path / 'spec.json'), load(MEMORY)


def config() -> dict:
    # Configuración humana opcional junto a memory.json; solo lectura.
    path = MEMORY.parent / 'config.json'
    cfg = {'model': DEFAULT_MODEL, 'effort': DEFAULT_EFFORT}
    if not path.exists():
        return cfg
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        raise ValueError(f'.microharness/config.json: JSON inválido ({e})') from None
    if not isinstance(data, dict):
        raise ValueError('.microharness/config.json: debe ser un objeto JSON')
    unknown = sorted(set(data) - set(cfg))
    if unknown:
        raise ValueError(f'.microharness/config.json: claves no admitidas: {", ".join(unknown)}')
    if 'model' in data and not (isinstance(data['model'], str) and data['model'].strip()):
        raise ValueError('.microharness/config.json: model debe ser una cadena no vacía')
    if 'effort' in data and data['effort'] not in EFFORTS:
        raise ValueError(f'.microharness/config.json: effort debe ser uno de: {", ".join(EFFORTS)}')
    cfg.update(data)
    return cfg


@memory_lock()
def ensure_init() -> None:
    (ROOT / 'docs').mkdir(exist_ok=True)
    (ROOT / 'spec').mkdir(exist_ok=True)
    for doc in DOCS:
        p = ROOT / 'docs' / doc
        old = LEGACY_DOCS.get(doc)
        if old and (ROOT / 'docs' / old).exists():
            if p.exists():
                print(f'AVISO: existen docs/{old} y docs/{doc}; fusiona el contenido en docs/{doc} '
                      f'y elimina docs/{old}')
            else:
                print(f'AVISO: docs/{old} usa el nombre antiguo; no se crea docs/{doc}. '
                      f'Migra con: git mv docs/{old} docs/{doc}')
        elif not p.exists():
            p.write_text(f'# {doc.removesuffix(".md")}\n\nPendiente de inspección.\n', encoding='utf-8')
    if not MEMORY.exists():
        dump(MEMORY, {'schema_version': 1, 'project': {'observations': [], 'decisions': []}, 'tasks': {}})
    print('Contexto inicializado, sin sobrescribir documentación existente.')


@memory_lock()
def new(slug: str) -> None:
    cfg = config()
    ensure_init()
    path = task_dir(slug)
    if path.exists():
        raise ValueError('Ya existe una especificación con ese nombre.')
    path.mkdir(parents=True)
    spec = {
        'schema_version': 1,
        'id': slug,
        'title': 'POR DEFINIR',
        'state': 'pendiente',
        'model': cfg['model'],
        'effort': cfg['effort'],
        'max_iterations': 3,
        'method': {'primary': 'SDD', 'optional': [], 'notes': ''},
        'scope': {'allowed_paths': [], 'excluded': []},
        'requirements': {'acceptance_ids': ['AC-01'], 'preconditions': []},
        'testing': {
            'strategy': 'tdd',
            'commands': [],
            'protected_tests': [],
            'mutation': {'enabled': False, 'command': [], 'reason': 'Activar solo si hay lógica crítica y herramienta existente.'}
        }
    }
    dump(path / 'spec.json', spec)
    (path / 'requerimientos.md').write_text(
        '# QUÉ: requisitos\n\n## Objetivo\n[PENDIENTE]\n\n## Precondiciones\n[PENDIENTE]\n\n'
        '## Requisitos EARS\n- REQ-01: WHEN [evento], THE [sistema] SHALL [conducta observable].\n\n'
        '## Criterios de aceptación\n- AC-01: [entrada, acción y salida esperada verificables].\n\n'
        '## Fuera de alcance\n[PENDIENTE]\n', encoding='utf-8')
    (path / 'plan.md').write_text('# CÓMO: diseño mínimo\n\n## Situación comprobada\n[PENDIENTE]\n\n'
                                  '## Decisión y justificación\n[PENDIENTE]\n\n## Invariantes y riesgos\n[PENDIENTE]\n', encoding='utf-8')
    (path / 'tareas.md').write_text('# PASOS: trabajo verificable\n\n- [ ] T01 (AC-01): [prueba o cambio mínimo concreto].\n'
                                   '- [ ] T02 (AC-01): [ejecutar verificación y comprobar resultado].\n', encoding='utf-8')
    memory = load(MEMORY)
    memory['tasks'][slug] = {'approvals': {'spec': None, 'close': None}, 'sealed_tests': {},
                             'review': None, 'review_fingerprint': None, 'iterations': 0, 'events': [{'at': now(), 'event': 'creada'}]}
    dump(MEMORY, memory)
    print(f'Tarea creada: spec/{slug}/ (4 archivos).')


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def spec_fingerprint(path: Path, spec: dict) -> str:
    # Firma de contenido; el campo de estado no cambia el contrato funcional.
    stable = {k: v for k, v in spec.items() if k != 'state'}
    canonical = json.dumps(stable, sort_keys=True, ensure_ascii=False).encode('utf-8')
    digest = hashlib.sha256(canonical)
    for name in ('requerimientos.md', 'plan.md', 'tareas.md'):
        digest.update(name.encode('utf-8') + b'\x00')
        digest.update((path / name).read_bytes().replace(b'\r\n', b'\n'))
    return digest.hexdigest()


def normalized_rel(raw: str) -> str:
    raw = raw.replace('\\', '/')
    path = PurePosixPath(raw)
    if path.is_absolute() or '..' in path.parts or raw.strip() != raw or not raw:
        raise ValueError(f'Ruta insegura: {raw!r}')
    return str(path)


def path_allowed(relative: str, patterns: list[str]) -> bool:
    relative = normalized_rel(relative)
    return any(PurePosixPath(relative).match(pattern) or
               (pattern.endswith('/**') and relative.startswith(pattern[:-3] + '/'))
               for pattern in patterns)


def diff_files() -> list[str]:
    if not (ROOT / '.git').exists() and not subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'],
        cwd=ROOT, capture_output=True, text=True).returncode == 0:
        return []
    commands = (['git', 'diff', '--name-only', '-z', 'HEAD'], ['git', 'ls-files', '-z', '--others', '--exclude-standard'])
    files: set[str] = set()
    for command in commands:
        r = subprocess.run(command, cwd=ROOT, capture_output=True, encoding='utf-8', check=False)
        if r.returncode == 0:
            files.update(n for n in r.stdout.split('\0') if n)
    return sorted(files)


def code_fingerprint(patterns: list[str]) -> str:
    # Sello reproducible del diff; no sustituye revisión del contenido.
    h = hashlib.sha256()
    for filename in diff_files():
        if path_allowed(filename, patterns):
            h.update(filename.encode('utf-8') + b'\x00')
            p = ROOT / filename
            h.update(p.read_bytes() if p.is_file() else b'<deleted>')
    return h.hexdigest()


def tests_ran(output: str) -> int | None:
    counts = [int(m[-1]) for m in (r.findall(output) for r in TEST_COUNT_RES) if m]
    go = len(GO_OK_RE.findall(output))
    if go:
        counts.append(go)
    return max(counts) if counts else None


def allowed_test_commands(memory: dict) -> tuple[list[tuple[str, ...]], list[str]]:
    allowed, errors = list(TEST_COMMANDS), []
    project = memory.get('project', {})
    if not isinstance(project, dict) or 'allowed_test_commands' not in project:
        return allowed, errors
    extra = project['allowed_test_commands']
    if not isinstance(extra, list):
        return allowed, [f'project.allowed_test_commands inválido: {extra}']
    for entry in extra:
        if isinstance(entry, list) and entry and all(isinstance(x, str) and x for x in entry):
            allowed.append(tuple(entry))
        else:
            errors.append(f'project.allowed_test_commands inválido: {entry}')
    return allowed, errors


def command_allowed(command, allowed: list[tuple[str, ...]]) -> bool:
    if not isinstance(command, list) or not command:
        return False
    argv = ['python', *command[1:]] if command[0] == sys.executable else command
    return any(tuple(argv[:len(p)]) == p for p in allowed)


def echo(data: bytes, stream) -> None:
    if not data:
        return
    buffer = getattr(stream, 'buffer', None)
    if buffer is None:
        stream.write(data.decode('utf-8', 'replace'))
    else:
        stream.flush()
        buffer.write(data)
        buffer.flush()


def _field(task, path: tuple[str, ...]):
    for key in path:
        task = task.get(key) if isinstance(task, dict) else None
    return task


def memory_integrity(memory: dict) -> list[str]:
    # Detección relativa a HEAD: no impide editar memory.json; quien confirma fija la nueva base.
    try:
        raw = git('show', f'HEAD:{MEMORY.relative_to(ROOT).as_posix()}')
    except UnicodeDecodeError:
        raw = None  # Existe en HEAD pero no es UTF-8 válido: ilegible, no «no aplica».
    except (ValueError, OSError):
        return []  # Sin repositorio, sin commits o sin memoria en HEAD: no aplica.
    try:
        base_tasks = json.loads(raw).get('tasks') if raw is not None else None
    except (ValueError, AttributeError):
        base_tasks = None
    if not isinstance(base_tasks, dict):
        return ['Integridad de memoria: .microharness/memory.json: memoria versionada en HEAD ilegible; '
                'confirma una memoria válida']
    work_tasks = memory.get('tasks') if isinstance(memory.get('tasks'), dict) else {}
    errors: list[str] = []
    for slug, base in base_tasks.items():
        tag = f'Integridad de memoria: {slug}:'
        if slug not in work_tasks:
            if (ROOT / 'spec' / slug).is_dir():
                errors.append(f'{tag} tarea eliminada de la memoria')
            continue
        work = work_tasks[slug]
        if _field(base, ('approvals', 'close')) is not None:
            if work != base:
                errors.append(f'{tag} tarea cerrada modificada')
            spec_path = ROOT / 'spec' / slug / 'spec.json'
            if spec_path.is_file():
                try:
                    state = load(spec_path).get('state')
                except (OSError, ValueError, AttributeError):
                    state = None
                if state != 'terminado':
                    errors.append(f'{tag} tarea cerrada reabierta (spec.json no está en terminado)')
            continue
        base_events = _field(base, ('events',))
        base_events = base_events if isinstance(base_events, list) else []
        work_events = _field(work, ('events',))
        new_events: set = set()
        if not isinstance(work_events, list) or work_events[:len(base_events)] != base_events:
            errors.append(f'{tag} events: se borraron, alteraron o reordenaron eventos confirmados')
        else:
            new_events = {e.get('event') for e in work_events[len(base_events):] if isinstance(e, dict)}
        for path, kinds in INTEGRITY_FIELDS:
            if _field(work, path) != _field(base, path) and not new_events.intersection(kinds):
                errors.append(f'{tag} {".".join(path)} cambió sin evento {" o ".join(kinds)}')
    return errors


def validate(slug: str, run: bool = False, scope: bool = True) -> list[str]:
    cfg = config()
    path, s, memory = task_files(slug)
    errors: list[str] = []
    for name in TASK_FILES:
        if not (path / name).is_file():
            errors.append(f'Falta spec/{slug}/{name}')
    for entry in sorted(path.iterdir()):
        if not entry.name.isascii():
            errors.append(f'Nombre de archivo no ASCII en spec/{slug}/: {entry.name}')
    if errors:
        return errors
    errors.extend(memory_integrity(memory))
    if s.get('id') != slug or s.get('schema_version') != 1:
        errors.append('ID o versión de spec.json incorrectos')
    if s.get('state') not in STATES:
        errors.append('Estado fuera de la máquina de tres estados')
    if s.get('state') != 'terminado' and s.get('model') != cfg['model']:
        errors.append(f"El modelo de spec.json ({s.get('model')}) no coincide con el configurado ({cfg['model']}) en .microharness/config.json")
    if s.get('effort') not in EFFORTS:
        errors.append(f'Effort inválido; usa uno de: {", ".join(EFFORTS)}')
    if type(s.get('max_iterations')) is not int or not 1 <= s['max_iterations'] <= 3:
        errors.append('max_iterations debe estar entre 1 y 3')
    method = s.get('method', {})
    if method.get('primary') != 'SDD' or any(x not in ('RDD', 'ODD') for x in method.get('optional', [])):
        errors.append('SDD obligatorio; opcionales: RDD, ODD')
    if method.get('optional') and not method.get('notes', '').strip():
        errors.append('Define el significado operativo de RDD/ODD si se activa')
    patterns = s.get('scope', {}).get('allowed_paths', [])
    if not isinstance(patterns, list) or not patterns:
        errors.append('Define un alcance reducido en scope.allowed_paths')
    else:
        for pattern in patterns:
            try:
                normalized_rel(pattern)
            except ValueError as e:
                errors.append(str(e))
    reqs = (path / 'requerimientos.md').read_text(encoding='utf-8')
    tasks = (path / 'tareas.md').read_text(encoding='utf-8')
    design = (path / 'plan.md').read_text(encoding='utf-8')
    ids = s.get('requirements', {}).get('acceptance_ids', [])
    if not ids or len(ids) != len(set(ids)) or not all(re.fullmatch(r'AC-\d{2,}', a) for a in ids):
        errors.append('Se requieren acceptance_ids únicos AC-01, AC-02...')
    for a in ids:
        if a not in reqs or a not in tasks:
            errors.append(f'{a} debe estar presente en requerimientos.md y tareas.md')
    for doc, content in [('requerimientos.md', reqs), ('plan.md', design), ('tareas.md', tasks)]:
        if '[PENDIENTE]' in content or '[evento]' in content or '[entrada' in content or '[prueba o cambio' in content:
            errors.append(f'{doc} conserva marcadores de plantilla')
    if not re.search(r'\b(WHEN|WHILE|IF)\b.+\b(SHALL|THEN)\b', reqs, re.I):
        errors.append('Falta al menos un requisito EARS verificable')
    testing = s.get('testing', {})
    if testing.get('strategy') not in ('tdd', 'after'):
        errors.append('testing.strategy debe ser tdd o after')
    if not testing.get('commands'):
        errors.append('Define al menos un comando de pruebas como arreglo de argumentos')
    for cmd in testing.get('commands', []):
        if not isinstance(cmd, list) or not cmd or not all(isinstance(x, str) and x for x in cmd):
            errors.append('Comando de pruebas inválido; usa ["python", "-m", "unittest"]')
    mutation = testing.get('mutation', {})
    if mutation.get('enabled') and not mutation.get('command'):
        errors.append('Mutation testing activado sin comando')
    if s.get('state') != 'terminado':
        allowed, invalid = allowed_test_commands(memory)
        errors.extend(invalid)
        for cmd in testing.get('commands', []):
            if isinstance(cmd, list) and cmd and all(isinstance(x, str) and x for x in cmd) \
                    and not command_allowed(cmd, allowed):
                errors.append(f'Comando de pruebas fuera de la lista blanca: {cmd}')
        if mutation.get('enabled') and mutation.get('command') \
                and not command_allowed(mutation['command'], allowed):
            errors.append(f'Comando de mutación fuera de la lista blanca: {mutation["command"]}')
    min_tests = testing.get('min_tests', 1)
    if type(min_tests) is not int or min_tests < 1:
        errors.append('testing.min_tests debe ser un entero mayor o igual a 1')
    if slug not in memory.get('tasks', {}):
        errors.append('No existe memoria para la tarea')
    else:
        task_memory = memory['tasks'][slug]
        if s.get('state') != 'terminado':
            for file, expected in task_memory.get('sealed_tests', {}).items():
                try:
                    target = ROOT / normalized_rel(file)
                    if not target.is_file() or hash_file(target) != expected:
                        errors.append(f'Test sellado modificado: {file}; requiere autorización y nuevo sello')
                except ValueError as e:
                    errors.append(str(e))
        if s.get('state') in ('proceso', 'terminado'):
            prior = task_memory.get('approvals', {}).get('spec')
            if not prior:
                errors.append('No consta aprobación humana de especificación')
            elif prior.get('fingerprint') != spec_fingerprint(path, s):
                errors.append('Especificación alterada después de aprobación; se requiere reaprobación')
        if s.get('state') == 'terminado' and not task_memory.get('approvals', {}).get('close'):
            errors.append('No consta aprobación humana de cierre')
    if scope and patterns:
        for filename in diff_files():
            if filename.startswith(('spec/', 'docs/', '.microharness/')) or filename in ('CLAUDE.md',):
                continue
            if not path_allowed(filename, patterns):
                errors.append(f'Archivo modificado fuera de scope: {filename}')
    if run and not errors:
        commands = [(c, True) for c in testing['commands']]
        if mutation.get('enabled'):
            commands.append((mutation['command'], False))
        for command, counted in commands:
            if command[0] in ('python', 'python3'):
                command = [sys.executable, *command[1:]]
            print('EJECUTANDO:', ' '.join(command), flush=True)
            try:
                outcome = subprocess.run(command, cwd=ROOT, check=False, timeout=300, capture_output=True)
                echo(outcome.stdout, sys.stdout)
                echo(outcome.stderr, sys.stderr)
                if outcome.returncode:
                    errors.append(f'Comando falló ({outcome.returncode}): {command}')
                elif counted and s.get('state') != 'terminado':
                    found = tests_ran(outcome.stdout.decode('utf-8', 'replace') + '\n'
                                      + outcome.stderr.decode('utf-8', 'replace'))
                    if found is None or found < min_tests:
                        detected = 'ninguna' if found is None else found
                        errors.append(f'Se requieren al menos {min_tests} pruebas ejecutadas; '
                                      f'detectadas: {detected} en {command}')
            except (OSError, subprocess.TimeoutExpired) as e:
                errors.append(f'No se pudo ejecutar {command}: {e}')
    return errors


@memory_lock()
def approve(slug: str, phase: str, by: str, evidence: str) -> None:
    # Se registra una declaración, no una identidad autenticada. Requiere decisión humana explícita.
    path, spec, memory = task_files(slug)
    if not by.strip() or not evidence.strip():
        raise ValueError('Se requiere autor de aprobación y texto de evidencia explícita.')
    if phase == 'spec':
        if spec['state'] == 'terminado':
            raise ValueError('La tarea terminó; inicia una nueva spec para otro cambio.')
        failures = [e for e in validate(slug, scope=False)
                    if 'Especificación alterada después de aprobación' not in e]
        if failures:
            raise ValueError('La spec no es válida: ' + '; '.join(failures))
    if phase == 'close':
        if spec['state'] != 'proceso':
            raise ValueError('Solo puede cerrarse una tarea en proceso.')
        if memory['tasks'][slug].get('review') != 'APROBADO':
            raise ValueError('Falta revisión independiente APROBADO registrada.')
        expected = memory['tasks'][slug].get('review_fingerprint')
        if expected != code_fingerprint(spec['scope']['allowed_paths']):
            raise ValueError('El código cambió después de la revisión: requiere otra revisión.')
        failures = validate(slug, run=True)
        if failures:
            raise ValueError('Puerta de calidad fallida: ' + '; '.join(failures))
    memory['tasks'][slug]['approvals'][phase] = {'by': by, 'evidence': evidence, 'at': now()}
    if phase == 'spec':
        memory['tasks'][slug]['approvals'][phase]['fingerprint'] = spec_fingerprint(path, spec)
        memory['tasks'][slug]['approvals']['close'] = None
        memory['tasks'][slug]['review'] = None
        memory['tasks'][slug]['review_fingerprint'] = None
        memory['tasks'][slug]['iterations'] = 0
    memory['tasks'][slug]['events'].append({'at': now(), 'event': f'aprobación_{phase}', 'by': by})
    if phase == 'spec':
        spec['state'] = 'proceso'
    else:
        spec['state'] = 'terminado'
    dump(MEMORY, memory)
    dump(path / 'spec.json', spec)
    print(f'Aprobación declarada registrada ({phase}). No es una firma ni autentica al usuario.')


@memory_lock()
def review(slug: str, verdict: str, evidence: str) -> None:
    path, spec, memory = task_files(slug)
    if spec['state'] != 'proceso' or not memory['tasks'][slug]['approvals']['spec']:
        raise ValueError('La tarea no está en proceso con spec aprobada.')
    if not evidence.strip():
        raise ValueError('Registra evidencia concreta del dictamen.')
    task = memory['tasks'][slug]
    task['iterations'] += 1
    if task['iterations'] > spec['max_iterations']:
        raise ValueError('Se agotó max_iterations; requiere intervención humana.')
    task['review'] = verdict
    task['review_fingerprint'] = code_fingerprint(spec['scope']['allowed_paths']) if verdict == 'APROBADO' else None
    task['events'].append({'at': now(), 'event': 'revisión', 'verdict': verdict, 'evidence': evidence})
    if verdict == 'RECHAZADO' and task['iterations'] >= spec['max_iterations']:
        spec['state'] = 'pendiente'
        task['events'].append({'at': now(), 'event': 'escalado', 'reason': 'Intentos agotados'})
    dump(path / 'spec.json', spec)
    dump(MEMORY, memory)
    print('Revisión registrada.', 'Escalada al humano.' if spec['state'] == 'pendiente' else '')


@memory_lock()
def note(fact: str | None, decision: str | None, by: str | None, evidence: str) -> None:
    # Se registra una declaración, no una identidad autenticada.
    if (fact is None) == (decision is None):
        raise ValueError('Indica exactamente uno de --fact o --decision.')
    if decision is not None and by is None:
        raise ValueError('--decision requiere --by.')
    if fact is not None and by is not None:
        raise ValueError('--by solo se admite con --decision.')
    if any(not text.strip() for text in (fact, decision, by, evidence) if text is not None):
        raise ValueError('Los textos de la nota no pueden estar vacíos.')
    if not MEMORY.exists():
        ensure_init()
    memory = load(MEMORY)
    project = memory.setdefault('project', {})
    if fact is not None:
        project.setdefault('observations', []).append({'at': now(), 'fact': fact, 'evidence': evidence})
    else:
        project.setdefault('decisions', []).append({'at': now(), 'by': by, 'decision': decision, 'evidence': evidence})
    dump(MEMORY, memory)
    print('Nota registrada en memory.json.' if fact is not None
          else 'Decisión declarada registrada. No es una firma ni autentica al usuario.')


@memory_lock()
def seal(slug: str, by: str) -> None:
    _, spec, memory = task_files(slug)
    tests = spec['testing']['protected_tests']
    if not tests:
        raise ValueError('No hay testing.protected_tests; selecciona pruebas concretas.')
    if not by.strip():
        raise ValueError('Se requiere identificación declarada del humano que revisó las pruebas.')
    hashes: dict[str, str] = {}
    for test in tests:
        relative = normalized_rel(test)
        target = ROOT / relative
        if not target.is_file() or not target.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError(f'No existe test seguro: {relative}')
        hashes[relative] = hash_file(target)
    memory['tasks'][slug]['sealed_tests'] = hashes
    memory['tasks'][slug]['events'].append({'at': now(), 'event': 'sellado_tests', 'by': by, 'files': list(hashes)})
    dump(MEMORY, memory)
    print(f'{len(hashes)} pruebas selladas. Versiona memory.json y conserva baseline Git protegido.')


def commit_check(message: str) -> None:
    if not COMMIT_RE.fullmatch(message):
        raise ValueError('Commit no convencional. Ej.: fix(auth): valida expiración del token')
    print('Mensaje Conventional Commit válido (validación sintáctica básica).')


def git(*args: str) -> str:
    result = subprocess.run(['git', '-c', 'core.quotePath=false', *args], cwd=ROOT, capture_output=True,
                            text=True, encoding='utf-8', check=False)
    if result.returncode != 0:
        raise ValueError(f'git {" ".join(args)} falló: {result.stderr.strip()}')
    return result.stdout


def release_propose() -> None:
    if git('branch', '--show-current').strip() != 'main':
        raise ValueError('release propose exige la rama main.')
    busy = [p.parent.name for p in sorted((ROOT / 'spec').glob('*/spec.json')) if load(p).get('state') == 'proceso']
    if busy:
        raise ValueError(f'Hay tareas en proceso: {", ".join(busy)}.')
    records, changed = iter(git('status', '--porcelain', '-z', '--untracked-files=all').split('\0')), []
    for record in records:
        if record:
            changed.append(record[3:])
            if 'R' in record[:2] or 'C' in record[:2]: changed.append(next(records))  # ruta de origen
    outside = [p for p in changed if not p.startswith('spec/') and p not in ('.microharness/memory.json', '.microharness/memory.lock')]
    if outside:
        raise ValueError(f'Árbol con cambios fuera de spec/ y .microharness/memory.json: {", ".join(outside)}')
    tags = [t for t in git('tag', '--merged', 'HEAD', '--list', 'v*').split() if FINAL_TAG_RE.match(t)]
    base = max(tags, key=lambda t: tuple(map(int, FINAL_TAG_RE.match(t).groups())), default=None)
    subjects = git('log', '--reverse', '--format=%s', f'{base}..HEAD' if base else 'HEAD').splitlines()
    level, lines = 0, []  # 3 incompatible, 2 añadido, 1 corregido, 0 sin incremento
    for subject in subjects:
        m = SUBJECT_RE.match(subject)
        if m and m.group(3): group, rank = 'Incompatible', 3
        elif m and m.group(1) == 'feat': group, rank = 'Añadido', 2
        elif m and m.group(1) in ('fix', 'perf'): group, rank = 'Corregido', 1
        else: group, rank = 'Otros', 0
        lines.append(f'{group}: {subject}')
        level = max(level, rank)
    if not level:
        raise ValueError('Commits sin incremento; no se publica versión.')
    if base:
        x, y, z = map(int, FINAL_TAG_RE.match(base).groups())
        if x == 0:
            level = 2 if level == 3 else 1
        version = {3: f'{x + 1}.0.0', 2: f'{x}.{y + 1}.0', 1: f'{x}.{y}.{z + 1}'}[level]
    else:
        m = re.search(r"^__version__ = '([^']*)'", (ROOT / '.microharness' / 'sdd.py').read_text(encoding='utf-8'), re.M)
        if not m:
            raise ValueError('No se encontró __version__ en .microharness/sdd.py.')
        version = re.sub(r'-rc\.[0-9]+$', '', m.group(1))
    print(f'Último tag: {base or "(ninguno)"}')
    for line in lines: print(line)
    print(f'Versión propuesta: {version}')


def main() -> int:
    p = argparse.ArgumentParser(description='MicroSDD · validación y memoria, no orquestación LLM')
    p.add_argument('--version', action='version', version=f'MicroSDD {__version__}')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    sub.add_parser('new').add_argument('slug')
    check = sub.add_parser('check'); check.add_argument('slug'); check.add_argument('--run', action='store_true'); check.add_argument('--no-scope', action='store_true')
    ap = sub.add_parser('approve'); ap.add_argument('slug'); ap.add_argument('phase', choices=('spec', 'close')); ap.add_argument('--by', required=True); ap.add_argument('--evidence', required=True)
    rev = sub.add_parser('review'); rev.add_argument('slug'); rev.add_argument('verdict', choices=('APROBADO', 'RECHAZADO')); rev.add_argument('--evidence', required=True)
    se = sub.add_parser('seal'); se.add_argument('slug'); se.add_argument('--by', required=True)
    no = sub.add_parser('note'); no.add_argument('--fact'); no.add_argument('--decision'); no.add_argument('--by'); no.add_argument('--evidence', required=True)
    sub.add_parser('commit-check').add_argument('message')
    rel = sub.add_parser('release')
    rel.add_subparsers(dest='action', required=True).add_parser('propose')
    args = p.parse_args()
    try:
        if args.command in ('approve', 'seal') and (
                'CLAUDECODE' in os.environ or sys.stdin is None or not sys.stdin.isatty()):
            raise ValueError(f'{args.command} es una decisión humana: ejecútalo tú en una terminal '
                             'interactiva, fuera de Claude Code.')
        if args.command == 'init': ensure_init()
        elif args.command == 'new': new(args.slug)
        elif args.command == 'check':
            failures = validate(args.slug, run=args.run, scope=not args.no_scope)
            if failures:
                for failure in failures: print('ERROR:', failure, file=sys.stderr)
                return 1
            print('OK: spec, alcance, hashes y' + (' ejecución de pruebas.' if args.run else ' estructura.'))
        elif args.command == 'approve': approve(args.slug, args.phase, args.by, args.evidence)
        elif args.command == 'review': review(args.slug, args.verdict, args.evidence)
        elif args.command == 'seal': seal(args.slug, args.by)
        elif args.command == 'note': note(args.fact, args.decision, args.by, args.evidence)
        elif args.command == 'commit-check': commit_check(args.message)
        elif args.command == 'release': release_propose()
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
        print('ERROR:', e, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
