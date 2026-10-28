"""T-034: arnés en treatment, dry-run y tope fail-closed."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
BENCH_PATH = ROOT / '.microharness' / 'bench.py'
OR_PATH = ROOT / '.microharness' / 'or_proxy.py'


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(mod)
    finally:
        if sys.path and sys.path[0] == str(path.parent):
            sys.path.pop(0)
    return mod


@unittest.skipUnless(BENCH_PATH.is_file(), 'bench.py ausente')
class AbHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = load('microsdd_ab_harness_ut', BENCH_PATH)

    def test_prepare_treatment_loads_harness_base_does_not(self):
        tasks = self.b.list_tasks()
        task = tasks[0]
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / 'base'
            treat = Path(tmp) / 'treatment'
            b_info = self.b.prepare_cell_workdir(
                Path(task['_dir']), base, 'base')
            t_info = self.b.prepare_cell_workdir(
                Path(task['_dir']), treat, 'treatment')
            self.assertFalse(b_info['loaded'])
            self.assertFalse(self.b.harness_loaded(base))
            self.assertTrue(t_info['loaded'])
            self.assertTrue(self.b.harness_loaded(treat))
            self.assertEqual(t_info['preset'], 'microsdd')
            self.assertNotEqual(b_info['fingerprint'], t_info['fingerprint'])
            self.assertTrue((treat / 'CLAUDE.md').is_file())
            self.assertTrue((treat / '.claude' / 'settings.json').is_file())
            self.assertFalse((base / 'CLAUDE.md').exists())

    def test_dry_run_harness_check_ok(self):
        result = self.b.dry_run_harness_check()
        self.assertTrue(result['ok'])
        self.assertFalse(result['base']['loaded'])
        self.assertTrue(result['treatment']['loaded'])
        self.assertEqual(result['treatment']['preset'], 'microsdd')
        self.assertGreaterEqual(result['treatment']['fileCount'], 8)
        self.assertNotEqual(
            result['base']['fingerprint'], result['treatment']['fingerprint'])

    def test_cmd_bench_dry_run_exit_0(self):
        code = self.b.cmd_bench(['dry-run'])
        self.assertEqual(code, 0)

    def test_cmd_bench_ab_dry_run_exit_0(self):
        code = self.b.cmd_bench(['ab', '--provider', 'deepseek', '--dry-run'])
        self.assertEqual(code, 0)

    def test_ab_caps_and_min_turns(self):
        self.assertEqual(self.b.AB_CAPS['free'], 500)
        self.assertEqual(self.b.AB_CAPS['deepseek'], 300)
        self.assertEqual(self.b.AB_MIN_TURNS, 6)
        name, cap, model = self.b.resolve_ab_provider('free')
        self.assertEqual((name, cap), ('free', 500))
        self.assertTrue(model.endswith(':free'))
        with self.assertRaises(self.b.BenchError):
            self.b.resolve_ab_provider('openai')

    def test_require_api_key_messages(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop('OPENROUTER_API_KEY', None)
            os.environ.pop('DEEPSEEK_API_KEY', None)
            with self.assertRaises(self.b.BenchError) as ctx:
                self.b.require_api_key('free')
            self.assertIn('OPENROUTER_API_KEY', str(ctx.exception))
            with self.assertRaises(self.b.BenchError) as ctx2:
                self.b.require_api_key('deepseek')
            self.assertIn('DEEPSEEK_API_KEY', str(ctx2.exception))

    def test_run_bench_marks_harness_on_cells(self):
        seen = []

        class Spy:
            def run_cell(self, task, variant, repetition, workdir=None):
                seen.append({
                    'variant': variant,
                    'loaded': self.outer.b.harness_loaded(workdir)
                    if workdir else False,
                })
                return {
                    'success': True, 'pending': False, 'status': 'ok',
                    'iterations': 1, 'retries': 0, 'calls': 1,
                    'tokens': 10, 'costUsd': 0.0, 'durationMs': 1,
                    'cacheRate': 0.0, 'firstTry': True,
                    'modelId': 'fake', 'seed': None,
                }

        Spy.outer = self
        cfg = dict(self.b.DEFAULT_CONFIG)
        cfg['bootstrap'] = 20
        cfg['nCheap'] = 1
        cfg['models'] = ['fake/test:free']
        cfg['maxTurnsPerCell'] = 6
        cfg['maxRequestsPerRun'] = 500
        report = self.b.run_bench(
            provider=Spy(), cheap=True, config=cfg, skip_key_check=True)
        self.assertEqual(len(seen), 10)  # 5 tasks × 2 arms × nCheap=1
        for item in seen:
            if item['variant'] == 'treatment':
                self.assertTrue(item['loaded'])
            else:
                self.assertFalse(item['loaded'])
        for cell in report['cells']:
            if cell['variant'] == 'treatment':
                self.assertTrue(cell.get('harnessLoaded'))
                self.assertEqual(cell.get('harnessPreset'), 'microsdd')
            else:
                self.assertFalse(cell.get('harnessLoaded'))

    def test_tope_alcanzado_in_report_when_headroom_cuts(self):
        """Presupuesto agotado → pending + status tope alcanzado + exit path."""
        class Stub:
            def run_cell(self, task, variant, repetition, workdir=None):
                return {
                    'success': True, 'pending': False, 'status': 'ok',
                    'iterations': 6, 'retries': 0, 'calls': 6,
                    'tokens': 10, 'costUsd': 0.0, 'durationMs': 1,
                    'cacheRate': 0.0, 'firstTry': True,
                    'modelId': 'meta/llama:free', 'seed': None,
                }

        class FakeProxy:
            def __init__(self):
                self._n = 0
                self.server = type('S', (), {'aborted': False, 'abort_reason': None})()

            def read_count(self):
                return self._n

            def bump(self, n):
                self._n = n

        proxy = FakeProxy()
        stub = Stub()
        # Tras cada celda el runner relee proxy; simulamos gasto de 6 por celda.
        orig = stub.run_cell

        def wrapping(task, variant, repetition, workdir=None):
            out = orig(task, variant, repetition, workdir=workdir)
            proxy.bump(proxy.read_count() + 6)
            return out

        stub.run_cell = wrapping
        stub.proxy = proxy
        cfg = dict(self.b.DEFAULT_CONFIG)
        cfg.update({
            'bootstrap': 20, 'nCheap': 3, 'models': ['meta/llama:free'],
            'maxTurnsPerCell': 6, 'maxRequestsPerRun': 12,  # cabe 2 celdas
            'allowPartialRun': True, 'maxSpendUsd': 99, 'maxPaidLimitUsd': 10,
        })
        key = {
            'usage': 0, 'limit': 0, 'limit_remaining': 0,
            'free_model_daily_requests': {'remaining': 1000},
        }

        def _resp(payload):
            class R:
                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False

                def read(self):
                    return json.dumps({'data': payload}).encode()

            return R()

        with mock.patch('urllib.request.urlopen',
                        side_effect=lambda *_a, **_k: _resp(key)):
            with mock.patch.dict(os.environ, {'OPENROUTER_API_KEY': 'sk-test'}):
                report = self.b.run_bench(
                    provider=stub, cheap=True, config=cfg, skip_key_check=False)
        self.assertTrue(report.get('topeAlcanzado'))
        self.assertEqual(report.get('status'), 'tope alcanzado')
        self.assertTrue(any(c.get('pending') for c in report['cells']))
        self.assertIn('tope', (report.get('abortReason') or '').lower())

    def test_default_ab_out_dir_outside_repo(self):
        out = self.b.default_ab_out_dir()
        self.assertFalse(str(out.resolve()).startswith(str(ROOT.resolve())))
        self.assertTrue(str(out).endswith('microsdd-ab') or 'microsdd-ab' in str(out))


@unittest.skipUnless(OR_PATH.is_file(), 'or_proxy.py ausente')
class FailClosedCapTests(unittest.TestCase):
    """Al llegar al tope no sale ninguna request más y el proxy responde 403."""

    @classmethod
    def setUpClass(cls):
        cls.or_mod = load('microsdd_or_ab_ut', OR_PATH)

    def test_cap_blocks_further_posts_and_persists(self):
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        hits = []

        class Upstream(BaseHTTPRequestHandler):
            def log_message(self, *a):
                return

            def do_POST(self):  # noqa: N802
                length = int(self.headers.get('Content-Length') or 0)
                body = self.rfile.read(length) if length else b''
                hits.append(body)
                payload = b'{"ok":true}'
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        up = ThreadingHTTPServer(('127.0.0.1', 0), Upstream)
        t = threading.Thread(target=up.serve_forever, daemon=True)
        t.start()
        self.addCleanup(up.shutdown)
        self.addCleanup(up.server_close)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        state = Path(tmp.name) / 'count.json'
        proxy = self.or_mod.OpenRouterCountingProxy(
            'sk-real',
            max_requests=2,
            state_path=state,
            upstream=f'http://127.0.0.1:{up.server_address[1]}',
            max_requests_per_minute=20,
        )
        proxy.start()
        self.addCleanup(proxy.stop)

        def post():
            req = urllib.request.Request(
                proxy.base_url + '/v1/messages',
                data=b'{"model":"x","messages":[]}',
                headers={
                    'Authorization': f'Bearer {self.or_mod.OpenRouterCountingProxy.LOCAL_TOKEN}',
                    'Content-Type': 'application/json',
                },
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status

        self.assertEqual(post(), 200)
        self.assertEqual(post(), 200)
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            post()
        self.assertEqual(ctx.exception.code, 403)
        self.assertEqual(len(hits), 2)  # no salió el 3er POST
        self.assertEqual(proxy.read_count(), 2)
        self.assertTrue(proxy.server.aborted)
        # Persistencia entre reinicios: initial_count desde disco.
        data = json.loads(state.read_text(encoding='utf-8'))
        self.assertEqual(data['count'], 2)
        self.assertEqual(data['max'], 2)


if __name__ == '__main__':
    unittest.main()
