#!/usr/bin/env python3
"""Proxy local que cuenta requests hacia OpenRouter (fail-closed). Solo stdlib.

Claude Code apunta ANTHROPIC_BASE_URL al proxy; la key real vive solo aquí.

Solo cuentan hacia el tope de 100 los POST de mensajes realmente reenviados a
OpenRouter (/v1/messages, /v1/chat/completions). Health, HEAD y otros métodos
no gastan slot. El rate limit 20/min ESPERA (cola/backoff) en vez de rechazar,
para que Claude no entre en bucle de reintentos por 429 del propio proxy.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

# Tope de politeness OpenRouter; el limiter espera, no rechaza.
DEFAULT_MAX_REQUESTS_PER_MINUTE = 20
# Espera máxima por slot de rate limit (evita colgar una celda indefinidamente).
DEFAULT_RATE_WAIT_TIMEOUT_S = 180.0
# Rutas POST que cuentan hacia el tope de 100 (mensajes reenviados).
COUNTABLE_POST_PATHS = (
    '/v1/messages',
    '/v1/chat/completions',
    '/messages',
    '/chat/completions',
)


class ProxyError(Exception):
    pass


def _path_only(path: str) -> str:
    return (path or '/').split('?', 1)[0]


def is_countable_request(method: str, path: str) -> bool:
    """True solo para POST de mensajes (los que deben gastar el tope de 100)."""
    if (method or '').upper() != 'POST':
        return False
    p = _path_only(path)
    if p in COUNTABLE_POST_PATHS:
        return True
    return any(p.endswith(suffix) for suffix in COUNTABLE_POST_PATHS)


class RateLimiter:
    """Ventana deslizante de 60s. Espera (cola) al llegar al tope; no rechaza."""

    def __init__(
        self,
        max_per_minute: int = DEFAULT_MAX_REQUESTS_PER_MINUTE,
        *,
        wait_timeout_s: float = DEFAULT_RATE_WAIT_TIMEOUT_S,
    ):
        if type(max_per_minute) is not int or max_per_minute < 1:
            raise ProxyError(f'max_per_minute inválido: {max_per_minute!r}')
        if not isinstance(wait_timeout_s, (int, float)) or isinstance(wait_timeout_s, bool):
            raise ProxyError(f'wait_timeout_s inválido: {wait_timeout_s!r}')
        timeout = float(wait_timeout_s)
        if timeout <= 0 or timeout != timeout:  # NaN check
            raise ProxyError(f'wait_timeout_s inválido: {wait_timeout_s!r}')
        self.max_per_minute = max_per_minute
        self.wait_timeout_s = timeout
        self._times: list[float] = []
        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)

    def acquire(self) -> None:
        """Bloquea hasta haber hueco en la ventana; registra el slot al salir."""
        deadline = time.monotonic() + self.wait_timeout_s
        with self._cv:
            while True:
                now = time.monotonic()
                cutoff = now - 60.0
                self._times = [t for t in self._times if t > cutoff]
                if len(self._times) < self.max_per_minute:
                    self._times.append(now)
                    self._cv.notify_all()
                    return
                if now >= deadline:
                    raise ProxyError(
                        f'rate limit {self.max_per_minute}/min: espera agotada '
                        f'({self.wait_timeout_s}s)')
                oldest = min(self._times)
                sleep_for = min((oldest + 60.0) - now, deadline - now)
                if sleep_for < 0.01:
                    sleep_for = 0.01
                self._cv.wait(timeout=sleep_for)


class RequestCounter:
    """Contador persistente fail-closed. Estado: {"count": int, "max": int}.

    El tope es acumulado entre intentos: si el archivo ya existe, se conserva
    `count` (p. ej. smoke previo o intento de otro repo) y solo se actualiza `max`.
    """

    def __init__(self, path: Path, max_requests: int, *, initial_count: int = 0):
        if type(max_requests) is not int or max_requests < 1:
            raise ProxyError(f'max_requests inválido: {max_requests!r}')
        if type(initial_count) is not int or initial_count < 0:
            raise ProxyError(f'initial_count inválido: {initial_count!r}')
        if initial_count > max_requests:
            raise ProxyError(
                f'initial_count={initial_count} ya supera max={max_requests} (fail-closed)')
        self.path = Path(path)
        self.max_requests = max_requests
        self.initial_count = initial_count
        self._lock = threading.Lock()
        self._ensure()

    def _ensure(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.is_file():
            self._write({'count': self.initial_count, 'max': self.max_requests})
            return
        data = self.read()
        # Acumulado: no bajar count si el archivo ya refleja intentos previos.
        changed = False
        if data['max'] != self.max_requests:
            data['max'] = self.max_requests
            changed = True
        if data['count'] < self.initial_count:
            data['count'] = self.initial_count
            changed = True
        if data['count'] > data['max']:
            raise ProxyError(
                f'contador ya sobre el tope: count={data["count"]} max={data["max"]}')
        if changed:
            self._write(data)

    def _write(self, data: dict) -> None:
        raw = json.dumps(data, separators=(',', ':')) + '\n'
        tmp = self.path.with_suffix(self.path.suffix + '.tmp')
        try:
            tmp.write_text(raw, encoding='utf-8')
            tmp.replace(self.path)
        except OSError as exc:
            raise ProxyError(f'no se pudo escribir contador {self.path}: {exc}') from exc

    def read(self) -> dict:
        try:
            text = self.path.read_text(encoding='utf-8')
            data = json.loads(text)
        except (OSError, ValueError) as exc:
            raise ProxyError(f'contador ilegible {self.path}: {exc}') from exc
        if not isinstance(data, dict):
            raise ProxyError('contador: raíz no es objeto')
        count = data.get('count')
        mx = data.get('max')
        if type(count) is not int or count < 0:
            raise ProxyError(f'contador count inválido: {count!r}')
        if type(mx) is not int or mx < 1:
            raise ProxyError(f'contador max inválido: {mx!r}')
        return {'count': count, 'max': mx}

    def allow_and_increment(self) -> int:
        """Si count < max, incrementa y devuelve el nuevo count. Si no, ProxyError."""
        with self._lock:
            data = self.read()
            if data['count'] >= data['max']:
                raise ProxyError(
                    f'tope de requests alcanzado: count={data["count"]} max={data["max"]}')
            data['count'] = data['count'] + 1
            self._write(data)
            return data['count']


def _scrub_auth_header(value: str) -> str:
    if not value:
        return value
    parts = value.split(None, 1)
    if len(parts) == 2 and parts[0].lower() in ('bearer', 'sk-'):
        return f'{parts[0]} [REDACTED]'
    if len(value) > 12:
        return value[:4] + '…[REDACTED]'
    return '[REDACTED]'


class _ProxyHandler(BaseHTTPRequestHandler):
    server: 'CountingProxyServer'

    def log_message(self, fmt: str, *args: Any) -> None:
        # No loguear headers/body (pueden llevar keys).
        return

    def _read_body(self) -> bytes:
        """Lee el body; soporta Content-Length y Transfer-Encoding: chunked.

        Sin esto, Claude Code suele enviar chunked sin Content-Length y el proxy
        reenviaba body vacío → error rápido de OpenRouter / is_error.
        """
        max_body = 32 * 1024 * 1024
        te = (self.headers.get('Transfer-Encoding') or '').lower()
        if 'chunked' in te:
            chunks: list[bytes] = []
            total = 0
            while True:
                line = self.rfile.readline()
                if not line:
                    break
                try:
                    size = int(line.strip().split(b';')[0], 16)
                except ValueError as exc:
                    raise ProxyError(f'chunk size inválido: {line!r}') from exc
                if size < 0 or total + size > max_body:
                    raise ProxyError('body chunked excede el máximo')
                if size == 0:
                    # trailer opcional hasta línea vacía
                    while True:
                        trailer = self.rfile.readline()
                        if trailer in (b'\r\n', b'\n', b''):
                            break
                    break
                chunks.append(self.rfile.read(size))
                total += size
                self.rfile.read(2)  # CRLF tras el chunk
            return b''.join(chunks)
        length_hdr = self.headers.get('Content-Length')
        if length_hdr is None or length_hdr == '':
            return b''
        try:
            length = int(length_hdr)
        except ValueError:
            return b''
        if length < 0 or length > max_body:
            return b''
        return self.rfile.read(length) if length else b''

    def _reject(self, code: int, message: str, *, error_type: str = 'microsdd_proxy') -> None:
        # No usar type=rate_limit_error: Claude Code reintenta en bucle ante 429.
        payload = json.dumps({
            'error': {'message': message, 'type': error_type},
            'type': 'error',
        }).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        # Señalar no-reintento a clientes que respeten Retry-After vacío / connection close.
        if code in (403, 401):
            self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(payload)

    def _local_ok(self, payload: dict) -> None:
        raw = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _handle_health(self) -> None:
        try:
            data = self.server.counter.read()
        except ProxyError as exc:
            self.server.aborted = True
            self.server.abort_reason = str(exc)
            self._reject(500, str(exc))
            return
        self._local_ok({
            'ok': True,
            'count': data['count'],
            'max': data['max'],
            'aborted': bool(self.server.aborted),
        })

    def _forward(self, method: str) -> None:
        counter: RequestCounter = self.server.counter
        api_key: str = self.server.api_key
        upstream: str = self.server.upstream
        path = self.path if self.path.startswith('/') else '/' + self.path
        countable = is_countable_request(method, path)

        # Leer body ANTES de contar: fallo de parseo no gasta slot.
        try:
            body = self._read_body() if method in ('POST', 'PUT', 'PATCH') else None
        except ProxyError as exc:
            self.server.aborted = True
            self.server.abort_reason = str(exc)
            self._reject(400, str(exc), error_type='invalid_request_error')
            return

        new_count: int | None = None
        if countable:
            # Rate limit: esperar hueco (no 429 → Claude no reintenta en bucle).
            try:
                self.server.rate_limiter.acquire()
            except ProxyError as exc:
                self.server.aborted = True
                self.server.abort_reason = str(exc)
                # 403 + tipo propio: no es rate_limit_error de API.
                self._reject(403, str(exc), error_type='microsdd_proxy_timeout')
                return
            try:
                new_count = counter.allow_and_increment()
            except ProxyError as exc:
                self.server.aborted = True
                self.server.abort_reason = str(exc)
                self._reject(403, str(exc), error_type='microsdd_proxy_budget')
                return

        url = upstream.rstrip('/') + path
        # Permitir fallbacks de proveedor en OpenRouter (NVIDIA Function-not-found).
        if body and method in ('POST', 'PUT', 'PATCH'):
            ctype = (self.headers.get('Content-Type') or '').lower()
            if 'json' in ctype:
                try:
                    parsed = json.loads(body.decode('utf-8'))
                except (UnicodeDecodeError, ValueError):
                    parsed = None
                if isinstance(parsed, dict) and 'provider' not in parsed:
                    parsed['provider'] = {
                        'allow_fallbacks': True,
                        'require_parameters': False,
                    }
                    body = json.dumps(parsed, separators=(',', ':')).encode('utf-8')
        # Key real solo aquí (Authorization + x-api-key Anthropic-style).
        headers = {
            'Authorization': f'Bearer {api_key}',
            'x-api-key': api_key,
            'User-Agent': self.headers.get('User-Agent') or 'microsdd-or-proxy/0',
            'Content-Type': self.headers.get('Content-Type') or 'application/json',
            'Accept': self.headers.get('Accept') or 'application/json',
        }
        # Propagar cabeceras del cliente excepto auth/hop-by-hop (token local no sale).
        skip = {
            'host', 'content-length', 'transfer-encoding', 'connection',
            'authorization', 'x-api-key', 'proxy-authorization',
        }
        for key, val in self.headers.items():
            if key.lower() in skip or not val:
                continue
            headers.setdefault(key, val)
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.server.upstream_timeout) as resp:
                raw = resp.read()
                status = resp.status
                content_type = resp.headers.get('Content-Type') or 'application/json'
        except urllib.error.HTTPError as exc:
            raw = exc.read() if exc.fp else b''
            status = exc.code
            content_type = exc.headers.get('Content-Type') if exc.headers else 'application/json'
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            label = f'#{new_count}' if new_count is not None else '(no contado)'
            self.server.aborted = True
            self.server.abort_reason = f'upstream error after request {label}: {exc}'
            self._reject(502, f'upstream error: {type(exc).__name__}')
            return
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(raw)))
        if new_count is not None:
            self.send_header('X-Microsdd-Request-Count', str(new_count))
        self.end_headers()
        self.wfile.write(raw)

    def do_HEAD(self) -> None:  # noqa: N802
        # Probes de auth de Claude/SDK: 200 local, sin reenviar ni contar (evita 401→retry).
        path = _path_only(self.path if self.path.startswith('/') else '/' + self.path)
        if path in ('/health', '/healthz', '/', '/v1/models', '/v1/messages'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        self.send_response(200)
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = _path_only(self.path if self.path.startswith('/') else '/' + self.path)
        if path in ('/health', '/healthz'):
            self._handle_health()
            return
        # Otros GET (p. ej. /v1/models): reenvío sin gastar el tope de 100.
        self._forward('GET')

    def do_POST(self) -> None:  # noqa: N802
        self._forward('POST')

    def do_PUT(self) -> None:  # noqa: N802
        self._forward('PUT')

    def do_DELETE(self) -> None:  # noqa: N802
        self._forward('DELETE')

    def do_PATCH(self) -> None:  # noqa: N802
        self._forward('PATCH')


class CountingProxyServer(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        *,
        counter: RequestCounter,
        api_key: str,
        upstream: str = 'https://openrouter.ai/api',
        upstream_timeout: float = 600.0,
        max_requests_per_minute: int = DEFAULT_MAX_REQUESTS_PER_MINUTE,
        rate_wait_timeout_s: float = DEFAULT_RATE_WAIT_TIMEOUT_S,
    ):
        if not api_key:
            raise ProxyError('api_key del proxy ausente')
        self.counter = counter
        self.api_key = api_key
        self.upstream = upstream.rstrip('/')
        self.upstream_timeout = upstream_timeout
        self.rate_limiter = RateLimiter(
            max_requests_per_minute, wait_timeout_s=rate_wait_timeout_s)
        self.aborted = False
        self.abort_reason: str | None = None
        super().__init__(server_address, _ProxyHandler)


def tempfile_state_dir() -> str:
    return tempfile.gettempdir()


class OpenRouterCountingProxy:
    """Arranca el proxy en un hilo. La key no se expone al cliente."""

    LOCAL_TOKEN = 'microsdd-proxy-local'

    def __init__(
        self,
        api_key: str,
        *,
        max_requests: int = 100,
        state_path: Path | None = None,
        host: str = '127.0.0.1',
        port: int = 0,
        upstream: str = 'https://openrouter.ai/api',
        initial_count: int = 0,
        max_requests_per_minute: int = DEFAULT_MAX_REQUESTS_PER_MINUTE,
        rate_wait_timeout_s: float = DEFAULT_RATE_WAIT_TIMEOUT_S,
    ):
        if not api_key:
            raise ProxyError('OPENROUTER_API_KEY ausente para el proxy')
        self.max_requests = max_requests
        self.state_path = Path(state_path or (Path(tempfile_state_dir()) / 'or-proxy-count.json'))
        self.counter = RequestCounter(
            self.state_path, max_requests, initial_count=initial_count)
        self._api_key = api_key
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((host, port))
        chosen_port = sock.getsockname()[1]
        sock.close()
        self.server = CountingProxyServer(
            (host, chosen_port),
            counter=self.counter,
            api_key=api_key,
            upstream=upstream,
            max_requests_per_minute=max_requests_per_minute,
            rate_wait_timeout_s=rate_wait_timeout_s,
        )
        self.host = host
        self.port = chosen_port
        self._thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        return f'http://{self.host}:{self.port}'

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        try:
            self.server.shutdown()
        except Exception:
            pass
        try:
            self.server.server_close()
        except Exception:
            pass

    def read_count(self) -> int:
        return self.counter.read()['count']

    def assert_readable(self) -> dict:
        return self.counter.read()

    def client_env(self, model_id: str, *, home: str | None = None) -> dict[str, str]:
        """Entorno para Claude Code: sin key real; solo apunta al proxy."""
        env = os.environ.copy()
        # Quitar keys reales del entorno del cliente (incl. alias DeepSeek).
        for k in (
            'OPENROUTER_API_KEY', 'DEEPSEEK_API_KEY',
            'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_API_KEY',
        ):
            env.pop(k, None)
        if home:
            env['HOME'] = home
            env['USERPROFILE'] = home  # Windows Claude/Node
            env['XDG_CONFIG_HOME'] = str(Path(home) / '.config')
            env['XDG_STATE_HOME'] = str(Path(home) / '.local' / 'state')
            env['XDG_CACHE_HOME'] = str(Path(home) / '.cache')
        env['ANTHROPIC_BASE_URL'] = self.base_url
        env['ANTHROPIC_AUTH_TOKEN'] = self.LOCAL_TOKEN
        env['ANTHROPIC_API_KEY'] = ''
        env['ANTHROPIC_DEFAULT_SONNET_MODEL'] = model_id
        env['ANTHROPIC_DEFAULT_OPUS_MODEL'] = model_id
        env['ANTHROPIC_DEFAULT_HAIKU_MODEL'] = model_id
        env['CLAUDE_CODE_SUBAGENT_MODEL'] = model_id
        env.setdefault('CI', 'true')
        env.setdefault('CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC', '1')
        # Mitigar reintentos agresivos del SDK ante fallos de red/proxy.
        env.setdefault('CLAUDE_CODE_MAX_RETRIES', '0')
        env.setdefault('ANTHROPIC_MAX_RETRIES', '0')
        return env


def main(argv: list[str] | None = None) -> int:
    """CLI mínima: or_proxy.py --max N --state PATH (bloquea hasta Ctrl-C)."""
    parser = argparse.ArgumentParser(description='Proxy contador OpenRouter (microsdd)')
    parser.add_argument('--max', type=int, default=100)
    parser.add_argument('--state', type=Path, default=None)
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument(
        '--initial-count', type=int, default=0,
        help='Requests ya gastados en intentos previos (tope acumulado).')
    parser.add_argument(
        '--rpm', type=int, default=DEFAULT_MAX_REQUESTS_PER_MINUTE,
        help='Tope de requests por minuto (espera/cola, no rechaza).')
    args = parser.parse_args(argv)
    key = os.environ.get('OPENROUTER_API_KEY') or ''
    if not key:
        print('ERROR: OPENROUTER_API_KEY ausente', flush=True)
        return 1
    proxy = OpenRouterCountingProxy(
        key, max_requests=args.max, state_path=args.state, port=args.port,
        initial_count=args.initial_count, max_requests_per_minute=args.rpm)
    proxy.start()
    print(f'proxy listening on {proxy.base_url} max={args.max}', flush=True)
    print(f'state={proxy.state_path}', flush=True)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        proxy.stop()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
