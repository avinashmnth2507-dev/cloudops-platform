import asyncio
import json
import uuid
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app import main as app_main
from app.main import app, request_logging_and_metrics_middleware

client = TestClient(app)

def test_root():
    r = client.get('/')
    assert r.status_code == 200
    assert r.headers['content-type'].startswith('application/json')
    assert r.json() == {
        'service': app_main.settings.app_name,
        'version': app_main.settings.app_version,
        'environment': app_main.settings.environment,
    }

def test_health():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('application/json')
    assert response.json() == {'status': 'healthy'}

def test_ready():
    response = client.get('/ready')
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('application/json')
    assert response.json() == {'status': 'ready'}

def test_status():
    response = client.get('/api/v1/status')
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('application/json')
    assert response.json() == {
        'service': app_main.settings.app_name,
        'status': 'operational',
        'version': app_main.settings.app_version,
    }

def test_info():
    response = client.get('/api/v1/info')

    assert response.status_code == 200
    assert response.headers['content-type'].startswith('application/json')

    body = response.json()
    assert set(body) == {'name', 'version', 'environment', 'uptime_seconds'}
    assert body['name'] == app_main.settings.app_name
    assert body['version'] == app_main.settings.app_version
    assert body['environment'] == app_main.settings.environment
    assert isinstance(body['uptime_seconds'], (int, float))
    assert body['uptime_seconds'] >= 0

def test_metrics():
    client.get('/health')
    r = client.get('/metrics')
    assert r.status_code == 200
    assert r.headers['content-type'].startswith('text/plain')
    assert 'cloudops_http_requests_total' in r.text
    assert 'cloudops_http_request_duration_seconds_bucket' in r.text
    assert 'path="/health"' in r.text


def _request_events(output: str) -> list[dict]:
    return [json.loads(line) for line in output.splitlines() if line]


def _metric_value(metrics_text: str, metric_name: str, labels: dict[str, str]) -> float:
    label_text = ','.join(f'{key}="{value}"' for key, value in labels.items())
    prefix = f'{metric_name}{{{label_text}}} '
    for line in metrics_text.splitlines():
        if line.startswith(prefix):
            return float(line.removeprefix(prefix))
    return 0.0


def _make_request(path: str = '/internal') -> Request:
    return Request(
        {
            'type': 'http',
            'asgi': {'version': '3.0'},
            'http_version': '1.1',
            'method': 'GET',
            'scheme': 'http',
            'path': path,
            'raw_path': path.encode(),
            'query_string': b'',
            'root_path': '',
            'headers': [],
            'client': ('test-client', 1234),
            'server': ('test-server', 80),
            'state': {},
        }
    )


def _patch_instrumentation(
    monkeypatch, *, counter_error=None, histogram_error=None, logger_error=None
):
    counter_child = Mock()
    histogram_child = Mock()
    if counter_error is not None:
        counter_child.inc.side_effect = counter_error
    if histogram_error is not None:
        histogram_child.observe.side_effect = histogram_error
    logger = Mock(side_effect=logger_error)

    monkeypatch.setattr(app_main.REQUEST_COUNT, 'labels', Mock(return_value=counter_child))
    monkeypatch.setattr(app_main.REQUEST_LATENCY, 'labels', Mock(return_value=histogram_child))
    monkeypatch.setattr(app_main.request_logger, 'info', logger)
    return counter_child, histogram_child, logger


def test_request_log_is_structured_and_contains_required_fields(capsys):
    before_metrics = client.get('/metrics').text
    before_count = _metric_value(
        before_metrics,
        'cloudops_http_requests_total',
        {'method': 'GET', 'path': '/health', 'status': '200'},
    )
    before_observations = _metric_value(
        before_metrics,
        'cloudops_http_request_duration_seconds_count',
        {'method': 'GET', 'path': '/health'},
    )
    capsys.readouterr()

    response = client.get('/health')

    events = _request_events(capsys.readouterr().out)
    after_metrics = client.get('/metrics').text
    assert response.status_code == 200
    assert len(events) == 1
    event = events[0]
    assert event['event'] == 'http_request_completed'
    assert uuid.UUID(event['request_id'])
    assert event['method'] == 'GET'
    assert event['route'] == '/health'
    assert event['status_code'] == response.status_code
    assert isinstance(event['duration_ms'], (int, float))
    assert event['duration_ms'] >= 0
    assert _metric_value(
        after_metrics,
        'cloudops_http_requests_total',
        {'method': 'GET', 'path': '/health', 'status': '200'},
    ) - before_count == 1
    assert _metric_value(
        after_metrics,
        'cloudops_http_request_duration_seconds_count',
        {'method': 'GET', 'path': '/health'},
    ) - before_observations == 1


def test_request_ids_are_unique(capsys):
    client.get('/health')
    client.get('/ready')

    events = _request_events(capsys.readouterr().out)
    assert len(events) == 2
    assert len({event['request_id'] for event in events}) == 2


def test_unknown_route_uses_fallback_and_logs_no_sensitive_values(capsys):
    sensitive_values = (
        'raw-path-secret',
        'query-token-secret',
        'authorization-secret',
        'cookie-secret',
        'client-request-id-secret',
    )
    response = client.get(
        f'/private-{sensitive_values[0]}?api_key={sensitive_values[1]}',
        headers={
            'Authorization': f'Bearer {sensitive_values[2]}',
            'Cookie': f'session={sensitive_values[3]}',
            'X-Request-ID': sensitive_values[4],
        },
    )

    output = capsys.readouterr().out
    events = _request_events(output)
    assert response.status_code == 404
    assert response.headers['content-type'].startswith('application/json')
    assert response.json() == {'detail': 'Not Found'}
    assert len(events) == 1
    assert events[0]['route'] == 'unmatched'
    assert events[0]['status_code'] == 404
    assert events[0]['request_id'] != sensitive_values[4]
    for secret in sensitive_values:
        assert secret not in output


def test_unknown_paths_share_bounded_metric_labels_and_exclude_secrets(capsys):
    before_metrics = client.get('/metrics').text
    before_get_count = _metric_value(
        before_metrics,
        'cloudops_http_requests_total',
        {'method': 'GET', 'path': 'unmatched', 'status': '404'},
    )
    before_post_count = _metric_value(
        before_metrics,
        'cloudops_http_requests_total',
        {'method': 'POST', 'path': 'unmatched', 'status': '404'},
    )
    capsys.readouterr()
    sensitive_values = (
        'metric-path-secret-one',
        'metric-path-secret-two',
        'metric-path-secret-three',
        'metric-query-secret',
        'metric-authorization-secret',
        'metric-cookie-secret',
        'metric-body-secret',
    )

    first = client.get(
        f'/{sensitive_values[0]}?token={sensitive_values[3]}',
        headers={
            'Authorization': f'Bearer {sensitive_values[4]}',
            'Cookie': f'session={sensitive_values[5]}',
        },
    )
    second = client.get(f'/{sensitive_values[1]}')
    third = client.post(
        f'/{sensitive_values[2]}',
        content=sensitive_values[6],
    )
    metrics_response = client.get('/metrics')

    output = capsys.readouterr().out
    events = _request_events(output)
    metrics_text = metrics_response.text
    assert (first.status_code, second.status_code, third.status_code) == (404, 404, 404)
    assert _metric_value(
        metrics_text,
        'cloudops_http_requests_total',
        {'method': 'GET', 'path': 'unmatched', 'status': '404'},
    ) - before_get_count == 2
    assert _metric_value(
        metrics_text,
        'cloudops_http_requests_total',
        {'method': 'POST', 'path': 'unmatched', 'status': '404'},
    ) - before_post_count == 1
    assert 'cloudops_http_request_duration_seconds_count{method="GET",path="unmatched"}' in (
        metrics_text
    )
    assert len(events) == 4
    assert [event['route'] for event in events[:3]] == ['unmatched'] * 3
    for secret in sensitive_values:
        assert secret not in output
        assert secret not in metrics_text


def test_unusual_http_methods_use_bounded_metric_labels(capsys):
    before_metrics = client.get('/metrics').text
    before_other_count = _metric_value(
        before_metrics,
        'cloudops_http_requests_total',
        {'method': 'OTHER', 'path': '/health', 'status': '405'},
    )
    before_other_observations = _metric_value(
        before_metrics,
        'cloudops_http_request_duration_seconds_count',
        {'method': 'OTHER', 'path': '/health'},
    )
    capsys.readouterr()

    unusual_methods = ('BREW', 'PURGE')
    responses = [client.request(method, '/health') for method in unusual_methods]

    output = capsys.readouterr().out
    events = _request_events(output)
    metrics_text = client.get('/metrics').text
    assert [response.status_code for response in responses] == [405, 405]
    assert len(events) == len(unusual_methods)
    assert [event['method'] for event in events] == ['OTHER', 'OTHER']
    assert [event['route'] for event in events] == ['/health', '/health']
    assert _metric_value(
        metrics_text,
        'cloudops_http_requests_total',
        {'method': 'OTHER', 'path': '/health', 'status': '405'},
    ) - before_other_count == len(unusual_methods)
    assert _metric_value(
        metrics_text,
        'cloudops_http_request_duration_seconds_count',
        {'method': 'OTHER', 'path': '/health'},
    ) - before_other_observations == len(unusual_methods)
    for method in unusual_methods:
        assert f'method="{method}"' not in metrics_text


def test_unhandled_exception_is_logged_as_500_without_exception_details(capsys):
    request = _make_request()
    before_metrics = client.get('/metrics').text
    before_error_count = _metric_value(
        before_metrics,
        'cloudops_http_requests_total',
        {'method': 'GET', 'path': 'unmatched', 'status': '500'},
    )
    before_observations = _metric_value(
        before_metrics,
        'cloudops_http_request_duration_seconds_count',
        {'method': 'GET', 'path': 'unmatched'},
    )
    capsys.readouterr()

    async def fail(_request):
        raise RuntimeError('Authorization: Bearer exception-secret')

    with pytest.raises(RuntimeError):
        asyncio.run(request_logging_and_metrics_middleware(request, fail))

    output = capsys.readouterr().out
    events = _request_events(output)
    after_metrics = client.get('/metrics').text
    assert len(events) == 1
    assert events[0]['status_code'] == 500
    assert events[0]['route'] == 'unmatched'
    assert 'exception-secret' not in output
    assert _metric_value(
        after_metrics,
        'cloudops_http_requests_total',
        {'method': 'GET', 'path': 'unmatched', 'status': '500'},
    ) - before_error_count == 1
    assert _metric_value(
        after_metrics,
        'cloudops_http_request_duration_seconds_count',
        {'method': 'GET', 'path': 'unmatched'},
    ) - before_observations == 1


def test_counter_failure_does_not_affect_success_or_other_instrumentation(monkeypatch):
    counter, histogram, logger = _patch_instrumentation(
        monkeypatch,
        counter_error=RuntimeError('counter-failure-secret'),
    )

    response = client.get('/health')

    assert response.status_code == 200
    counter.inc.assert_called_once()
    histogram.observe.assert_called_once()
    logger.assert_called_once()
    event_json = logger.call_args.args[0]
    assert json.loads(event_json)['status_code'] == 200
    assert 'counter-failure-secret' not in event_json


def test_histogram_failure_does_not_affect_success_or_other_instrumentation(monkeypatch):
    counter, histogram, logger = _patch_instrumentation(
        monkeypatch,
        histogram_error=RuntimeError('histogram-failure-secret'),
    )

    response = client.get('/health')

    assert response.status_code == 200
    counter.inc.assert_called_once()
    histogram.observe.assert_called_once()
    logger.assert_called_once()
    event_json = logger.call_args.args[0]
    assert json.loads(event_json)['status_code'] == 200
    assert 'histogram-failure-secret' not in event_json


def test_logger_failure_does_not_affect_success_or_metrics(monkeypatch):
    counter, histogram, logger = _patch_instrumentation(
        monkeypatch,
        logger_error=RuntimeError('logger-failure-secret'),
    )

    response = client.get('/health')

    assert response.status_code == 200
    counter.inc.assert_called_once()
    histogram.observe.assert_called_once()
    logger.assert_called_once()
    event_json = logger.call_args.args[0]
    assert json.loads(event_json)['status_code'] == 200
    assert 'logger-failure-secret' not in event_json


def test_json_serialization_failure_does_not_affect_success(monkeypatch):
    counter, histogram, logger = _patch_instrumentation(monkeypatch)
    failing_json = Mock()
    failing_json.dumps.side_effect = RuntimeError('serialization-failure-secret')
    monkeypatch.setattr(app_main, 'json', failing_json)

    response = client.get('/health')

    assert response.status_code == 200
    counter.inc.assert_called_once()
    histogram.observe.assert_called_once()
    failing_json.dumps.assert_called_once()
    logger.assert_not_called()


def test_all_instrumentation_failures_preserve_application_exception(monkeypatch):
    counter, histogram, logger = _patch_instrumentation(
        monkeypatch,
        counter_error=RuntimeError('counter-failure-secret'),
        histogram_error=RuntimeError('histogram-failure-secret'),
        logger_error=RuntimeError('logger-failure-secret'),
    )
    request = _make_request()
    original_error = RuntimeError('original application failure secret')

    async def fail(_request):
        raise original_error

    with pytest.raises(RuntimeError) as caught:
        asyncio.run(request_logging_and_metrics_middleware(request, fail))

    assert caught.value is original_error
    counter.inc.assert_called_once()
    histogram.observe.assert_called_once()
    logger.assert_called_once()
    event_json = logger.call_args.args[0]
    event = json.loads(event_json)
    assert event['status_code'] == 500
    for secret in (
        'counter-failure-secret',
        'histogram-failure-secret',
        'logger-failure-secret',
        'original application failure secret',
    ):
        assert secret not in event_json
