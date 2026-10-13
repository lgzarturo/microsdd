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


def tokens(cmd: str) -> list[str] | None:
    """Tokens POSIX del comando; None si hay sustituciones, escapes u operadores de shell."""
    # PowerShell trata U+2018..U+201B como comilla simple y U+201C..U+201E como doble.
    if re.search(r'[$`\\\n\r\u2018-\u201e]', cmd):
        return None
    lexer = shlex.shlex(cmd, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = ''  # `x#;rm` no es un comentario para la shell.
    try:
        toks = list(lexer)
    except ValueError:
        return None
    if any(t and set(t) <= set('();<>|&') for t in toks):
        return None
    return toks


def sdd_args(toks: list[str]) -> list[str] | None:
    """Argumentos tras `.microharness/sdd.py` si el comando usa un lanzador admitido."""
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


def legit_exception(toks: list[str]) -> bool:
    if toks == ['sh', '.microharness/python.sh', '--version']:
        return True
    if toks[:4] == ['sh', '.microharness/python.sh', '-m', 'unittest']:
        return not any(PROTECTED_RE.search(t) for t in toks[4:])
    if toks[:1] == ['git'] and toks[1:2] and toks[1] in ('add', 'diff', 'status', 'log', 'show'):
        return all(re.fullmatch(r'[\w./:^~=+,@-]+', t) and not t.startswith(('--output', '--ext-diff'))
                   for t in toks[2:])
    return False


def protected_bash(cmd: str) -> str | None:
    if not PROTECTED_RE.search(cmd):
        return None
    toks = tokens(cmd)
    if toks is not None:
        args = sdd_args(toks)
        if (args and args[0] in SDD_ALLOWED) or legit_exception(toks):
            return None
    return ('Comando denegado: menciona microharness, memory.json o sdd.py fuera de las formas permitidas '
            '(lanzador admitido + .microharness/sdd.py con init, new, check, review, commit-check, note, '
            'release, --version o --help; sh .microharness/python.sh --version o -m unittest; '
            'git add|diff|status|log|show), sin $, comilla invertida, \\, saltos de línea ni operadores '
            'de shell. approve y seal los ejecuta el humano en su terminal; lee la memoria con Read.')


def guard_bash(cmd: str) -> str | None:
    if not (TOGGLE_RE.search(cmd) or SETTINGS_RE.search(cmd)):
        return None
    toks = tokens(cmd)
    if toks is not None and (
            (toks[:1] == ['git'] and toks[1:2] and toks[1] in SETTINGS_GIT
             and not any(t.startswith('--output') for t in toks))
            or (len(toks) == 4 and toks[0] in ('python', 'python3') and toks[1:3] == ['-m', 'json.tool'])):
        return None
    return ('Comando denegado: on, off y uninstall de microsdd, y los cambios a .claude/settings.json, '
            'los ejecuta el humano en su terminal, fuera de Claude Code.')


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
        try:
            rel = target.resolve().relative_to(base).as_posix()
        except ValueError:
            return 'Se prohíbe editar fuera del proyecto.'
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
            # No existe un slug implícito seguro; las specs aprobadas definen el scope.
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
        cmd = inputs.get('command') or ''
        return guard_bash(cmd) or protected_bash(cmd)
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
