"""Bench m2: estadísticas, candado :free, fake provider y prompt-diff."""
from __future__ import annotations

import importlib.util
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
    # Asegura que imports relativos al dir .microharness funcionen.
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(mod)
    finally:
        if sys.path[0] == str(path.parent):
            sys.path.pop(0)
    return mod


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

    def test_assert_free_model(self):
        self.b.assert_free_model('meta/llama:free')
        with self.assertRaises(self.b.BenchError):
            self.b.assert_free_model('anthropic/claude-opus-5-5')

    def test_openrouter_lock_aborts_on_paid_usage(self):
        payload = json.dumps({'data': {'usage': 1.5, 'limit': None,
                                       'free_model_daily_requests': {'remaining': 100}}}).encode()

        class Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return payload

        with mock.patch('urllib.request.urlopen', return_value=Resp()):
            with self.assertRaises(self.b.BenchError) as ctx:
                self.b.check_openrouter_free_lock('sk-test', 10)
            self.assertIn('usage', str(ctx.exception).lower())

    def test_openrouter_lock_aborts_without_key(self):
        with self.assertRaises(self.b.BenchError):
            self.b.check_openrouter_free_lock(None, 10)

    def test_fake_run_produces_verdict_and_cheap_flag(self):
        cfg = self.b.load_config()
        cfg['bootstrap'] = 500  # más rápido en CI
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
        self.assertEqual(data['baselineStatus'], 'pending')
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


@unittest.skipUnless(METRICS_PATH.is_file() and BENCH_PATH.is_file(), 'metrics/bench ausentes')
class MetricsBenchDispatchTests(unittest.TestCase):
    def test_metrics_dispatches_bench_and_prompt_diff(self):
        # Carga metrics desde su directorio para que `import bench` funcione.
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
