import http.client
import subprocess
from email.message import Message
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import ProxyHandler

from scripts import demo_local

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEMO_SCRIPT = REPOSITORY_ROOT / 'scripts' / 'demo-local.sh'
JSON_BODY = b'{"status":"ok","private":"DEMO_RESPONSE_SECRET_SENTINEL"}'
METRICS_BODY = b'''# HELP cloudops_http_requests_total Total HTTP requests
# TYPE cloudops_http_requests_total counter
cloudops_http_requests_total{method="GET",path="/health",status="200"} 1.0
# HELP cloudops_http_request_duration_seconds HTTP request latency
# TYPE cloudops_http_request_duration_seconds histogram
cloudops_http_request_duration_seconds_bucket{method="GET",path="/health",le="0.1"} 1.0
cloudops_http_request_duration_seconds_bucket{method="GET",path="/health",le="+Inf"} 1.0
cloudops_http_request_duration_seconds_sum{method="GET",path="/health"} 0.01
cloudops_http_request_duration_seconds_count{method="GET",path="/health"} 1.0
'''
JSON_PATHS = {'/', '/health', '/ready', '/api/v1/status', '/api/v1/info'}
ALL_PATHS = JSON_PATHS | {'/metrics'}


class FakeResponse:
    def __init__(self, status: int, content_type: str, body: bytes):
        self.status = status
        self.headers = Message()
        self.headers['Content-Type'] = content_type
        self.body = body

    def read(self, limit: int) -> bytes:
        return self.body[:limit]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class FakeOpener:
    def __init__(self, responses=None, failures=None, malformed=None):
        self.responses = responses or {}
        self.failures = failures or set()
        self.malformed = malformed or set()
        self.calls = []

    def open(self, request, timeout):
        path = urlsplit(request.full_url).path
        self.calls.append((request, timeout))
        if path in self.failures:
            raise URLError(TimeoutError('simulated timeout'))
        if path in self.malformed:
            raise http.client.BadStatusLine('sensitive malformed response')

        default = (200, 'application/json; charset=utf-8', JSON_BODY)
        if path == '/metrics':
            default = (200, 'text/plain; version=0.0.4; charset=utf-8', METRICS_BODY)
        status, content_type, body = self.responses.get(path, default)
        return FakeResponse(status, content_type, body)


def _run(base_url: str, opener: FakeOpener, timeout: float = 3.0) -> tuple[int, str, str]:
    from io import StringIO
    from unittest.mock import patch

    stdout = StringIO()
    stderr = StringIO()
    with patch('sys.stdout', stdout), patch('sys.stderr', stderr):
        result = demo_local.run(base_url, timeout, opener)
    return result, stdout.getvalue(), stderr.getvalue()


def test_local_demo_passes_six_mocked_endpoints_without_printing_bodies():
    opener = FakeOpener()

    code, stdout, stderr = _run('http://127.0.0.1:8000', opener)

    assert code == 0
    assert 'Demo result: 6 passed, 0 failed.' in stdout
    assert 'PASS /health (liveness): HTTP 200, application/json' in stdout
    assert 'PASS /ready (readiness): HTTP 200, application/json' in stdout
    assert 'PASS /metrics (metrics): HTTP 200, text/plain' in stdout
    assert len(opener.calls) == 6
    assert all(request.get_method() == 'GET' for request, _ in opener.calls)
    assert 'DEMO_RESPONSE_SECRET_SENTINEL' not in stdout + stderr


def test_local_demo_reports_unavailable_application_without_traceback():
    opener = FakeOpener(failures=ALL_PATHS)

    code, stdout, stderr = _run('http://127.0.0.1:8000', opener, timeout=0.1)

    assert code == 1
    assert 'FAIL / (metadata): unavailable or timed out' in stdout
    assert 'Demo result: 0 passed, 6 failed.' in stdout
    assert 'Traceback' not in stderr
    assert len(opener.calls) == 6


def test_local_demo_reports_unexpected_http_status_without_response_body():
    opener = FakeOpener({'/': (503, 'application/json', b'UPSTREAM_PASSWORD_SENTINEL')})

    code, stdout, stderr = _run('http://127.0.0.1:8000', opener)

    assert code == 1
    assert 'FAIL / (metadata): expected HTTP 200, received HTTP 503' in stdout
    assert 'UPSTREAM_PASSWORD_SENTINEL' not in stdout + stderr


def test_local_demo_rejects_unexpected_content_type_without_response_body():
    opener = FakeOpener(
        {'/api/v1/info': (200, 'text/html', b'HTML_SECRET_SENTINEL')}
    )

    code, stdout, stderr = _run('http://127.0.0.1:8000', opener)

    assert code == 1
    assert 'FAIL /api/v1/info (info): expected application/json content type' in stdout
    assert 'HTML_SECRET_SENTINEL' not in stdout + stderr


def test_local_demo_rejects_malformed_metrics():
    opener = FakeOpener(
        {'/metrics': (200, 'text/plain; version=0.0.4', b'this is not a Prometheus exposition')}
    )

    code, stdout, _ = _run('http://127.0.0.1:8000', opener)

    assert code == 1
    assert 'FAIL /metrics (metrics): metrics exposition is malformed' in stdout


def test_local_demo_rejects_remote_hosts_before_connecting():
    opener = FakeOpener()

    code, stdout, stderr = _run('http://example.com', opener)

    assert code == 2
    assert 'base URL host must be a numeric loopback IP address' in stderr
    assert not opener.calls
    assert 'example.com' not in stdout + stderr


def test_local_demo_handles_timeout_and_continues_to_remaining_endpoints():
    opener = FakeOpener(failures={'/ready'})

    code, stdout, _ = _run('http://127.0.0.1:8000', opener, timeout=0.1)

    assert code == 1
    assert 'PASS /health (liveness)' in stdout
    assert 'FAIL /ready (readiness): unavailable or timed out' in stdout
    assert 'PASS /api/v1/status' in stdout
    assert len(opener.calls) == 6


def test_local_demo_handles_malformed_http_without_exposing_error_details():
    opener = FakeOpener(malformed={'/api/v1/status'})

    code, stdout, stderr = _run('http://127.0.0.1:8000', opener)

    assert code == 1
    assert 'FAIL /api/v1/status (status): unavailable or timed out' in stdout
    assert 'sensitive malformed response' not in stdout + stderr
    assert 'Traceback' not in stderr


def test_local_demo_rejects_oversized_response_without_printing_body():
    oversized = b'x' * (demo_local.MAX_RESPONSE_BYTES + 1)
    opener = FakeOpener({'/api/v1/info': (200, 'application/json', oversized)})

    code, stdout, stderr = _run('http://127.0.0.1:8000', opener)

    assert code == 1
    assert 'FAIL /api/v1/info (info): response exceeded the' in stdout
    assert 'x' * 100 not in stdout + stderr


def test_default_http_opener_disables_proxies_and_redirects(monkeypatch):
    captured_handlers = []
    fake_opener = FakeOpener()

    def build_fake_opener(*handlers):
        captured_handlers.extend(handlers)
        return fake_opener

    monkeypatch.setattr(demo_local, 'build_opener', build_fake_opener)
    code, stdout, stderr = _run('http://127.0.0.1:8000', None)

    proxy_handlers = [
        handler for handler in captured_handlers if isinstance(handler, ProxyHandler)
    ]
    redirect_handlers = [
        handler
        for handler in captured_handlers
        if isinstance(handler, demo_local.NoRedirectHandler)
    ]
    assert code == 0
    assert not stderr
    assert 'Demo result: 6 passed, 0 failed.' in stdout
    assert len(proxy_handlers) == 1
    assert proxy_handlers[0].proxies == {}
    assert len(redirect_handlers) == 1
    assert redirect_handlers[0].redirect_request(
        None, None, 302, 'Found', {}, 'http://example.com/'
    ) is None


def test_demo_shell_wrapper_runs_from_another_directory_and_rejects_remote_url(tmp_path):
    help_result = subprocess.run(
        [str(DEMO_SCRIPT), '--help'],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    remote_result = subprocess.run(
        [str(DEMO_SCRIPT), '--base-url', 'http://example.com'],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert help_result.returncode == 0
    assert '--base-url' in help_result.stdout
    assert remote_result.returncode == 2
    assert 'base URL host must be a numeric loopback IP address' in remote_result.stderr
    assert 'example.com' not in remote_result.stdout + remote_result.stderr
