"""Bordes del proxy contador OpenRouter (fail-closed)."""
from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
OR_PATH = ROOT / '.microharness' / 'or_proxy.py'


def load_or():
    spec = importlib.util.spec_from_file_location('microsdd_or_proxy_ut', OR_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(OR_PATH.is_file(), 'or_proxy.py ausente')
class RequestCounterTests(unittest.TestCase):
    def setUp(self):
        self.or_mod = load_or()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'count.json'

    def test_starts_at_zero_and_increments_up_to_max(self):
        c = self.or_mod.RequestCounter(self.path, 3)
        self.assertEqual(c.read()['count'], 0)
        self.assertEqual(c.allow_and_increment(), 1)
        self.assertEqual(c.allow_and_increment(), 2)
        self.assertEqual(c.allow_and_increment(), 3)
        with self.assertRaises(self.or_mod.ProxyError) as ctx:
            c.allow_and_increment()
        self.assertIn('tope', str(ctx.exception))
        self.assertEqual(c.read()['count'], 3)

    def test_reject_request_101_when_max_100(self):
        c = self.or_mod.RequestCounter(self.path, 100)
        for _ in range(100):
            c.allow_and_increment()
        with self.assertRaises(self.or_mod.ProxyError):
            c.allow_and_increment()
        self.assertEqual(c.read()['count'], 100)

    def test_initial_count_accumulates_across_attempts(self):
        # Intentos previos (p. ej. smoke CC = 4) cuentan hacia el tope.
        c = self.or_mod.RequestCounter(self.path, 100, initial_count=4)
        self.assertEqual(c.read()['count'], 4)
        self.assertEqual(c.allow_and_increment(), 5)
        # Reabrir el mismo state no baja el count.
        c2 = self.or_mod.RequestCounter(self.path, 100, initial_count=4)
        self.assertEqual(c2.read()['count'], 5)
        with self.assertRaises(self.or_mod.ProxyError):
            self.or_mod.RequestCounter(self.path, 100, initial_count=101)

    def test_unreadable_counter_raises(self):
        self.path.write_text('not-json', encoding='utf-8')
        c = self.or_mod.RequestCounter.__new__(self.or_mod.RequestCounter)
        c.path = self.path
        c.max_requests = 10
        c._lock = __import__('threading').Lock()
        with self.assertRaises(self.or_mod.ProxyError) as ctx:
            c.read()
        self.assertIn('ilegible', str(ctx.exception))

    def test_invalid_max_raises(self):
        for bad in (0, -1, True, '8', None, 1.5):
            with self.subTest(bad=bad):
                with self.assertRaises(self.or_mod.ProxyError):
                    self.or_mod.RequestCounter(self.path, bad)

    def test_corrupt_count_field_fail_closed(self):
        self.path.write_text(json.dumps({'count': '1', 'max': 10}) + '\n', encoding='utf-8')
        c = self.or_mod.RequestCounter.__new__(self.or_mod.RequestCounter)
        c.path = self.path
        c.max_requests = 10
        c._lock = __import__('threading').Lock()
        with self.assertRaises(self.or_mod.ProxyError):
            c.read()


@unittest.skipUnless(OR_PATH.is_file(), 'or_proxy.py ausente')
class ProxyServerTests(unittest.TestCase):
    def setUp(self):
        self.or_mod = load_or()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.upstream_hits = []

        class Upstream(BaseHTTPRequestHandler):
            def log_message(self, *a):
                return

            def do_POST(handler_self):  # noqa: N802
                length = int(handler_self.headers.get('Content-Length') or 0)
                body = handler_self.rfile.read(length) if length else b''
                auth = handler_self.headers.get('Authorization') or ''
                self.upstream_hits.append({'auth': auth, 'body': body, 'path': handler_self.path})
                payload = b'{"ok":true}'
                handler_self.send_response(200)
                handler_self.send_header('Content-Type', 'application/json')
                handler_self.send_header('Content-Length', str(len(payload)))
                handler_self.end_headers()
                handler_self.wfile.write(payload)

        self.up = ThreadingHTTPServer(('127.0.0.1', 0), Upstream)
        self.up_thread = threading.Thread(target=self.up.serve_forever, daemon=True)
        self.up_thread.start()
        self.addCleanup(self.up.shutdown)
        self.addCleanup(self.up.server_close)
        up_url = f'http://127.0.0.1:{self.up.server_address[1]}'
        state = Path(self.tmp.name) / 'c.json'
        self.proxy = self.or_mod.OpenRouterCountingProxy(
            'sk-real-secret-key',
            max_requests=2,
            state_path=state,
            upstream=up_url,
        )
        self.proxy.start()
        self.addCleanup(self.proxy.stop)

    def _post(self, path='/v1/messages'):
        req = urllib.request.Request(
            self.proxy.base_url + path,
            data=b'{"model":"x"}',
            headers={
                'Authorization': f'Bearer {self.or_mod.OpenRouterCountingProxy.LOCAL_TOKEN}',
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.read(), dict(resp.headers)

    def test_forwards_with_real_key_and_counts(self):
        status, body, headers = self._post()
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {'ok': True})
        self.assertEqual(headers.get('X-Microsdd-Request-Count'), '1')
        self.assertEqual(self.proxy.read_count(), 1)
        self.assertEqual(len(self.upstream_hits), 1)
        self.assertEqual(self.upstream_hits[0]['auth'], 'Bearer sk-real-secret-key')

    def test_third_request_rejected_when_max_2(self):
        self._post()
        self._post()
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._post()
        self.assertEqual(ctx.exception.code, 403)
        self.assertTrue(self.proxy.server.aborted)
        self.assertEqual(self.proxy.read_count(), 2)

    def test_client_env_strips_real_key(self):
        with tempfile.TemporaryDirectory() as home:
            with mock.patch.dict(os.environ, {
                'OPENROUTER_API_KEY': 'sk-real-secret-key',
                'ANTHROPIC_AUTH_TOKEN': 'sk-real-secret-key',
                'ANTHROPIC_API_KEY': 'sk-leak',
            }):
                env = self.proxy.client_env('meta/llama:free', home=home)
        self.assertNotIn('OPENROUTER_API_KEY', env)
        self.assertEqual(env['ANTHROPIC_AUTH_TOKEN'], self.or_mod.OpenRouterCountingProxy.LOCAL_TOKEN)
        self.assertEqual(env['ANTHROPIC_API_KEY'], '')
        self.assertEqual(env['ANTHROPIC_BASE_URL'], self.proxy.base_url)
        self.assertEqual(env['HOME'], home)
        self.assertNotIn('sk-real-secret-key', json.dumps(env))

    def test_health_ok_and_unreadable_aborts(self):
        with urllib.request.urlopen(self.proxy.base_url + '/health', timeout=5) as resp:
            data = json.loads(resp.read())
        self.assertTrue(data['ok'])
        self.assertEqual(data['max'], 2)
        # Corromper el contador → health falla cerrado.
        self.proxy.state_path.write_text('{bad', encoding='utf-8')
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(self.proxy.base_url + '/health', timeout=5)
        self.assertEqual(ctx.exception.code, 500)
        self.assertTrue(self.proxy.server.aborted)

    def test_missing_api_key_raises(self):
        with self.assertRaises(self.or_mod.ProxyError):
            self.or_mod.OpenRouterCountingProxy('', max_requests=1)


if __name__ == '__main__':
    unittest.main()
