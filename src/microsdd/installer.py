"""Instalador por proyecto de MicroSDD for Claude Opus 5.5 (solo biblioteca estándar)."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

try:
    from microsdd.worktree import worktree_sync
except ImportError:  # carga directa del archivo (p. ej. tests/test_installer.py)
    _wt = Path(__file__).resolve().parent / 'worktree.py'
    _spec = importlib.util.spec_from_file_location('_microsdd_worktree', _wt)
    _mod = importlib.util.module_from_spec(_spec)
    assert _spec.loader is not None
    _spec.loader.exec_module(_mod)
    worktree_sync = _mod.worktree_sync

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
    '.microharness/python.sh': '.microharness/python.sh',
    '.microharness/python.ps1': '.microharness/python.ps1',
    '.microharness/python.cmd': '.microharness/python.cmd',
    'CLAUDE.md': 'CLAUDE.microsdd.md',
    '.claude/settings.json': '.claude/settings.json',
}
SETTINGS = '.claude/settings.json'
SETTINGS_LOCAL = '.claude/settings.local.json'
SETTINGS_LOCAL_DEFAULTS = {
    'claudeMdExcludes': ['~/.claude/CLAUDE.md'],
    'plansDirectory': 'docs/plans',
}
LEGACY_SETTINGS = '.claude/settings.microsdd.json'
INSTALL_RECORD = '.microharness/install.json'
MERGE_KEYS = ('agent', 'model', 'effortLevel')
INIT_FILES = ('docs/AGENT.md', 'docs/arquitectura.md', 'docs/convenciones.md',
              'docs/especificaciones.md', '.microharness/memory.json')
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


def remediation(problem: str) -> str:
    lines = [f'ERROR: {problem}. MicroSDD requiere uv ejecutable en el PATH '
             '(el hook se ejecuta con "uv run" en forma exec).', 'Opciones:']
    if sys.platform == 'win32':
        lines += ['  - Se exige uv.exe: los shims .cmd/.bat no sirven en forma exec.',
                  '  - powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"',
                  '  - winget install astral-sh.uv']
    elif sys.platform == 'darwin':
        lines += ['  - brew install uv', '  - curl -LsSf https://astral.sh/uv/install.sh | sh']
    else:
        lines += ['  - curl -LsSf https://astral.sh/uv/install.sh | sh']
    return '\n'.join(lines)


def check_uv(uv: list[str] | None) -> str | None:
    if uv is None:
        search = filter_path(os.environ.get('PATH', ''), sys.prefix, sys.base_prefix)
        found = shutil.which('uv.exe' if sys.platform == 'win32' else 'uv', path=search)
        if not found:
            return remediation('no se encontró uv en el PATH')
        uv = [found]
    try:
        result = subprocess.run([*uv, '--version'], capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as err:
        return remediation(f'uv no se pudo ejecutar ({err})')
    if result.returncode != 0:
        return remediation(f'uv --version falló (código {result.returncode})')
    return None


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
