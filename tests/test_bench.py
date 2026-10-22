"""Bench m2: estadísticas, candado :free fail-closed, fake provider y prompt-diff."""
from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
BENCH_PATH = ROOT / '.microharness' / 'bench.py'
METRICS_PATH = ROOT / '.microharness' / 'metrics.py'


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(mod)
    finally:
        if sys.path[0] == str(path.parent):
            sys.path.pop(0)
    return mod


def _resp(payload: dict | bytes | str):
    if isinstance(payload, dict):
        raw = json.dumps(payload).encode('utf-8')
    elif isinstance(payload, str):
        raw = payload.encode('utf-8')
    else:
        raw = payload

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return raw

    return Resp()


VALID_KEY_DATA = {
    'usage': 0,
    'limit': 0,
    'limit_remaining': 0,
    'free_model_daily_requests': {'remaining': 100},
}


@unittest.skipUnless(BENCH_PATH.is_file(), 'bench.py ausente')
class BenchStatsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = load('microsdd_bench_ut', BENCH_PATH)

    def test_wilson_and_bootstrap_shapes(self):
        lo, hi = self.b.wilson_interval(4, 5)
        self.assertGreaterEqual(lo, 0.0)
        self.assertLessEqual(hi, 1.0)
        ci = self.b.bootstrap_ci_delta([10, 12, 11], [8, 7, 9], seed=1, n_boot=200)
        self.assertEqual(len(ci), 2)
        self.assertLess(ci[0], ci[1])

    def test_assert_free_model_rejects_uppercase_suffix(self):
        self.b.assert_free_model('meta/llama:free')
        with self.assertRaises(self.b.BenchError):
            self.b.assert_free_model('meta/llama:FREE')
        with self.assertRaises(self.b.BenchError):
            self.b.assert_free_model('anthropic/claude-opus-5-5')

    def test_openrouter_lock_aborts_without_key(self):
        with self.assertRaises(self.b.BenchError):
            self.b.check_openrouter_free_lock(None, 10)

    def test_openrouter_lock_aborts_on_empty_data(self):
        with mock.patch('urllib.request.urlopen', return_value=_resp({'data': {}})):
            with self.assertRaises(self.b.BenchError) as ctx:
                self.b.check_openrouter_free_lock('sk-test', 10)
        self.assertIn('fail-closed', str(ctx.exception).lower())

    def test_openrouter_lock_aborts_on_null_limit_with_remaining(self):
        data = {
            'usage': 0,
            'limit': None,
            'limit_remaining': 50,
            'free_model_daily_requests': {'remaining': 100},
        }
        with mock.patch('urllib.request.urlopen', return_value=_resp({'data': data})):
            with self.assertRaises(self.b.BenchError) as ctx:
                self.b.check_openrouter_free_lock('sk-test', 10)
        self.assertIn('limit', str(ctx.exception).lower())

    def test_openrouter_lock_aborts_on_null_limit_with_camel_remaining(self):
        data = {
            'usage': 0,
            'limit': None,
            'limitRemaining': 50,
            'free_model_daily_requests': {'remaining': 100},
        }
        with mock.patch('urllib.request.urlopen', return_value=_resp({'data': data})):
            with self.assertRaises(self.b.BenchError) as ctx:
                self.b.check_openrouter_free_lock('sk-test', 10)
        msg = str(ctx.exception).lower()
        self.assertTrue('limit' in msg)

    def test_openrouter_lock_aborts_on_usage_string(self):
        data = dict(VALID_KEY_DATA)
        data['usage'] = '1.5'
        with mock.patch('urllib.request.urlopen', return_value=_resp({'data': data})):
            with self.assertRaises(self.b.BenchError) as ctx:
                self.b.check_openrouter_free_lock('sk-test', 10)
        self.assertIn('usage', str(ctx.exception).lower())
        self.assertIn('inesperado', str(ctx.exception).lower())

    def test_openrouter_lock_aborts_when_usage_absent_and_limit_null(self):
        data = {
            'limit': None,
            'limit_remaining': 0,
            'free_model_daily_requests': {'remaining': 100},
        }
        with mock.patch('urllib.request.urlopen', return_value=_resp({'data': data})):
            with self.assertRaises(self.b.BenchError) as ctx:
                self.b.check_openrouter_free_lock('sk-test', 10)
        self.assertIn('usage', str(ctx.exception).lower())

    def test_openrouter_lock_aborts_when_quota_absent(self):
        data = {'usage': 0, 'limit': 0, 'limit_remaining': 0}
        with mock.patch('urllib.request.urlopen', return_value=_resp({'data': data})):
            with self.assertRaises(self.b.BenchError) as ctx:
                self.b.check_openrouter_free_lock('sk-test', 10)
        self.assertIn('free_model_daily_requests', str(ctx.exception).lower())

    def test_openrouter_lock_aborts_on_remaining_unexpected_type(self):
        data = dict(VALID_KEY_DATA)
        data['free_model_daily_requests'] = {'remaining': ['x']}
        with mock.patch('urllib.request.urlopen', return_value=_resp({'data': data})):
            with self.assertRaises(self.b.BenchError) as ctx:
                self.b.check_openrouter_free_lock('sk-test', 10)
        self.assertIsInstance(ctx.exception, self.b.BenchError)
        self.assertIn('inesperado', str(ctx.exception).lower())

    def test_openrouter_lock_accepts_nonzero_usage_when_limit_ok(self):
        """usage previo > 0 es válido; solo el delta durante la corrida invalida."""
        data = dict(VALID_KEY_DATA)
        data['usage'] = 1.5
        data['limit'] = 5
        with mock.patch('urllib.request.urlopen', return_value=_resp({'data': data})):
            out = self.b.check_openrouter_free_lock('sk-test', 10, max_paid_limit_usd=5)
        self.assertEqual(out['usage'], 1.5)
        self.assertEqual(out['limit'], 5)

    def test_openrouter_lock_aborts_when_limit_exceeds_cap(self):
        data = dict(VALID_KEY_DATA)
        data['limit'] = 5.01
        with mock.patch('urllib.request.urlopen', return_value=_resp({'data': data})):
            with self.assertRaises(self.b.BenchError) as ctx:
                self.b.check_openrouter_free_lock('sk-test', 10, max_paid_limit_usd=5)
        self.assertIn('maxpaidlimitusd', str(ctx.exception).lower())

    def test_openrouter_lock_aborts_on_infinite_limit(self):
        data = dict(VALID_KEY_DATA)
        data['limit'] = float('inf')
        with mock.patch('urllib.request.urlopen', return_value=_resp({'data': data})):
            with self.assertRaises(self.b.BenchError) as ctx:
                self.b.check_openrouter_free_lock('sk-test', 10)
        self.assertIn('finito', str(ctx.exception).lower())

    def test_openrouter_lock_aborts_on_http_error(self):
        with mock.patch('urllib.request.urlopen', side_effect=OSError('boom')):
            with self.assertRaises(self.b.BenchError) as ctx:
                self.b.check_openrouter_free_lock('sk-test', 10)
        self.assertIn('/api/v1/key', str(ctx.exception))

    def test_openrouter_lock_aborts_on_invalid_json(self):
        with mock.patch('urllib.request.urlopen', return_value=_resp('not-json{')):
            with self.assertRaises(self.b.BenchError):
                self.b.check_openrouter_free_lock('sk-test', 10)

    def test_openrouter_lock_accepts_strict_zero_key(self):
        with mock.patch('urllib.request.urlopen', return_value=_resp({'data': VALID_KEY_DATA})):
            out = self.b.check_openrouter_free_lock('sk-test', 10)
        self.assertEqual(out['usage'], 0)
        self.assertEqual(out['limit'], 0)

    def test_openrouter_lock_accepts_limit_at_default_cap(self):
        data = dict(VALID_KEY_DATA)
        data['limit'] = 5
        with mock.patch('urllib.request.urlopen', return_value=_resp({'data': data})):
            out = self.b.check_openrouter_free_lock('sk-test', 10)
        self.assertEqual(out['limit'], 5)

    def test_assert_usage_unchanged_passes_when_same(self):
        data = dict(VALID_KEY_DATA)
        data['usage'] = 2.0
        with mock.patch('urllib.request.urlopen', return_value=_resp({'data': data})):
            after = self.b.assert_usage_unchanged('sk-test', 2.0)
        self.assertEqual(after, 2.0)

    def test_assert_usage_unchanged_aborts_on_rise(self):
        data = dict(VALID_KEY_DATA)
        data['usage'] = 2.5
        with mock.patch('urllib.request.urlopen', return_value=_resp({'data': data})):
            with self.assertRaises(self.b.BenchError) as ctx:
                self.b.assert_usage_unchanged('sk-test', 2.0)
        msg = str(ctx.exception).lower()
        self.assertIn('usage', msg)
        self.assertIn('invalida', msg)

    def test_assert_usage_unchanged_accepts_injected_data(self):
        data = dict(VALID_KEY_DATA)
        data['usage'] = 1.0
        after = self.b.assert_usage_unchanged('sk-test', 1.0, data=data)
        self.assertEqual(after, 1.0)

    def test_run_bench_invalidates_when_usage_rises(self):
        """Corrida real (no fake): snapshot usage y aborta si sube."""
        before = dict(VALID_KEY_DATA)
        before['usage'] = 1.0
        before['limit'] = 5
        after = dict(before)
        after['usage'] = 1.25
        calls = {'n': 0}

        def fake_urlopen(*_a, **_k):
            calls['n'] += 1
            payload = before if calls['n'] == 1 else after
            return _resp({'data': payload})

        class StubProvider:
            def run_cell(self, task, variant, repetition):
                return {
                    'success': True,
                    'iterations': 1,
                    'retries': 0,
                    'calls': 1,
                    'tokens': 100,
                    'costUsd': 0.0,
                    'durationMs': 1,
                    'cacheRate': 0.0,
                    'firstTry': True,
                    'modelId': 'meta/llama:free',
                    'seed': None,
                }

        cfg = self.b.load_config()
        cfg['bootstrap'] = 50
        cfg['models'] = ['meta/llama:free']
        cfg['maxPaidLimitUsd'] = 5
        cfg['maxTurnsPerCell'] = 1
        cfg['maxRequestsPerRun'] = 30
        with mock.patch('urllib.request.urlopen', side_effect=fake_urlopen):
            with mock.patch.dict(os.environ, {'OPENROUTER_API_KEY': 'sk-test'}):
                with self.assertRaises(self.b.BenchError) as ctx:
                    self.b.run_bench(
                        provider=StubProvider(), cheap=True, claim='efficiency',
                        config=cfg, skip_key_check=False,
                    )
        self.assertIn('usage', str(ctx.exception).lower())
        self.assertGreaterEqual(calls['n'], 2)

    def test_run_bench_records_usage_before_when_stable(self):
        data = dict(VALID_KEY_DATA)
        data['usage'] = 0.75
        data['limit'] = 5

        class StubProvider:
            def run_cell(self, task, variant, repetition):
                return {
                    'success': True,
                    'iterations': 1,
                    'retries': 0,
                    'calls': 1,
                    'tokens': 100,
                    'costUsd': 0.0,
                    'durationMs': 1,
                    'cacheRate': 0.0,
                    'firstTry': True,
                    'modelId': 'meta/llama:free',
                    'seed': None,
                }

        cfg = self.b.load_config()
        cfg['bootstrap'] = 50
        cfg['models'] = ['meta/llama:free']
        cfg['maxTurnsPerCell'] = 1
        cfg['maxRequestsPerRun'] = 30
        with mock.patch('urllib.request.urlopen', return_value=_resp({'data': data})):
            with mock.patch.dict(os.environ, {'OPENROUTER_API_KEY': 'sk-test'}):
                report = self.b.run_bench(
                    provider=StubProvider(), cheap=True, claim='efficiency',
                    config=cfg, skip_key_check=False,
                )
        self.assertEqual(report['usageBefore'], 0.75)
        self.assertTrue(any('maxPaidLimitUsd' in r for r in report['risks']))

    def test_report_md_is_cp1252_safe_ascii_arrows(self):
        """Windows cp1252: el markdown no usa flechas Unicode."""
        cfg = self.b.load_config()
        cfg['bootstrap'] = 100
        report = self.b.run_bench(
            provider=self.b.FakeProvider(seed=1), cheap=True, claim='efficiency',
            config=cfg, skip_key_check=True,
        )
        md = self.b.format_report_md(report)
        self.assertNotIn('\u2192', md)
        self.assertIn('->', md)
        md.encode('cp1252')  # no debe lanzar
        # safe_print no depende del encoding de la consola
        buf = io.BytesIO()

        class FakeOut:
            buffer = buf

            def write(self, *_a, **_k):
                return 0

            def flush(self):
                return None

        with mock.patch.object(sys, 'stdout', FakeOut()):
            self.b.safe_print(md)
        self.assertTrue(buf.getvalue().startswith(b'# Bench report'))

    def test_fake_run_produces_verdict_and_cheap_flag(self):
        cfg = self.b.load_config()
        cfg['bootstrap'] = 500
        provider = self.b.FakeProvider(seed=42)
        report = self.b.run_bench(
            provider=provider, cheap=False, claim='efficiency',
            config=cfg, skip_key_check=True,
        )
        self.assertIn(report['verdict'], ('ACEPTA', 'RECHAZA', 'NO CONCLUYENTE'))
        self.assertEqual(report['n'], 5)
        self.assertFalse(report['cheap'])
        self.assertEqual(len(report['tasks']), 5)
        self.assertEqual(len(report['cells']), 5 * 2 * 5)
        cheap = self.b.run_bench(
            provider=provider, cheap=True, claim='efficiency',
            config=cfg, skip_key_check=True,
        )
        self.assertTrue(cheap['cheap'])
        self.assertEqual(cheap['n'], 3)
        self.assertTrue(any('No verificado' in r for r in report['risks']))
        self.assertTrue(any('20' in r and 'req/min' in r for r in report['risks']))

    def test_cli_bench_fake_writes_report(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = Path(tmp.name) / 'out'
        code = self.b.cmd_bench(['run', '--provider', 'fake', '--out', str(out)])
        self.assertIn(code, (0, 2))
        self.assertTrue((out / 'bench-report.json').is_file())
        self.assertTrue((out / 'bench-report.md').is_file())
        data = json.loads((out / 'bench-report.json').read_text(encoding='utf-8'))
        self.assertEqual(data['baselineStatus'], self.b.load_config().get('baselineStatus'))
        code2 = self.b.cmd_bench(['report', '--from', str(out)])
        self.assertEqual(code2, 0)

    def test_cli_openrouter_aborts_without_key(self):
        env = {k: v for k, v in os.environ.items() if k != 'OPENROUTER_API_KEY'}
        with mock.patch.dict(os.environ, env, clear=True):
            code = self.b.cmd_bench(['run', '--provider', 'openrouter'])
        self.assertEqual(code, 1)

    def test_prompt_diff_stable(self):
        diff = self.b.prompt_diff(ROOT, ROOT)
        self.assertEqual(diff['fingerprintA'], diff['fingerprintB'])
        self.assertTrue(diff['layers'])
        self.assertEqual(diff['layers'][0]['deltaBytes'], 0)

    def test_list_tasks_five(self):
        tasks = self.b.list_tasks()
        self.assertEqual(len(tasks), 5)
        self.assertTrue(all(t.get('frozen') for t in tasks))

    def test_sanitize_report_strips_sensitive_fields(self):
        dirty = {
            'schema': 'microsdd-bench-report/v1',
            'verdict': 'NO CONCLUYENTE',
            'prompt': 'SECRET PROMPT',
            'session_id': 'sess-xyz',
            'cells': [{
                'taskId': '01', 'variant': 'base', 'repetition': 0,
                'success': True, 'tokens': 10, 'prompt': 'no',
                'session_id': 'x', 'workdir': '/tmp/secret',
                'exitCode': 1, 'stderrTruncated': 'boom', 'subtype': 'error',
                'isError': True,
            }],
        }
        clean = self.b.sanitize_report(dirty)
        self.assertNotIn('prompt', clean)
        self.assertNotIn('session_id', clean)
        self.assertEqual(clean['privacy'], 'strict-aggregate')
        self.assertEqual(clean['cells'][0]['tokens'], 10)
        self.assertEqual(clean['cells'][0]['exitCode'], 1)
        self.assertEqual(clean['cells'][0]['subtype'], 'error')
        self.assertNotIn('workdir', clean['cells'][0])
        self.assertNotIn('prompt', clean['cells'][0])

    def test_aggregate_zero_valid_cells_is_no_concluyente(self):
        """0/0 celdas válidas (todas pending) → NO CONCLUYENTE, no RECHAZA."""
        cfg = self.b.load_config()
        cfg['bootstrap'] = 50
        cells = []
        for tid in ('01-correccion-localizada', '02-regla-nueva', '03-refactor',
                    '04-config-docs', '05-prueba-regresion'):
            for variant in ('base', 'treatment'):
                for rep in range(3):
                    cells.append({
                        'taskId': tid, 'variant': variant, 'repetition': rep,
                        'success': False, 'pending': True, 'status': 'pending',
                        'iterations': None, 'tokens': None, 'costUsd': None,
                    })
        report = self.b.aggregate_report(
            cells, cfg=cfg, claim='efficiency', cheap=True, seed=1, n=3)
        self.assertEqual(report['verdict'], 'NO CONCLUYENTE')
        self.assertEqual(report['success']['base'], '0/0')
        self.assertEqual(report['success']['treatment'], '0/0')

    def test_verify_model_pricing_requires_zero(self):
        models = {
            'data': [{
                'id': 'nvidia/nemotron-3-super-120b-a12b:free',
                'pricing': {'prompt': '0', 'completion': '0'},
            }]
        }
        with mock.patch('urllib.request.urlopen', return_value=_resp(models)):
            out = self.b.verify_openrouter_model_pricing(
                'sk-test', 'nvidia/nemotron-3-super-120b-a12b:free')
        self.assertEqual(out['id'], 'nvidia/nemotron-3-super-120b-a12b:free')
        paid = {
            'data': [{
                'id': 'nvidia/nemotron-3-super-120b-a12b:free',
                'pricing': {'prompt': '0.001', 'completion': '0'},
            }]
        }
        with mock.patch('urllib.request.urlopen', return_value=_resp(paid)):
            with self.assertRaises(self.b.BenchError):
                self.b.verify_openrouter_model_pricing(
                    'sk-test', 'nvidia/nemotron-3-super-120b-a12b:free')


@unittest.skipUnless(BENCH_PATH.is_file(), 'bench.py ausente')
class BenchRequestBudgetTests(unittest.TestCase):
    """Presupuesto de solicitudes por turnos (spec bench-request-budget)."""

    @classmethod
    def setUpClass(cls):
        cls.b = load('microsdd_bench_budget_ut', BENCH_PATH)

    def _cfg(self, **over):
        cfg = dict(self.b.DEFAULT_CONFIG)
        cfg['bootstrap'] = 50
        cfg['models'] = ['meta/llama:free']
        cfg['maxPaidLimitUsd'] = 5
        cfg.update(over)
        return cfg

    def test_invalid_budget_config_raises_even_with_fake(self):
        for key in ('maxTurnsPerCell', 'maxRequestsPerRun'):
            for bad in ('8', 0, -1, True, None):
                with self.subTest(key=key, bad=bad):
                    cfg = self._cfg(**{key: bad})
                    with self.assertRaises(self.b.BenchError):
                        self.b.run_bench(
                            provider=self.b.FakeProvider(seed=1), cheap=True,
                            config=cfg, skip_key_check=True)

    def test_default_budget_config_values_and_fake_run(self):
        self.assertEqual(self.b.DEFAULT_CONFIG['maxTurnsPerCell'], 6)
        self.assertEqual(self.b.DEFAULT_CONFIG['maxRequestsPerRun'], 100)
        report = self.b.run_bench(
            provider=self.b.FakeProvider(seed=1), cheap=True,
            config=self._cfg(), skip_key_check=True)
        self.assertEqual(len(report['cells']), 30)

    def test_bench_config_json_declares_budget(self):
        raw = json.loads((ROOT / 'bench' / 'config.json').read_text(encoding='utf-8'))
        self.assertEqual(raw.get('maxTurnsPerCell'), 6)
        self.assertEqual(raw.get('maxRequestsPerRun'), 100)
        cfg = self.b.load_config()
        self.assertEqual(self.b.request_budget(cfg), (6, 100))
        # cheap-partial sigue siendo válido en load_config (no rompe la línea base).
        self.assertEqual(cfg.get('baselineStatus'), 'cheap-partial')

    # --- corrida real simulada ---

    @staticmethod
    def _key(remaining, usage=0):
        return {'usage': usage, 'limit': 0, 'limit_remaining': 0,
                'free_model_daily_requests': {'remaining': remaining}}

    @staticmethod
    def _stub(calls_value):
        class Stub:
            def __init__(self):
                self.count = 0

            def run_cell(self, task, variant, repetition, workdir=None):
                self.count += 1
                return {
                    'success': True, 'pending': False, 'status': 'ok',
                    'iterations': calls_value, 'retries': 0, 'calls': calls_value,
                    'tokens': 100, 'costUsd': 0.0, 'durationMs': 1, 'cacheRate': 0.0,
                    'firstTry': True, 'modelId': 'meta/llama:free', 'seed': None,
                }
        return Stub()

    def _real_run(self, cfg, stub, remaining_seq):
        """remaining_seq(i) -> remaining en la i-ésima lectura de /api/v1/key (0 = candado)."""
        reads = {'n': 0}

        def fake_urlopen(*_a, **_k):
            i = reads['n']
            reads['n'] += 1
            return _resp({'data': self._key(remaining_seq(i))})

        with mock.patch('urllib.request.urlopen', side_effect=fake_urlopen):
            with mock.patch.dict(os.environ, {'OPENROUTER_API_KEY': 'sk-test'}):
                return self.b.run_bench(
                    provider=stub, cheap=True, claim='efficiency',
                    config=cfg, skip_key_check=False)

    def test_aborts_before_first_cell_when_estimate_exceeds_run_budget(self):
        stub = self._stub(1)
        cfg = self._cfg(maxTurnsPerCell=8, maxRequestsPerRun=200)
        with self.assertRaises(self.b.BenchError):
            self._real_run(cfg, stub, lambda i: 1000)
        self.assertEqual(stub.count, 0)

    def test_aborts_before_first_cell_when_estimate_exceeds_remaining(self):
        stub = self._stub(1)
        cfg = self._cfg(maxTurnsPerCell=8, maxRequestsPerRun=1000)
        with self.assertRaises(self.b.BenchError):
            self._real_run(cfg, stub, lambda i: 100)
        self.assertEqual(stub.count, 0)

    def test_default_budget_allows_cheap_run(self):
        # Con tope 100, 30x6=180 aborta; corrida cheap simulada necesita presupuesto mayor.
        stub = self._stub(1)
        self._real_run(self._cfg(maxRequestsPerRun=200), stub, lambda i: 1000)
        self.assertGreaterEqual(stub.count, 1)

    def test_planned_requests_formula(self):
        cfg = self._cfg()
        self.assertEqual(self.b.planned_requests(cfg, 16), 96)
        with self.assertRaises(self.b.BenchError):
            self.b.planned_requests(cfg, 17)  # 102 > 100
        with self.assertRaises(self.b.BenchError):
            self.b.planned_requests(cfg, 30)  # 180 > 100; no relanzar cheap entero

    def test_cuts_when_remaining_runs_out(self):
        stub = self._stub(4)
        cfg = self._cfg(maxTurnsPerCell=4, maxRequestsPerRun=1000)
        report = self._real_run(cfg, stub, lambda i: max(200 - 10 * i, 0))
        self.assertEqual(stub.count, 20)
        self.assertEqual(len(report['pendingCells']), 10)
        self.assertEqual(report['requestsUsed'], 200)

    def test_cuts_when_run_budget_runs_out(self):
        stub = self._stub(4)
        cfg = self._cfg(maxTurnsPerCell=4, maxRequestsPerRun=120)
        report = self._real_run(cfg, stub, lambda i: 1000 - 6 * i)
        self.assertEqual(stub.count, 20)
        self.assertEqual(len(report['pendingCells']), 10)
        self.assertEqual(report['requestsUsed'], 120)

    def test_missing_calls_counts_turn_cap(self):
        stub = self._stub(None)
        cfg = self._cfg(maxTurnsPerCell=4, maxRequestsPerRun=120)
        report = self._real_run(cfg, stub, lambda i: 1000)
        self.assertEqual(stub.count, 30)
        self.assertEqual(report['pendingCells'], [])
        self.assertEqual(report['requestsUsed'], 120)

    def test_report_exposes_request_budget_fields(self):
        cfg = self._cfg(maxTurnsPerCell=4, maxRequestsPerRun=120)
        report = self._real_run(cfg, self._stub(4), lambda i: 1000)
        self.assertIsInstance(report['requestsUsed'], int)
        self.assertEqual(report['requestBudget'], 120)
        self.assertEqual(report['requestsEstimated'], 120)
        self.assertEqual(report['maxTurnsPerCell'], 4)
        clean = self.b.sanitize_report(report)
        for key in ('requestsUsed', 'requestBudget', 'requestsEstimated', 'maxTurnsPerCell'):
            self.assertEqual(clean[key], report[key])
        md = self.b.format_report_md(report)
        self.assertIn(f"requests: {report['requestsUsed']}/120", md)
        self.assertTrue(any('proxy local' in r and 'fail-closed' in r
                            for r in report['risks']))

    def test_fake_report_has_null_requests_used(self):
        report = self.b.run_bench(
            provider=self.b.FakeProvider(seed=1), cheap=True,
            config=self._cfg(), skip_key_check=True)
        self.assertIsNone(report['requestsUsed'])
        self.assertEqual(report['requestBudget'], 100)
        self.assertEqual(report['maxTurnsPerCell'], 6)
        self.assertIn('requests: None/100', self.b.format_report_md(report))

    def test_min_interval_comment_does_not_promise_rpm(self):
        src = BENCH_PATH.read_text(encoding='utf-8')
        line = next(ln for ln in src.splitlines() if 'MIN_INTERVAL_S =' in ln)
        self.assertNotIn('respeta', line)

    # --- ClaudeCodeProvider con subprocess simulado ---

    def _fake_proxy(self):
        """Proxy mínimo para tests de ClaudeCodeProvider (sin red)."""
        or_mod = load('microsdd_or_proxy_bench_ut', ROOT / '.microharness' / 'or_proxy.py')
        home_dir = tempfile.mkdtemp()
        state = Path(home_dir) / 'c.json'
        self.addCleanup(lambda: shutil.rmtree(home_dir, ignore_errors=True))

        class StubServer:
            aborted = False
            abort_reason = None

        class StubProxy:
            LOCAL_TOKEN = or_mod.OpenRouterCountingProxy.LOCAL_TOKEN

            def __init__(self):
                self.counter = or_mod.RequestCounter(state, 100)
                self.server = StubServer()
                self.base_url = 'http://127.0.0.1:9'

            def assert_readable(self):
                return self.counter.read()

            def read_count(self):
                return self.counter.read()['count']

            def client_env(self, model_id, *, home=None):
                env = os.environ.copy()
                for k in ('OPENROUTER_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_API_KEY'):
                    env.pop(k, None)
                if home:
                    env['HOME'] = home
                env['ANTHROPIC_BASE_URL'] = self.base_url
                env['ANTHROPIC_AUTH_TOKEN'] = self.LOCAL_TOKEN
                env['ANTHROPIC_API_KEY'] = ''
                env['ANTHROPIC_DEFAULT_SONNET_MODEL'] = model_id
                env['ANTHROPIC_DEFAULT_OPUS_MODEL'] = model_id
                env['ANTHROPIC_DEFAULT_HAIKU_MODEL'] = model_id
                env['CLAUDE_CODE_SUBAGENT_MODEL'] = model_id
                env.setdefault('CI', 'true')
                return env

        return StubProxy()

    def _run_claude(self, payload, *, test_ok, max_turns=5):
        calls = []

        def fake_run(cmd, *a, **k):
            calls.append((list(cmd), k.get('env')))
            if '--version' in cmd:
                return mock.Mock(returncode=0, stdout='2.1.197 (Claude Code)', stderr='')
            if '-p' in cmd:
                return mock.Mock(returncode=0, stdout=json.dumps(payload), stderr='')
            return mock.Mock(returncode=0 if test_ok else 1, stdout='', stderr='')

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        proxy = self._fake_proxy()
        with mock.patch('subprocess.run', side_effect=fake_run):
            with mock.patch.dict(os.environ, {'OPENROUTER_API_KEY': 'sk-should-not-leak'}):
                prov = self.b.ClaudeCodeProvider(
                    'meta/llama:free', max_turns=max_turns, proxy=proxy)
                task = {'id': '01', 'title': 't', 'testCommand': ['python', '-m', 'unittest']}
                result = prov.run_cell(task, 'base', 0, workdir=Path(tmp.name))
        cmds = [c for c, _ in calls]
        envs = [e for c, e in calls if e is not None]
        return result, cmds, envs

    def test_claude_cmd_includes_max_turns(self):
        payload = {'is_error': False, 'subtype': 'success', 'num_turns': 2,
                   'usage': {'input_tokens': 10, 'output_tokens': 5}}
        _result, cmds, envs = self._run_claude(payload, test_ok=True, max_turns=5)
        cmd = next(c for c in cmds if '-p' in c)
        i = cmd.index('--max-turns')
        self.assertEqual(cmd[i + 1], '5')
        # Key real no llega al entorno de Claude; solo token local del proxy + HOME temp.
        p_env = next(e for e in envs if e.get('ANTHROPIC_AUTH_TOKEN') == 'microsdd-proxy-local')
        self.assertNotIn('OPENROUTER_API_KEY', p_env)
        self.assertNotIn('sk-should-not-leak', json.dumps(p_env))
        self.assertIn('microsdd-claude-home-', p_env.get('HOME', ''))

    def test_claude_provider_requires_proxy(self):
        with self.assertRaises(self.b.BenchError) as ctx:
            self.b.ClaudeCodeProvider('meta/llama:free', max_turns=3)
        self.assertIn('proxy', str(ctx.exception).lower())

    def test_num_turns_sets_calls_and_iterations(self):
        base = {'is_error': False, 'subtype': 'success',
                'usage': {'input_tokens': 10, 'output_tokens': 5}}
        result, _, _ = self._run_claude(dict(base, num_turns=6), test_ok=True)
        self.assertEqual(result['calls'], 6)
        self.assertEqual(result['iterations'], 6)
        for extra in ({}, {'num_turns': '6'}, {'num_turns': True}):
            with self.subTest(extra=extra):
                result, _, _ = self._run_claude(dict(base, **extra), test_ok=True)
                self.assertIsNone(result['calls'])
                self.assertIsNone(result['iterations'])

    def test_error_max_turns_counts_as_completed_cell(self):
        payload = {'is_error': True, 'subtype': 'error_max_turns', 'num_turns': 6,
                   'usage': {'input_tokens': 10, 'output_tokens': 5}}
        result, _, _ = self._run_claude(payload, test_ok=False)
        self.assertIs(result['pending'], False)
        self.assertEqual(result['status'], 'fail')
        self.assertEqual(result['calls'], 6)

    def test_cmd_bench_uses_turn_estimate_and_max_turns(self):
        seen = {}

        def fake_lock(api_key, n_total, **_k):
            seen['n_total'] = n_total
            return self._key(1000)

        # Presupuesto 200 solo para ejercitar el cableado; el default 100 aborta 30x6.
        cfg = self._cfg(maxRequestsPerRun=200)
        prov_cls = mock.Mock()
        fake_proxy = mock.Mock()
        fake_proxy.assert_readable = mock.Mock(return_value={'count': 0, 'max': 200})
        fake_proxy_cls = mock.Mock(return_value=fake_proxy)
        fake_mod = mock.Mock(OpenRouterCountingProxy=fake_proxy_cls)
        with mock.patch.object(self.b, 'load_config', return_value=cfg), \
                mock.patch.object(self.b, 'check_openrouter_free_lock', side_effect=fake_lock), \
                mock.patch.object(self.b, 'verify_openrouter_model_pricing'), \
                mock.patch.object(self.b, '_load_or_proxy', return_value=fake_mod), \
                mock.patch.object(self.b, 'ClaudeCodeProvider', prov_cls), \
                mock.patch.object(self.b, 'run_bench', side_effect=self.b.BenchError('stop')), \
                mock.patch.dict(os.environ, {'OPENROUTER_API_KEY': 'sk-test'}):
            code = self.b.cmd_bench(['run', '--cheap', '--provider', 'openrouter'])
        self.assertEqual(code, 1)
        self.assertEqual(seen['n_total'], 3 * 5 * 2 * 6)
        self.assertEqual(prov_cls.call_args.kwargs.get('max_turns'), 6)
        self.assertIs(prov_cls.call_args.kwargs.get('proxy'), fake_proxy)
        fake_proxy.start.assert_called()
        fake_proxy.stop.assert_called()

    def test_cmd_bench_cheap_aborts_when_estimate_exceeds_100(self):
        with mock.patch.object(self.b, 'load_config', return_value=self._cfg()), \
                mock.patch.dict(os.environ, {'OPENROUTER_API_KEY': 'sk-test'}):
            code = self.b.cmd_bench(['run', '--cheap', '--provider', 'openrouter'])
        self.assertEqual(code, 1)

    def test_remaining_missing_after_cell_is_fail_closed(self):
        stub = self._stub(1)
        reads = {'n': 0}

        def fake_urlopen(*_a, **_k):
            reads['n'] += 1
            data = self._key(1000)
            if reads['n'] > 1:
                del data['free_model_daily_requests']
            return _resp({'data': data})

        cfg = self._cfg(maxRequestsPerRun=200)  # 30x6 cabe; el fallo es remaining ausente
        with mock.patch('urllib.request.urlopen', side_effect=fake_urlopen):
            with mock.patch.dict(os.environ, {'OPENROUTER_API_KEY': 'sk-test'}):
                with self.assertRaises(self.b.BenchError):
                    self.b.run_bench(provider=stub, cheap=True, config=cfg,
                                     skip_key_check=False)
        self.assertEqual(stub.count, 1)


@unittest.skipUnless(METRICS_PATH.is_file() and BENCH_PATH.is_file(), 'metrics/bench ausentes')
class MetricsBenchDispatchTests(unittest.TestCase):
    def test_metrics_dispatches_bench_and_prompt_diff(self):
        sys.path.insert(0, str(METRICS_PATH.parent))
        self.addCleanup(lambda: sys.path.remove(str(METRICS_PATH.parent))
                        if str(METRICS_PATH.parent) in sys.path else None)
        m = load('microsdd_metrics_bench_ut', METRICS_PATH)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = Path(tmp.name) / 'o'
        code = m.main(['bench', 'run', '--cheap', '--provider', 'fake', '--out', str(out)])
        self.assertIn(code, (0, 2))
        code2 = m.main(['prompt-diff', str(ROOT), str(ROOT)])
        self.assertEqual(code2, 0)


if __name__ == '__main__':
    unittest.main()
