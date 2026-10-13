#!/usr/bin/env python3
"""MicroSDD: validaciones locales sin dependencias. No ejecuta Claude ni autentica al humano."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
MEMORY = ROOT / '.microharness' / 'memory.json'
DOCS = ('AGENT.md', 'arquitectura.md', 'convensiones.md', 'specificaciones.md')
TASK_FILES = ('spec.json', 'requerimientos.md', 'diseño.md', 'tareas.md')
STATES = ('pendiente', 'proceso', 'terminado')
SLUG_RE = re.compile(r'^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$')
COMMIT_RE = re.compile(r'^(feat|fix|docs|test|refactor|perf|chore)(\([a-z0-9][a-z0-9-]*\))?(!)?: [^\n]{1,72}$')


def dump(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def task_dir(slug: str) -> Path:
    if not SLUG_RE.fullmatch(slug):
        raise ValueError('Slug inválido: usa minúsculas, números y guiones; empieza con letra.')
    return ROOT / 'spec' / slug


def task_files(slug: str) -> tuple[Path, dict, dict]:
    path = task_dir(slug)
    return path, load(path / 'spec.json'), load(MEMORY)


def ensure_init() -> None:
    (ROOT / 'docs').mkdir(exist_ok=True)
    (ROOT / 'spec').mkdir(exist_ok=True)
    for doc in DOCS:
        p = ROOT / 'docs' / doc
        if not p.exists():
            p.write_text(f'# {doc.removesuffix(".md")}\n\nPendiente de inspección.\n', encoding='utf-8')
    if not MEMORY.exists():
        dump(MEMORY, {'schema_version': 1, 'project': {'observations': [], 'decisions': []}, 'tasks': {}})
    print('Contexto inicializado, sin sobrescribir documentación existente.')


def new(slug: str) -> None:
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
        'model': 'claude-opus-5-5',
        'effort': 'medium',
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
    (path / 'diseño.md').write_text('# CÓMO: diseño mínimo\n\n## Situación comprobada\n[PENDIENTE]\n\n'
                                    '## Decisión y justificación\n[PENDIENTE]\n\n## Invariantes y riesgos\n[PENDIENTE]\n', encoding='utf-8')
    (path / 'tareas.md').write_text('# PASOS: trabajo verificable\n\n- [ ] T01 (AC-01): [prueba o cambio mínimo concreto].\n'
                                   '- [ ] T02 (AC-01): [ejecutar verificación y comprobar resultado].\n', encoding='utf-8')
    memory = load(MEMORY)
    memory['tasks'][slug] = {'approvals': {'spec': None, 'close': None}, 'sealed_tests': {},
                             'review': None, 'review_fingerprint': None, 'iterations': 0, 'events': [{'at': now(), 'event': 'creada'}]}
    dump(MEMORY, memory)
    print(f'Tarea creada: spec/{slug}/ (4 archivos).')


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def spec_fingerprint(path: Path, spec: dict) -> str:
    # Firma de contenido; el campo de estado no cambia el contrato funcional.
    stable = {k: v for k, v in spec.items() if k != 'state'}
    canonical = json.dumps(stable, sort_keys=True, ensure_ascii=False).encode('utf-8')
    digest = hashlib.sha256(canonical)
    for name in ('requerimientos.md', 'diseño.md', 'tareas.md'):
        digest.update(name.encode('utf-8') + b'\x00')
        digest.update((path / name).read_bytes())
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
    commands = (['git', '-c', 'core.quotePath=false', 'diff', '--name-only', 'HEAD'],
                ['git', '-c', 'core.quotePath=false', 'ls-files', '--others', '--exclude-standard'])
    files: set[str] = set()
    for command in commands:
        r = subprocess.run(command, cwd=ROOT, capture_output=True, encoding='utf-8', check=False)
        if r.returncode == 0:
            files.update(n for n in r.stdout.splitlines() if n)
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


def validate(slug: str, run: bool = False, scope: bool = True) -> list[str]:
    path, s, memory = task_files(slug)
    errors: list[str] = []
    for name in TASK_FILES:
        if not (path / name).is_file():
            errors.append(f'Falta spec/{slug}/{name}')
    if errors:
        return errors
    if s.get('id') != slug or s.get('schema_version') != 1:
        errors.append('ID o versión de spec.json incorrectos')
    if s.get('state') not in STATES:
        errors.append('Estado fuera de la máquina de tres estados')
    if s.get('model') != 'claude-opus-5-5':
        errors.append('El modelo debe ser exclusivamente claude-opus-5-5')
    if s.get('effort') not in ('low', 'medium', 'high', 'xhigh', 'max'):
        errors.append('Effort inválido')
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
    design = (path / 'diseño.md').read_text(encoding='utf-8')
    ids = s.get('requirements', {}).get('acceptance_ids', [])
    if not ids or len(ids) != len(set(ids)) or not all(re.fullmatch(r'AC-\d{2,}', a) for a in ids):
        errors.append('Se requieren acceptance_ids únicos AC-01, AC-02...')
    for a in ids:
        if a not in reqs or a not in tasks:
            errors.append(f'{a} debe estar presente en requerimientos.md y tareas.md')
    for doc, content in [('requerimientos.md', reqs), ('diseño.md', design), ('tareas.md', tasks)]:
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
    if slug not in memory.get('tasks', {}):
        errors.append('No existe memoria para la tarea')
    else:
        task_memory = memory['tasks'][slug]
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
        for command in testing['commands'] + ([mutation['command']] if mutation.get('enabled') else []):
            if command[0] in ('python', 'python3'):
                command = [sys.executable, *command[1:]]
            print('EJECUTANDO:', ' '.join(command), flush=True)
            try:
                outcome = subprocess.run(command, cwd=ROOT, check=False, timeout=300)
                if outcome.returncode:
                    errors.append(f'Comando falló ({outcome.returncode}): {command}')
            except (OSError, subprocess.TimeoutExpired) as e:
                errors.append(f'No se pudo ejecutar {command}: {e}')
    return errors


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


def main() -> int:
    p = argparse.ArgumentParser(description='MicroSDD · validación y memoria, no orquestación LLM')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    sub.add_parser('new').add_argument('slug')
    check = sub.add_parser('check'); check.add_argument('slug'); check.add_argument('--run', action='store_true'); check.add_argument('--no-scope', action='store_true')
    ap = sub.add_parser('approve'); ap.add_argument('slug'); ap.add_argument('phase', choices=('spec', 'close')); ap.add_argument('--by', required=True); ap.add_argument('--evidence', required=True)
    rev = sub.add_parser('review'); rev.add_argument('slug'); rev.add_argument('verdict', choices=('APROBADO', 'RECHAZADO')); rev.add_argument('--evidence', required=True)
    se = sub.add_parser('seal'); se.add_argument('slug'); se.add_argument('--by', required=True)
    sub.add_parser('commit-check').add_argument('message')
    args = p.parse_args()
    try:
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
        elif args.command == 'commit-check': commit_check(args.message)
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
        print('ERROR:', e, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
