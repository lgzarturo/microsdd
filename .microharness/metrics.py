#!/usr/bin/env python3
"""Telemetría opcional harness-telemetry/v1 (stdlib). Sin este módulo, sdd.py no emite nada."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = 'harness-telemetry/v1'
HARNESS_NAME = 'microsdd'
HARNESS_VERSION = '1.4.0'
EXPECTED_SCHEMA_SHA256 = (
    '3adfba482e42fb956d9486bf5e28ffb5818643c71372b0ce11c9be0e9fe44d5a'
)
AGENT_ROLES = frozenset({'lider', 'autor', 'implementador', 'revisor', 'main'})

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')


def _git_commit() -> str | None:
    try:
        r = subprocess.run(['git', 'rev-parse', '--short=12', 'HEAD'], cwd=ROOT,
                           capture_output=True, text=True, timeout=5, check=False)
        return r.stdout.strip() or None if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _read_metrics_cfg() -> dict:
    path = HERE / 'config.json'
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    cfg = data.get('metrics') if isinstance(data, dict) else None
    return cfg if isinstance(cfg, dict) else {}


def state_dir() -> Path:
    """Ruta de datos: local_dir o XDG/LOCALAPPDATA fuera del repo."""
    cfg = _read_metrics_cfg()
    if cfg.get('local_dir') is True:
        return HERE / 'metrics'
    raw = str(ROOT.resolve())
    digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()[:12]
    if os.name == 'nt':
        base = Path(os.environ.get('LOCALAPPDATA') or (Path.home() / 'AppData' / 'Local'))
    else:
        base = Path(os.environ.get('XDG_STATE_HOME') or (Path.home() / '.local' / 'state'))
    return base / 'microsdd' / digest


def runs_path() -> Path:
    return state_dir() / 'runs.jsonl'


def _run_id() -> str:
    env = os.environ.get('MICROSDD_RUN_ID', '').strip()
    if env:
        return env
    path = state_dir() / 'current_run_id'
    try:
        if path.is_file():
            value = path.read_text(encoding='utf-8').strip()
            if value:
                return value
    except OSError:
        pass
    value = f'r-{uuid.uuid4().hex[:12]}'
    try:
        state_dir().mkdir(parents=True, exist_ok=True)
        path.write_text(value + '\n', encoding='utf-8')
    except OSError:
        pass
    return value


def _sum_nullable(a: int | float | None, b: int | float | None) -> int | float | None:
    if a is None and b is None:
        return None
    return (a or 0) + (b or 0)


def empty_usage() -> dict:
    return {
        'input': None, 'output': None, 'cacheRead': None, 'cacheWrite': None,
        'reasoning': None, 'calls': None, 'apiRetries': None,
    }


def merge_usage(a: dict, b: dict | None) -> dict:
    if not b:
        return dict(a)
    return {
        'input': _sum_nullable(a.get('input'), b.get('input')),
        'output': _sum_nullable(a.get('output'), b.get('output')),
        'cacheRead': _sum_nullable(a.get('cacheRead'), b.get('cacheRead')),
        'cacheWrite': _sum_nullable(a.get('cacheWrite'), b.get('cacheWrite')),
        'reasoning': _sum_nullable(a.get('reasoning'), b.get('reasoning')),
        'calls': _sum_nullable(a.get('calls'), b.get('calls')),
        'apiRetries': _sum_nullable(a.get('apiRetries'), b.get('apiRetries')),
    }


def add_cost(a: float | None, b: float | None) -> float | None:
    if a is None and b is None:
        return None
    return (a or 0) + (b or 0)


def total_tokens(usage: dict | None) -> int | None:
    if not usage:
        return None
    parts = [usage.get('input'), usage.get('cacheRead'), usage.get('cacheWrite'), usage.get('output')]
    if all(p is None for p in parts):
        return None
    return sum(p or 0 for p in parts)


def aggregate_by_specialist(events: list[dict]) -> list[dict]:
    """Suma model.call + agent.end por taskId + role (misma lógica que aggregate.ts)."""
    amap: dict[str, dict] = {}
    for ev in events:
        if ev.get('event') not in ('model.call', 'agent.end'):
            continue
        task_id = ev.get('taskId') or '_'
        role = (ev.get('agent') or {}).get('role') or 'main'
        key = f'{task_id}::{role}'
        entry = amap.get(key)
        if entry is None:
            entry = {
                'taskId': task_id, 'role': role, 'usage': empty_usage(),
                'costUsd': None, 'events': 0, 'modelCalls': 0, 'agentEnds': 0,
            }
            amap[key] = entry
        entry['events'] += 1
        if ev.get('event') == 'model.call':
            entry['modelCalls'] += 1
        if ev.get('event') == 'agent.end':
            entry['agentEnds'] += 1
        entry['usage'] = merge_usage(entry['usage'], ev.get('usage'))
        cost = (ev.get('cost') or {}).get('usd')
        entry['costUsd'] = add_cost(entry['costUsd'], cost if cost is not None else None)
    return sorted(amap.values(), key=lambda x: (x['taskId'], x['role']))


def aggregate_by_task(events: list[dict]) -> list[dict]:
    specialists = aggregate_by_specialist(events)
    by_task: dict[str, dict] = {}

    def ensure(task_id: str) -> dict:
        t = by_task.get(task_id)
        if t is None:
            t = {
                'taskId': task_id, 'usage': empty_usage(), 'costUsd': None,
                'iterations': None, 'retries': 0, 'verifications': {},
                'specialists': [], 'taskEnd': None,
            }
            by_task[task_id] = t
        return t

    for ev in events:
        if ev.get('event') in ('run.start', 'run.end'):
            continue
        task_id = ev.get('taskId') or '_'
        t = ensure(task_id)
        if ev.get('event') == 'task.end':
            t['taskEnd'] = ev
            t['usage'] = merge_usage(t['usage'], ev.get('usage'))
            cost = (ev.get('cost') or {}).get('usd')
            t['costUsd'] = add_cost(t['costUsd'], cost if cost is not None else None)
            it = (ev.get('loop') or {}).get('iteration')
            if it is not None:
                t['iterations'] = it if t['iterations'] is None else max(t['iterations'], it)
        if ev.get('event') == 'iteration':
            it = (ev.get('loop') or {}).get('iteration')
            if it is not None:
                t['iterations'] = it if t['iterations'] is None else max(t['iterations'], it)
        if ev.get('event') == 'retry':
            t['retries'] += 1
        if ev.get('event') == 'verification' and (ev.get('verification') or {}).get('gate'):
            gate = ev['verification']['gate']
            bucket = t['verifications'].setdefault(gate, {'passed': 0, 'failed': 0})
            passed = ev['verification'].get('passed')
            if passed is True:
                bucket['passed'] += 1
            elif passed is False:
                bucket['failed'] += 1

    for s in specialists:
        t = ensure(s['taskId'])
        t['specialists'].append(s)
        if not t['taskEnd']:
            t['usage'] = merge_usage(t['usage'], s['usage'])
            t['costUsd'] = add_cost(t['costUsd'], s['costUsd'])
    return sorted(by_task.values(), key=lambda x: x['taskId'])


def aggregate_by_run(events: list[dict]) -> list[dict]:
    by_run: dict[str, list] = {}
    for ev in events:
        by_run.setdefault(ev['runId'], []).append(ev)
    out = []
    for run_id, run_events in by_run.items():
        tasks = aggregate_by_task(run_events)
        run_end = next((e for e in reversed(run_events) if e.get('event') == 'run.end'), None)
        usage = empty_usage()
        cost_usd: float | None = None
        if run_end and run_end.get('usage'):
            usage = merge_usage(usage, run_end['usage'])
            cost_usd = (run_end.get('cost') or {}).get('usd')
        else:
            for t in tasks:
                usage = merge_usage(usage, t['usage'])
                cost_usd = add_cost(cost_usd, t['costUsd'])
        out.append({
            'runId': run_id, 'usage': usage, 'costUsd': cost_usd,
            'durationMs': (run_end or {}).get('durationMs'),
            'tasks': tasks, 'runEnd': run_end,
        })
    return sorted(out, key=lambda x: x['runId'])


def apply_privacy(event: dict, privacy: str) -> dict:
    next_ev = dict(event)
    next_ev['privacy'] = privacy
    loop = dict(next_ev['loop']) if isinstance(next_ev.get('loop'), dict) else None
    if privacy != 'strict':
        if loop and isinstance(loop.get('retryReason'), str) and len(loop['retryReason']) > 120:
            loop = {**loop, 'retryReason': loop['retryReason'][:120]}
            next_ev['loop'] = loop
        return next_ev
    model = next_ev.get('model')
    if isinstance(model, dict):
        next_ev['model'] = {'id': None, 'provider': model.get('provider'), 'effort': model.get('effort')}
    agent = next_ev.get('agent')
    if isinstance(agent, dict):
        next_ev['agent'] = {'role': agent.get('role'), 'agentId': None}
    if loop and loop.get('retryReason'):
        digest = hashlib.sha256(str(loop['retryReason']).encode('utf-8')).hexdigest()[:16]
        next_ev['loop'] = {**loop, 'retryReason': f'sha256:{digest}'}
    return next_ev


def base_event(event: str, **fields: Any) -> dict:
    payload = {
        'schema': SCHEMA,
        'ts': _now(),
        'harness': {
            'name': HARNESS_NAME,
            'version': HARNESS_VERSION,
            'commit': _git_commit(),
            'promptCompilerVersion': None,
            'promptFingerprint': None,
        },
        'runId': fields.pop('runId', None) or _run_id(),
        'taskId': fields.pop('taskId', None),
        'agent': fields.pop('agent', None),
        'event': event,
        'host': fields.pop('host', {'name': 'claude-code', 'version': None, 'mode': None}),
        'model': fields.pop('model', None),
        'usage': fields.pop('usage', None),
        'cost': fields.pop('cost', None),
        'loop': fields.pop('loop', None),
        'verification': fields.pop('verification', None),
        'durationMs': fields.pop('durationMs', None),
        'outcome': fields.pop('outcome', None),
        'source': fields.pop('source', {'usage': 'harness', 'reliability': 'medium'}),
        'privacy': fields.pop('privacy', None) or _read_metrics_cfg().get('privacy') or 'standard',
    }
    payload.update(fields)
    return payload


def emit(event: str, **fields: Any) -> None:
    """Escribe un evento JSONL. Nunca lanza hacia el llamador de sdd."""
    try:
        privacy = fields.get('privacy') or _read_metrics_cfg().get('privacy') or 'standard'
        if privacy not in ('standard', 'strict'):
            privacy = 'standard'
        payload = apply_privacy(base_event(event, **fields), privacy)
        path = runs_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n')
    except Exception:
        return


def purge() -> None:
    path = runs_path()
    if path.is_file():
        path.unlink()
    cur = state_dir() / 'current_run_id'
    if cur.is_file():
        cur.unlink()


def handle_hook(event_name: str, payload: dict) -> None:
    """SubagentStop → agent.end; SessionEnd → run.end (§1.3 / §7)."""
    session_id = payload.get('session_id')
    run_id = f'r-{hashlib.sha256(str(session_id or uuid.uuid4()).encode()).hexdigest()[:12]}'
    if event_name == 'SubagentStop':
        role = payload.get('agent_type')
        if role not in AGENT_ROLES:
            role = 'main'
        emit(
            'agent.end',
            runId=run_id,
            agent={'role': role, 'agentId': payload.get('agent_id')},
            source={'usage': 'harness', 'reliability': 'medium'},
        )
        return
    if event_name == 'SessionEnd':
        emit('run.end', runId=run_id, source={'usage': 'harness', 'reliability': 'medium'})


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ('-h', '--help'):
        print('usage: metrics.py hook <SubagentStop|SessionEnd> | purge | schema-hash')
        print('       metrics.py bench run|report …')
        print('       metrics.py prompt-diff <dirA> <dirB>')
        return 0
    cmd = args[0]
    if cmd == 'purge':
        purge()
        print('Telemetría local borrada.')
        return 0
    if cmd == 'schema-hash':
        # Bytes reales; `.gitattributes` eol=lf garantiza LF en checkout.
        raw = (ROOT / 'schemas' / 'harness-telemetry.v1.json').read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        print(digest)
        return 0 if digest == EXPECTED_SCHEMA_SHA256 else 1
    if cmd == 'hook' and len(args) >= 2:
        raw = sys.stdin.read()
        try:
            payload = json.loads(raw) if raw.strip() else {}
        except ValueError:
            return 0
        if not isinstance(payload, dict):
            return 0
        handle_hook(args[1], payload)
        return 0
    if cmd == 'bench':
        try:
            import bench as _bench
        except ImportError:
            print('ERROR: falta .microharness/bench.py (instala con --with-metrics).',
                  file=sys.stderr)
            return 1
        return _bench.cmd_bench(args[1:])
    if cmd == 'prompt-diff':
        try:
            import bench as _bench
        except ImportError:
            print('ERROR: falta .microharness/bench.py (instala con --with-metrics).',
                  file=sys.stderr)
            return 1
        return _bench.cmd_prompt_diff(args[1:])
    print('ERROR: subcomando no reconocido', file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
