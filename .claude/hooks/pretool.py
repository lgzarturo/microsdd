#!/usr/bin/env python3
"""Guardia de herramientas nativas Claude Code (best effort, NO sandbox)."""
import json
import os
import re
import shlex
import sys
from pathlib import Path, PurePosixPath


PROTECTED_RE = re.compile(r'microharness|memory\.json|sdd\.py', re.I)
SDD_ALLOWED = ('init', 'new', 'check', 'review', 'commit-check', 'note', 'release', '--version', '--help')
LAUNCHERS = (
    ['sh', '.microharness/python.sh'],
    ['python'], ['python3'], ['python.exe'],
    ['py', '-3'],
    ['.microharness/python.ps1'],
    ['cmd', '/c', '.microharness/python.cmd'],
    ['pwsh', '-File', '.microharness/python.ps1'],
    ['powershell', '-File', '.microharness/python.ps1'],
)
HARNESS_EDITABLE = (
    '.microharness/sdd.py',
    '.microharness/python.sh',
    '.microharness/python.ps1',
    '.microharness/python.cmd',
)
TOGGLE_RE = re.compile(r'(?:microsdd|installer\.py).*\b(?:on|off|uninstall)\b', re.I | re.S)
SETTINGS_RE = re.compile(r'settings(?:\.local)?\.json', re.I)
SETTINGS_GIT = ('add', 'diff', 'status', 'log', 'show', 'commit')
EXEC_EXTS = ('.py', '.sh', '.bash', '.zsh', '.ps1', '.bat', '.cmd', '.exe')
REVIEWER_SDD_CHECK_RE = re.compile(
    r'^(?:&\s+)?(?:'
    r'python(?:3(?:\.\d+)?|\.exe)?'
    r'|py -3'
    r'|sh \.microharness/python\.sh'
    r'|\.microharness/python\.ps1'
    r'|cmd /c \.microharness/python\.cmd'
    r'|(?:pwsh|powershell) -File \.microharness/python\.ps1'
    r'|uv run --no-project(?: --quiet)?(?: --python (?:\'>=3\.[0-9]+\'|">=3\.[0-9]+"|3\.[0-9]+))?'
    r') \.microharness/sdd\.py check [a-z][a-z0-9-]* --run$'
)
REVIEWER_GIT_RE = re.compile(
    r'git (diff|status)(?: (?!'
    r'--output(?:[= ]|$)|--ext-diff(?: |$)|--textconv(?:[= ]|$)|--open-files-in-pager(?:[= ]|$)|-[^ -]*O'
    r')[\w./:^~=+,-]+)*'
)


def msg_approve() -> str:
    if os.name == 'nt':
        return ('approve y seal los ejecuta el humano en su terminal fuera de Claude Code; '
                'usa python .microharness\\sdd.py o .\\.microharness\\python.ps1, no PowerShell/Bash del agente.')
    return ('approve y seal los ejecuta el humano en su terminal fuera de Claude Code; '
            'no uses Bash/PowerShell del agente para eso.')


def msg_protected() -> str:
    if os.name == 'nt':
        version_hint = '.\\.microharness\\python.ps1 --version o -m unittest'
    else:
        version_hint = 'sh .microharness/python.sh --version o -m unittest'
    return ('Comando denegado: menciona microharness, memory.json o sdd.py fuera de las formas '
            'permitidas (lanzador admitido + .microharness/sdd.py con init, new, check, review, '
            f'commit-check, note, release, --version o --help; {version_hint}; '
            'git add|diff|status|log|show|commit -m). '
            + msg_approve() + ' Lee la memoria con Read.')


def msg_chain() -> str:
    return ('Comando encadenado denegado: no combines operaciones sensibles (sdd/microharness/settings/'
            'microsdd) con &&, || o ;. Ejecuta cada paso por separado; ' + msg_approve())


def msg_unparseable() -> str:
    return ('Comando no analizable con seguridad (comillas desbalanceadas, operadores, $, '
            'backticks o escapes). Reformúlalo sin sustituciones ni operadores; ' + msg_approve())


MSG_TOGGLE = ('microsdd on|off|uninstall solo lo ejecuta el humano en su terminal fuera de Claude Code.')
MSG_SETTINGS_WRITE = ('No modifiques .claude/settings.json ni settings.local.json desde el agente; '
                      'usa Read o cat/jq para leerlos; los cambios los hace el humano.')
MSG_SETTINGS_READ_HINT = ('Para leer settings usa cat, head, tail, grep, rg, jq o python -m json.tool; '
                          'no los modifiques desde el agente.')
MSG_EXECUTABLES = ('El líder/autor no escriben ejecutables en docs/ ni spec/; ' + msg_approve())
MSG_DOCS_PY = ('No ejecutes scripts bajo docs/ o spec/ desde el agente; ' + msg_approve())


def norm_path_token(t: str) -> str:
    return t.lstrip('&').replace('\\', '/').lower()


def tokens_match_prefix(toks: list[str], prefix: list[str]) -> bool:
    if len(toks) < len(prefix):
        return False
    return all(norm_path_token(a) == norm_path_token(b) for a, b in zip(toks, prefix))


def strip_call_operator(toks: list[str]) -> list[str]:
    while toks and toks[0] == '&':
        toks = toks[1:]
    return toks


def is_sdd_script_token(t: str) -> bool:
    return norm_path_token(t).endswith('microharness/sdd.py')


def split_segments(cmd: str) -> list[str] | None:
    if re.search(r'[$`\\\n\r\u2018-\u201e]', cmd):
        return None
    segments: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(cmd)
    quote = ''
    while i < n:
        ch = cmd[i]
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = ''
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if ch == ';' or (ch in '&|' and i + 1 < n and cmd[i + 1] == ch):
            part = ''.join(buf).strip()
            if not part:
                return None
            segments.append(part)
            buf = []
            i += 2 if ch in '&|' else 1
            continue
        if ch in '&|()<>':
            return None
        buf.append(ch)
        i += 1
    if quote:
        return None
    part = ''.join(buf).strip()
    if not part:
        return None if segments else []
    segments.append(part)
    return segments


def tokens(cmd: str) -> list[str] | None:
    if re.search(r'[$`\\\n\r\u2018-\u201e]', cmd):
        return None
    lexer = shlex.shlex(cmd, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = ''
    try:
        toks = list(lexer)
    except ValueError:
        return None
    if any(t and set(t) <= set('();<>|&') for t in toks):
        return None
    return toks


def sdd_args(toks: list[str]) -> list[str] | None:
    toks = strip_call_operator(toks)
    rest: list[str] | None = None
    for prefix in LAUNCHERS:
        if tokens_match_prefix(toks, prefix):
            rest = toks[len(prefix):]
            break
    if rest is None:
        if toks[:3] != ['uv', 'run', '--no-project']:
            return None
        rest = toks[3:]
        if rest[:1] == ['--quiet']:
            rest = rest[1:]
        if rest[:1] == ['--python']:
            if len(rest) < 2 or not re.fullmatch(r'(>=)?3\.[0-9]+', rest[1]):
                return None
            rest = rest[2:]
    if not rest or not is_sdd_script_token(rest[0]):
        return None
    return rest[1:]


def find_sdd_subcommand(toks: list[str]) -> str | None:
    toks = strip_call_operator(toks)
    for i, t in enumerate(toks):
        low = t.replace('\\', '/').lower()
        base = PurePosixPath(low).name
        if base == 'sdd.py':
            return toks[i + 1] if i + 1 < len(toks) else ''
        if 'microharness.sdd' in low or low.endswith('.sdd'):
            return toks[i + 1] if i + 1 < len(toks) else ''
    return None


def commit_exception(toks: list[str]) -> bool:
    if toks[:1] != ['git'] or toks[1:2] != ['commit']:
        return False
    for t in toks[2:]:
        if t == '--output' or t.startswith('--output=') or t in ('-F', '--file', '-o'):
            return False
        if t.startswith('--file='):
            return False
        if t.startswith('-') and not t.startswith('--') and t not in ('-m', '-a', '-am'):
            if 'o' in t[1:] or 'F' in t[1:]:
                return False
    return True


def _launcher_version_ok(toks: list[str]) -> bool:
    for prefix in LAUNCHERS:
        if tokens_match_prefix(toks, prefix) and len(toks) == len(prefix) + 1 and toks[len(prefix)] == '--version':
            return True
    return False


def _launcher_unittest_ok(toks: list[str]) -> bool:
    for prefix in LAUNCHERS:
        n = len(prefix)
        if tokens_match_prefix(toks, prefix) and toks[n:n + 2] == ['-m', 'unittest']:
            return not any(PROTECTED_RE.search(t) for t in toks[n + 2:])
    return False


def legit_exception(toks: list[str]) -> bool:
    toks = strip_call_operator(toks)
    if _launcher_version_ok(toks):
        return True
    if _launcher_unittest_ok(toks):
        return True
    if toks[:1] == ['git'] and toks[1:2] and toks[1] in ('add', 'diff', 'status', 'log', 'show'):
        return all(re.fullmatch(r'[\w./:^~=+,@-]+', t) and not t.startswith(('--output', '--ext-diff'))
                   for t in toks[2:])
    if commit_exception(toks):
        return True
    return False


def settings_path_token(t: str) -> bool:
    low = t.replace('\\', '/').lower()
    name = PurePosixPath(low).name
    if name not in ('settings.json', 'settings.local.json'):
        return False
    return (low in ('.claude/settings.json', '.claude/settings.local.json', name)
            or '/.claude/' + name in low or low.endswith('/' + name))


def settings_read_ok(toks: list[str]) -> bool:
    if not toks:
        return False
    cmd0 = toks[0]
    if cmd0 in ('cat', 'head', 'tail'):
        return len(toks) >= 2 and all(settings_path_token(t) for t in toks[1:] if not t.startswith('-')) and (
            any(settings_path_token(t) for t in toks[1:]))
    if cmd0 in ('grep', 'rg'):
        if any(settings_path_token(t) for t in toks[1:]):
            if any(t in ('-f', '--file', '-o', '--output') or t.startswith(('--output=', '--file='))
                   for t in toks[1:]):
                return False
            return True
        return False
    if cmd0 == 'jq':
        if len(toks) < 3:
            return False
        for t in toks[1:]:
            if t in ('-i', '--in-place', '-f', '--from-file', '-o', '--output') or t.startswith(('--output=',)):
                return False
            if t.startswith('-') and not t.startswith('--') and 'i' in t[1:]:
                return False
        files = [t for t in toks[1:] if settings_path_token(t)]
        others = [t for t in toks[1:] if not settings_path_token(t) and not t.startswith('-')]
        return bool(files) and len(others) == 1
    return False


def settings_ok(toks: list[str]) -> bool:
    if settings_read_ok(toks):
        return True
    if toks[:1] == ['git'] and toks[1:2] and toks[1] in SETTINGS_GIT:
        return not any(t.startswith('--output') for t in toks)
    if (len(toks) == 4 and toks[0] in ('python', 'python3', 'python.exe')
            and toks[1:3] == ['-m', 'json.tool'] and settings_path_token(toks[3])):
        return True
    return False


def segment_guarded_material(cmd: str) -> bool:
    return bool(TOGGLE_RE.search(cmd) or SETTINGS_RE.search(cmd) or PROTECTED_RE.search(cmd))


def docs_or_spec_py_execution(toks: list[str]) -> bool:
    if not toks:
        return False
    rest = toks
    if toks[:2] == ['py', '-3']:
        rest = toks[2:]
    elif toks[0] in ('python', 'python3', 'python.exe') or toks[0].startswith('python3.'):
        rest = toks[1:]
    else:
        return False
    for t in rest:
        if t.startswith('-'):
            continue
        low = t.replace('\\', '/').lower()
        if low.endswith('.py') and (low.startswith('docs/') or low.startswith('spec/')
                                    or '/docs/' in low or '/spec/' in low
                                    or low == 'docs' or PurePosixPath(low).parts[:1] in (('docs',), ('spec',))):
            return True
        parts = PurePosixPath(low).parts
        if parts and parts[-1].endswith('.py'):
            if 'docs' in parts or 'spec' in parts:
                for part in parts[:-1]:
                    if part in ('docs', 'spec'):
                        return True
    return False


def guard_segment(cmd: str) -> str | None:
    toks = tokens(cmd)
    if toks is not None and docs_or_spec_py_execution(toks):
        return MSG_DOCS_PY
    if TOGGLE_RE.search(cmd):
        if toks is not None and toks[:1] == ['git'] and toks[1:2] and toks[1] in SETTINGS_GIT and not any(
                t.startswith('--output') for t in toks):
            pass
        else:
            return MSG_TOGGLE
    if SETTINGS_RE.search(cmd):
        if toks is not None and settings_ok(toks):
            return None
        if toks is not None and toks[:1] in (['cat'], ['head'], ['tail'], ['grep'], ['rg'], ['jq']):
            return MSG_SETTINGS_READ_HINT
        return MSG_SETTINGS_WRITE
    if PROTECTED_RE.search(cmd):
        if toks is not None:
            sub = find_sdd_subcommand(toks)
            if sub in ('approve', 'seal'):
                return msg_approve()
            args = sdd_args(toks)
            if args is not None:
                if args and args[0] in ('approve', 'seal'):
                    return msg_approve()
                if args and args[0] in SDD_ALLOWED:
                    return None
                return msg_protected()
            if legit_exception(toks):
                return None
            return msg_protected()
        return msg_unparseable()
    return None


def check_shell(cmd: str) -> str | None:
    segments = split_segments(cmd)
    if segments is None:
        if PROTECTED_RE.search(cmd) or TOGGLE_RE.search(cmd) or SETTINGS_RE.search(cmd):
            return msg_unparseable()
        return None
    reasons = []
    for seg in segments:
        reason = guard_segment(seg)
        if reason:
            reasons.append(reason)
    if reasons:
        return reasons[0]
    if len(segments) > 1 and any(segment_guarded_material(seg) for seg in segments):
        return msg_chain()
    return None


def guard_bash(cmd: str) -> str | None:
    if not (TOGGLE_RE.search(cmd) or SETTINGS_RE.search(cmd) or PROTECTED_RE.search(cmd)):
        return None
    return check_shell(cmd)


def protected_bash(cmd: str) -> str | None:
    if not PROTECTED_RE.search(cmd):
        return None
    return check_shell(cmd)


def reviewer_command_ok(cmd: str) -> bool:
    norm = cmd.strip().replace('\\', '/')
    return bool(REVIEWER_SDD_CHECK_RE.fullmatch(norm) or REVIEWER_GIT_RE.fullmatch(norm))


def plans_md_exception(target: Path, agent: str) -> bool:
    if agent != 'lider':
        return False
    try:
        plans = (Path.home() / '.claude' / 'plans').resolve()
        resolved = target.resolve()
    except (ValueError, OSError):
        return False
    if resolved.parent != plans:
        return False
    return resolved.suffix.lower() == '.md'


def run(event: dict) -> str | None:
    agent = event.get('agent_type') or ''
    tool = event.get('tool_name') or ''
    inputs = event.get('tool_input') or {}
    if agent not in ('autor', 'implementador', 'revisor', 'lider'):
        if tool in ('Write', 'Edit', 'MultiEdit', 'NotebookEdit', 'Bash', 'PowerShell'):
            return ('Agente no reconocido por MicroSDD: inicia la sesión con `claude --agent lider` '
                    'o usa uno de los agentes autor, implementador, revisor o lider.')
        return None
    if tool in ('Write', 'Edit', 'MultiEdit', 'NotebookEdit'):
        if agent == 'revisor':
            return 'El revisor es solo lectura.'
        base = Path(event.get('cwd') or '.').resolve()
        filename = inputs.get('file_path') or inputs.get('notebook_path')
        if not filename:
            return 'No se conoce la ruta de edición.'
        target = Path(filename)
        if not target.is_absolute():
            target = base / target
        if plans_md_exception(target, agent):
            return None
        try:
            rel = target.resolve().relative_to(base).as_posix()
        except ValueError:
            return ('Se prohíbe editar fuera del proyecto (excepción: ~/.claude/plans/*.md). '
                    'No abras el resto de ~/.claude.')
        low = rel.lower()
        if agent in ('lider', 'autor') and (rel.startswith('docs/') or rel.startswith('spec/')):
            suffix = Path(rel).suffix.lower()
            if suffix in EXEC_EXTS:
                return MSG_EXECUTABLES
            blob = (inputs.get('content') or inputs.get('new_string') or inputs.get('old_string') or '')
            if isinstance(blob, str) and blob.lstrip().startswith('#!'):
                return MSG_EXECUTABLES
        if (low == '.microharness' or low.startswith('.microharness/')) and not (
                agent == 'implementador' and rel in HARNESS_EDITABLE):
            return ('Ningún agente edita .microharness/ (memoria y configuración); '
                    'la memoria solo cambia con sdd.py.')
        if agent == 'autor':
            if not re.fullmatch(r'spec/[a-z][a-z0-9-]*/(spec\.json|requerimientos\.md|plan\.md|tareas\.md)', rel):
                return 'El autor solo modifica cuatro archivos de la spec.'
        elif agent == 'implementador':
            if rel.startswith(('.claude/', 'docs/', 'spec/')) or rel == 'CLAUDE.md':
                return 'El implementador no puede editar políticas, memoria o especificaciones.'
            root = base
            tasks = sorted(root.glob('spec/*/spec.json'))
            active = []
            for file in tasks:
                try:
                    s = json.loads(file.read_text(encoding='utf-8'))
                    if s.get('state') == 'proceso':
                        active.append(s)
                except (OSError, ValueError):
                    continue
            if len(active) != 1:
                return 'Se requiere exactamente una spec activa en proceso.'
            from fnmatch import fnmatchcase
            paths = active[0].get('scope', {}).get('allowed_paths', [])
            ok = any(fnmatchcase(rel, p) or
                     (p.endswith('/**') and rel.startswith(p[:-3] + '/')) for p in paths)
            if not ok:
                return f'Fuera del alcance aprobado: {rel}'
            memory_file = root / '.microharness/memory.json'
            if memory_file.exists():
                try:
                    memory = json.loads(memory_file.read_text(encoding='utf-8'))
                    task = memory['tasks'][active[0]['id']]
                    if not task.get('approvals', {}).get('spec'):
                        return 'Especificación sin aprobación registrada.'
                    sealed = task.get('sealed_tests', {})
                    if rel in sealed:
                        return 'El test está sellado; pide aprobación humana para resellarlo.'
                except (OSError, ValueError, KeyError):
                    return 'Memoria inválida; no se puede autorizar edición.'
        elif agent == 'lider':
            if not rel.startswith(('docs/', 'spec/')):
                return 'El líder no modifica código; delega al implementador.'
    if tool in ('Bash', 'PowerShell') and agent in ('lider', 'autor', 'implementador'):
        return check_shell(inputs.get('command') or '')
    if tool in ('Bash', 'PowerShell') and agent == 'revisor':
        cmd = inputs.get('command', '').strip()
        if not reviewer_command_ok(cmd):
            return 'El revisor solo puede ejecutar el checker o inspecciones Git permitidas.'
    return None


if __name__ == '__main__':
    try:
        reason = run(json.load(sys.stdin))
        if reason:
            print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse',
                'permissionDecision': 'deny', 'permissionDecisionReason': reason}}, ensure_ascii=False))
    except Exception as err:
        print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse',
            'permissionDecision': 'deny', 'permissionDecisionReason': f'Guardia inválida: {err}'}}))
