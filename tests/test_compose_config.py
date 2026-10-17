"""Offline Compose configuration checks; these tests never invoke Docker."""

import re
from pathlib import Path

import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = REPOSITORY_ROOT / 'docker-compose.yml'
PRODUCTION_DOCKERFILE = REPOSITORY_ROOT / 'Dockerfile'


def _compose_config() -> dict:
    return yaml.safe_load(COMPOSE_FILE.read_text(encoding='utf-8'))


def _app_service() -> dict:
    services = _compose_config()['services']
    assert set(services) == {'app'}
    return services['app']


def test_compose_keeps_the_existing_app_service_and_production_build_context():
    service = _app_service()
    build = service['build']

    if isinstance(build, str):
        context = build
        dockerfile = 'Dockerfile'
    else:
        context = build['context']
        dockerfile = build.get('dockerfile', 'Dockerfile')

    assert context in {'.', './'}
    assert dockerfile == 'Dockerfile'
    assert service['ports'] == ['127.0.0.1:8000:8000']


def test_compose_keeps_read_only_filesystem_and_temporary_path():
    service = _app_service()
    tmpfs = service.get('tmpfs', [])
    tmpfs_paths = {tmpfs} if isinstance(tmpfs, str) else {entry.split(':', 1)[0] for entry in tmpfs}

    assert service['read_only'] is True
    assert '/tmp' in tmpfs_paths


def test_compose_drops_all_capabilities_and_does_not_enable_privilege_or_host_access():
    service = _app_service()

    assert service['cap_drop'] == ['ALL']
    assert service.get('privileged', False) is not True
    assert not service.get('cap_add')
    assert service.get('network_mode') != 'host'
    for mount in service.get('volumes', []):
        if isinstance(mount, dict):
            assert mount.get('type', 'volume') != 'bind'
            continue

        fields = mount.split(':')
        if len(fields) > 1:
            source = fields[0]
            assert not source.startswith(('/', '.', '~'))
            assert re.match(r'^[A-Za-z]:[\\/]', source) is None


def test_compose_does_not_override_the_non_root_image_user():
    service = _app_service()

    assert service.get('user') in (None, '10001:10001')


def test_compose_disables_privilege_escalation():
    service = _app_service()

    assert 'no-new-privileges:true' in service['security_opt']


def test_compose_inherits_the_bounded_production_healthcheck():
    service = _app_service()
    assert service.get('healthcheck', {}).get('disable') is not True

    healthchecks = [
        line.strip()
        for line in PRODUCTION_DOCKERFILE.read_text(encoding='utf-8').splitlines()
        if line.strip().startswith('HEALTHCHECK ')
    ]
    assert len(healthchecks) == 1
    healthcheck = healthchecks[0]
    assert '--timeout=5s' in healthcheck
    assert 'http://127.0.0.1:8000/health' in healthcheck


def test_compose_environment_contains_only_nonsecret_application_metadata():
    service = _app_service()
    environment = service.get('environment', {})
    variables = (
        environment
        if isinstance(environment, dict)
        else dict(entry.split('=', 1) for entry in environment)
    )
    names = set(variables)

    assert names == {'APP_NAME', 'APP_VERSION', 'ENVIRONMENT'}
    assert variables == {
        'APP_NAME': 'CloudOps Platform',
        'APP_VERSION': '1.0.0',
        'ENVIRONMENT': 'docker',
    }
    assert not service.get('env_file')
    assert not service.get('secrets')
    assert not _compose_config().get('secrets')
    assert all(
        re.search(r'(?:PASSWORD|TOKEN|SECRET|CREDENTIAL|API_KEY)', name, re.IGNORECASE) is None
        for name in names
    )
