#!/usr/bin/env python3
"""Guardia de herramientas nativas Claude Code (best effort, NO sandbox)."""
import json
import re
import sys
from pathlib import Path, PurePosixPath


def run(event: dict) -> str | None:
    agent = event.get('agent_type') or ''
    tool = event.get('tool_name') or ''
    inputs = event.get('tool_input') or {}
    if agent not in ('autor', 'implementador', 'revisor', 'lider'):
        return None
    if tool in ('Write', 'Edit', 'MultiEdit', 'NotebookEdit'):
        if agent == 'revisor':
            return 'El revisor es solo lectura.'
        base = Path(event.get('cwd') or '.').resolve()
        filename = inputs.get('file_path') or inputs.get('notebook_path')
        if not filename:
            return 'No se conoce la ruta de edición.'
        try:
            rel = Path(filename).resolve().relative_to(base).as_posix()
        except ValueError:
            return 'Se prohíbe editar fuera del proyecto.'
        if agent == 'autor':
            if not re.fullmatch(r'spec/[a-z][a-z0-9-]*/(spec\.json|requerimientos\.md|diseño\.md|tareas\.md)', rel):
                return 'El autor solo modifica cuatro archivos de la spec.'
        elif agent == 'implementador':
            if rel.startswith(('.claude/', '.microharness/', 'docs/', 'spec/')) or rel == 'CLAUDE.md':
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
            if not (rel.startswith(('docs/', 'spec/')) or rel == '.microharness/memory.json'):
                return 'El líder no modifica código; delega al implementador.'
    if tool in ('Bash', 'PowerShell') and agent == 'revisor':
        cmd = inputs.get('command', '').strip()
        if not (re.fullmatch(r'(?:python3?|py -3|sh \.microharness/python\.sh|uv run --no-project(?: --quiet)?(?: --python (?:\'>=3\.\d+\'|">=3\.\d+"|3\.\d+))?) \.microharness/sdd\.py check [a-z][a-z0-9-]* --run', cmd)
                or re.fullmatch(r'git (diff|status)(?: [^;&|\n]+)?', cmd)):
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
