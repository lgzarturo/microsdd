"""Archiva el historial del arnés MicroSDD antes de un release.

Uso: python scripts/limpiar_arnes.py <versión> [--dry-run]

Copia `.microharness/memory.json`, `docs/` y las tareas de `spec/` a
`historial/<versión>/`, verifica la copia byte a byte, elimina los originales y
ejecuta `.microharness/sdd.py init` para dejar el estado inicial del arnés.
Aborta sin cambios si hay tareas no terminadas, el árbol de git no está limpio,
hay archivos ignorados o enlaces simbólicos en las rutas archivadas, o
`historial/<versión>/` ya existe. No crea commits, tags ni hace push: al terminar
imprime el `git add` y el mensaje de commit sugeridos.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

DOCS = ('AGENT.md', 'arquitectura.md', 'convenciones.md', 'especificaciones.md')
LEGACY_DOCS = ('convensiones.md', 'specificaciones.md')  # nombres antiguos aceptados al archivar
VERSION_RE = re.compile(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?')
GIT_ENV = {k: v for k, v in os.environ.items() if k not in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE')}


class Abort(Exception):
    pass


def git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(['git', *args], cwd=root, env=GIT_ENV, capture_output=True,
                                text=True, encoding='utf-8', errors='replace')
    except OSError as exc:
        raise Abort(f'No se pudo ejecutar git: {exc}') from exc
    if result.returncode != 0:
        raise Abort(f'La raíz no es un repositorio git utilizable: {root}')
    return result.stdout


def open_tasks(root: Path, tasks: dict) -> list[str]:
    spec = root / 'spec'
    slugs = set(tasks) | ({p.name for p in spec.iterdir() if p.is_dir()} if spec.is_dir() else set())
    found = []
    for slug in sorted(slugs):
        path = spec / slug / 'spec.json'
        if not (spec / slug).is_dir():
            found.append(f'{slug}: está en memory.json pero no tiene directorio en spec/')
            continue
        try:
            state = json.loads(path.read_text(encoding='utf-8')).get('state')
        except (OSError, ValueError, AttributeError):
            found.append(f'{slug}: spec.json ausente o ilegible')
            continue
        if state != 'terminado':
            found.append(f'{slug}: estado {state!r}')
    return found


def validate(root: Path, version: str) -> list[tuple[Path, Path]]:
    if not VERSION_RE.fullmatch(version):
        raise Abort(f'Versión inválida {version!r}: usa SemVer MAYOR.MENOR.PARCHE[-prerelease].')
    if not (root / '.microharness' / 'sdd.py').is_file():
        raise Abort('Falta .microharness/sdd.py en la raíz.')
    top = git(root, 'rev-parse', '--show-toplevel').strip()
    if Path(top).resolve() != root.resolve():
        raise Abort(f'La raíz {root} no es la raíz del repositorio git ({top}).')
    if git(root, 'status', '--porcelain'):
        raise Abort('El árbol de trabajo tiene cambios o archivos no rastreados; confírmalos o descártalos.')
    ignored = git(root, 'status', '--porcelain', '--ignored', '--', 'docs', 'spec', '.microharness/memory.json')
    if ignored:
        raise Abort('Hay archivos ignorados por git en las rutas a archivar:\n' + ignored.rstrip())
    historial = root / 'historial'
    if historial.is_symlink() or historial.exists() and not historial.is_dir():
        raise Abort('historial existe y no es un directorio.')
    target = historial / version
    if target.exists() or target.is_symlink():
        raise Abort(f'historial/{version} ya existe.')
    memory = root / '.microharness' / 'memory.json'
    if memory.is_symlink() or not memory.is_file():
        raise Abort('Falta .microharness/memory.json o no es un archivo regular.')
    try:
        tasks = json.loads(memory.read_text(encoding='utf-8')).get('tasks')
    except (OSError, ValueError, AttributeError) as exc:
        raise Abort(f'.microharness/memory.json no es JSON válido: {exc}') from exc
    if not isinstance(tasks, dict):
        raise Abort('El campo tasks de .microharness/memory.json no es un objeto.')
    docs, spec = root / 'docs', root / 'spec'
    links = [p for p in (docs, spec) if p.is_symlink()]
    if links:
        raise Abort('Enlace simbólico en las rutas a archivar: ' + ', '.join(str(p) for p in links))
    doc_entries = sorted(docs.iterdir()) if docs.is_dir() else []
    unknown = [p.name for p in doc_entries if p.name not in DOCS + LEGACY_DOCS]
    if unknown:
        raise Abort('docs/ contiene entradas desconocidas: ' + ', '.join(unknown))
    links = [p for p in doc_entries if p.is_symlink()]
    if spec.is_dir():
        for folder, dirs, files in os.walk(spec):
            links += [Path(folder) / n for n in dirs + files if (Path(folder) / n).is_symlink()]
    if links:
        raise Abort('Enlace simbólico en las rutas a archivar: ' + ', '.join(str(p) for p in links))
    found = open_tasks(root, tasks)
    if found:
        raise Abort('Hay tareas abiertas:\n' + '\n'.join(f'- {line}' for line in found))
    plan = [(memory, target / 'memory.json')]
    plan += [(p, target / 'docs' / p.name) for p in doc_entries]
    if spec.is_dir():
        plan += [(p, target / 'spec' / p.name) for p in sorted(spec.iterdir()) if p.name != '.gitkeep']
    return plan


def archive(root: Path, plan: list[tuple[Path, Path]]) -> None:
    for source, dest in plan:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, dest)
        else:
            shutil.copy2(source, dest)
    for source, dest in plan:
        pairs = [(source, dest)]
        if source.is_dir():
            pairs = [(f, dest / f.relative_to(source)) for f in source.rglob('*') if f.is_file()]
        for original, copy in pairs:
            if not copy.is_file() or original.read_bytes() != copy.read_bytes():
                raise OSError(f'La copia de {original} no coincide byte a byte.')
    for source, _ in plan:
        if source.is_dir():
            shutil.rmtree(source)
        else:
            source.unlink()
    result = subprocess.run([sys.executable, str(root / '.microharness' / 'sdd.py'), 'init'], cwd=root,
                            capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode != 0:
        raise OSError(f'sdd.py init terminó con código {result.returncode}: {result.stderr.strip()}')
    print(result.stdout.rstrip())
    gitkeep = root / 'spec' / '.gitkeep'
    if not gitkeep.exists():
        gitkeep.write_bytes(b'')
    docs = sorted(p.name for p in (root / 'docs').iterdir())
    spec = [p.name for p in (root / 'spec').iterdir()]
    if docs != sorted(DOCS) or spec != ['.gitkeep'] or not (root / '.microharness' / 'memory.json').is_file():
        raise OSError('El estado posterior no coincide con el de sdd.py init.')


def main(argv: list[str] | None = None, root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('version', help='versión SemVer del release, p. ej. 1.2.0')
    parser.add_argument('--dry-run', action='store_true', help='muestra el plan sin escribir nada')
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent.parent if root is None else root
    try:
        plan = validate(root, args.version)
    except Abort as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    print(f'Plan de archivado en historial/{args.version}:')
    for source, dest in plan:
        print(f'- {source.relative_to(root).as_posix()} -> {dest.relative_to(root).as_posix()}')
    print('Se eliminarán los originales y se ejecutará .microharness/sdd.py init.')
    if args.dry_run:
        print('Modo --dry-run: no se escribió nada.')
        return 0
    try:
        archive(root, plan)
    except OSError as exc:
        print(f'ERROR: {exc}\nRemediación: git restore --source=HEAD --staged --worktree -- docs spec '
              f'.microharness/memory.json y elimina historial/{args.version}/', file=sys.stderr)
        return 1
    print('Limpieza completada. La herramienta no crea commits, tags ni hace push. Próximos pasos:')
    print(f'  git add -- historial/{args.version} docs spec .microharness/memory.json')
    print(f'  git commit -m "chore(release): archiva historial {args.version}"')
    return 0


if __name__ == '__main__':
    sys.exit(main())
