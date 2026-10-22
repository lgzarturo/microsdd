#!/usr/bin/env python3
"""Bench runner, estadística y prompt-diff (m2). Solo stdlib. Resultados fuera del repo."""
from __future__ import annotations

import hashlib
import importlib.util
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
    'models': [],  # IDs :free o pago económico; vacío = pendiente
    'baselineStatus': 'pending',
    # Techo del campo `limit` de la key (créditos en cuenta; Arturo: $10).
    'maxPaidLimitUsd': 10,
    # Candado de gasto por repo: delta usage antes/después (Arturo: $5).
    'maxSpendUsd': 5,
    # Fracción del tope a partir de la cual se aborta ("se acerca").
    'spendApproachRatio': 0.8,
    # Presupuesto de solicitudes HTTP al modelo (turnos agénticos), no celdas.
    # Tope duro por repo (OpenRouter): 100; el proxy local rechaza el 101+.
    # maxTurnsPerCell=3 → cheap 30×3=90 ≤ 100 (matriz nueva 22 oct).
    'maxTurnsPerCell': 3,
    'maxRequestsPerRun': 100,
}
# Límites OpenRouter :free / proxy (documentados; riesgo de corte).
FREE_RPM = 20
FREE_RPD_LOW = 50  # < 10 créditos comprados
FREE_RPD_HIGH = 1000
# Fallback pago económico con tool use (alineable con CodeConductor).
DEFAULT_PAID_FALLBACK_MODEL = 'openai/gpt-oss-20b'


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


def request_budget(cfg: dict) -> tuple[int, int]:
    """Valida maxTurnsPerCell/maxRequestsPerRun (int >= 1, no bool). Fail-closed."""
    out = []
    for key in ('maxTurnsPerCell', 'maxRequestsPerRun'):
        val = cfg.get(key)
        if type(val) is not int or val < 1:
            raise BenchError(f'{key} inválido: {val!r} (entero >= 1).')
        out.append(val)
    return out[0], out[1]


def planned_requests(cfg: dict, cells: int) -> int:
    """Estimación de solicitudes = celdas × maxTurnsPerCell; aborta si supera maxRequestsPerRun."""
    max_turns, max_requests = request_budget(cfg)
    estimated = int(cells) * max_turns
    if estimated > max_requests:
        raise BenchError(
            f'Solicitudes estimadas {estimated} ({cells} celdas x {max_turns} turnos) '
            f'superan maxRequestsPerRun={max_requests}; no se lanza la corrida.')
    return estimated


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


def is_free_model(model_id: str) -> bool:
    return isinstance(model_id, str) and model_id.endswith(':free')


def assert_free_model(model_id: str) -> None:
    # Solo sufijo exacto ':free' (minúsculas); ':FREE' u otros fallan.
    if not is_free_model(model_id):
        raise BenchError(
            f'Modelo {model_id!r} no termina en :free; se esperaba un modelo gratis.')


def assert_bench_model(model_id: str) -> None:
    """Acepta :free o ID de pago no vacío (candado es gasto ≤ maxSpendUsd)."""
    if not isinstance(model_id, str) or not model_id.strip():
        raise BenchError(f'Modelo inválido: {model_id!r}')
    # Variantes :FREE / :Free no cuentan como gratis ni como pago válido.
    if model_id.lower().endswith(':free') and not model_id.endswith(':free'):
        raise BenchError(
            f'Modelo {model_id!r}: sufijo :free debe ser minúsculas exactas.')


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


def _validate_usd_cap(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise BenchError(f'{name} inválido: {value!r}')
    cap = float(value)
    if cap < 0 or math.isnan(cap) or math.isinf(cap):
        raise BenchError(f'{name} inválido: {value!r}')
    return cap


def check_openrouter_spend_lock(
    api_key: str | None,
    n_total: int,
    *,
    max_paid_limit_usd: float = 10.0,
    max_spend_usd: float = 5.0,
    require_free_quota: bool = False,
    data: dict | None = None,
) -> dict:
    """Candado de gasto: limit finito ≤ techo key; usage snapshot; cuota :free opcional.

    n_total = solicitudes estimadas (celdas × maxTurnsPerCell), no celdas.
    El tope de gasto runtime es max_spend_usd (delta usage); aquí solo se valida
    la key y, si require_free_quota, la cuota diaria :free.
    """
    if type(n_total) is not int or n_total < 1:
        raise BenchError(f'n_total inválido: {n_total!r}')
    max_cap = _validate_usd_cap(max_paid_limit_usd, 'maxPaidLimitUsd')
    _validate_usd_cap(max_spend_usd, 'maxSpendUsd')

    if data is None:
        data = fetch_openrouter_key(api_key or '')

    # usage debe ser número finito (snapshot); no se exige 0.
    read_usage(data)

    # limit: numérico finito y ≤ techo de créditos en cuenta (null/ilimitado aborta).
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

    if require_free_quota:
        free = data.get('free_model_daily_requests')
        if not isinstance(free, dict) or not free:
            raise BenchError(
                '/api/v1/key: free_model_daily_requests ausente o vacío (fail-closed).')
        remaining = _require_nonneg_int(
            free, 'remaining', label='free_model_daily_requests.remaining')
        if remaining < n_total:
            raise BenchError(
                f'Cuota :free insuficiente: remaining={remaining}, hace falta {n_total} '
                f'(limite tipico {FREE_RPD_LOW}/dia o {FREE_RPD_HIGH}/dia; {FREE_RPM}/min).')
    return data


def check_openrouter_free_lock(
    api_key: str | None,
    n_total: int,
    *,
    max_paid_limit_usd: float = 10.0,
    data: dict | None = None,
) -> dict:
    """Compat: candado con cuota :free obligatoria (equiv. spend_lock + require_free_quota)."""
    return check_openrouter_spend_lock(
        api_key, n_total, max_paid_limit_usd=max_paid_limit_usd,
        max_spend_usd=DEFAULT_CONFIG['maxSpendUsd'],
        require_free_quota=True, data=data)


def assert_spend_within_cap(
    api_key: str,
    usage_before: float,
    *,
    max_spend_usd: float = 5.0,
    approach_ratio: float = 0.8,
    data: dict | None = None,
) -> float:
    """Relee usage; aborta si el delta alcanza el tope o se acerca (approach_ratio)."""
    max_spend = _validate_usd_cap(max_spend_usd, 'maxSpendUsd')
    ratio = _validate_usd_cap(approach_ratio, 'spendApproachRatio')
    if ratio > 1.0:
        raise BenchError(f'spendApproachRatio inválido: {approach_ratio!r}')
    payload = data if data is not None else fetch_openrouter_key(api_key)
    usage_after = read_usage(payload)
    delta = usage_after - float(usage_before)
    if delta < 0:
        # Reembolsos/ajustes: no invalidar; tratar como 0 gastado neto.
        delta = 0.0
    approach_at = max_spend * ratio
    if delta >= max_spend:
        raise BenchError(
            f'gasto supera tope: before={usage_before} after={usage_after} '
            f'delta={delta} maxSpendUsd={max_spend}; corrida invalida.')
    if delta >= approach_at and max_spend > 0:
        raise BenchError(
            f'gasto se acerca al tope: before={usage_before} after={usage_after} '
            f'delta={delta} approach={approach_at} maxSpendUsd={max_spend}; aborta.')
    return usage_after


def assert_usage_unchanged(api_key: str, usage_before: float, *, data: dict | None = None) -> float:
    """Compat estricta: delta > 0 aborta (solo corridas :free sin gasto)."""
    payload = data if data is not None else fetch_openrouter_key(api_key)
    usage_after = read_usage(payload)
    delta = usage_after - float(usage_before)
    if delta > 0:
        raise BenchError(
            f'usage subio durante la corrida: before={usage_before} after={usage_after} '
            f'delta={delta}; corrida invalida (solo :free sin gasto).')
    return usage_after


def _parse_pricing_amount(raw: Any, key: str) -> float:
    if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
        raise BenchError(
            f'/api/v1/models: pricing.{key} tipo inesperado {type(raw).__name__} (fail-closed).')
    try:
        num = float(raw)
    except (TypeError, ValueError) as exc:
        raise BenchError(
            f'/api/v1/models: pricing.{key}={raw!r} no parseable (fail-closed).') from exc
    if math.isnan(num) or math.isinf(num) or num < 0:
        raise BenchError(
            f'/api/v1/models: pricing.{key}={num} inválido (fail-closed).')
    return num


def verify_openrouter_model_pricing(
    api_key: str,
    model_id: str,
    *,
    allow_paid: bool = False,
) -> dict:
    """Fail-closed: localiza el modelo y valida pricing.

    :free → prompt/completion deben ser 0.
    allow_paid → acepta precio > 0 y exige soporte de tools (supported_parameters).
    """
    assert_bench_model(model_id)
    free = is_free_model(model_id)
    if not free and not allow_paid:
        raise BenchError(
            f'Modelo {model_id!r} no es :free; pasa allow_paid=True para pago económico.')
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
    prices: dict[str, float] = {}
    for key in ('prompt', 'completion'):
        if key not in pricing:
            raise BenchError(f'/api/v1/models: falta pricing.{key} (fail-closed).')
        prices[key] = _parse_pricing_amount(pricing[key], key)
        if free and prices[key] != 0.0:
            raise BenchError(
                f'/api/v1/models: pricing.{key}={prices[key]} no es 0 (fail-closed; solo :free).')
    if not free:
        # Tool use obligatorio para el fallback de pago (Claude Code / agentic).
        supported = match.get('supported_parameters')
        if not isinstance(supported, list):
            raise BenchError(
                f'/api/v1/models: supported_parameters ausente para {model_id!r} (fail-closed).')
        ok_tools = any(
            isinstance(p, str) and p in ('tools', 'tool_choice') for p in supported)
        if not ok_tools:
            raise BenchError(
                f'/api/v1/models: {model_id!r} sin tools/tool_choice (fail-closed; pago).')
    match = dict(match)
    match['_parsedPricing'] = prices
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
    # aborted / abortReason se conservan en el scrub genérico (no están en forbidden).

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


def _load_or_proxy():
    """Carga or_proxy.py del mismo directorio (sin empaquetar)."""
    path = HERE / 'or_proxy.py'
    if not path.is_file():
        raise BenchError(f'Falta {path}; el provider openrouter exige el proxy contador.')
    spec = importlib.util.spec_from_file_location('microsdd_or_proxy', path)
    if spec is None or spec.loader is None:
        raise BenchError(f'No se pudo cargar {path}')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ClaudeCodeProvider:
    """Bench agéntico vía Claude Code + OpenRouter (proxy contador; :free o pago)."""

    MIN_INTERVAL_S = 3.1  # pausa entre celdas; el proxy cuenta cada HTTP a OpenRouter
    CELL_TIMEOUT_S = 900

    def __init__(self, model_id: str, *, claude_bin: str = 'claude',
                 max_turns: int = DEFAULT_CONFIG['maxTurnsPerCell'],
                 proxy: Any = None):
        assert_bench_model(model_id)
        if type(max_turns) is not int or max_turns < 1:
            raise BenchError(f'max_turns inválido: {max_turns!r}')
        if proxy is None:
            raise BenchError(
                'ClaudeCodeProvider exige proxy contador OpenRouter (fail-closed); '
                'no se inyecta la key real en el entorno de Claude.')
        self.model_id = model_id
        self.claude_bin = claude_bin
        self.max_turns = max_turns
        self.proxy = proxy
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

    def _assert_proxy_ok(self) -> int:
        """Fail-closed: contador legible y proxy no abortado. Devuelve count."""
        try:
            data = self.proxy.assert_readable()
        except Exception as exc:
            raise BenchError(f'contador de requests ilegible (fail-closed): {exc}') from exc
        if getattr(self.proxy.server, 'aborted', False):
            reason = getattr(self.proxy.server, 'abort_reason', None) or 'aborted'
            raise BenchError(f'proxy OpenRouter abortado: {reason}')
        return int(data['count'])

    def _env(self, *, home: str) -> dict[str, str]:
        self._assert_proxy_ok()
        return self.proxy.client_env(self.model_id, home=home)

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
        # Mitiga --dangerously-skip-permissions: cwd y HOME solo en temp;
        # la key real no entra al env de Claude (solo LOCAL_TOKEN vía proxy).
        work = Path(workdir)
        if not work.is_dir():
            return self._pending_diag(
                exit_code=None, stderr='workdir inválido', subtype=None, is_error=True)
        self._throttle()
        # Flags compatibles con Claude Code 2.1.197 + OpenRouter (Arturo).
        cmd = [
            self.claude_bin, '-p', self._prompt(task),
            '--output-format', 'json',
            '--dangerously-skip-permissions',
            '--allowedTools', 'Read,Edit,Bash',
            '--model', self.model_id,
            '--max-turns', str(self.max_turns),
        ]
        started = time.monotonic()
        self._last_call = started
        try:
            with tempfile.TemporaryDirectory(prefix='microsdd-claude-home-') as home:
                env = self._env(home=home)
                # Defensa: la key real no debe aparecer en el env del cliente.
                for forbidden in ('OPENROUTER_API_KEY',):
                    if env.get(forbidden):
                        raise BenchError(
                            f'{forbidden} filtrada al entorno de Claude (fail-closed).')
                if env.get('ANTHROPIC_AUTH_TOKEN') != self.proxy.LOCAL_TOKEN:
                    raise BenchError(
                        'ANTHROPIC_AUTH_TOKEN del cliente no es el token local del proxy.')
                proc = subprocess.run(
                    cmd, cwd=str(work), env=env, capture_output=True, text=True,
                    timeout=self.CELL_TIMEOUT_S, check=False)
        except BenchError:
            raise
        except (OSError, subprocess.TimeoutExpired) as exc:
            return self._pending_diag(
                exit_code=None, stderr=str(exc)[:800], subtype=None, is_error=True,
                error_class=type(exc).__name__,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
        duration_ms = int((time.monotonic() - started) * 1000)
        # Tras la celda: si el contador no se lee o el proxy abortó, fallar cerrado.
        self._assert_proxy_ok()
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
        # Tope de turnos alcanzado: celda completada; la prueba del fixture decide.
        max_turns_hit = subtype == 'error_max_turns'
        # Fallo inmediato de Claude (login, flags, 429, …) → pending + diagnóstico.
        if not max_turns_hit and (proc.returncode != 0 or is_error is True or not payload):
            return self._pending_diag(
                exit_code=proc.returncode, stderr=stderr_trunc, subtype=subtype,
                is_error=is_error if isinstance(is_error, bool) else True,
                duration_ms=duration_ms,
            )
        num_turns = payload.get('num_turns')
        turns = num_turns if type(num_turns) is int and num_turns >= 0 else None
        pending = not test_ok and tokens is None and not max_turns_hit
        return {
            'success': bool(test_ok),
            'pending': bool(pending),
            'status': 'pending' if pending else ('ok' if test_ok else 'fail'),
            'iterations': turns,
            'retries': 0,
            'calls': turns,
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


def _pending_cell(task: dict, variant: str, rep: int, model_id: str | None) -> dict:
    return {
        'taskId': task['id'], 'variant': variant, 'repetition': rep,
        'success': False, 'pending': True, 'status': 'pending',
        'iterations': None, 'retries': None, 'calls': None,
        'tokens': None, 'costUsd': None, 'durationMs': None,
        'cacheRate': None, 'firstTry': None,
        'modelId': model_id, 'seed': None,
    }


def _cell_key(task_id: str, variant: str, rep: int) -> tuple[str, str, int]:
    return (task_id, variant, int(rep))


def _parse_only_cells(raw: Any) -> list[tuple[str, str, int]] | None:
    """Lista opcional [{taskId, variant, repetition}, ...] para relleno selectivo."""
    if raw is None:
        return None
    if not isinstance(raw, list) or not raw:
        raise BenchError('onlyCells debe ser una lista no vacía de celdas.')
    out: list[tuple[str, str, int]] = []
    seen: set[tuple[str, str, int]] = set()
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise BenchError(f'onlyCells[{i}] no es objeto.')
        tid = item.get('taskId')
        variant = item.get('variant')
        rep = item.get('repetition')
        if not isinstance(tid, str) or not tid:
            raise BenchError(f'onlyCells[{i}].taskId inválido.')
        if variant not in ('base', 'treatment'):
            raise BenchError(f'onlyCells[{i}].variant inválido: {variant!r}')
        if type(rep) is not int or rep < 0:
            raise BenchError(f'onlyCells[{i}].repetition inválido: {rep!r}')
        key = _cell_key(tid, variant, rep)
        if key in seen:
            raise BenchError(f'onlyCells duplicada: {key}')
        seen.add(key)
        out.append(key)
    return out


def _load_prior_cells(path: Path | None) -> list[dict]:
    if path is None:
        return []
    if not path.is_file():
        raise BenchError(f'priorReport ausente: {path}')
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise BenchError('priorReport: raíz no es objeto')
    cells = data.get('cells')
    if not isinstance(cells, list):
        raise BenchError('priorReport: cells ausente')
    return [c for c in cells if isinstance(c, dict)]


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
    max_turns, max_requests = request_budget(cfg)
    claim = claim or cfg.get('claim') or 'efficiency'
    n = int(cfg['nCheap'] if cheap else cfg['n'])
    seed = int(cfg.get('seed', 42))
    tasks = list_tasks()
    tasks_by_id = {t['id']: t for t in tasks}
    model_list = models if models is not None else list(cfg.get('models') or [])
    only = _parse_only_cells(cfg.get('onlyCells'))
    prior_path_raw = cfg.get('priorReport')
    prior_path = Path(prior_path_raw) if isinstance(prior_path_raw, str) and prior_path_raw else None
    if prior_path is not None and not prior_path.is_absolute():
        prior_path = ROOT / prior_path
    prior_cells = _load_prior_cells(prior_path) if only is not None else []
    api_key: str | None = None
    usage_before: float | None = None
    estimated: int | None = None
    remaining: int | None = None  # cuota :free; None = solo tope proxy/gasto
    max_spend = float(cfg.get('maxSpendUsd', DEFAULT_CONFIG['maxSpendUsd']))
    approach_ratio = float(cfg.get(
        'spendApproachRatio', DEFAULT_CONFIG['spendApproachRatio']))
    # Orden intercalado A/B con semilla (deriva temporal), o solo onlyCells.
    if only is not None:
        schedule: list[tuple[dict, str, int]] = []
        for tid, variant, rep in only:
            task = tasks_by_id.get(tid)
            if task is None:
                raise BenchError(f'onlyCells: tarea desconocida {tid!r}')
            schedule.append((task, variant, rep))
        n_schedule = len(schedule)
    else:
        rng = random.Random(seed)
        schedule = []
        for task in tasks:
            for rep in range(n):
                schedule.append((task, 'base', rep))
                schedule.append((task, 'treatment', rep))
        rng.shuffle(schedule)
        # Re-intercalar aproximadamente A/B manteniendo pares por tarea.
        schedule.sort(key=lambda x: (x[0]['id'], x[2], 0 if x[1] == 'base' else 1))
        n_schedule = len(schedule)

    if not skip_key_check and not isinstance(provider, FakeProvider):
        if not model_list:
            raise BenchError(
                'bench.config models vacío; indica IDs :free o pago económico.')
        for mid in model_list:
            assert_bench_model(mid)
        estimated = planned_requests(cfg, n_schedule)
        api_key = os.environ.get('OPENROUTER_API_KEY')
        max_cap = cfg.get('maxPaidLimitUsd', DEFAULT_CONFIG['maxPaidLimitUsd'])
        need_free_quota = all(is_free_model(m) for m in model_list)
        key_data = check_openrouter_spend_lock(
            api_key, estimated, max_paid_limit_usd=max_cap,
            max_spend_usd=max_spend, require_free_quota=need_free_quota)
        usage_before = read_usage(key_data)
        if need_free_quota:
            remaining = _require_nonneg_int(
                key_data['free_model_daily_requests'], 'remaining',
                label='free_model_daily_requests.remaining')
        else:
            remaining = None

    model_id = model_list[0] if model_list else None
    real = usage_before is not None and api_key is not None
    proxy = getattr(provider, 'proxy', None)
    requests_used: int | None = 0 if real else None
    cells: list[dict] = []
    pending_rest = False
    abort_reason: str | None = None
    with tempfile.TemporaryDirectory(prefix='microsdd-bench-') as tmp:
        tmp_path = Path(tmp)
        for task, variant, rep in schedule:
            if abort_reason or pending_rest:
                cells.append(_pending_cell(task, variant, rep, model_id))
                continue
            try:
                if real:
                    used_now = requests_used or 0
                    if proxy is not None:
                        try:
                            used_now = int(proxy.read_count())
                        except Exception as exc:
                            raise BenchError(
                                f'contador de requests ilegible antes de celda (fail-closed): {exc}'
                            ) from exc
                        if getattr(proxy.server, 'aborted', False):
                            raise BenchError(
                                f'proxy OpenRouter abortado: '
                                f'{getattr(proxy.server, "abort_reason", None) or "aborted"}')
                        requests_used = used_now
                    # Corte por celda completa: no cabe otra celda con el tope de turnos.
                    headroom = max_requests - used_now
                    if remaining is not None:
                        headroom = min(headroom, remaining)
                    if headroom < max_turns:
                        pending_rest = True
                        cells.append(_pending_cell(task, variant, rep, model_id))
                        continue
                work = tmp_path / f"{task['id']}-{variant}-{rep}"
                copy_fixture(Path(task['_dir']), work)
                try:
                    result = provider.run_cell(task, variant, rep, workdir=work)
                except TypeError:
                    result = provider.run_cell(task, variant, rep)
                cells.append({
                    'taskId': task['id'],
                    'variant': variant,
                    'repetition': rep,
                    **result,
                })
                if real:
                    # Relectura por celda: gasto ≤ maxSpendUsd (aborta si se acerca).
                    key_data = fetch_openrouter_key(api_key)
                    assert_spend_within_cap(
                        api_key, usage_before, max_spend_usd=max_spend,
                        approach_ratio=approach_ratio, data=key_data)
                    if remaining is not None:
                        free = key_data.get('free_model_daily_requests')
                        if not isinstance(free, dict) or not free:
                            raise BenchError(
                                '/api/v1/key: free_model_daily_requests ausente tras la celda '
                                '(fail-closed).')
                        new_remaining = _require_nonneg_int(
                            free, 'remaining',
                            label='free_model_daily_requests.remaining')
                    else:
                        new_remaining = None
                    if proxy is not None:
                        try:
                            requests_used = int(proxy.read_count())
                        except Exception as exc:
                            raise BenchError(
                                f'contador de requests ilegible tras celda (fail-closed): {exc}'
                            ) from exc
                        if getattr(proxy.server, 'aborted', False):
                            raise BenchError(
                                f'proxy OpenRouter abortado: '
                                f'{getattr(proxy.server, "abort_reason", None) or "aborted"}')
                    else:
                        calls = result.get('calls')
                        turns = calls if type(calls) is int else max_turns
                        if remaining is not None and new_remaining is not None:
                            requests_used += max(remaining - new_remaining, turns)
                        else:
                            requests_used += turns
                    remaining = new_remaining
            except BenchError as exc:
                # Abort mid-celda / post-celda: marcar resto (y esta si falta) como pending.
                abort_reason = str(exc)
                done = {
                    _cell_key(c['taskId'], c['variant'], c['repetition']) for c in cells
                }
                cur = _cell_key(task['id'], variant, rep)
                if cur not in done:
                    cells.append(_pending_cell(task, variant, rep, model_id))
                continue

    usage_after = None
    usage_delta = None
    if usage_before is not None and api_key is not None:
        try:
            usage_after = assert_spend_within_cap(
                api_key, usage_before, max_spend_usd=max_spend,
                approach_ratio=approach_ratio)
            usage_delta = float(usage_after) - float(usage_before)
            if usage_delta < 0:
                usage_delta = 0.0
        except BenchError as exc:
            if abort_reason is None:
                abort_reason = str(exc)
            else:
                abort_reason = f'{abort_reason}; {exc}'
            try:
                usage_after = read_usage(fetch_openrouter_key(api_key))
                usage_delta = max(0.0, float(usage_after) - float(usage_before))
            except BenchError:
                pass

    if real and proxy is not None:
        try:
            requests_used = int(proxy.read_count())
        except Exception as exc:
            msg = f'contador de requests ilegible al cerrar (fail-closed): {exc}'
            if abort_reason is None:
                abort_reason = msg
            # Sin count legible: no inventar; dejar el último known o fallar en reporte.
            if requests_used is None:
                requests_used = 0

    # Relleno: fusionar celdas previas no reejecutadas + resultado del schedule.
    if only is not None:
        only_keys = set(only)
        kept = [
            c for c in prior_cells
            if _cell_key(c.get('taskId', ''), c.get('variant', ''), int(c.get('repetition') or 0))
            not in only_keys
        ]
        merged = kept + cells
        merged.sort(key=lambda c: (
            str(c.get('taskId') or ''),
            int(c.get('repetition') or 0),
            0 if c.get('variant') == 'base' else 1,
        ))
        cells = merged

    report = aggregate_report(cells, cfg=cfg, claim=claim, cheap=cheap, seed=seed, n=n)
    report['models'] = model_list
    report['baselineStatus'] = cfg.get('baselineStatus', 'pending')
    report['usageBefore'] = usage_before
    report['usageAfter'] = usage_after
    report['usageDelta'] = usage_delta
    report['maxSpendUsd'] = max_spend
    report['requestsUsed'] = requests_used
    report['requestBudget'] = max_requests
    report['requestsEstimated'] = estimated
    report['maxTurnsPerCell'] = max_turns
    report['pendingCells'] = [
        {'taskId': c['taskId'], 'variant': c['variant'], 'repetition': c['repetition']}
        for c in cells if c.get('pending')
    ]
    if abort_reason:
        report['aborted'] = True
        report['abortReason'] = abort_reason
    report['risks'] = [
        f'Proxy rate limit: {FREE_RPM} req/min (espera/cola, no 429); '
        f'solo POST de mensajes cuentan al tope; '
        f':free tipico {FREE_RPD_LOW} o {FREE_RPD_HIGH} req/día según créditos.',
        f'Candado: gasto máximo maxSpendUsd={max_spend} por repo '
        f'(usage antes/después; aborta al acercarse ratio={approach_ratio}); '
        f'limit de key <= maxPaidLimitUsd='
        f'{cfg.get("maxPaidLimitUsd", DEFAULT_CONFIG["maxPaidLimitUsd"])}; '
        f'modelos :free o pago económico con tools.',
        '[No verificado] Política de datos y retención de modelos OpenRouter.',
        'Semilla Claude Code: seed=null (sin flag documentado).',
        f'Presupuesto: maxTurnsPerCell={max_turns}, maxRequestsPerRun={max_requests}; '
        f'proxy local cuenta cada HTTP a OpenRouter (incl. small-fast) y rechaza el '
        f'{max_requests + 1}+ (fail-closed si el contador es ilegible; tope acumulado '
        f'entre intentos).',
        'minN desbloqueado (nb/nt >= expected) no implica veredicto favorable: efficiency '
        'o IC95 pueden seguir en NO CONCLUYENTE / RECHAZA.',
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
        f"- requests: {report.get('requestsUsed')}/{report.get('requestBudget')}",
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
            proxy = None
            try:
                models = list(cfg.get('models') or [])
                if not models:
                    raise BenchError(
                        'bench.config models vacío; indica IDs :free o pago económico.')
                for m in models:
                    assert_bench_model(m)
                api_key = os.environ.get('OPENROUTER_API_KEY')
                if not api_key:
                    raise BenchError(
                        'OPENROUTER_API_KEY ausente; no se lanza la línea base real. '
                        'Usa --provider fake para pruebas deterministas.')
                max_turns, max_requests = request_budget(cfg)
                only = _parse_only_cells(cfg.get('onlyCells'))
                if only is not None:
                    n_est = len(only)
                else:
                    n_est = int(cfg['nCheap'] if cheap else cfg['n']) * 5 * 2
                max_cap = cfg.get('maxPaidLimitUsd', DEFAULT_CONFIG['maxPaidLimitUsd'])
                max_spend = cfg.get('maxSpendUsd', DEFAULT_CONFIG['maxSpendUsd'])
                need_free = all(is_free_model(m) for m in models)
                check_openrouter_spend_lock(
                    api_key, planned_requests(cfg, n_est),
                    max_paid_limit_usd=max_cap, max_spend_usd=max_spend,
                    require_free_quota=need_free)
                for m in models:
                    verify_openrouter_model_pricing(
                        api_key, m, allow_paid=not is_free_model(m))
                or_proxy = _load_or_proxy()
                state_env = os.environ.get('BENCH_PROXY_STATE')
                state = Path(state_env) if state_env else (
                    Path(tempfile.gettempdir()) / 'microsdd-or-proxy-count.json')
                prior_raw = os.environ.get('BENCH_PRIOR_REQUESTS', '0')
                try:
                    prior_n = int(prior_raw)
                except ValueError as exc:
                    raise BenchError(
                        f'BENCH_PRIOR_REQUESTS inválido: {prior_raw!r}') from exc
                if type(cfg.get('requestsAlreadyUsed')) is int:
                    prior_n = max(prior_n, int(cfg['requestsAlreadyUsed']))
                proxy = or_proxy.OpenRouterCountingProxy(
                    api_key, max_requests=max_requests, state_path=state,
                    initial_count=prior_n,
                    max_requests_per_minute=FREE_RPM)
                proxy.start()
                proxy.assert_readable()
                provider = ClaudeCodeProvider(
                    models[0], max_turns=max_turns, proxy=proxy)
            except BenchError as exc:
                if proxy is not None:
                    proxy.stop()
                print(f'ERROR: {exc}', flush=True)
                return 1
            except Exception as exc:
                if proxy is not None:
                    proxy.stop()
                print(f'ERROR: proxy OpenRouter: {exc}', flush=True)
                return 1
        else:
            print(f'ERROR: provider desconocido {provider_name}', flush=True)
            return 1
        report = None
        run_exc: BenchError | None = None
        try:
            report = run_bench(
                provider=provider, cheap=cheap, claim=claim, config=cfg, skip_key_check=skip)
        except BenchError as exc:
            # Fallo antes de tener celdas (candado/config): sin reporte parcial.
            run_exc = exc
            print(f'ERROR: {exc}', flush=True)
        finally:
            if provider_name == 'openrouter':
                try:
                    proxy.stop()
                except Exception:
                    pass
        if report is None:
            return 1
        dest = out or (Path(os.environ.get('XDG_STATE_HOME')
                            or (Path.home() / '.local' / 'state')) / 'microsdd' / 'bench-last')
        if os.name == 'nt' and out is None:
            dest = Path(os.environ.get('LOCALAPPDATA') or (Path.home() / 'AppData' / 'Local')) / 'microsdd' / 'bench-last'
        # Siempre escribir reporte si hay celdas (incluye abort mid-celda con pendientes).
        write_report(report, dest)
        sanitized = sanitize_report(report)
        (dest / 'bench-report.sanitized.json').write_text(
            json.dumps(sanitized, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')
        safe_print(format_report_md(report))
        safe_print(f'Reporte escrito en {dest}')
        if report.get('aborted'):
            print(f"ERROR: abortado: {report.get('abortReason')}", flush=True)
            return 1
        if run_exc is not None:
            return 1
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
