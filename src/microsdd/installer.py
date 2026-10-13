"""Instalador por proyecto de MicroSDD for Claude Opus 5.5 (solo biblioteca estándar)."""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from importlib import metadata
from pathlib import Path

NAME = 'MicroSDD for Claude Opus 5.5'
PAYLOAD = Path(__file__).resolve().parent / 'payload'
# Única fuente del manifiesto: ruta en el payload -> ruta en el destino.
# pyproject.toml lo replica explícitamente; la prueba AC-10 verifica la coherencia.
MANIFEST = {
    '.claude/agents/lider.md': '.claude/agents/lider.md',
    '.claude/agents/autor.md': '.claude/agents/autor.md',
    '.claude/agents/implementador.md': '.claude/agents/implementador.md',
    '.claude/agents/revisor.md': '.claude/agents/revisor.md',
    '.claude/hooks/pretool.py': '.claude/hooks/pretool.py',
    '.claude/skills/sdd/SKILL.md': '.claude/skills/sdd/SKILL.md',
    '.microharness/sdd.py': '.microharness/sdd.py',
    'CLAUDE.md': 'CLAUDE.microsdd.md',
    '.claude/settings.json': '.claude/settings.json',
}
SETTINGS = '.claude/settings.json'
SETTINGS_ALT = '.claude/settings.microsdd.json'
INIT_FILES = ('docs/AGENT.md', 'docs/arquitectura.md', 'docs/convensiones.md',
              'docs/specificaciones.md', '.microharness/memory.json')
BEGIN = '<!-- microsdd:begin -->'
END = '<!-- microsdd:end -->'
BLOCK = (BEGIN,
         f'## {NAME}',
         '',
         f'Este repositorio usa {NAME}: micro arnés SDD por proyecto, agnóstico al stack y basado en el',
         'código de este repositorio. No es una configuración global de `~/.claude`.',
         '',
         '@CLAUDE.microsdd.md',
         END)
VERSION_CODE = 'import sys; print("%d.%d.%d" % sys.version_info[:3])'


def version() -> str:
    try:
        return metadata.version('microsdd')
    except metadata.PackageNotFoundError:
        return 'dev'


def banner() -> str:
    return (f'{NAME} {version()}\n'
            'ALERTA: micro arnés por proyecto; no es un arnés global y no modifica ~/.claude.\n')


def filter_path(value: str, prefix: str, base_prefix: str) -> str:
    """Quita del PATH los directorios bin/Scripts del entorno aislado (uvx) cuando prefix != base_prefix."""
    if prefix == base_prefix:
        return value
    excluded = {os.path.normcase(os.path.normpath(os.path.join(prefix, d))) for d in ('bin', 'Scripts')}
    kept = [p for p in value.split(os.pathsep)
            if p and os.path.normcase(os.path.normpath(p)) not in excluded]
    return os.pathsep.join(kept)


def remediation(problem: str, location: str) -> str:
    lines = [f'ERROR: {problem}. MicroSDD requiere un python3 real >= 3.10 en el PATH '
             '(el hook y sdd.py se invocan como python3).', 'Opciones:']
    if sys.platform == 'win32':
        if 'windowsapps' in location.lower():
            lines.append(f'  - {location} es el alias de ejecución de Microsoft Store: desactívalo en '
                         'Configuración > Aplicaciones > Configuración avanzada de aplicaciones > '
                         'Alias de ejecución de aplicaciones.')
        lines += ['  - Se exige python3.exe: los shims .cmd/.bat no sirven para Git Bash, donde corre el hook.',
                  '  - uv python install 3.12 --default (provee python3) y agrega su directorio al PATH.',
                  '  - Instala Python 3.10+ (python.org o winget install Python.Python.3.12) y '
                  'confirma que "python3 --version" funciona en Git Bash.']
    elif sys.platform == 'darwin':
        lines += ['  - brew install python@3.12', '  - uv python install 3.12 --default']
    else:
        lines += ['  - Instala python3 >= 3.10 con el gestor de paquetes (p. ej. sudo apt install python3).',
                  '  - uv python install 3.12 --default']
    return '\n'.join(lines)


def check_python(python: list[str] | None) -> tuple[list[str] | None, str | None]:
    if python is None:
        search = filter_path(os.environ.get('PATH', ''), sys.prefix, sys.base_prefix)
        # En Windows solo python3.exe, como lo resuelve Git Bash: se ignoran shims .cmd/.bat.
        found = shutil.which('python3.exe' if sys.platform == 'win32' else 'python3', path=search)
        if not found:
            return None, remediation('no se encontró python3 en el PATH', '')
        python = [found]
    try:
        result = subprocess.run([*python, '-c', VERSION_CODE], capture_output=True, text=True,
                                errors='replace', timeout=60)
    except (OSError, subprocess.SubprocessError) as err:
        return None, remediation(f'python3 no se pudo ejecutar ({err})', python[0])
    found_version = re.search(r'(\d+)\.(\d+)', result.stdout)
    if result.returncode != 0 or not found_version:
        return None, remediation(f'python3 falló (código {result.returncode})', python[0])
    if (int(found_version[1]), int(found_version[2])) < (3, 10):
        return None, remediation(f'python3 reporta {found_version[0]} (< 3.10)', python[0])
    return python, None


def same_path(a: Path, b: Path) -> bool:
    return os.path.normcase(str(a.resolve())) == os.path.normcase(str(b.resolve()))


def check_target(target: Path, home: Path) -> str | None:
    if same_path(target, home):
        return 'ERROR: el destino es el directorio home; MicroSDD se instala por repositorio.'
    claude = home / '.claude'
    if any(same_path(p, claude) for p in (target, *target.resolve().parents)):
        return 'ERROR: el destino está bajo ~/.claude; MicroSDD no es un arnés global.'
    try:
        result = subprocess.run(['git', '-C', str(target), 'rev-parse', '--show-toplevel'],
                                capture_output=True, text=True, errors='replace')
    except OSError:
        return 'ERROR: git no está disponible en el PATH.'
    if result.returncode != 0:
        return f'ERROR: {target} no es un repositorio Git.'
    if not same_path(Path(result.stdout.strip()), target):
        return f'ERROR: el destino debe ser la raíz del repositorio ({result.stdout.strip()}).'
    return None


def registry_block(existing: bytes | None, agents: bool) -> bytes:
    if existing is None:
        lines = (['@AGENTS.md', ''] if agents else []) + list(BLOCK)
        return ('\n'.join(lines) + '\n').encode('utf-8')
    eol = b'\r\n' if existing.count(b'\r\n') * 2 > existing.count(b'\n') else b'\n'
    block = eol.join(line.encode('utf-8') for line in BLOCK) + eol
    if not existing:
        return block
    separator = eol if existing.endswith(b'\n') else eol + eol
    return existing + separator + block


def plan(source: Path, target: Path, force: bool) -> tuple[list[tuple[str, str, Path | None, bytes | None]], bool]:
    """Clasifica cada entrada sin escribir. Devuelve (acciones, settings_alterno)."""
    actions = []
    alternate = False
    for src, dst in MANIFEST.items():
        data = (source / src).read_bytes()
        current = target / dst
        if dst == SETTINGS and current.is_file() and current.read_bytes() != data:
            alternate, dst, current = True, SETTINGS_ALT, target / SETTINGS_ALT
            if not current.exists():
                actions.append(('alterno', dst, source / src, None))
                continue
        if not current.exists():
            actions.append(('crear', dst, source / src, None))
        elif current.read_bytes() == data:
            actions.append(('sin cambios', dst, None, None))
        else:
            actions.append(('actualizar' if force else 'conflicto', dst, source / src, None))
    claude = target / 'CLAUDE.md'
    if not claude.exists():
        actions.append(('crear', 'CLAUDE.md', None, registry_block(None, (target / 'AGENTS.md').is_file())))
    elif BEGIN.encode('utf-8') in claude.read_bytes():
        actions.append(('sin cambios', 'CLAUDE.md', None, None))
    else:
        actions.append(('anexar registro', 'CLAUDE.md', None, registry_block(claude.read_bytes(), False)))
    return actions, alternate


def install(source: Path, target: Path, *, python: list[str] | None, home: Path,
            force: bool = False, dry_run: bool = False) -> int:
    reconfigure = getattr(sys.stdout, 'reconfigure', None)
    if reconfigure:
        reconfigure(errors='replace')
    print(banner())
    target = Path(target)
    error = check_target(target, Path(home))
    if error:
        print(error)
        return 1
    target = target.resolve()
    python, error = check_python(python)
    if error:
        print(error)
        return 1
    status = subprocess.run(['git', '--no-optional-locks', '-C', str(target), 'status', '--porcelain'],
                            capture_output=True, text=True, errors='replace')
    if status.stdout.strip():
        print('ADVERTENCIA: el árbol de trabajo tiene cambios sin confirmar; se continúa.')
    actions, alternate = plan(Path(source), target, force)
    print('Plan:')
    for label, dst, _, _ in actions:
        print(f'  [{label}] {dst}')
    conflicts = [dst for label, dst, _, _ in actions if label == 'conflicto']
    if conflicts:
        print('ERROR: archivos propios modificados (conflicto); no se escribió nada. '
              'Usa --force para sobrescribir solo archivos propios del arnés.')
        return 1
    if dry_run:
        print('Simulación (--dry-run): no se escribió nada.')
        return 0
    for label, dst, src, content in actions:
        if label == 'sin cambios':
            continue
        path = target / dst
        path.parent.mkdir(parents=True, exist_ok=True)
        if content is not None:
            path.write_bytes(content)
        else:
            shutil.copyfile(src, path)
        if dst == '.microharness/sdd.py' and os.name != 'nt':
            path.chmod(path.stat().st_mode | 0o111)
    init = subprocess.run([*python, '.microharness/sdd.py', 'init'], cwd=target, capture_output=True)
    if init.returncode != 0:
        print(f'ERROR: python3 .microharness/sdd.py init falló (código {init.returncode}).')
        return 1
    smoke = subprocess.run([*python, '.claude/hooks/pretool.py'], cwd=target, capture_output=True,
                           input=b'{"agent_type": "revisor", "tool_name": "Edit", "tool_input": {}}')
    if b'deny' not in smoke.stdout or b'solo lectura' not in smoke.stdout:
        print('ERROR: el smoke test del hook no produjo "deny" por "solo lectura"; '
              'revisa .claude/hooks/pretool.py.')
        return 1
    print('Smoke test del hook: revisor + Edit -> deny (correcto).')
    if alternate:
        print(f'AVISO: {SETTINGS} existente se conservó; `agent: lider` y el hook PreToolUse no están '
              f'activos hasta fusionar manualmente {SETTINGS_ALT} en {SETTINGS}.')
    files = [dst for _, dst, _, _ in actions] + [f for f in INIT_FILES if (target / f).is_file()]
    print('Próximos pasos:')
    print('  git add ' + ' '.join(files))
    print('  claude')
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='microsdd', description=f'{NAME}: instalador por proyecto.')
    sub = parser.add_subparsers(dest='command', required=True)
    cmd = sub.add_parser('install', help='Instala MicroSDD en la raíz de un repositorio Git.')
    cmd.add_argument('--target', default='.', help='Raíz del repositorio destino (por defecto: actual).')
    cmd.add_argument('--dry-run', action='store_true', help='Muestra el plan sin escribir.')
    cmd.add_argument('--force', action='store_true', help='Sobrescribe solo archivos propios del arnés.')
    args = parser.parse_args(argv)
    return install(PAYLOAD, Path(args.target), python=None, home=Path.home(),
                   force=args.force, dry_run=args.dry_run)
