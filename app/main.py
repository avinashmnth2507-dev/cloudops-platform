import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .config import settings
from .metrics import REQUEST_COUNT, REQUEST_LATENCY

START_TIME = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

@app.middleware('http')
async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    path = request.url.path
    REQUEST_COUNT.labels(request.method, path, response.status_code).inc()
    REQUEST_LATENCY.labels(request.method, path).observe(elapsed)
    return response

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
