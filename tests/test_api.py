from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_root():
    r = client.get('/')
    assert r.status_code == 200
    assert r.json()['service'] == 'CloudOps Platform'

def test_health():
    assert client.get('/health').json() == {'status': 'healthy'}

def test_ready():
    assert client.get('/ready').json() == {'status': 'ready'}

def test_status():
    assert client.get('/api/v1/status').status_code == 200

def test_metrics():
    r = client.get('/metrics')
    assert r.status_code == 200
    assert 'cloudops_http_requests_total' in r.text
