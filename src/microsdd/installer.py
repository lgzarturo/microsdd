"""Instalador por proyecto de MicroSDD for Claude Opus 5.5 (solo biblioteca estándar)."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
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
    '.microharness/python.sh': '.microharness/python.sh',
    'CLAUDE.md': 'CLAUDE.microsdd.md',
    '.claude/settings.json': '.claude/settings.json',
}
SETTINGS = '.claude/settings.json'
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
        # En Windows solo uv.exe, como lo exige la forma exec: se ignoran shims .cmd/.bat.
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


def load_settings(path: Path) -> dict | None:
    """Contenido validado de settings.json; None si no existe. ValueError si no se puede fusionar."""
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_bytes().decode('utf-8'))
    except ValueError as err:
        raise ValueError(f'{SETTINGS} no es JSON válido ({err})') from err
    if not isinstance(data, dict):
        raise ValueError(f'la raíz de {SETTINGS} no es un objeto')
    hooks = data.get('hooks', {})
    if not isinstance(hooks, dict):
        raise ValueError(f'«hooks» de {SETTINGS} no es un objeto')
    if not isinstance(hooks.get('PreToolUse', []), list):
        raise ValueError(f'«hooks.PreToolUse» de {SETTINGS} no es una lista')
    return data


def dump_json(data: dict) -> bytes:
    return (json.dumps(data, indent=2, ensure_ascii=False) + '\n').encode('utf-8')


def fingerprint(entry) -> str:
    return hashlib.sha256(json.dumps(entry, sort_keys=True).encode('utf-8')).hexdigest()


def merge(current: dict, payload: dict) -> tuple[dict, dict]:
    """Aplica agent, model, effortLevel y la entrada PreToolUse del payload. Devuelve (nuevo, registro)."""
    new = copy.deepcopy(current)
    keys = {}
    for key in MERGE_KEYS:
        # agent solo existe por MicroSDD: aunque ya valga lider, off debe quitarlo.
        if key not in new or (key == 'agent' and new[key] == payload[key]):
            keys[key] = {'previous_absent': True}
        elif new[key] != payload[key]:
            keys[key] = {'previous': new[key]}
        new[key] = payload[key]
    entry = payload['hooks']['PreToolUse'][0]
    pre = new.setdefault('hooks', {}).setdefault('PreToolUse', [])
    if entry not in pre:
        pre.append(copy.deepcopy(entry))
    return new, {'keys': keys, 'hook': fingerprint(entry)}


def unmerge(current: dict, record: dict) -> dict:
    """Quita o restaura lo registrado por merge(); lo ajeno queda igual."""
    new = copy.deepcopy(current)
    for key, info in record.get('keys', {}).items():
        if info.get('previous_absent'):
            new.pop(key, None)
        else:
            new[key] = info['previous']
    hooks = new.get('hooks')
    if record.get('hook') and isinstance(hooks, dict) and 'PreToolUse' in hooks:
        hooks['PreToolUse'] = [e for e in hooks['PreToolUse'] if fingerprint(e) != record['hook']]
        if not hooks['PreToolUse']:
            del hooks['PreToolUse']
        if not hooks:
            del new['hooks']
    return new


def backup(path: Path) -> None:
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    shutil.copyfile(path, path.with_name(f'{path.name}.bak.{stamp}'))


def write_settings(path: Path, data: dict) -> None:
    if path.is_file():
        backup(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(dump_json(data))


def read_record(target: Path) -> dict | None:
    path = target / INSTALL_RECORD
    if not path.is_file():
        return None
    try:
        record = json.loads(path.read_bytes().decode('utf-8'))
        if not isinstance(record, dict) or not isinstance(record.get('settings'), dict):
            raise ValueError('falta «settings»')
    except ValueError as err:
        raise ValueError(f'{INSTALL_RECORD} no es válido ({err})') from err
    return record


def write_record(target: Path, record: dict) -> None:
    path = target / INSTALL_RECORD
    data = dump_json(record)
    if not path.is_file() or path.read_bytes() != data:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def install_record(actions, previous: dict | None, applied: dict, claude_before: bytes) -> dict:
    labels = {dst: (label, content) for label, dst, _, content in actions}
    old = (previous or {}).get('settings', {})
    label, content = labels['CLAUDE.md']
    if label == 'crear':
        claude_md = {'mode': 'created', 'text': content.decode('utf-8')}
    elif label == 'anexar registro':
        claude_md = {'mode': 'appended', 'text': content[len(claude_before):].decode('utf-8')}
    else:
        claude_md = (previous or {}).get('claude_md')
    # Las claves ya registradas conservan su valor previo original en reinstalaciones.
    return {'schema_version': 1,
            'settings': {'created': labels[SETTINGS][0] == 'crear' or bool(old.get('created')),
                         'enabled': True,
                         'keys': {**applied['keys'], **old.get('keys', {})},
                         'hook': applied['hook']},
            'claude_md': claude_md}


def plan(source: Path, target: Path, force: bool) -> list[tuple[str, str, Path | None, bytes | None]]:
    """Clasifica cada entrada sin escribir. ValueError si .claude/settings.json no se puede fusionar."""
    actions = []
    for src, dst in MANIFEST.items():
        data = (source / src).read_bytes()
        current = target / dst
        if dst == SETTINGS and current.is_file():
            existing = load_settings(current)
            merged, _ = merge(existing, json.loads(data))
            actions.append(('sin cambios', dst, None, None) if merged == existing
                           else ('fusionar', dst, None, dump_json(merged)))
        elif not current.exists():
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
    return actions


def install(source: Path, target: Path, *, uv: list[str] | None, home: Path,
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
    error = check_uv(uv)
    if error:
        print(error)
        return 1
    status = subprocess.run(['git', '--no-optional-locks', '-C', str(target), 'status', '--porcelain'],
                            capture_output=True, text=True, errors='replace')
    if status.stdout.strip():
        print('ADVERTENCIA: el árbol de trabajo tiene cambios sin confirmar; se continúa.')
    source = Path(source)
    try:
        actions = plan(source, target, force)
        previous = read_record(target)
    except ValueError as err:
        print(f'ERROR: {err}; no se escribió nada.')
        return 1
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
    _, applied = merge(load_settings(target / SETTINGS) or {}, json.loads((source / SETTINGS).read_bytes()))
    claude = target / 'CLAUDE.md'
    claude_before = claude.read_bytes() if claude.is_file() else b''
    for label, dst, src, content in actions:
        if label == 'sin cambios':
            continue
        path = target / dst
        path.parent.mkdir(parents=True, exist_ok=True)
        if label == 'fusionar':
            backup(path)
        if content is not None:
            path.write_bytes(content)
        else:
            shutil.copyfile(src, path)
        if dst == '.microharness/sdd.py' and os.name != 'nt':
            path.chmod(path.stat().st_mode | 0o111)
    write_record(target, install_record(actions, previous, applied, claude_before))
    init = subprocess.run([sys.executable, '.microharness/sdd.py', 'init'], cwd=target, capture_output=True)
    if init.returncode != 0:
        print(f'ERROR: .microharness/sdd.py init falló (código {init.returncode}).')
        return 1
    for line in init.stdout.decode('utf-8', errors='replace').splitlines():
        if line.startswith('AVISO:'):
            print(line)
    smoke = subprocess.run([sys.executable, '.claude/hooks/pretool.py'], cwd=target, capture_output=True,
                           input=b'{"agent_type": "revisor", "tool_name": "Edit", "tool_input": {}}')
    if b'deny' not in smoke.stdout or b'solo lectura' not in smoke.stdout:
        print('ERROR: el smoke test del hook no produjo "deny" por "solo lectura"; '
              'revisa .claude/hooks/pretool.py.')
        return 1
    print('Smoke test del hook: revisor + Edit -> deny (correcto).')
    if (target / LEGACY_SETTINGS).is_file():
        print(f'AVISO: {LEGACY_SETTINGS} es obsoleto (Claude Code no lo lee) y {SETTINGS} ya se fusionó; '
              'bórralo o quítalo con microsdd uninstall.')
    files = ([dst for _, dst, _, _ in actions] + [f for f in INIT_FILES if (target / f).is_file()]
             + [INSTALL_RECORD])
    print('Próximos pasos:')
    print('  git add ' + ' '.join(files))
    print('  claude')
    return 0


def toggle(source: Path, target: Path, enable: bool) -> int:
    """on/off: aplica o retira de .claude/settings.json lo registrado en el manifiesto."""
    target = Path(target)
    path = target / SETTINGS
    try:
        record = read_record(target)
        current = load_settings(path)
    except ValueError as err:
        print(f'ERROR: {err}; no se escribió nada.')
        return 1
    if record is None:
        print(f'ERROR: no existe {INSTALL_RECORD}; instala primero con microsdd install. No se escribió nada.')
        return 1
    state = record['settings']
    if enable:
        new, applied = merge(current or {}, json.loads((Path(source) / SETTINGS).read_bytes()))
        state = {**state, 'enabled': True, 'keys': {**applied['keys'], **state.get('keys', {})},
                 'hook': applied['hook']}
    else:
        new = None if current is None else unmerge(current, state)
        state = {**state, 'enabled': False, 'keys': {}, 'hook': None}
    if new is not None and new != current:
        write_settings(path, new)
    write_record(target, {**record, 'settings': state})
    word = 'activado' if enable else 'desactivado'
    print(f'MicroSDD {word} en {SETTINGS}; reinicia la sesión de Claude Code.')
    return 0


def status(source: Path, target: Path) -> int:
    """Solo lectura: activo, inactivo o parcial según el contenido real de .claude/settings.json."""
    try:
        current = load_settings(Path(target) / SETTINGS) or {}
    except ValueError as err:
        print(f'ERROR: {err}.')
        return 1
    entry = json.loads((Path(source) / SETTINGS).read_bytes())['hooks']['PreToolUse'][0]
    agent = current.get('agent') == 'lider'
    hook = entry in current.get('hooks', {}).get('PreToolUse', [])
    print('estado: ' + ('activo' if agent and hook else 'parcial' if agent or hook else 'inactivo'))
    for key in MERGE_KEYS:
        print(f'{key}: {json.dumps(current.get(key), ensure_ascii=False)}')
    print('hook PreToolUse: ' + ('presente' if hook else 'ausente'))
    return 0


def restore_claude_md(target: Path, info: dict | None) -> None:
    path = target / 'CLAUDE.md'
    if not path.is_file():
        return
    data = path.read_bytes()
    text = (info or {}).get('text', '').encode('utf-8')
    if info and info.get('mode') == 'created' and data == text:
        path.unlink()
        print('  [eliminar] CLAUDE.md')
    elif text and data.endswith(text):
        path.write_bytes(data[:-len(text)])
        print('  [restaurar] CLAUDE.md')
    elif BEGIN.encode('utf-8') in data:
        start = data.index(BEGIN.encode('utf-8'))
        end = data.find(END.encode('utf-8'), start)
        if end < 0:
            print(f'AVISO: CLAUDE.md tiene {BEGIN} sin {END}; no se modificó.')
            return
        rest = data[end + len(END):]
        for eol in (b'\r\n', b'\n'):
            if rest.startswith(eol):
                rest = rest[len(eol):]
                break
        path.write_bytes(data[:start] + rest)
        print('AVISO: CLAUDE.md cambió tras la instalación; solo se quitó el bloque de registro. Revísalo.')


def uninstall(source: Path, target: Path, force: bool = False) -> int:
    """Quita lo que instaló MicroSDD según el manifiesto; conserva docs/, spec/, memory.json y lo ajeno."""
    target = Path(target)
    settings = target / SETTINGS
    try:
        record = read_record(target)
        current = load_settings(settings)
    except ValueError as err:
        print(f'ERROR: {err}; no se escribió nada.')
        return 1
    if record is None:
        print(f'ERROR: no existe {INSTALL_RECORD}; no se sabe qué instaló MicroSDD. No se escribió nada.')
        return 1
    own, conflicts = [], []
    for src, dst in MANIFEST.items():
        path = target / dst
        if dst == SETTINGS or not path.is_file():
            continue
        own.append((dst, path))
        if path.read_bytes() != (Path(source) / src).read_bytes():
            conflicts.append(dst)
    for dst in conflicts:
        print(f'  [conflicto] {dst}')
    if conflicts and not force:
        print('ERROR: archivos propios modificados (conflicto); no se escribió nada. '
              'Usa --force para eliminarlos igualmente.')
        return 1
    state = record['settings']
    if current is not None:
        new = unmerge(current, state) if state.get('enabled') else current
        if state.get('created') and not new:
            settings.unlink()
            print(f'  [eliminar] {SETTINGS}')
        elif new != current:
            write_settings(settings, new)
            print(f'  [restaurar] {SETTINGS}')
    for dst, path in own:
        path.unlink()
        print(f'  [eliminar] {dst}')
    legacy = target / LEGACY_SETTINGS
    if legacy.is_file():
        legacy.unlink()
        print(f'  [eliminar] {LEGACY_SETTINGS}')
    restore_claude_md(target, record.get('claude_md'))
    (target / INSTALL_RECORD).unlink()
    print(f'  [eliminar] {INSTALL_RECORD}')
    print('MicroSDD desinstalado; se conservan docs/, spec/ y .microharness/memory.json. Revisa git status.')
    return 0


def human_gate(command: str) -> str | None:
    if 'CLAUDECODE' in os.environ or sys.stdin is None or not sys.stdin.isatty():
        return (f'ERROR: microsdd {command} solo lo ejecuta el humano en una terminal interactiva, fuera de '
                'Claude Code (CLAUDECODE definido o stdin sin TTY); no se escribió nada.')
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='microsdd', description=f'{NAME}: instalador por proyecto.')
    sub = parser.add_subparsers(dest='command', required=True)
    target_help = 'Raíz del repositorio destino (por defecto: actual).'
    cmd = sub.add_parser('install', help='Instala MicroSDD en la raíz de un repositorio Git.')
    cmd.add_argument('--target', default='.', help=target_help)
    cmd.add_argument('--dry-run', action='store_true', help='Muestra el plan sin escribir.')
    cmd.add_argument('--force', action='store_true', help='Sobrescribe solo archivos propios del arnés.')
    cmd = sub.add_parser('uninstall', help=f'Quita MicroSDD según {INSTALL_RECORD} (solo el humano).')
    cmd.add_argument('--target', default='.', help=target_help)
    cmd.add_argument('--force', action='store_true', help='Elimina también archivos propios modificados.')
    for name, text in (('on', f'Reaplica MicroSDD en {SETTINGS} (solo el humano).'),
                       ('off', f'Retira MicroSDD de {SETTINGS} (solo el humano).'),
                       ('status', f'Informa si MicroSDD está activo, inactivo o parcial en {SETTINGS}.')):
        sub.add_parser(name, help=text).add_argument('--target', default='.', help=target_help)
    args = parser.parse_args(argv)
    if args.command == 'install':
        return install(PAYLOAD, Path(args.target), uv=None, home=Path.home(),
                       force=args.force, dry_run=args.dry_run)
    if args.command != 'status':
        error = human_gate(args.command)
        if error:
            print(error)
            return 1
    target = Path(args.target).resolve()
    if args.command == 'status':
        return status(PAYLOAD, target)
    if args.command == 'uninstall':
        return uninstall(PAYLOAD, target, force=args.force)
    return toggle(PAYLOAD, target, args.command == 'on')
