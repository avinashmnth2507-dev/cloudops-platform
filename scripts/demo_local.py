"""Safe, bounded checks for an already-running loopback CloudOps application."""

import argparse
import http.client
import ipaddress
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from prometheus_client.parser import text_string_to_metric_families

DEFAULT_BASE_URL = 'http://127.0.0.1:8000'
MAX_TIMEOUT_SECONDS = 30.0
MAX_RESPONSE_BYTES = 1024 * 1024
REQUIRED_METRIC_SAMPLES = {
    'cloudops_http_requests_total',
    'cloudops_http_request_duration_seconds_bucket',
}
ENDPOINTS = (
    ('/', 'application/json', 'metadata'),
    ('/health', 'application/json', 'liveness'),
    ('/ready', 'application/json', 'readiness'),
    ('/api/v1/status', 'application/json', 'status'),
    ('/api/v1/info', 'application/json', 'info'),
    ('/metrics', 'text/plain', 'metrics'),
)


class NoRedirectHandler(HTTPRedirectHandler):
    """Do not let a local endpoint redirect this check to a remote host."""

    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def _base_url(value: str) -> str:
    try:
        parts = urlsplit(value)
        host = parts.hostname
        port = parts.port
    except ValueError as error:
        raise ValueError('base URL is malformed') from error

    if (
        parts.scheme != 'http'
        or host is None
        or parts.username is not None
        or parts.password is not None
        or parts.path not in ('', '/')
        or '?' in value
        or '#' in value
    ):
        raise ValueError('use an HTTP loopback base URL without credentials, path, or query')

    try:
        address = ipaddress.ip_address(host)
    except ValueError as error:
        raise ValueError('base URL host must be a numeric loopback IP address') from error

    if not address.is_loopback:
        raise ValueError('base URL host must be a loopback IP address')
    if port is not None and not 1 <= port <= 65535:
        raise ValueError('base URL port must be between 1 and 65535')

    normalized_host = f'[{host}]' if address.version == 6 else host
    netloc = normalized_host if port is None else f'{normalized_host}:{port}'
    return urlunsplit(('http', netloc, '', '', ''))


def _validate_timeout(value: float) -> float:
    if not 0.05 <= value <= MAX_TIMEOUT_SECONDS:
        raise ValueError(f'timeout must be between 0.05 and {MAX_TIMEOUT_SECONDS:g} seconds')
    return value


def _response(opener, url: str, timeout: float):
    request = Request(
        url,
        headers={
            'Accept': 'application/json, text/plain; version=0.0.4',
            'User-Agent': 'cloudops-local-demo/1.0',
        },
        method='GET',
    )
    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1) if response.status == 200 else b''
            return response.status, response.headers, body, None
    except HTTPError as error:
        error.close()
        return error.code, error.headers, b'', None
    except (TimeoutError, URLError, OSError, http.client.HTTPException):
        return None, None, b'', 'unavailable or timed out'


def _check_response(path: str, expected_type: str, body: bytes, headers) -> str | None:
    if len(body) > MAX_RESPONSE_BYTES:
        return f'response exceeded the {MAX_RESPONSE_BYTES}-byte limit'

    content_header = headers.get('Content-Type')
    content_type = (
        content_header.split(';', maxsplit=1)[0].strip().lower() if content_header else ''
    )
    allowed_types = (
        {'text/plain', 'application/openmetrics-text'}
        if path == '/metrics'
        else {expected_type}
    )
    if content_type not in allowed_types:
        return f'expected {expected_type} content type'

    if path == '/metrics':
        try:
            exposition = body.decode('utf-8')
            sample_names = {
                sample.name
                for family in text_string_to_metric_families(exposition)
                for sample in family.samples
            }
        except (UnicodeDecodeError, ValueError, TypeError):
            return 'metrics exposition is malformed'
        missing = REQUIRED_METRIC_SAMPLES - sample_names
        if missing:
            return 'metrics exposition is malformed or missing required request series'
        return None

    try:
        json.loads(body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return 'response body is not valid JSON'
    return None


def run(base_url: str, timeout: float, opener=None) -> int:
    try:
        normalized_url = _base_url(base_url)
        timeout = _validate_timeout(timeout)
    except ValueError as error:
        print(f'FAIL: {error}', file=sys.stderr)
        return 2

    if opener is None:
        opener = build_opener(ProxyHandler({}), NoRedirectHandler())
    passed = 0
    failed = 0
    print(f'Checking existing application at {normalized_url}')

    for path, expected_type, label in ENDPOINTS:
        status, headers, body, transport_error = _response(
            opener, f'{normalized_url}{path}', timeout
        )
        if transport_error:
            print(f'FAIL {path} ({label}): {transport_error}')
            failed += 1
            continue
        if status != 200:
            print(f'FAIL {path} ({label}): expected HTTP 200, received HTTP {status}')
            failed += 1
            continue

        error = _check_response(path, expected_type, body, headers)
        if error:
            print(f'FAIL {path} ({label}): {error}')
            failed += 1
            continue

        print(f'PASS {path} ({label}): HTTP 200, {expected_type}')
        passed += 1

    print(f'Demo result: {passed} passed, {failed} failed.')
    return 0 if failed == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Check an already-running CloudOps application on loopback only.'
    )
    parser.add_argument('--base-url', default=DEFAULT_BASE_URL)
    parser.add_argument('--timeout', type=float, default=3.0)
    args = parser.parse_args()
    return run(args.base_url, args.timeout)


if __name__ == '__main__':
    raise SystemExit(main())
