#!/usr/bin/env python3
"""Proxy local que cuenta requests hacia OpenRouter (fail-closed). Solo stdlib.

Claude Code apunta ANTHROPIC_BASE_URL al proxy; la key real vive solo aquí.
Cada request HTTP (incluido small-fast u otros modelos) incrementa el contador.
Si el contador no se puede leer/escribir, o si se alcanza el tope, se rechaza.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


class ProxyError(Exception):
    pass


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

    def _reject(self, code: int, message: str) -> None:
        payload = json.dumps({'error': {'message': message, 'type': 'microsdd_proxy'}}).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _forward(self, method: str) -> None:
        counter: RequestCounter = self.server.counter
        api_key: str = self.server.api_key
        upstream: str = self.server.upstream
        try:
            new_count = counter.allow_and_increment()
        except ProxyError as exc:
            self.server.aborted = True
            self.server.abort_reason = str(exc)
            self._reject(403, str(exc))
            return

        path = self.path if self.path.startswith('/') else '/' + self.path
        url = upstream.rstrip('/') + path
        try:
            body = self._read_body() if method in ('POST', 'PUT', 'PATCH') else None
        except ProxyError as exc:
            self.server.aborted = True
            self.server.abort_reason = str(exc)
            self._reject(400, str(exc))
            return
        headers = {
            'Authorization': f'Bearer {api_key}',
            'User-Agent': self.headers.get('User-Agent') or 'microsdd-or-proxy/0',
            'Content-Type': self.headers.get('Content-Type') or 'application/json',
            'Accept': self.headers.get('Accept') or 'application/json',
        }
        # Propagar cabeceras útiles sin reenviar Authorization del cliente.
        for hop in ('anthropic-version', 'anthropic-beta', 'x-title', 'http-referer'):
            val = self.headers.get(hop)
            if val:
                headers[hop] = val
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
            self.server.aborted = True
            self.server.abort_reason = f'upstream error after request #{new_count}: {exc}'
            self._reject(502, f'upstream error: {type(exc).__name__}')
            return
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('X-Microsdd-Request-Count', str(new_count))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ('/health', '/healthz'):
            try:
                data = self.server.counter.read()
            except ProxyError as exc:
                self.server.aborted = True
                self.server.abort_reason = str(exc)
                self._reject(500, str(exc))
                return
            payload = json.dumps({
                'ok': True,
                'count': data['count'],
                'max': data['max'],
                'aborted': bool(self.server.aborted),
            }).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
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
    ):
        if not api_key:
            raise ProxyError('api_key del proxy ausente')
        self.counter = counter
        self.api_key = api_key
        self.upstream = upstream.rstrip('/')
        self.upstream_timeout = upstream_timeout
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
        # Quitar keys reales del entorno del cliente.
        for k in ('OPENROUTER_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_API_KEY'):
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
    args = parser.parse_args(argv)
    key = os.environ.get('OPENROUTER_API_KEY') or ''
    if not key:
        print('ERROR: OPENROUTER_API_KEY ausente', flush=True)
        return 1
    proxy = OpenRouterCountingProxy(
        key, max_requests=args.max, state_path=args.state, port=args.port,
        initial_count=args.initial_count)
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
