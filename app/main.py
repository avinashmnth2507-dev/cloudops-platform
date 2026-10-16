import json
import logging
import sys
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .config import settings
from .metrics import REQUEST_COUNT, REQUEST_LATENCY

START_TIME = time.time()
ROUTE_LABELS = frozenset(
    {'/', '/health', '/ready', '/api/v1/status', '/api/v1/info', '/metrics'}
)
HTTP_METHODS = frozenset(
    {'GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'TRACE', 'CONNECT'}
)


class StdoutRequestHandler(logging.StreamHandler):
    def emit(self, record: logging.LogRecord) -> None:
        self.stream = sys.stdout
        super().emit(record)


request_logger = logging.getLogger('cloudops.request')
request_logger.setLevel(logging.INFO)
request_logger.propagate = False
if not request_logger.handlers:
    request_handler = StdoutRequestHandler(sys.stdout)
    request_handler.setFormatter(logging.Formatter('%(message)s'))
    request_logger.addHandler(request_handler)


def _route_label(request: Request) -> str:
    route = request.scope.get('route')
    template = getattr(route, 'path', None)
    if template in ROUTE_LABELS:
        return template

    # Router metadata may not be available for unmatched routes. Exact matches
    # are safe here; arbitrary paths always fall back to one bounded value.
    path = request.scope.get('path')
    if path in ROUTE_LABELS:
        return path
    return 'unmatched'


def _method_label(request: Request) -> str:
    method = request.method.upper()
    return method if method in HTTP_METHODS else 'OTHER'

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

@app.middleware('http')
async def request_logging_and_metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    method = _method_label(request)
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception:
        # Keep the default 500 status and omit exception text and traceback,
        # which may contain credentials or request data.
        raise
    finally:
        elapsed = time.perf_counter() - start
        route = _route_label(request)
        try:
            REQUEST_COUNT.labels(request.method, route, status_code).inc()
        except Exception:
            # Instrumentation is best-effort; do not log its own failures.
            pass

        try:
            REQUEST_LATENCY.labels(request.method, route).observe(elapsed)
        except Exception:
            pass

        try:
            event = {
                'event': 'http_request_completed',
                'request_id': request_id,
                'method': method,
                'route': route,
                'status_code': status_code,
                'duration_ms': round(elapsed * 1000, 3),
            }
            request_logger.info(json.dumps(event, separators=(',', ':'), sort_keys=True))
        except Exception:
            # Avoid recursive logging and preserve the application response/error.
            pass

@app.get('/')
def root():
    return {
        'service': settings.app_name,
        'version': settings.app_version,
        'environment': settings.environment,
    }

@app.get('/health')
def health():
    return {'status': 'healthy'}

@app.get('/ready')
def ready():
    return {'status': 'ready'}

@app.get('/api/v1/status')
def status():
    return {'service': settings.app_name, 'status': 'operational', 'version': settings.app_version}

@app.get('/api/v1/info')
def info():
    return {
        'name': settings.app_name,
        'version': settings.app_version,
        'environment': settings.environment,
        'uptime_seconds': round(time.time() - START_TIME, 2),
    }

@app.get('/metrics')
def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
