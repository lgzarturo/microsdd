"""Migra las huellas de aprobación `spec` tras renombrar `diseño.md` a `plan.md`.

Uso: python scripts/migrar_plan_md.py <raíz>

Ejecutar después de renombrar `spec/<slug>/diseño.md` a `spec/<slug>/plan.md`.
Para cada tarea con aprobación `spec` cuya huella almacenada coincide con el
esquema antiguo (nombre `diseño.md`) sobre el contenido actual de `plan.md`,
reescribe la huella con el esquema nuevo y añade un evento `migración_plan_md`.
Aborta sin escribir si alguna huella no coincide con ningún esquema, si falta
`plan.md` o si queda algún `diseño.md`. No ejecuta git ni renombra archivos.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

OLD_NAME, NEW_NAME = 'diseño.md', 'plan.md'


def huella(path: Path, spec: dict, nombre: str) -> str:
    # Mismo cálculo que spec_fingerprint de sdd.py; `nombre` es el del documento de diseño.
    stable = {k: v for k, v in spec.items() if k != 'state'}
    digest = hashlib.sha256(json.dumps(stable, sort_keys=True, ensure_ascii=False).encode('utf-8'))
    for name, source in (('requerimientos.md', 'requerimientos.md'), (nombre, NEW_NAME), ('tareas.md', 'tareas.md')):
        digest.update(name.encode('utf-8') + b'\x00')
        digest.update((path / source).read_bytes().replace(b'\r\n', b'\n'))
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('root', help='raíz del repositorio con el arnés MicroSDD')
    root = Path(parser.parse_args(argv).root)
    memory_path = root / '.microharness' / 'memory.json'
    memory = json.loads(memory_path.read_text(encoding='utf-8'))
    errors, pending = [], []
    for folder in sorted((root / 'spec').iterdir()):
        if folder.is_dir() and (folder / OLD_NAME).exists():
            errors.append(f'{folder.name}: conserva spec/{folder.name}/{OLD_NAME}; renómbralo a {NEW_NAME}')
    for slug, task in memory.get('tasks', {}).items():
        approval = (task.get('approvals') or {}).get('spec')
        if not approval:
            continue
        path = root / 'spec' / slug
        if not (path / NEW_NAME).is_file():
            errors.append(f'{slug}: falta spec/{slug}/{NEW_NAME}')
            continue
        spec = json.loads((path / 'spec.json').read_text(encoding='utf-8'))
        new = huella(path, spec, NEW_NAME)
        if approval.get('fingerprint') == new:
            continue
        if approval.get('fingerprint') != huella(path, spec, OLD_NAME):
            errors.append(f'{slug}: la huella aprobada no coincide con ningún esquema (especificación alterada)')
            continue
        pending.append((slug, new))
    if errors:
        for error in errors:
            print(f'ERROR: {error}', file=sys.stderr)
        print('No se escribió nada.', file=sys.stderr)
        return 1
    at = datetime.now(timezone.utc).isoformat(timespec='seconds')
    for slug, new in pending:
        approval = memory['tasks'][slug]['approvals']['spec']
        memory['tasks'][slug]['events'].append({'at': at, 'event': 'migración_plan_md',
                                                'old': approval['fingerprint'], 'new': new})
        approval['fingerprint'] = new
        print(f'Migrada: {slug}')
    if pending:
        memory_path.write_text(json.dumps(memory, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Tareas migradas: {len(pending)}.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
