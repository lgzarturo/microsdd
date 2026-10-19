#!/usr/bin/env python3
"""Bench runner, estadística y prompt-diff (m2). Solo stdlib. Resultados fuera del repo."""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BENCH = ROOT / 'bench'
TASKS = BENCH / 'tareas'
DEFAULT_CONFIG = {
    'n': 5,
    'nCheap': 3,
    'seed': 42,
    'bootstrap': 10000,
    'efficiencyDeltaPct': 10,
    'qualityTokenCeilingPct': 15,
    'claim': 'efficiency',  # efficiency | quality
    'models': [],  # rellenar con IDs :free; vacío = pendiente
    'baselineStatus': 'pending',
    # Tope de limit de la key OpenRouter (USD/mes). Arturo: key real con $5.
    'maxPaidLimitUsd': 5,
}
# Límites OpenRouter :free (documentados; riesgo de corte).
FREE_RPM = 20
FREE_RPD_LOW = 50  # < 10 créditos comprados
FREE_RPD_HIGH = 1000


class BenchError(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')


def load_config(path: Path | None = None) -> dict:
    cfg = dict(DEFAULT_CONFIG)
    p = path or (BENCH / 'config.json')
    if p.is_file():
        data = json.loads(p.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise BenchError('bench/config.json debe ser un objeto')
        cfg.update(data)
    return cfg


def list_tasks() -> list[dict]:
    if not TASKS.is_dir():
        raise BenchError(f'Falta {TASKS}')
    out = []
    for d in sorted(TASKS.iterdir()):
        meta = d / 'task.json'
        if d.is_dir() and meta.is_file():
            data = json.loads(meta.read_text(encoding='utf-8'))
            data['_dir'] = str(d)
            out.append(data)
    if len(out) != 5:
        raise BenchError(f'Se esperan 5 tareas en bench/tareas/; hay {len(out)}')
    return out


def assert_free_model(model_id: str) -> None:
    # Solo sufijo exacto ':free' (minúsculas); ':FREE' u otros fallan.
    if not isinstance(model_id, str) or not model_id.endswith(':free'):
        raise BenchError(
            f'Modelo {model_id!r} no termina en :free; la línea base solo admite modelos gratis.')


def _require_number(data: dict, key: str, *, label: str | None = None) -> float:
    """Fail-closed: campo presente, numérico finito (no bool/str/null)."""
    name = label or key
    if key not in data:
        raise BenchError(f'/api/v1/key: falta {name} (fail-closed).')
    val = data[key]
    if val is None:
        raise BenchError(f'/api/v1/key: {name} es null (fail-closed).')
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise BenchError(
            f'/api/v1/key: {name} tipo inesperado {type(val).__name__}={val!r} (fail-closed).')
    num = float(val)
    if math.isnan(num) or math.isinf(num):
        raise BenchError(f'/api/v1/key: {name}={val} no es finito (fail-closed).')
    return num


def _require_nonneg_int(data: dict, key: str, *, label: str | None = None) -> int:
    """Fail-closed: entero/float no bool, >= 0."""
    num = _require_number(data, key, label=label)
    if num < 0 or num != int(num):
        raise BenchError(
            f'/api/v1/key: {label or key}={num} no es un entero >= 0 (fail-closed).')
    return int(num)


def fetch_openrouter_key(api_key: str) -> dict:
    """GET /api/v1/key → objeto data (fail-closed ante HTTP/JSON inválido)."""
    if not api_key:
        raise BenchError(
            'OPENROUTER_API_KEY ausente; no se lanza la línea base real. '
            'Usa --provider fake para pruebas deterministas.')
    req = urllib.request.Request(
        'https://openrouter.ai/api/v1/key',
        headers={'Authorization': f'Bearer {api_key}', 'User-Agent': 'microsdd-bench/0'},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode('utf-8'))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        raise BenchError(f'No se pudo consultar /api/v1/key: {exc}') from exc
    if not isinstance(body, dict):
        raise BenchError('/api/v1/key: JSON raíz no es objeto (fail-closed).')
    data = body.get('data')
    if not isinstance(data, dict) or not data:
        raise BenchError('/api/v1/key: data ausente o vacío (fail-closed).')
    return data


def read_usage(data: dict) -> float:
    """Lee usage numérico fail-closed."""
    usage = _require_number(data, 'usage')
    if usage < 0:
        raise BenchError(f'/api/v1/key: usage={usage} negativo (fail-closed).')
    return usage


def check_openrouter_free_lock(
    api_key: str | None,
    n_total: int,
    *,
    max_paid_limit_usd: float = 5.0,
    data: dict | None = None,
) -> dict:
    """Candado :free + limit finito ≤ tope. Fail-closed. Devuelve data de /key."""
    if type(n_total) is not int or n_total < 1:
        raise BenchError(f'n_total inválido: {n_total!r}')
    if not isinstance(max_paid_limit_usd, (int, float)) or isinstance(max_paid_limit_usd, bool):
        raise BenchError(f'maxPaidLimitUsd inválido: {max_paid_limit_usd!r}')
    max_cap = float(max_paid_limit_usd)
    if max_cap < 0 or math.isnan(max_cap) or math.isinf(max_cap):
        raise BenchError(f'maxPaidLimitUsd inválido: {max_paid_limit_usd!r}')

    if data is None:
        data = fetch_openrouter_key(api_key or '')

    # usage debe ser número finito (snapshot); no se exige 0.
    read_usage(data)

    # limit: numérico finito y ≤ tope (null/ilimitado aborta).
    limit = _require_number(data, 'limit')
    if limit < 0:
        raise BenchError(f'/api/v1/key: limit={limit} negativo (fail-closed).')
    if limit > max_cap:
        raise BenchError(
            f'/api/v1/key: limit={limit} supera tope maxPaidLimitUsd={max_cap} (fail-closed).')

    # limit_remaining opcional: si aparece, debe ser numérico finito ≥ 0.
    for lr_key in ('limit_remaining', 'limitRemaining'):
        if lr_key in data:
            lr = _require_number(data, lr_key, label=lr_key)
            if lr < 0:
                raise BenchError(f'/api/v1/key: {lr_key}={lr} negativo (fail-closed).')

    free = data.get('free_model_daily_requests')
    if not isinstance(free, dict) or not free:
        raise BenchError(
            '/api/v1/key: free_model_daily_requests ausente o vacío (fail-closed; §3.6).')
    remaining = _require_nonneg_int(free, 'remaining', label='free_model_daily_requests.remaining')
    if remaining < n_total:
        raise BenchError(
            f'Cuota :free insuficiente: remaining={remaining}, hace falta {n_total} '
            f'(limite tipico {FREE_RPD_LOW}/dia o {FREE_RPD_HIGH}/dia; {FREE_RPM}/min).')
    return data


def assert_usage_unchanged(api_key: str, usage_before: float, *, data: dict | None = None) -> float:
    """Relee usage; si subió (delta > 0) aborta y la corrida queda inválida."""
    payload = data if data is not None else fetch_openrouter_key(api_key)
    usage_after = read_usage(payload)
    delta = usage_after - float(usage_before)
    if delta > 0:
        raise BenchError(
            f'usage subio durante la corrida: before={usage_before} after={usage_after} '
            f'delta={delta}; corrida invalida (solo :free sin gasto).')
    return usage_after


def verify_openrouter_model_pricing(api_key: str, model_id: str) -> dict:
    """Fail-closed: modelo :free con precio 0 en /api/v1/models."""
    assert_free_model(model_id)
    if not api_key:
        raise BenchError('OPENROUTER_API_KEY ausente para verificar precio del modelo.')
    req = urllib.request.Request(
        'https://openrouter.ai/api/v1/models',
        headers={'Authorization': f'Bearer {api_key}', 'User-Agent': 'microsdd-bench/0'},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode('utf-8'))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        raise BenchError(f'No se pudo consultar /api/v1/models: {exc}') from exc
    if not isinstance(body, dict):
        raise BenchError('/api/v1/models: JSON raíz no es objeto (fail-closed).')
    data = body.get('data')
    if not isinstance(data, list):
        raise BenchError('/api/v1/models: data no es lista (fail-closed).')
    match = None
    for item in data:
        if isinstance(item, dict) and item.get('id') == model_id:
            match = item
            break
    if match is None:
        raise BenchError(f'/api/v1/models: modelo {model_id!r} no encontrado (fail-closed).')
    pricing = match.get('pricing')
    if not isinstance(pricing, dict):
        raise BenchError(f'/api/v1/models: pricing ausente para {model_id!r} (fail-closed).')
    for key in ('prompt', 'completion'):
        if key not in pricing:
            raise BenchError(f'/api/v1/models: falta pricing.{key} (fail-closed).')
        raw = pricing[key]
        if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
            raise BenchError(
                f'/api/v1/models: pricing.{key} tipo inesperado {type(raw).__name__} (fail-closed).')
        try:
            num = float(raw)
        except (TypeError, ValueError) as exc:
            raise BenchError(
                f'/api/v1/models: pricing.{key}={raw!r} no parseable (fail-closed).') from exc
        if math.isnan(num) or math.isinf(num) or num != 0.0:
            raise BenchError(
                f'/api/v1/models: pricing.{key}={num} no es 0 (fail-closed; solo :free).')
    return match


def sanitize_report(report: dict) -> dict:
    """§7: agregados sin prompts, session_id, rutas ni keys."""
    forbidden = frozenset({
        'prompt', 'prompts', 'response', 'responses', 'diff', 'diffs',
        'toolOutput', 'tool_output', 'session_id', 'sessionId', 'transcript',
        'apiKey', 'api_key', 'authToken', 'workdir', 'cwd', 'path', 'paths',
        'raw', 'stdout', 'stderr', 'message', 'messages', 'errorClass',
    })
    cell_keep = frozenset({
        'taskId', 'variant', 'repetition', 'success', 'pending', 'iterations',
        'retries', 'calls', 'tokens', 'costUsd', 'durationMs', 'cacheRate',
        'firstTry', 'modelId', 'seed', 'hostVersion', 'status',
        'exitCode', 'stderrTruncated', 'subtype', 'isError', 'errorClass',
    })

    def scrub(obj: Any) -> Any:
        if isinstance(obj, dict):
            out = {}
            for k, v in obj.items():
                if k in forbidden:
                    continue
                if k == 'cells' and isinstance(v, list):
                    out[k] = [
                        {ck: scrub(c[ck]) for ck in cell_keep if isinstance(c, dict) and ck in c}
                        for c in v
                    ]
                else:
                    out[k] = scrub(v)
            return out
        if isinstance(obj, list):
            return [scrub(x) for x in obj]
        return obj

    cleaned = scrub(report)
    if not isinstance(cleaned, dict):
        raise BenchError('sanitize_report: resultado no es objeto')
    cleaned['privacy'] = 'strict-aggregate'
    cleaned['schema'] = report.get('schema') or 'microsdd-bench-report/v1'
    return cleaned


def safe_print(text: str) -> None:
    """Imprime sin depender del encoding de la consola (Windows cp1252)."""
    payload = (text if text.endswith('\n') else text + '\n').encode('utf-8', errors='replace')
    buf = getattr(sys.stdout, 'buffer', None)
    if buf is not None:
        buf.write(payload)
        buf.flush()
        return
    # Fallback: ASCII sustituyendo no representables.
    sys.stdout.write(payload.decode('ascii', errors='replace'))
    sys.stdout.flush()


def median(xs: list[float]) -> float | None:
    if not xs:
        return None
    return float(statistics.median(xs))


def iqr(xs: list[float]) -> list[float] | None:
    if len(xs) < 2:
        return None
    q = statistics.quantiles(xs, n=4)
    return [float(q[0]), float(q[2])]


def wilson_interval(k: int, n: int, z: float = 1.96) -> list[float]:
    if n <= 0:
        return [0.0, 0.0]
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / den
    return [max(0.0, centre - margin), min(1.0, centre + margin)]


def bootstrap_ci_delta(
    base: list[float],
    treat: list[float],
    *,
    seed: int,
    n_boot: int = 10000,
) -> list[float]:
    """IC 95 % de mediana(treat) − mediana(base) por bootstrap."""
    rng = random.Random(seed)
    if not base or not treat:
        return [0.0, 0.0]
    deltas = []
    for _ in range(n_boot):
        b = [base[rng.randrange(len(base))] for _ in base]
        t = [treat[rng.randrange(len(treat))] for _ in treat]
        deltas.append(statistics.median(t) - statistics.median(b))
    deltas.sort()
    lo = deltas[int(0.025 * (n_boot - 1))]
    hi = deltas[int(0.975 * (n_boot - 1))]
    return [float(lo), float(hi)]


def total_tokens(usage: dict | None) -> int | None:
    if not usage:
        return None
    parts = [usage.get('input'), usage.get('cacheRead'), usage.get('cacheWrite'), usage.get('output')]
    if all(p is None for p in parts):
        return None
    return int(sum(p or 0 for p in parts))


class FakeProvider:
    """Proveedor determinista para tests; no llama a modelos."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def run_cell(self, task: dict, variant: str, repetition: int,
                 workdir: Path | None = None) -> dict:
        # Base ligeramente peor que tratamiento para que efficiency pueda ACEPTA en fixtures.
        bias = 0 if variant == 'treatment' else 1
        tokens = 1000 + bias * 200 + repetition * 10 + self.rng.randint(0, 50)
        success = True if variant == 'treatment' else (repetition % 5 != 0)  # 4/5 base
        if variant == 'treatment':
            success = True  # 5/5
        return {
            'success': success,
            'iterations': 1 + bias,
            'retries': bias,
            'calls': 2 + bias,
            'tokens': tokens,
            'costUsd': 0.0,
            'durationMs': 100 + bias * 20,
            'cacheRate': 0.5,
            'firstTry': success and bias == 0,
            'modelId': 'fake/test:free',
            'seed': None,
        }


def _scrub_secrets(text: str) -> str:
    """Quita valores de keys del texto (nunca imprimir secrets)."""
    out = text or ''
    for env_key in ('OPENROUTER_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_API_KEY'):
        val = os.environ.get(env_key) or ''
        if len(val) >= 8:
            out = out.replace(val, '[REDACTED]')
    return out


class ClaudeCodeProvider:
    """Bench agéntico vía Claude Code + OpenRouter (:free)."""

    MIN_INTERVAL_S = 3.1  # respeta ~20 req/min entre celdas
    CELL_TIMEOUT_S = 900

    def __init__(self, model_id: str, *, claude_bin: str = 'claude'):
        assert_free_model(model_id)
        self.model_id = model_id
        self.claude_bin = claude_bin
        self._last_call = 0.0
        self.host_version = self._detect_version()

    def _detect_version(self) -> str | None:
        try:
            proc = subprocess.run(
                [self.claude_bin, '--version'], capture_output=True, text=True,
                timeout=30, check=False)
            out = (proc.stdout or proc.stderr or '').strip()
            return out.splitlines()[0][:120] if out else None
        except (OSError, subprocess.TimeoutExpired):
            return None

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if elapsed < self.MIN_INTERVAL_S:
            time.sleep(self.MIN_INTERVAL_S - elapsed)

    def _env(self) -> dict[str, str]:
        env = os.environ.copy()
        # Key solo desde entorno; no se imprime.
        or_key = env.get('OPENROUTER_API_KEY') or env.get('ANTHROPIC_AUTH_TOKEN') or ''
        env['ANTHROPIC_BASE_URL'] = 'https://openrouter.ai/api'
        env['ANTHROPIC_AUTH_TOKEN'] = or_key
        env['ANTHROPIC_API_KEY'] = ''
        env['ANTHROPIC_DEFAULT_SONNET_MODEL'] = self.model_id
        env['ANTHROPIC_DEFAULT_OPUS_MODEL'] = self.model_id
        env['ANTHROPIC_DEFAULT_HAIKU_MODEL'] = self.model_id
        env['CLAUDE_CODE_SUBAGENT_MODEL'] = self.model_id
        # Evitar prompts interactivos de trust/onboarding en CI.
        env.setdefault('CI', 'true')
        env.setdefault('CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC', '1')
        return env

    def _prompt(self, task: dict) -> str:
        title = task.get('title') or task.get('id')
        cmd = ' '.join(task.get('testCommand') or ['python', '-m', 'unittest', 'test_fixture'])
        return (
            f'Fix the Python fixture in the current directory so `{cmd}` passes. '
            f'Task: {title}. Edit only local fixture files. Do not print secrets.'
        )

    def _pending_diag(self, *, exit_code: int | None, stderr: str, subtype: Any,
                      is_error: Any, error_class: str | None = None,
                      duration_ms: int | None = None) -> dict:
        return {
            'success': False, 'pending': True, 'status': 'pending',
            'iterations': None, 'retries': None, 'calls': None, 'tokens': None,
            'costUsd': None, 'durationMs': duration_ms, 'cacheRate': None,
            'firstTry': None, 'modelId': self.model_id, 'seed': None,
            'hostVersion': self.host_version,
            'exitCode': exit_code,
            'stderrTruncated': _scrub_secrets(stderr)[:800],
            'subtype': subtype if isinstance(subtype, str) else None,
            'isError': is_error if isinstance(is_error, bool) else None,
            'errorClass': error_class,
        }

    def run_cell(self, task: dict, variant: str, repetition: int,
                 workdir: Path | None = None) -> dict:
        if workdir is None:
            return self._pending_diag(
                exit_code=None, stderr='workdir ausente', subtype=None, is_error=True)
        self._throttle()
        env = self._env()
        # Flags compatibles con Claude Code 2.1.197 + OpenRouter (Arturo).
        cmd = [
            self.claude_bin, '-p', self._prompt(task),
            '--output-format', 'json',
            '--dangerously-skip-permissions',
            '--allowedTools', 'Read,Edit,Bash',
            '--model', self.model_id,
        ]
        started = time.monotonic()
        self._last_call = started
        try:
            proc = subprocess.run(
                cmd, cwd=str(workdir), env=env, capture_output=True, text=True,
                timeout=self.CELL_TIMEOUT_S, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return self._pending_diag(
                exit_code=None, stderr=str(exc)[:800], subtype=None, is_error=True,
                error_class=type(exc).__name__,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
        duration_ms = int((time.monotonic() - started) * 1000)
        payload: dict = {}
        raw_out = (proc.stdout or '').strip()
        if raw_out:
            try:
                parsed = json.loads(raw_out)
                if isinstance(parsed, dict):
                    payload = parsed
            except ValueError:
                payload = {}
        subtype = payload.get('subtype')
        is_error = payload.get('is_error')
        stderr_trunc = _scrub_secrets(proc.stderr or '')[:800]
        usage = payload.get('usage') if isinstance(payload.get('usage'), dict) else {}
        model_usage = payload.get('modelUsage') if isinstance(payload.get('modelUsage'), dict) else {}
        tokens = None
        if usage:
            parts = [
                usage.get('input_tokens'), usage.get('output_tokens'),
                usage.get('cache_read_input_tokens'), usage.get('cache_creation_input_tokens'),
            ]
            if any(isinstance(p, (int, float)) for p in parts):
                tokens = int(sum(p or 0 for p in parts if isinstance(p, (int, float))))
        if tokens is None and model_usage:
            total = 0
            found = False
            for entry in model_usage.values():
                if not isinstance(entry, dict):
                    continue
                found = True
                total += int(entry.get('inputTokens') or 0)
                total += int(entry.get('outputTokens') or 0)
                total += int(entry.get('cacheReadInputTokens') or 0)
                total += int(entry.get('cacheCreationInputTokens') or 0)
            if found:
                tokens = total
        cost = payload.get('total_cost_usd')
        if not isinstance(cost, (int, float)):
            cost = None
        test_cmd = list(task.get('testCommand') or ['python', '-m', 'unittest', 'test_fixture'])
        test_ok = False
        try:
            tproc = subprocess.run(
                test_cmd, cwd=str(workdir), capture_output=True, text=True,
                timeout=60, check=False)
            test_ok = tproc.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            test_ok = False
        # Fallo inmediato de Claude (login, flags, 429, …) → pending + diagnóstico.
        if proc.returncode != 0 or is_error is True or not payload:
            return self._pending_diag(
                exit_code=proc.returncode, stderr=stderr_trunc, subtype=subtype,
                is_error=is_error if isinstance(is_error, bool) else True,
                duration_ms=duration_ms,
            )
        pending = not test_ok and tokens is None
        return {
            'success': bool(test_ok),
            'pending': bool(pending),
            'status': 'pending' if pending else ('ok' if test_ok else 'fail'),
            'iterations': 1,
            'retries': 0,
            'calls': 1,
            'tokens': tokens,
            'costUsd': float(cost) if cost is not None else 0.0,
            'durationMs': duration_ms,
            'cacheRate': None,
            'firstTry': bool(test_ok),
            'modelId': self.model_id,
            'seed': None,
            'hostVersion': self.host_version,
            'exitCode': proc.returncode,
            'stderrTruncated': stderr_trunc,
            'subtype': subtype if isinstance(subtype, str) else None,
            'isError': is_error if isinstance(is_error, bool) else False,
        }


def copy_fixture(task_dir: Path, dest: Path) -> None:
    src = task_dir / 'fixture'
    if dest.exists():
        shutil.rmtree(dest)
    if src.is_dir():
        shutil.copytree(src, dest)
    else:
        dest.mkdir(parents=True)


def run_bench(
    *,
    provider: Any,
    cheap: bool = False,
    claim: str | None = None,
    config: dict | None = None,
    models: list[str] | None = None,
    skip_key_check: bool = False,
) -> dict:
    cfg = config or load_config()
    claim = claim or cfg.get('claim') or 'efficiency'
    n = int(cfg['nCheap'] if cheap else cfg['n'])
    seed = int(cfg.get('seed', 42))
    tasks = list_tasks()
    model_list = models if models is not None else list(cfg.get('models') or [])
    api_key: str | None = None
    usage_before: float | None = None
    if not skip_key_check and not isinstance(provider, FakeProvider):
        for mid in model_list:
            assert_free_model(mid)
        n_total = n * len(tasks) * 2  # base + treatment intercalados
        api_key = os.environ.get('OPENROUTER_API_KEY')
        max_cap = cfg.get('maxPaidLimitUsd', DEFAULT_CONFIG['maxPaidLimitUsd'])
        key_data = check_openrouter_free_lock(
            api_key, n_total, max_paid_limit_usd=max_cap)
        usage_before = read_usage(key_data)
        if not model_list:
            raise BenchError('bench.config models vacío; línea base pendiente de IDs :free.')

    # Orden intercalado A/B con semilla (deriva temporal).
    rng = random.Random(seed)
    schedule: list[tuple[dict, str, int]] = []
    for task in tasks:
        for rep in range(n):
            schedule.append((task, 'base', rep))
            schedule.append((task, 'treatment', rep))
    rng.shuffle(schedule)
    # Re-intercalar aproximadamente A/B manteniendo pares por tarea.
    schedule.sort(key=lambda x: (x[0]['id'], x[2], 0 if x[1] == 'base' else 1))

    cells: list[dict] = []
    pending_rest = False
    last_task_id: str | None = None
    with tempfile.TemporaryDirectory(prefix='microsdd-bench-') as tmp:
        tmp_path = Path(tmp)
        for task, variant, rep in schedule:
            if pending_rest:
                cells.append({
                    'taskId': task['id'], 'variant': variant, 'repetition': rep,
                    'success': False, 'pending': True, 'status': 'pending',
                    'iterations': None, 'retries': None, 'calls': None,
                    'tokens': None, 'costUsd': None, 'durationMs': None,
                    'cacheRate': None, 'firstTry': None,
                    'modelId': (model_list[0] if model_list else None), 'seed': None,
                })
                continue
            if (usage_before is not None and api_key is not None
                    and last_task_id is not None and task['id'] != last_task_id):
                # Candado entre tareas: usage no debe subir; cuota restante.
                key_data = fetch_openrouter_key(api_key)
                assert_usage_unchanged(api_key, usage_before, data=key_data)
                free = key_data.get('free_model_daily_requests')
                if isinstance(free, dict) and 'remaining' in free:
                    try:
                        rem = _require_nonneg_int(
                            free, 'remaining', label='free_model_daily_requests.remaining')
                    except BenchError:
                        raise
                    if rem < 1:
                        pending_rest = True
                        cells.append({
                            'taskId': task['id'], 'variant': variant, 'repetition': rep,
                            'success': False, 'pending': True, 'status': 'pending',
                            'iterations': None, 'retries': None, 'calls': None,
                            'tokens': None, 'costUsd': None, 'durationMs': None,
                            'cacheRate': None, 'firstTry': None,
                            'modelId': (model_list[0] if model_list else None), 'seed': None,
                        })
                        continue
            last_task_id = task['id']
            work = tmp_path / f"{task['id']}-{variant}-{rep}"
            copy_fixture(Path(task['_dir']), work)
            try:
                try:
                    result = provider.run_cell(task, variant, rep, workdir=work)
                except TypeError:
                    result = provider.run_cell(task, variant, rep)
            except BenchError:
                raise
            except Exception:
                result = {
                    'success': False, 'pending': True, 'status': 'pending',
                    'iterations': None, 'retries': None, 'calls': None,
                    'tokens': None, 'costUsd': None, 'durationMs': None,
                    'cacheRate': None, 'firstTry': None,
                    'modelId': (model_list[0] if model_list else None), 'seed': None,
                }
            cells.append({
                'taskId': task['id'],
                'variant': variant,
                'repetition': rep,
                **result,
            })

    usage_after = None
    if usage_before is not None and api_key is not None:
        usage_after = assert_usage_unchanged(api_key, usage_before)

    report = aggregate_report(cells, cfg=cfg, claim=claim, cheap=cheap, seed=seed, n=n)
    report['models'] = model_list
    report['baselineStatus'] = cfg.get('baselineStatus', 'pending')
    report['usageBefore'] = usage_before
    report['usageAfter'] = usage_after
    report['pendingCells'] = [
        {'taskId': c['taskId'], 'variant': c['variant'], 'repetition': c['repetition']}
        for c in cells if c.get('pending')
    ]
    report['risks'] = [
        f'OpenRouter :free: ~{FREE_RPM} req/min; {FREE_RPD_LOW} o {FREE_RPD_HIGH} req/día según créditos.',
        f'Candado: modelos :free; limit de key <= maxPaidLimitUsd '
        f'({cfg.get("maxPaidLimitUsd", DEFAULT_CONFIG["maxPaidLimitUsd"])}); '
        'usage no debe subir durante la corrida.',
        '[No verificado] Política de datos y retención de modelos :free de OpenRouter.',
        'Semilla Claude Code: seed=null (sin flag documentado).',
    ]
    return report


def _by_variant(cells: list[dict], task_id: str | None = None) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {'base': [], 'treatment': []}
    for c in cells:
        if task_id is not None and c['taskId'] != task_id:
            continue
        out[c['variant']].append(c)
    return out


def aggregate_report(
    cells: list[dict],
    *,
    cfg: dict,
    claim: str,
    cheap: bool,
    seed: int,
    n: int,
) -> dict:
    task_ids = sorted({c['taskId'] for c in cells})
    rows = []
    non_inf_ok = True
    for tid in task_ids:
        parts = _by_variant(cells, tid)
        b_done = [c for c in parts['base'] if not c.get('pending')]
        t_done = [c for c in parts['treatment'] if not c.get('pending')]
        b_succ = sum(1 for c in b_done if c.get('success'))
        t_succ = sum(1 for c in t_done if c.get('success'))
        nb, nt = len(b_done), len(t_done)
        # No inferioridad: ninguna tarea ≥4/5 → ≤2/5.
        if nb >= 5 and b_succ >= 4 and t_succ <= 2:
            non_inf_ok = False
        b_tok = [float(c['tokens']) for c in b_done if c.get('tokens') is not None]
        t_tok = [float(c['tokens']) for c in t_done if c.get('tokens') is not None]
        b_it = [float(c['iterations']) for c in parts['base']
                if c.get('iterations') is not None and not c.get('pending')]
        t_it = [float(c['iterations']) for c in parts['treatment']
                if c.get('iterations') is not None and not c.get('pending')]
        d_tok = (median(t_tok) or 0) - (median(b_tok) or 0)
        ci_tok = bootstrap_ci_delta(b_tok, t_tok, seed=seed + hash(tid) % 1000,
                                   n_boot=int(cfg.get('bootstrap', 10000)))
        rows.append({
            'taskId': tid,
            'base': {
                'success': f'{b_succ}/{nb}',
                'successWilson': wilson_interval(b_succ, nb),
                'tokensMedian': median(b_tok),
                'tokensIqr': iqr(b_tok),
                'iterationsMedian': median(b_it),
            },
            'treatment': {
                'success': f'{t_succ}/{nt}',
                'successWilson': wilson_interval(t_succ, nt),
                'tokensMedian': median(t_tok),
                'tokensIqr': iqr(t_tok),
                'iterationsMedian': median(t_it),
            },
            'deltaTokens': d_tok,
            'deltaTokensCI95': ci_tok,
        })

    all_b = [c for c in _by_variant(cells)['base'] if not c.get('pending')]
    all_t = [c for c in _by_variant(cells)['treatment'] if not c.get('pending')]
    kb, kt = sum(1 for c in all_b if c.get('success')), sum(1 for c in all_t if c.get('success'))
    nb, nt = len(all_b), len(all_t)
    rate_b, rate_t = (kb / nb if nb else 0.0), (kt / nt if nt else 0.0)
    b_tok = [float(c['tokens']) for c in all_b if c.get('tokens') is not None]
    t_tok = [float(c['tokens']) for c in all_t if c.get('tokens') is not None]
    b_it = [float(c['iterations']) for c in all_b if c.get('iterations') is not None]
    t_it = [float(c['iterations']) for c in all_t if c.get('iterations') is not None]
    d_tok = (median(t_tok) or 0) - (median(b_tok) or 0)
    ci_tok = bootstrap_ci_delta(b_tok, t_tok, seed=seed, n_boot=int(cfg.get('bootstrap', 10000)))
    d_it = (median(t_it) or 0) - (median(b_it) or 0)
    ci_it = bootstrap_ci_delta(b_it, t_it, seed=seed + 1, n_boot=int(cfg.get('bootstrap', 10000)))

    x = float(cfg.get('efficiencyDeltaPct', 10)) / 100.0
    y = float(cfg.get('qualityTokenCeilingPct', 15)) / 100.0
    expected = n * max(1, len(task_ids))
    # Sin datos suficientes: no rechazar; marcar inconcluso (celdas pending aparte).
    if nb == 0 or nt == 0 or nb < expected or nt < expected:
        verdict = 'NO CONCLUYENTE'
    else:
        success_ok = rate_t >= rate_b and non_inf_ok
        med_b_tok = median(b_tok) or 0
        efficiency_ok = (
            med_b_tok > 0
            and d_tok <= -x * med_b_tok
            and ci_tok[1] < 0
        ) or (
            (median(b_it) or 0) > 0
            and d_it <= -x * (median(b_it) or 1)
            and ci_it[1] < 0
        )
        quality_ok = med_b_tok == 0 or d_tok <= y * med_b_tok

        if not success_ok:
            verdict = 'RECHAZA'
        elif claim == 'efficiency' and not efficiency_ok:
            # IC cruza 0 o no baja lo suficiente
            verdict = (
                'NO CONCLUYENTE'
                if ci_tok[0] < 0 < ci_tok[1] or ci_it[0] < 0 < ci_it[1]
                else 'RECHAZA'
            )
        elif claim == 'quality' and not quality_ok:
            verdict = 'RECHAZA'
        elif claim == 'efficiency' and efficiency_ok:
            verdict = 'ACEPTA'
        elif claim == 'quality' and quality_ok and success_ok:
            verdict = 'ACEPTA'
        else:
            verdict = 'NO CONCLUYENTE'

    return {
        'schema': 'microsdd-bench-report/v1',
        'ts': _now(),
        'cheap': bool(cheap),
        'claim': claim,
        'n': n,
        'seed': seed,
        'verdict': verdict,
        'success': {'base': f'{kb}/{nb}', 'treatment': f'{kt}/{nt}',
                    'baseWilson': wilson_interval(kb, nb),
                    'treatmentWilson': wilson_interval(kt, nt)},
        'tokens': {
            'baseMedian': median(b_tok), 'treatmentMedian': median(t_tok),
            'delta': d_tok, 'ci95': ci_tok,
        },
        'iterations': {
            'baseMedian': median(b_it), 'treatmentMedian': median(t_it),
            'delta': d_it, 'ci95': ci_it,
        },
        'tasks': rows,
        'cells': cells,
        'costUsdTotal': sum(float(c.get('costUsd') or 0) for c in cells),
        'notes': {
            'dataPolicyFreeModels': '[No verificado]',
            'seedClaudeCode': None,
        },
    }


def format_report_md(report: dict) -> str:
    lines = [
        f"# Bench report ({report.get('verdict')})",
        '',
        f"- ts: `{report.get('ts')}`",
        f"- cheap: `{report.get('cheap')}` | N={report.get('n')} | seed={report.get('seed')}",
        f"- claim: `{report.get('claim')}`",
        f"- success: base {report['success']['base']} -> treatment {report['success']['treatment']}",
        f"- tokens delta: {report['tokens']['delta']} IC95 {report['tokens']['ci95']}",
        f"- iterations delta: {report['iterations']['delta']} IC95 {report['iterations']['ci95']}",
        f"- costUsdTotal: {report.get('costUsdTotal')}",
        f"- baselineStatus: {report.get('baselineStatus')}",
        '',
        '| task | base success | treat success | delta tokens | IC95 |',
        '|---|---|---|---|---|',
    ]
    for row in report.get('tasks') or []:
        lines.append(
            f"| {row['taskId']} | {row['base']['success']} | {row['treatment']['success']} | "
            f"{row['deltaTokens']} | {row['deltaTokensCI95']} |"
        )
    lines += ['', '## Riesgos', '']
    for r in report.get('risks') or []:
        lines.append(f'- {r}')
    lines.append('')
    return '\n'.join(lines)


def write_report(report: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'bench-report.json').write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (out_dir / 'bench-report.md').write_text(format_report_md(report), encoding='utf-8')


# --- prompt-diff (§2) ---

PROMPT_PATHS = (
    'CLAUDE.md',
    '.claude/agents/lider.md',
    '.claude/agents/autor.md',
    '.claude/agents/implementador.md',
    '.claude/agents/revisor.md',
    '.claude/skills/sdd/SKILL.md',
    'docs/AGENT.md',
    'docs/arquitectura.md',
    'docs/convenciones.md',
    'docs/especificaciones.md',
)


def _shingles(text: str, n: int = 8) -> list[str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < n:
        return ['\n'.join(lines)] if lines else []
    return ['\n'.join(lines[i:i + n]) for i in range(len(lines) - n + 1)]


def _file_metrics(path: Path) -> dict:
    if not path.is_file():
        return {'bytes': 0, 'tokensEstimate': 0, 'sha256': None, 'dupRatio': 0.0}
    raw = path.read_bytes().replace(b'\r\n', b'\n')
    text = raw.decode('utf-8', errors='replace')
    sh = _shingles(text)
    hashes = [hashlib.sha256(s.encode()).hexdigest() for s in sh]
    dup = 0
    seen: set[str] = set()
    for h in hashes:
        if h in seen:
            dup += 1
        seen.add(h)
    dup_ratio = (dup / len(hashes)) if hashes else 0.0
    return {
        'bytes': len(raw),
        'tokensEstimate': max(1, len(raw) // 4) if raw else 0,
        'sha256': hashlib.sha256(raw).hexdigest(),
        'dupRatio': round(dup_ratio, 4),
        'label': 'estimate',
    }


def prompt_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for rel in PROMPT_PATHS:
        m = _file_metrics(root / rel)
        digest.update(rel.encode() + b'\0')
        digest.update((m['sha256'] or '').encode())
    return digest.hexdigest()


def prompt_diff(root_a: Path, root_b: Path) -> dict:
    layers = []
    for rel in PROMPT_PATHS:
        a, b = _file_metrics(root_a / rel), _file_metrics(root_b / rel)
        layers.append({
            'path': rel,
            'a': a,
            'b': b,
            'deltaBytes': b['bytes'] - a['bytes'],
            'deltaTokensEstimate': b['tokensEstimate'] - a['tokensEstimate'],
            'deltaDupRatio': round(b['dupRatio'] - a['dupRatio'], 4),
        })
    return {
        'schema': 'microsdd-prompt-diff/v1',
        'fingerprintA': prompt_fingerprint(root_a),
        'fingerprintB': prompt_fingerprint(root_b),
        'layers': layers,
    }


def cmd_bench(argv: list[str]) -> int:
    if not argv or argv[0] in ('-h', '--help'):
        print('usage: metrics.py bench run [--cheap] [--provider fake|openrouter] [--out DIR]')
        print('       metrics.py bench report --from DIR')
        return 0
    sub = argv[0]
    if sub == 'run':
        cheap = '--cheap' in argv
        provider_name = 'fake'
        out = None
        claim = None
        i = 1
        while i < len(argv):
            if argv[i] == '--cheap':
                i += 1
            elif argv[i] == '--provider' and i + 1 < len(argv):
                provider_name = argv[i + 1]
                i += 2
            elif argv[i] == '--out' and i + 1 < len(argv):
                out = Path(argv[i + 1])
                i += 2
            elif argv[i] == '--claim' and i + 1 < len(argv):
                claim = argv[i + 1]
                i += 2
            else:
                print(f'ERROR: argumento desconocido {argv[i]}', flush=True)
                return 1
        cfg = load_config()
        if provider_name == 'fake':
            provider = FakeProvider(seed=int(cfg.get('seed', 42)))
            skip = True
        elif provider_name == 'openrouter':
            skip = False
            try:
                models = list(cfg.get('models') or [])
                if not models:
                    raise BenchError(
                        'bench.config models vacío; indica IDs :free antes de openrouter.')
                for m in models:
                    assert_free_model(m)
                api_key = os.environ.get('OPENROUTER_API_KEY')
                if not api_key:
                    raise BenchError(
                        'OPENROUTER_API_KEY ausente; no se lanza la línea base real. '
                        'Usa --provider fake para pruebas deterministas.')
                n = int(cfg['nCheap'] if cheap else cfg['n'])
                max_cap = cfg.get('maxPaidLimitUsd', DEFAULT_CONFIG['maxPaidLimitUsd'])
                check_openrouter_free_lock(api_key, n * 5 * 2, max_paid_limit_usd=max_cap)
                for m in models:
                    verify_openrouter_model_pricing(api_key, m)
                provider = ClaudeCodeProvider(models[0])
            except BenchError as exc:
                print(f'ERROR: {exc}', flush=True)
                return 1
        else:
            print(f'ERROR: provider desconocido {provider_name}', flush=True)
            return 1
        try:
            report = run_bench(
                provider=provider, cheap=cheap, claim=claim, config=cfg, skip_key_check=skip)
        except BenchError as exc:
            print(f'ERROR: {exc}', flush=True)
            return 1
        dest = out or (Path(os.environ.get('XDG_STATE_HOME')
                            or (Path.home() / '.local' / 'state')) / 'microsdd' / 'bench-last')
        if os.name == 'nt' and out is None:
            dest = Path(os.environ.get('LOCALAPPDATA') or (Path.home() / 'AppData' / 'Local')) / 'microsdd' / 'bench-last'
        write_report(report, dest)
        sanitized = sanitize_report(report)
        (dest / 'bench-report.sanitized.json').write_text(
            json.dumps(sanitized, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')
        safe_print(format_report_md(report))
        safe_print(f'Reporte escrito en {dest}')
        return 0 if report['verdict'] != 'RECHAZA' else 2
    if sub == 'report':
        src = None
        i = 1
        while i < len(argv):
            if argv[i] == '--from' and i + 1 < len(argv):
                src = Path(argv[i + 1])
                i += 2
            else:
                print(f'ERROR: argumento desconocido {argv[i]}', flush=True)
                return 1
        if src is None:
            print('ERROR: indica --from DIR', flush=True)
            return 1
        data = json.loads((src / 'bench-report.json').read_text(encoding='utf-8'))
        safe_print(format_report_md(data))
        return 0
    print(f'ERROR: subcomando bench desconocido: {sub}', flush=True)
    return 1


def cmd_prompt_diff(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] in ('-h', '--help'):
        print('usage: metrics.py prompt-diff <dirA> <dirB>')
        return 0
    a, b = Path(argv[0]), Path(argv[1])
    diff = prompt_diff(a, b)
    safe_print(json.dumps(diff, indent=2, ensure_ascii=True))
    return 0
