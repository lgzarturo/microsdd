"""Bench m2: estadísticas, candado :free fail-closed, fake provider y prompt-diff."""
from __future__ import annotations

import importlib.util
import io
import json
import os
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
