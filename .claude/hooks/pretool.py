#!/usr/bin/env python3
"""Guardia de herramientas nativas Claude Code (best effort, NO sandbox)."""
import json
import re
import shlex
import sys
from pathlib import Path, PurePosixPath


PROTECTED_RE = re.compile(r'microharness|memory\.json|sdd\.py', re.I)
SDD_ALLOWED = ('init', 'new', 'check', 'review', 'commit-check', 'note', 'release', '--version', '--help')
LAUNCHERS = (['sh', '.microharness/python.sh'], ['python'], ['python3'], ['py', '-3'])
HARNESS_EDITABLE = ('.microharness/sdd.py', '.microharness/python.sh')
TOGGLE_RE = re.compile(r'(?:microsdd|installer\.py).*\b(?:on|off|uninstall)\b', re.I | re.S)
SETTINGS_RE = re.compile(r'settings(?:\.local)?\.json', re.I)
SETTINGS_GIT = ('add', 'diff', 'status', 'log', 'show', 'commit')
MSG_APPROVE = ('approve y seal los ejecuta el humano en su terminal fuera de Claude Code; '
               'no uses Bash/PowerShell del agente para eso.')
MSG_TOGGLE = ('microsdd on|off|uninstall solo lo ejecuta el humano en su terminal fuera de Claude Code.')
MSG_SETTINGS_WRITE = ('No modifiques .claude/settings.json ni settings.local.json desde el agente; '
                      'usa Read o cat/jq para leerlos; los cambios los hace el humano.')
MSG_PROTECTED = ('Comando denegado: menciona microharness, memory.json o sdd.py fuera de las formas '
                 'permitidas (lanzador admitido + .microharness/sdd.py con init, new, check, review, '
                 'commit-check, note, release, --version o --help; sh .microharness/python.sh --version '
                 'o -m unittest; git add|diff|status|log|show|commit -m). '
                 + MSG_APPROVE + ' Lee la memoria con Read.')
MSG_CHAIN = ('Comando encadenado denegado: no combines operaciones sensibles (sdd/microharness/settings/'
             'microsdd) con &&, || o ;. Ejecuta cada paso por separado; approve/seal los ejecuta el humano '
             'en su terminal fuera de Claude Code.')
MSG_UNPARSEABLE = ('Comando no analizable con seguridad (comillas desbalanceadas, operadores, $, '
                   'backticks o escapes). Reformúlalo sin sustituciones ni operadores; '
                   + MSG_APPROVE)


def split_segments(cmd: str) -> list[str] | None:
    """Parte por &&, || y ; respetando comillas; None si no se puede analizar."""
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
    """Tokens POSIX del comando; None si hay sustituciones, escapes u operadores de shell."""
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
    """Argumentos tras .microharness/sdd.py si el comando usa un lanzador admitido."""
    for prefix in LAUNCHERS:
        if toks[:len(prefix)] == prefix:
            rest = toks[len(prefix):]
            break
    else:
        if toks[:3] != ['uv', 'run', '--no-project']:
            return None
        rest = toks[3:]
        if rest[:1] == ['--quiet']:
            rest = rest[1:]
        if rest[:1] == ['--python']:
            if len(rest) < 2 or not re.fullmatch(r'(>=)?3\.[0-9]+', rest[1]):
                return None
            rest = rest[2:]
    return rest[1:] if rest[:1] == ['.microharness/sdd.py'] else None


def find_sdd_subcommand(toks: list[str]) -> str | None:
    """Subcomando sdd tras cualquier mención de sdd.py o módulo sdd."""
    for i, t in enumerate(toks):
        low = t.replace('\\', '/').lower()
        base = PurePosixPath(low).name
        if base == 'sdd.py':
            return toks[i + 1] if i + 1 < len(toks) else ''
        if 'microharness.sdd' in low or low.endswith('.sdd'):
            return toks[i + 1] if i + 1 < len(toks) else ''
    return None


def safe_git_arg(t: str) -> bool:
    if t.startswith(('--output', '--ext-diff', '--textconv', '--open-files-in-pager')):
        return False
    return bool(re.fullmatch(r'[\w./:^~=+,@\'\" -]+', t))


def commit_exception(toks: list[str]) -> bool:
    """git commit -m (u args seguros) permitido aunque el mensaje mencione sdd.py."""
    if toks[:1] != ['git'] or toks[1:2] != ['commit']:
        return False
    # tokens() ya rechazó operadores de shell; denegar solo escritura via output/file.
    for t in toks[2:]:
        if t == '--output' or t.startswith('--output=') or t in ('-F', '--file', '-o'):
            return False
        if t.startswith('--file='):
            return False
        if t.startswith('-') and not t.startswith('--') and t not in ('-m', '-a', '-am'):
            if 'o' in t[1:] or 'F' in t[1:]:
                return False
    return True
def legit_exception(toks: list[str]) -> bool:
    if toks == ['sh', '.microharness/python.sh', '--version']:
        return True
    if toks[:4] == ['sh', '.microharness/python.sh', '-m', 'unittest']:
        return not any(PROTECTED_RE.search(t) for t in toks[4:])
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
    """cat/jq de settings(.local).json sin redirecciones de escritura."""
    if not toks:
        return False
    if toks[0] == 'cat':
        return len(toks) >= 2 and all(settings_path_token(t) for t in toks[1:])
    if toks[0] == 'jq':
        if len(toks) < 3:
            return False
        if any(t in ('-f', '--from-file', '-o', '--output') or t.startswith(('--output=',))
               for t in toks[1:]):
            return False
        files = [t for t in toks[1:] if settings_path_token(t)]
        others = [t for t in toks[1:] if not settings_path_token(t) and not t.startswith("-")]
        return bool(files) and len(others) == 1
    return False


def settings_ok(toks: list[str]) -> bool:
    if settings_read_ok(toks):
        return True
    if toks[:1] == ['git'] and toks[1:2] and toks[1] in SETTINGS_GIT:
        return not any(t.startswith('--output') for t in toks)
    if (len(toks) == 4 and toks[0] in ('python', 'python3')
            and toks[1:3] == ['-m', 'json.tool'] and settings_path_token(toks[3])):
        return True
    return False


def segment_sensitive(cmd: str, toks: list[str] | None) -> bool:
    """True si el segmento toca material protegido (salvo lecturas/commit legítimos)."""
    if TOGGLE_RE.search(cmd):
        if toks is not None and toks[:1] == ['git'] and toks[1:2] and toks[1] in SETTINGS_GIT                 and not any(t.startswith('--output') for t in toks):
            return False
        return True
    if SETTINGS_RE.search(cmd):
        return not (toks is not None and settings_ok(toks))
    if not PROTECTED_RE.search(cmd):
        return False
    if toks is not None and commit_exception(toks):
        return False
    if toks is not None and toks[:1] == ['git'] and toks[1:2] and toks[1] in ('add', 'diff', 'status', 'log', 'show'):
        return not legit_exception(toks)
    if toks is not None and toks == ['sh', '.microharness/python.sh', '--version']:
        return False
    return True


def guard_segment(cmd: str) -> str | None:
    """Valida un segmento ya partido; None = permitir."""
    toks = tokens(cmd)

    if TOGGLE_RE.search(cmd):
        # git commit -m '... microsdd on ...' es mensaje, no el toggle
        if toks is not None and toks[:1] == ['git'] and toks[1:2] and toks[1] in SETTINGS_GIT                 and not any(t.startswith('--output') for t in toks):
            pass
        else:
            return MSG_TOGGLE

    if SETTINGS_RE.search(cmd):
        if toks is not None and settings_ok(toks):
            return None
        return MSG_SETTINGS_WRITE

    if PROTECTED_RE.search(cmd):
        if toks is not None:
            sub = find_sdd_subcommand(toks)
            if sub in ('approve', 'seal'):
                return MSG_APPROVE
            args = sdd_args(toks)
            if args is not None:
                if args and args[0] in ('approve', 'seal'):
                    return MSG_APPROVE
                if args and args[0] in SDD_ALLOWED:
                    return None
                return MSG_PROTECTED
            if legit_exception(toks):
                return None
            return MSG_PROTECTED
        return MSG_UNPARSEABLE

    return None


def check_shell(cmd: str) -> str | None:
    segments = split_segments(cmd)
    if segments is None:
        if PROTECTED_RE.search(cmd) or TOGGLE_RE.search(cmd) or SETTINGS_RE.search(cmd):
            return MSG_UNPARSEABLE
        return None
    reasons = []
    sensitive = 0
    for seg in segments:
        reason = guard_segment(seg)
        if reason:
            reasons.append(reason)
        if segment_sensitive(seg, tokens(seg)):
            sensitive += 1
    if reasons:
        return reasons[0]
    if len(segments) > 1 and sensitive:
        return MSG_CHAIN
    return None


def guard_bash(cmd: str) -> str | None:
    """Compatibilidad con pruebas que llaman guard_bash directamente."""
    if not (TOGGLE_RE.search(cmd) or SETTINGS_RE.search(cmd) or PROTECTED_RE.search(cmd)):
        return None
    return check_shell(cmd)


def protected_bash(cmd: str) -> str | None:
    """Compatibilidad con pruebas que llaman protected_bash directamente."""
    if not PROTECTED_RE.search(cmd):
        return None
    return check_shell(cmd)


def plans_md_exception(target: Path) -> bool:
    """Write/Edit de *.md bajo ~/.claude/plans."""
    try:
        plans = (Path.home() / '.claude' / 'plans').resolve()
        resolved = target.resolve()
        resolved.relative_to(plans)
    except (ValueError, OSError):
        return False
    return resolved.name.lower().endswith('.md')


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
        if plans_md_exception(target):
            return None
        try:
            rel = target.resolve().relative_to(base).as_posix()
        except ValueError:
            return ('Se prohíbe editar fuera del proyecto (excepción: ~/.claude/plans/*.md). '
                    'No abras el resto de ~/.claude.')
        low = rel.lower()
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
        if not (re.fullmatch(r'(?:python3?|py -3|sh \.microharness/python\.sh|uv run --no-project(?: --quiet)?(?: --python (?:\'>=3\.[0-9]+\'|">=3\.[0-9]+"|3\.[0-9]+))?) \.microharness/sdd\.py check [a-z][a-z0-9-]* --run', cmd)
                or re.fullmatch(r'git (diff|status)(?: (?!--output(?:[= ]|$)|--ext-diff(?: |$)|--textconv(?:[= ]|$)|--open-files-in-pager(?:[= ]|$)|-[^ -]*O)[\w./:^~=+,-]+)*', cmd)):
            return 'El revisor solo puede ejecutar el checker o inspecciones Git permitidas.'
    return None


if __name__ == '__main__':
    try:
        reason = run(json.load(sys.stdin))
        if reason:
            print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse',
                'permissionDecision': 'deny', 'permissionDecisionReason': reason}}, ensure_ascii=False))
    except Exception as err:
        # Denegar ante entradas inválidas para no dejar un bypass silencioso.
        print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse',
            'permissionDecision': 'deny', 'permissionDecisionReason': f'Guardia inválida: {err}'}}))
