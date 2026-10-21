#!/usr/bin/env python3
"""Guardia de herramientas nativas Claude Code (best effort, NO sandbox)."""
import hashlib
import json
import os
import re
import shlex
import sys
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath


PROTECTED_RE = re.compile(r'microharness|memory\.json|sdd\.py', re.I)
NOTE_EVIDENCE_CMD_RE = re.compile(r'--evidence\s+@note:[a-zA-Z0-9_-]+')
GATED_SUBCOMMANDS = ('approve', 'seal', 'allow-test-command')
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
    '.microharness/bench.py',
    '.microharness/metrics.py',
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


def msg_gated_lider_only() -> str:
    return ('Solo el líder puede ejecutar approve, seal o allow-test-command con '
            '--evidence @note:<id> (agent_may_approve). Autor, implementador y otros roles: denegado.')


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


DEFAULT_RDD_MAX_FILES = 20
DEFAULT_RDD_MAX_LINES = 500
DEFAULT_ODD_REWRITE_PERCENT = 80
RDD_RUNTIME_NAME = 'rdd_runtime.json'


def load_harness_config(cwd: str | None) -> dict:
    path = Path(cwd or '.').resolve() / '.microharness' / 'config.json'
    cfg = {
        'agent_may_approve': True,
        'rdd_max_files': DEFAULT_RDD_MAX_FILES,
        'rdd_max_lines': DEFAULT_RDD_MAX_LINES,
        'odd_rewrite_percent': DEFAULT_ODD_REWRITE_PERCENT,
    }
    if not path.is_file():
        return cfg
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        return cfg
    if not isinstance(data, dict):
        return cfg
    if isinstance(data.get('agent_may_approve'), bool):
        cfg['agent_may_approve'] = data['agent_may_approve']
    for key, lo, hi in (
            ('rdd_max_files', 1, None),
            ('rdd_max_lines', 1, None),
            ('odd_rewrite_percent', 50, 100),
    ):
        val = data.get(key)
        if type(val) is int and not isinstance(val, bool) and val >= lo and (hi is None or val <= hi):
            cfg[key] = val
    return cfg


def agent_may_approve(cwd: str | None) -> bool:
    return bool(load_harness_config(cwd).get('agent_may_approve', True))


def count_lines(text: str | None) -> int:
    if not text:
        return 0
    if text.endswith('\n'):
        return text.count('\n')
    return text.count('\n') + (1 if text else 0)


def estimate_edit_lines(tool: str, inputs: dict) -> int:
    """Estimación aproximada de líneas tocadas en una llamada (no es un diff unificado)."""
    if tool == 'Write':
        return count_lines(inputs.get('content') if isinstance(inputs.get('content'), str) else '')
    if tool == 'Edit':
        new = inputs.get('new_string') if isinstance(inputs.get('new_string'), str) else ''
        old = inputs.get('old_string') if isinstance(inputs.get('old_string'), str) else ''
        return max(count_lines(new), count_lines(old), abs(count_lines(new) - count_lines(old)))
    if tool == 'MultiEdit':
        edits = inputs.get('edits') or []
        total = 0
        if isinstance(edits, list):
            for edit in edits:
                if not isinstance(edit, dict):
                    continue
                new = edit.get('new_string') if isinstance(edit.get('new_string'), str) else ''
                old = edit.get('old_string') if isinstance(edit.get('old_string'), str) else ''
                total += max(count_lines(new), count_lines(old), abs(count_lines(new) - count_lines(old)))
        return total
    if tool == 'NotebookEdit':
        src = inputs.get('new_source') if isinstance(inputs.get('new_source'), str) else ''
        return count_lines(src)
    return 0


def _norm_newlines(text: str) -> str:
    return text.replace('\r\n', '\n').replace('\r', '\n')


def collect_old_strings(tool: str, inputs: dict) -> list[str]:
    if tool == 'Edit':
        old = inputs.get('old_string')
        return [old] if isinstance(old, str) and old else []
    if tool == 'MultiEdit':
        edits = inputs.get('edits') or []
        out: list[str] = []
        if isinstance(edits, list):
            for edit in edits:
                if isinstance(edit, dict) and isinstance(edit.get('old_string'), str) and edit['old_string']:
                    out.append(edit['old_string'])
        return out
    return []


def is_near_full_rewrite(tool: str, inputs: dict, target: Path, percent: int) -> bool:
    """True si old_string(s) cubren ≥ percent% del archivo en disco (ODD: no reescribir)."""
    if tool not in ('Edit', 'MultiEdit') or not target.is_file():
        return False
    try:
        disk = _norm_newlines(target.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError):
        return False
    if not disk:
        return False
    olds = collect_old_strings(tool, inputs)
    if not olds:
        return False
    if any(_norm_newlines(o) == disk for o in olds):
        return True
    covered = sum(len(_norm_newlines(o)) for o in olds)
    return covered * 100 >= percent * len(disk)


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def paths_casefold() -> bool:
    """En Windows las rutas del recibo se comparan sin distinguir mayúsculas."""
    return os.name == 'nt'


def path_key(rel: str, casefold: bool | None = None) -> str:
    if casefold is None:
        casefold = paths_casefold()
    return rel.casefold() if casefold else rel


def changed_files_vs_receipt(root: Path, receipt: dict) -> int:
    """Cuenta archivos del recibo cuyo contenido actual difiere del hash sellado."""
    files = receipt.get('files') if isinstance(receipt, dict) else None
    if not isinstance(files, dict):
        return 0
    changed = 0
    for rel, expected in files.items():
        if not isinstance(rel, str) or not isinstance(expected, str):
            continue
        path = root / rel
        if not path.is_file():
            changed += 1
            continue
        if file_digest(path) != expected:
            changed += 1
    return changed


def path_in_patterns(rel: str, patterns: list, casefold: bool | None = None) -> bool:
    if casefold is None:
        casefold = paths_casefold()
    rel_n = path_key(rel, casefold)
    for p in patterns:
        if not isinstance(p, str):
            continue
        p_n = path_key(p, casefold)
        if fnmatchcase(rel_n, p_n):
            return True
        if p_n.endswith('/**') and rel_n.startswith(p_n[:-3] + '/'):
            return True
    return False


def receipt_baseline_lookup(baseline: dict, rel: str) -> str | None:
    """Devuelve el hash esperado para rel, con lookup casefold en Windows."""
    if rel in baseline and isinstance(baseline[rel], str):
        return baseline[rel]
    if not paths_casefold():
        return None
    key = rel.casefold()
    for k, v in baseline.items():
        if isinstance(k, str) and k.casefold() == key and isinstance(v, str):
            return v
    return None


def resolve_edit_rel(base: Path, target: Path) -> tuple[str | None, str | None]:
    """(rel_posix, error). resolve() sigue symlinks; el destino real debe quedar en el proyecto."""
    try:
        resolved = target.resolve()
        rel = resolved.relative_to(base.resolve()).as_posix()
    except (ValueError, OSError):
        return None, ('Se prohíbe editar fuera del proyecto (excepción: ~/.claude/plans/*.md). '
                      'No abras el resto de ~/.claude. Symlinks cuyo destino real sale del árbol '
                      'también se rechazan.')
    return rel, None


def runtime_path(root: Path) -> Path:
    return root / '.microharness' / RDD_RUNTIME_NAME


def load_runtime_lines(root: Path, slug: str) -> int:
    path = runtime_path(root)
    if not path.is_file():
        return 0
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        return 0
    tasks = data.get('tasks') if isinstance(data, dict) else None
    if not isinstance(tasks, dict):
        return 0
    entry = tasks.get(slug)
    if isinstance(entry, dict) and type(entry.get('lines')) is int and not isinstance(entry.get('lines'), bool):
        return max(0, entry['lines'])
    return 0


def add_runtime_lines(root: Path, slug: str, delta: int) -> int:
    """Suma líneas aproximadas al contador de la tarea; archivo local no versionado."""
    path = runtime_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {'tasks': {}}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(loaded, dict) and isinstance(loaded.get('tasks'), dict):
                data = loaded
        except (OSError, ValueError, TypeError):
            data = {'tasks': {}}
    tasks = data.setdefault('tasks', {})
    entry = tasks.get(slug) if isinstance(tasks.get(slug), dict) else {}
    current = entry.get('lines') if type(entry.get('lines')) is int else 0
    total = max(0, current) + max(0, delta)
    tasks[slug] = {'lines': total}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return total


def msg_kill_switch(reason: str) -> str:
    return (f'Kill switch RDD: {reason}. Detén la ejecución; reduce el alcance o pide ampliar '
            f'rdd_max_files / rdd_max_lines en .microharness/config.json (humano). '
            f'El conteo de líneas es aproximado y acumulado por tarea '
            f'(defensa global del implementador, aunque RDD no esté en optional).')


def msg_outside_receipt(rel: str) -> str:
    return (f'Fuera del recibo RDD: {rel}. El alcance quedó congelado al aprobar la spec '
            f'(receipt.allowed_paths); no edites rutas fuera de ese recibo '
            f'(incluye destino real tras resolver symlinks).')


def gated_with_note_evidence(cmd: str) -> bool:
    return bool(NOTE_EVIDENCE_CMD_RE.search(cmd))


def deny_or_allow_gated(cmd: str, cwd: str | None, agent: str = '',
                        toks: list[str] | None = None) -> str | None:
    if not agent_may_approve(cwd):
        return msg_approve()
    if agent != 'lider':
        return msg_gated_lider_only()
    # Loop autónomo: seal y approve-close del líder pasan el hook sin @note;
    # sdd.py exige el lease activo (fail-closed sin él).
    args = sdd_args(toks or []) or []
    is_autonomous_step = (
        (len(args) >= 2 and args[0] == 'seal') or
        (len(args) >= 3 and args[0] == 'approve' and args[2] == 'close')
    )
    if is_autonomous_step or gated_with_note_evidence(cmd):
        return None
    return msg_approve()


MSG_TOGGLE = ('microsdd on|off|uninstall solo lo ejecuta el humano en su terminal fuera de Claude Code.')
MSG_SETTINGS_WRITE = ('No modifiques .claude/settings.json ni settings.local.json desde el agente; '
                      'usa Read o cat/jq para leerlos; los cambios los hace el humano.')
MSG_SETTINGS_READ_HINT = ('Para leer settings usa cat, head, tail, grep, rg, jq o python -m json.tool; '
                          'no los modifiques desde el agente.')
MSG_EXECUTABLES = ('El líder/autor no escriben ejecutables en docs/ ni spec/; ' + msg_approve())
MSG_DOCS_PY = ('No ejecutes scripts bajo docs/ o spec/ desde el agente; ' + msg_approve())
MSG_FULL_REWRITE = (
    'Reescritura completa bloqueada (ODD): no sustituyas casi todo el archivo de una vez. '
    'Write solo para archivos nuevos; Edit/MultiEdit deben ser diffs acotados '
    f'(old_string < odd_rewrite_percent% del contenido en disco, default {DEFAULT_ODD_REWRITE_PERCENT}%). '
    'Así se evita saturar el contexto y se preserva el historial quirúrgico del cambio.'
)


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


def normalize_shell_cmd(cmd: str) -> str:
    """Quita el call operator de PowerShell al inicio (& python …), no &&."""
    s = cmd.lstrip()
    if s.startswith('&') and not s.startswith('&&'):
        rest = s[1:].lstrip()
        if rest and rest[0] not in '&|':
            return rest
    return cmd


def is_sdd_script_token(t: str) -> bool:
    return norm_path_token(t).endswith('microharness/sdd.py')


_WIN_ABS_PATH_RE = re.compile(r'(?<![A-Za-z0-9_])[A-Za-z]:\\[^ \t\n\r\'";|&<>()$`]*')


def _slashes_for_win_abs(cmd: str) -> str:
    r"""Reescribe `\` → `/` solo dentro de rutas absolutas Windows (`X:\...`).

    El resto del comando queda intacto: la relativa con backslash
    (`.microharness\sdd.py`) sigue siendo rechazada como evasiva.
    """
    return _WIN_ABS_PATH_RE.sub(lambda m: m.group(0).replace('\\', '/'), cmd)


def split_segments(cmd: str) -> list[str] | None:
    cmd = _slashes_for_win_abs(cmd)
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
    cmd = _slashes_for_win_abs(cmd)
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


def guard_segment(cmd: str, cwd: str | None = None, agent: str = '') -> str | None:
    cmd = normalize_shell_cmd(cmd)
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
            if sub in GATED_SUBCOMMANDS:
                return deny_or_allow_gated(cmd, cwd, agent, toks)
            args = sdd_args(toks)
            if args is not None:
                if args and args[0] in GATED_SUBCOMMANDS:
                    return deny_or_allow_gated(cmd, cwd, agent, toks)
                if args and args[0] in SDD_ALLOWED:
                    return None
                return msg_protected()
            if legit_exception(toks):
                return None
            return msg_protected()
        return msg_unparseable()
    return None


def check_shell(cmd: str, cwd: str | None = None, agent: str = '') -> str | None:
    cmd = normalize_shell_cmd(cmd)
    segments = split_segments(cmd)
    if segments is None:
        if PROTECTED_RE.search(cmd) or TOGGLE_RE.search(cmd) or SETTINGS_RE.search(cmd):
            return msg_unparseable()
        return None
    reasons = []
    for seg in segments:
        reason = guard_segment(seg, cwd, agent)
        if reason:
            reasons.append(reason)
    if reasons:
        return reasons[0]
    if len(segments) > 1 and any(segment_guarded_material(seg) for seg in segments):
        return msg_chain()
    return None


def guard_bash(cmd: str, cwd: str | None = None, agent: str = '') -> str | None:
    if not (TOGGLE_RE.search(cmd) or SETTINGS_RE.search(cmd) or PROTECTED_RE.search(cmd)):
        return None
    return check_shell(cmd, cwd, agent)


def protected_bash(cmd: str, cwd: str | None = None, agent: str = '') -> str | None:
    if not PROTECTED_RE.search(cmd):
        return None
    return check_shell(cmd, cwd, agent)


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
        rel, rel_err = resolve_edit_rel(base, target)
        if rel_err:
            return rel_err
        assert rel is not None
        low = rel.lower()
        cfg = load_harness_config(event.get('cwd'))
        # ODD: Write sobre existente, o Edit/MultiEdit que cubre ≥ odd_rewrite_percent del disco.
        if agent == 'implementador':
            if tool == 'Write' and target.exists() and target.is_file():
                return MSG_FULL_REWRITE
            disk_file = base / rel
            if is_near_full_rewrite(tool, inputs, disk_file if disk_file.is_file() else target,
                                    cfg['odd_rewrite_percent']):
                return MSG_FULL_REWRITE
        if agent in ('lider', 'autor') and (rel.startswith('docs/') or rel.startswith('spec/')):
            suffix = Path(rel).suffix.lower()
            if suffix in EXEC_EXTS:
                return MSG_EXECUTABLES
            blob = (inputs.get('content') or inputs.get('new_string') or inputs.get('old_string') or '')
            if isinstance(blob, str) and blob.lstrip().startswith('#!'):
                return MSG_EXECUTABLES
        # En Windows resolve() normaliza mayúsculas: la excepción exige la grafía exacta pedida.
        if (low == '.microharness' or low.startswith('.microharness/')) and not (
                agent == 'implementador' and rel in HARNESS_EDITABLE
                and Path(filename).as_posix().endswith(rel)):
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
            slug = active[0]['id']
            memory_file = root / '.microharness/memory.json'
            receipt = None
            if memory_file.exists():
                try:
                    memory = json.loads(memory_file.read_text(encoding='utf-8'))
                    task = memory['tasks'][slug]
                    if not task.get('approvals', {}).get('spec'):
                        return 'Especificación sin aprobación registrada.'
                    sealed = task.get('sealed_tests', {})
                    sealed_hit = rel in sealed or (
                        paths_casefold() and any(isinstance(k, str) and k.casefold() == rel.casefold()
                                                 for k in sealed))
                    if sealed_hit:
                        return 'El test está sellado; pide aprobación humana para resellarlo.'
                    receipt = task.get('receipt')
                except (OSError, ValueError, KeyError):
                    return 'Memoria inválida; no se puede autorizar edición.'
            if isinstance(receipt, dict) and isinstance(receipt.get('allowed_paths'), list) and receipt['allowed_paths']:
                if not path_in_patterns(rel, receipt['allowed_paths']):
                    return msg_outside_receipt(rel)
                baseline = receipt.get('files') if isinstance(receipt.get('files'), dict) else {}
                already = changed_files_vs_receipt(root, receipt)
                expected_hash = receipt_baseline_lookup(baseline, rel)
                disk_path = root / rel
                unchanged = (expected_hash is not None and disk_path.is_file()
                             and file_digest(disk_path) == expected_hash)
                new_file = expected_hash is None
                will_add = 1 if (unchanged or new_file) else 0
                if already + will_add > cfg['rdd_max_files']:
                    return msg_kill_switch(
                        f'se superarían {already + will_add} archivos distintos del recibo '
                        f'(límite rdd_max_files={cfg["rdd_max_files"]})')
            else:
                paths = active[0].get('scope', {}).get('allowed_paths', [])
                if not path_in_patterns(rel, paths):
                    return f'Fuera del alcance aprobado: {rel}'
            # Kill switch de líneas: acumula por tarea (defensa global; conteo aproximado).
            line_delta = estimate_edit_lines(tool, inputs)
            used = load_runtime_lines(root, slug)
            if used + line_delta > cfg['rdd_max_lines']:
                return msg_kill_switch(
                    f'acumulado ~{used}+{line_delta} líneas en la tarea {slug} '
                    f'(límite rdd_max_lines={cfg["rdd_max_lines"]}; conteo aproximado)')
            if line_delta:
                add_runtime_lines(root, slug, line_delta)
        elif agent == 'lider':
            if not rel.startswith(('docs/', 'spec/')):
                return 'El líder no modifica código; delega al implementador.'
    if tool in ('Bash', 'PowerShell') and agent in ('lider', 'autor', 'implementador'):
        return check_shell(inputs.get('command') or '', event.get('cwd'), agent)
    if tool in ('Bash', 'PowerShell') and agent == 'revisor':
        cmd = inputs.get('command', '').strip()
        if not reviewer_command_ok(cmd):
            return 'El revisor solo puede ejecutar el checker o inspecciones Git permitidas.'
    return None


if __name__ == '__main__':
    try:
        # Claude Code intercambia JSON en UTF-8; en Windows las tuberías usan la página de códigos ANSI.
        for stream in (sys.stdin, sys.stdout):
            if hasattr(stream, 'reconfigure'):
                stream.reconfigure(encoding='utf-8')
        event = json.load(sys.stdin)
        reason = run(event)
        if reason:
            print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse',
                'permissionDecision': 'deny', 'permissionDecisionReason': reason}}, ensure_ascii=False))
        elif (event.get('agent_type') or '') in ('lider', 'autor', 'implementador'):
            print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse',
                'permissionDecision': 'allow'}}, ensure_ascii=False))
    except Exception as err:
        print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse',
            'permissionDecision': 'deny', 'permissionDecisionReason': f'Guardia inválida: {err}'}}))
