"""Instalador por proyecto de MicroSDD for Claude Opus 5.5 (solo biblioteca estándar)."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import re
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
# Solo con microsdd install --with-metrics (no van en MANIFEST ni en instalación por defecto).
METRICS_MANIFEST = {
    '.microharness/metrics.py': '.microharness/metrics.py',
    '.microharness/pricing.json': '.microharness/pricing.json',
}
METRICS_HOOK_EVENTS = ('SubagentStop', 'SessionEnd')
GITIGNORE_METRICS = '.microharness/metrics/'
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
AGENT_REL_PATHS = (
    '.claude/agents/lider.md',
    '.claude/agents/autor.md',
    '.claude/agents/implementador.md',
    '.claude/agents/revisor.md',
)
DEFAULT_MODEL = 'claude-opus-5-5'
DEFAULT_EFFORT = 'medium'
EFFORTS = ('low', 'medium', 'high', 'xhigh', 'max')
FRONTMATTER_RE = re.compile(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', re.DOTALL)
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


def target_runtime(target: Path) -> tuple[str, str]:
    """Modelo y esfuerzo efectivos desde config.json del destino (fuente de verdad) o defaults."""
    path = Path(target) / '.microharness' / 'config.json'
    model, effort = DEFAULT_MODEL, DEFAULT_EFFORT
    if not path.is_file():
        return model, effort
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as err:
        raise ValueError(f'.microharness/config.json: ilegible ({err})') from err
    if not isinstance(data, dict):
        raise ValueError('.microharness/config.json: debe ser un objeto JSON')
    profiles = data.get('profiles') if isinstance(data.get('profiles'), dict) else {}
    pid = data.get('profile')
    if isinstance(pid, str) and pid.strip() and pid.strip() in profiles:
        chosen = profiles[pid.strip()]
        if isinstance(chosen, dict):
            if isinstance(chosen.get('model'), str) and chosen['model'].strip():
                model = chosen['model'].strip()
            if chosen.get('effort') in EFFORTS:
                effort = chosen['effort']
    if isinstance(data.get('model'), str) and data['model'].strip():
        model = data['model'].strip()
    if data.get('effort') in EFFORTS:
        effort = data['effort']
    return model, effort


def parse_frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ':' not in line:
            continue
        key, _, value = line.partition(':')
        fields[key.strip()] = value.strip()
    return fields


def apply_frontmatter_fields(text: str, updates: dict[str, str]) -> str:
    match = FRONTMATTER_RE.match(text)
    if match:
        body = text[match.end():]
        lines = match.group(1).splitlines()
    else:
        body = text
        lines = []
    seen: set[str] = set()
    new_lines: list[str] = []
    for line in lines:
        if ':' in line:
            key = line.partition(':')[0].strip()
            if key in updates:
                new_lines.append(f'{key}: {updates[key]}')
                seen.add(key)
                continue
        new_lines.append(line)
    for key, value in updates.items():
        if key not in seen:
            new_lines.append(f'{key}: {value}')
    return '---\n' + '\n'.join(new_lines) + '\n---\n' + body


def payload_with_runtime(source: Path, rel: str, model: str, effort: str) -> bytes:
    raw = (source / rel).read_bytes()
    if rel == SETTINGS:
        data = json.loads(raw.decode('utf-8'))
        if data.get('model') == model and data.get('effortLevel') == effort:
            return raw
        data['model'] = model
        data['effortLevel'] = effort
        return dump_json(data)
    if rel in AGENT_REL_PATHS:
        text = raw.decode('utf-8')
        fields = parse_frontmatter(text)
        if fields.get('model') == model and fields.get('effort') == effort:
            return raw
        return apply_frontmatter_fields(text, {'model': model, 'effort': effort}).encode('utf-8')
    return raw


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


def load_settings_local(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except ValueError as err:
        raise ValueError(f"{SETTINGS_LOCAL} no es JSON válido ({err})") from err
    if not isinstance(data, dict):
        raise ValueError(f"la raíz de {SETTINGS_LOCAL} no es un objeto")
    return data


def merge_settings_local(current: dict | None) -> tuple[dict, list[str]]:
    new = {} if current is None else copy.deepcopy(current)
    added = []
    for key, value in SETTINGS_LOCAL_DEFAULTS.items():
        if key not in new:
            new[key] = copy.deepcopy(value)
            added.append(key)
    return new, added


def fingerprint(entry) -> str:
    return hashlib.sha256(json.dumps(entry, sort_keys=True).encode('utf-8')).hexdigest()


def metrics_hook_entry(event_name: str) -> dict:
    """Hook async para SubagentStop / SessionEnd (§1.3 microsdd)."""
    return {
        'hooks': [{
            'type': 'command',
            'command': 'uv',
            'args': [
                'run', '--no-project', '--quiet', '--python', '>=3.10',
                '${CLAUDE_PROJECT_DIR}/.microharness/metrics.py', 'hook', event_name,
            ],
            'async': True,
            'timeout': 60,
        }]
    }


def merge(current: dict, payload: dict, *, with_metrics: bool = False) -> tuple[dict, dict]:
    new = copy.deepcopy(current)
    keys = {}
    for key in MERGE_KEYS:
        if key not in new or (key == 'agent' and new[key] == payload[key]):
            keys[key] = {'previous_absent': True}
        elif new[key] != payload[key]:
            keys[key] = {'previous': new[key]}
        new[key] = payload[key]
    entry = payload['hooks']['PreToolUse'][0]
    pre = new.setdefault('hooks', {}).setdefault('PreToolUse', [])
    if entry not in pre:
        pre.append(copy.deepcopy(entry))
    metrics_hooks: dict[str, str] = {}
    if with_metrics:
        for event_name in METRICS_HOOK_EVENTS:
            hook_entry = metrics_hook_entry(event_name)
            bucket = new.setdefault('hooks', {}).setdefault(event_name, [])
            if hook_entry not in bucket:
                bucket.append(copy.deepcopy(hook_entry))
            metrics_hooks[event_name] = fingerprint(hook_entry)
    return new, {'keys': keys, 'hook': fingerprint(entry), 'metrics_hooks': metrics_hooks}


def unmerge(current: dict, record: dict) -> dict:
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
    metrics_hooks = record.get('metrics_hooks') or {}
    if metrics_hooks and isinstance(hooks, dict):
        for event_name, fp in metrics_hooks.items():
            if event_name not in hooks:
                continue
            hooks[event_name] = [e for e in hooks[event_name] if fingerprint(e) != fp]
            if not hooks[event_name]:
                del hooks[event_name]
    if isinstance(hooks, dict) and not hooks:
        del new['hooks']
    return new


def ensure_gitignore_metrics(target: Path) -> bool:
    """Añade `.microharness/metrics/` a .gitignore si falta. Devuelve True si escribió."""
    path = target / '.gitignore'
    line = GITIGNORE_METRICS
    existing = path.read_text(encoding='utf-8') if path.is_file() else ''
    lines = existing.splitlines()
    if line in lines or any(x.strip() == line for x in lines):
        return False
    suffix = '' if not existing or existing.endswith('\n') else '\n'
    path.write_text(existing + suffix + line + '\n', encoding='utf-8')
    return True


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


def install_record(actions, previous: dict | None, applied: dict, claude_before: bytes,
                    settings_local_added: list[str] | None = None,
                    with_metrics: bool = False) -> dict:
    labels = {dst: (label, content) for label, dst, _, content in actions}
    old = (previous or {}).get("settings", {})
    label, content = labels["CLAUDE.md"]
    if label == "crear":
        claude_md = {"mode": "created", "text": content.decode("utf-8")}
    elif label == "anexar registro":
        claude_md = {"mode": "appended", "text": content[len(claude_before):].decode("utf-8")}
    else:
        claude_md = (previous or {}).get("claude_md")
    prev_local = (previous or {}).get("settings_local") or {}
    local_label, local_content = labels.get(SETTINGS_LOCAL, ("sin cambios", None))
    keys_added = list(prev_local.get("keys_added") or [])
    if local_label == "crear":
        keys_added = list(SETTINGS_LOCAL_DEFAULTS.keys())
    elif local_label == "fusionar":
        for key in (settings_local_added or []):
            if key not in keys_added:
                keys_added.append(key)
    settings_local = {
        "created": bool(prev_local.get("created")) or local_label == "crear",
        "keys_added": keys_added,
    }
    settings = {"created": labels[SETTINGS][0] == "crear" or bool(old.get("created")),
                "enabled": True,
                "keys": {**applied["keys"], **old.get("keys", {})},
                "hook": applied["hook"]}
    if with_metrics or applied.get('metrics_hooks') or old.get('metrics_hooks'):
        settings['metrics_hooks'] = applied.get('metrics_hooks') or old.get('metrics_hooks') or {}
    return {"schema_version": 1,
            "settings": settings,
            "settings_local": settings_local,
            "claude_md": claude_md,
            "with_metrics": bool(with_metrics or (previous or {}).get('with_metrics'))}


def plan(source: Path, target: Path, force: bool,
         with_metrics: bool = False) -> list[tuple[str, str, Path | None, bytes | None]]:
    actions = []
    model, effort = target_runtime(target)
    items = list(MANIFEST.items())
    if with_metrics:
        items += list(METRICS_MANIFEST.items())
    for src, dst in items:
        data = payload_with_runtime(source, src, model, effort)
        current = target / dst
        if dst == SETTINGS:
            if not current.is_file():
                if with_metrics:
                    merged, _ = merge({}, json.loads(data.decode('utf-8')), with_metrics=True)
                    actions.append(('crear', dst, None, dump_json(merged)))
                elif data != (source / src).read_bytes():
                    actions.append(('crear', dst, None, data))
                else:
                    actions.append(('crear', dst, source / src, None))
            else:
                existing = load_settings(current)
                merged, _ = merge(existing or {}, json.loads(data.decode('utf-8')),
                                  with_metrics=with_metrics)
                if merged == existing:
                    actions.append(('sin cambios', dst, None, None))
                else:
                    actions.append(('fusionar', dst, None, dump_json(merged)))
            continue
        if dst in AGENT_REL_PATHS and current.is_file() and not force:
            # Alinea model/effort solo si el cuerpo del agente coincide con el payload.
            if current.read_bytes() == data:
                actions.append(('sin cambios', dst, None, None))
            else:
                current_text = current.read_text(encoding='utf-8')
                source_text = data.decode('utf-8')
                cur_match = FRONTMATTER_RE.match(current_text)
                src_match = FRONTMATTER_RE.match(source_text)
                if (cur_match and src_match
                        and current_text[cur_match.end():] == source_text[src_match.end():]):
                    updated = apply_frontmatter_fields(
                        current_text, {'model': model, 'effort': effort}
                    ).encode('utf-8')
                    actions.append(('sin cambios', dst, None, None) if updated == current.read_bytes()
                                   else ('fusionar', dst, None, updated))
                else:
                    actions.append(('conflicto', dst, source / src, None))
        elif not current.exists():
            actions.append(('crear', dst, None, data) if data != (source / src).read_bytes()
                           else ('crear', dst, source / src, None))
        elif current.read_bytes() == data:
            actions.append(('sin cambios', dst, None, None))
        else:
            actions.append(('actualizar' if force else 'conflicto', dst,
                            None if force else source / src, data if force else None))
    claude = target / 'CLAUDE.md'
    if not claude.exists():
        actions.append(('crear', 'CLAUDE.md', None, registry_block(None, (target / 'AGENTS.md').is_file())))
    elif BEGIN.encode('utf-8') in claude.read_bytes():
        actions.append(('sin cambios', 'CLAUDE.md', None, None))
    else:
        actions.append(('anexar registro', 'CLAUDE.md', None, registry_block(claude.read_bytes(), False)))
    local = target / SETTINGS_LOCAL
    current_local = load_settings_local(local)
    merged_local, added_local = merge_settings_local(current_local)
    if current_local is None:
        actions.append(("crear", SETTINGS_LOCAL, None, dump_json(merged_local)))
    elif added_local:
        actions.append(("fusionar", SETTINGS_LOCAL, None, dump_json(merged_local)))
    else:
        actions.append(("sin cambios", SETTINGS_LOCAL, None, None))
    return actions


def install(source: Path, target: Path, *, uv: list[str] | None, home: Path,
            force: bool = False, dry_run: bool = False, with_metrics: bool = False) -> int:
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
    if with_metrics:
        missing = [src for src in METRICS_MANIFEST if not (source / src).is_file()]
        if missing:
            print('ERROR: --with-metrics requiere ' + ', '.join(missing) + '; no se escribió nada.')
            return 1
    try:
        actions = plan(source, target, force, with_metrics=with_metrics)
        previous = read_record(target)
    except ValueError as err:
        print(f'ERROR: {err}; no se escribió nada.')
        return 1
    print('Plan:')
    for label, dst, _, _ in actions:
        print(f'  [{label}] {dst}')
    if with_metrics:
        print('  [opción] --with-metrics: metrics.py, pricing.json, hooks SubagentStop/SessionEnd')
    conflicts = [dst for label, dst, _, _ in actions if label == 'conflicto']
    if conflicts:
        print('ERROR: archivos propios modificados (conflicto); no se escribió nada. '
              'Usa --force para sobrescribir solo archivos propios del arnés.')
        return 1
    if dry_run:
        print('Simulación (--dry-run): no se escribió nada.')
        return 0
    model, effort = target_runtime(target)
    _, applied = merge(load_settings(target / SETTINGS) or {},
                       json.loads(payload_with_runtime(source, SETTINGS, model, effort)),
                       with_metrics=with_metrics)
    _local_data = load_settings_local(target / SETTINGS_LOCAL)
    _, local_added = merge_settings_local(_local_data)
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
        if dst in ('.microharness/sdd.py', '.microharness/metrics.py') and os.name != 'nt':
            path.chmod(path.stat().st_mode | 0o111)
    if with_metrics:
        ensure_gitignore_metrics(target)
    write_record(target, install_record(actions, previous, applied, claude_before,
                                       settings_local_added=local_added,
                                       with_metrics=with_metrics))
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
    written_local = any(label != 'sin cambios' and dst == SETTINGS_LOCAL for label, dst, _, _ in actions)
    files = ([dst for label, dst, _, _ in actions if not (dst == SETTINGS_LOCAL and label == 'sin cambios')]
             + [f for f in INIT_FILES if (target / f).is_file()]
             + [INSTALL_RECORD])
    if written_local:
        print(f'AVISO: {SETTINGS_LOCAL} es local (suele ignorarse en git); se incluyó en git add si se escribió.')
    print('Próximos pasos:')
    print('  git add ' + ' '.join(files))
    print('  claude')
    return 0


def toggle(source: Path, target: Path, enable: bool) -> int:
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
        model, effort = target_runtime(target)
        payload = json.loads(payload_with_runtime(Path(source), SETTINGS, model, effort))
        with_metrics = bool((record or {}).get('with_metrics'))
        new, applied = merge(current or {}, payload, with_metrics=with_metrics)
        state = {**state, 'enabled': True, 'keys': {**applied['keys'], **state.get('keys', {})},
                 'hook': applied['hook']}
        if applied.get('metrics_hooks'):
            state['metrics_hooks'] = applied['metrics_hooks']
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
    if record.get('with_metrics'):
        for dst in METRICS_MANIFEST.values():
            path = target / dst
            if path.is_file():
                path.unlink()
                print(f'  [eliminar] {dst}')
    legacy = target / LEGACY_SETTINGS
    if legacy.is_file():
        legacy.unlink()
        print(f'  [eliminar] {LEGACY_SETTINGS}')
    local_info = record.get('settings_local') or {}
    local_path = target / SETTINGS_LOCAL
    if local_path.is_file() and local_info:
        try:
            before = load_settings_local(local_path) or {}
        except ValueError:
            before = None
        if before is not None:
            after = dict(before)
            for key in local_info.get('keys_added', []):
                after.pop(key, None)
            if not after and local_info.get('created'):
                local_path.unlink()
                print(f'  [eliminar] {SETTINGS_LOCAL}')
            elif after != before:
                local_path.write_bytes(dump_json(after))
                print(f'  [restaurar] {SETTINGS_LOCAL}')
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
    cmd.add_argument('--with-metrics', action='store_true',
                     help='Instala metrics.py, pricing.json y hooks SubagentStop/SessionEnd (async).')
    cmd = sub.add_parser('uninstall', help=f'Quita MicroSDD según {INSTALL_RECORD} (solo el humano).')
    cmd.add_argument('--target', default='.', help=target_help)
    cmd.add_argument('--force', action='store_true', help='Elimina también archivos propios modificados.')
    for name, text in (('on', f'Reaplica MicroSDD en {SETTINGS} (solo el humano).'),
                       ('off', f'Retira MicroSDD de {SETTINGS} (solo el humano).'),
                       ('status', f'Informa si MicroSDD está activo, inactivo o parcial en {SETTINGS}.')):
        sub.add_parser(name, help=text).add_argument('--target', default='.', help=target_help)
    wt = sub.add_parser('worktree', help='Sincroniza arnés y docs hacia un git worktree (solo el humano).')
    wt_sub = wt.add_subparsers(dest='worktree_command', required=True)
    sync = wt_sub.add_parser('sync', help='Copia lanzadores, sdd.py y docs/ al worktree.')
    sync.add_argument('ruta', help='Raíz del worktree destino.')
    sync.add_argument('--source', default='.', help='Checkout origen con .microharness/ y docs/.')
    sync.add_argument('--with-memory', action='store_true',
                      help='Copia .microharness/memory.json del origen (copia; nunca symlink).')
    args = parser.parse_args(argv)
    if args.command == 'install':
        return install(PAYLOAD, Path(args.target), uv=None, home=Path.home(),
                       force=args.force, dry_run=args.dry_run, with_metrics=args.with_metrics)
    if args.command == 'worktree':
        if args.worktree_command != 'sync':
            parser.error('subcomando worktree no reconocido')
        error = human_gate('worktree sync')
        if error:
            print(error)
            return 1
        return worktree_sync(Path(args.source), Path(args.ruta), with_memory=args.with_memory)
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
