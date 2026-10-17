"""Sincronización del arnés MicroSDD hacia un git worktree (solo biblioteca estándar)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

WORKTREE_SYNC_FILES = (
    '.microharness/sdd.py',
    '.microharness/python.sh',
    '.microharness/python.ps1',
    '.microharness/python.cmd',
    'docs/AGENT.md',
    'docs/arquitectura.md',
    'docs/convenciones.md',
    'docs/especificaciones.md',
)

EMPTY_MEMORY = {
    'schema_version': 1,
    'project': {'observations': [], 'decisions': [], 'progress': [], 'discoveries': []},
    'tasks': {},
}


def git_toplevel(path: Path) -> Path | None:
    try:
        result = subprocess.run(
            ['git', '-C', str(path), 'rev-parse', '--show-toplevel'],
            capture_output=True,
            text=True,
            errors='replace',
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).resolve()


def check_worktree_target(target: Path) -> str | None:
    top = git_toplevel(target)
    if top is None:
        return f'ERROR: {target} no es un repositorio Git ni worktree.'
    if os.path.normcase(str(top)) != os.path.normcase(str(target.resolve())):
        return f'ERROR: la ruta debe ser la raíz del worktree ({top}), no un subdirectorio.'
    return None


def worktree_sync(source: Path, target: Path, *, with_memory: bool = False) -> int:
    reconfigure = getattr(sys.stdout, 'reconfigure', None)
    if reconfigure:
        reconfigure(errors='replace')
    source = source.resolve()
    target = target.resolve()
    error = check_worktree_target(target)
    if error:
        print(error)
        return 1
    if not source.is_dir():
        print(f'ERROR: origen inexistente: {source}')
        return 1
    missing = [rel for rel in WORKTREE_SYNC_FILES if not (source / rel).is_file()]
    if missing:
        print('ERROR: faltan archivos en el origen: ' + ', '.join(missing))
        return 1
    for rel in WORKTREE_SYNC_FILES:
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / rel, dest)
        if rel == '.microharness/sdd.py' and os.name != 'nt':
            dest.chmod(dest.stat().st_mode | 0o111)
        print(f'  [copiar] {rel}')
    mem_path = target / '.microharness' / 'memory.json'
    if with_memory:
        src_mem = source / '.microharness' / 'memory.json'
        if not src_mem.is_file():
            print('ERROR: --with-memory pero el origen no tiene .microharness/memory.json')
            return 1
        mem_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src_mem, mem_path)
        print('  [copiar] .microharness/memory.json (copia explícita; no es symlink)')
    elif not mem_path.is_file():
        mem_path.parent.mkdir(parents=True, exist_ok=True)
        mem_path.write_bytes(
            (json.dumps(EMPTY_MEMORY, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        )
        print('  [crear] .microharness/memory.json (andamiaje mínimo)')
    else:
        print('  [conservar] .microharness/memory.json existente en el worktree')
    print(f'Sincronización completada hacia {target}.')
    return 0
