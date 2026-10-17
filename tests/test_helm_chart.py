import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CHART = REPOSITORY_ROOT / 'helm' / 'cloudops'
HELM = shutil.which('helm')

pytestmark = pytest.mark.skipif(HELM is None, reason='Helm CLI is not installed')


def _helm_template(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [HELM, 'template', 'cloudops', str(CHART), *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )


def _resources(rendered: str) -> list[dict]:
    return [document for document in yaml.safe_load_all(rendered) if document]


def test_helm_lint_passes_for_default_chart():
    result = subprocess.run(
        [HELM, 'lint', str(CHART)],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_default_helm_render_has_consistent_service_deployment_and_security():
    result = _helm_template()

    assert result.returncode == 0, result.stderr
    resources = _resources(result.stdout)
    by_kind = {resource['kind']: resource for resource in resources}
    deployment = by_kind['Deployment']
    service = by_kind['Service']
    pod = deployment['spec']['template']
    container = pod['spec']['containers'][0]

    assert deployment['spec']['selector']['matchLabels'] == pod['metadata']['labels']
    assert service['spec']['selector'] == deployment['spec']['selector']['matchLabels']
    assert service['spec']['ports'][0]['targetPort'] == container['ports'][0]['containerPort']
    assert container['ports'][0]['name'] == service['spec']['ports'][0]['name'] == 'http'
    assert container['livenessProbe']['httpGet']['path'] == '/health'
    assert container['readinessProbe']['httpGet']['path'] == '/ready'
    assert pod['spec']['securityContext']['seccompProfile']['type'] == 'RuntimeDefault'
    security = container['securityContext']
    assert security['runAsNonRoot'] is True
    assert security['runAsUser'] == security['runAsGroup'] == 10001
    assert security['allowPrivilegeEscalation'] is False
    assert security['capabilities']['drop'] == ['ALL']
    assert security['readOnlyRootFilesystem'] is True
    assert 'NetworkPolicy' not in {resource['kind'] for resource in resources}
    assert 'ServiceMonitor' not in {resource['kind'] for resource in resources}
    assert 'Ingress' not in {resource['kind'] for resource in resources}


def test_network_policy_enabled_without_verified_selectors_fails_closed():
    result = _helm_template('--set', 'networkPolicy.enabled=true')

    assert result.returncode != 0
    assert 'requires a non-empty networkPolicy.ingressController.namespaceSelector' in (
        result.stderr
    )


@pytest.mark.parametrize(
    'arguments',
    [
        ('--set', 'service.port=0'),
        ('--set', 'containerPort=not-a-port'),
        ('--set', 'service.type=ExternalName'),
        ('--set', 'ingress.enabled=true', '--set', 'ingress.host='),
        ('--set', 'resources.requests.cpu=not-a-quantity'),
        ('--set', 'resources.limits.memory=not-a-quantity'),
        ('--set', 'hpa.minReplicas=5', '--set', 'hpa.maxReplicas=2'),
    ],
)
def test_invalid_or_incomplete_critical_values_fail_chart_validation(arguments):
    result = _helm_template(*arguments)

    assert result.returncode != 0


def test_zero_replicas_are_allowed_when_hpa_is_disabled():
    result = _helm_template('--set', 'hpa.enabled=false', '--set', 'replicaCount=0')

    assert result.returncode == 0, result.stderr
    deployment = next(
        resource for resource in _resources(result.stdout) if resource['kind'] == 'Deployment'
    )
    assert deployment['spec']['replicas'] == 0


def test_network_policy_with_monitoring_requires_prometheus_identity(tmp_path):
    values = {
        'networkPolicy': {
            'enabled': True,
            'ingressController': {
                'namespaceSelector': {'matchLabels': {'kubernetes.io/metadata.name': 'ingress'}},
                'podSelector': {'matchLabels': {'app': 'ingress-controller'}},
            },
        },
        'monitoring': {'serviceMonitor': {'enabled': True}},
    }
    values_file = tmp_path / 'values.yaml'
    values_file.write_text(yaml.safe_dump(values), encoding='utf-8')

    result = _helm_template('--values', str(values_file))

    assert result.returncode != 0
    assert 'requires a non-empty networkPolicy.prometheus.namespaceSelector' in result.stderr


def test_enabled_service_monitor_and_policy_render_explicit_scrape_identity(tmp_path):
    values = {
        'networkPolicy': {
            'enabled': True,
            'ingressController': {
                'namespaceSelector': {'matchLabels': {'kubernetes.io/metadata.name': 'ingress'}},
                'podSelector': {'matchLabels': {'app': 'ingress-controller'}},
            },
            'prometheus': {
                'namespaceSelector': {'matchLabels': {'kubernetes.io/metadata.name': 'monitoring'}},
                'podSelector': {'matchLabels': {'app': 'prometheus'}},
            },
        },
        'monitoring': {'serviceMonitor': {'enabled': True}},
    }
    values_file = tmp_path / 'values.yaml'
    values_file.write_text(yaml.safe_dump(values), encoding='utf-8')

    result = _helm_template('--values', str(values_file))

    assert result.returncode == 0, result.stderr
    resources = _resources(result.stdout)
    monitor = next(resource for resource in resources if resource['kind'] == 'ServiceMonitor')
    policy = next(resource for resource in resources if resource['kind'] == 'NetworkPolicy')
    service = next(resource for resource in resources if resource['kind'] == 'Service')

    assert monitor['spec']['selector']['matchLabels'] == service['metadata']['labels']
    endpoint = monitor['spec']['endpoints'][0]
    assert endpoint['port'] == service['spec']['ports'][0]['name'] == 'http'
    assert endpoint['path'] == '/metrics'
    assert monitor['metadata']['labels']['release'] == 'monitoring'
    assert len(policy['spec']['ingress']) == 2
    assert policy['spec']['ingress'][1]['from'][0]['namespaceSelector'] == values[
        'networkPolicy'
    ]['prometheus']['namespaceSelector']
    assert policy['spec']['ingress'][1]['from'][0]['podSelector'] == values[
        'networkPolicy'
    ]['prometheus']['podSelector']


def test_values_schema_is_valid_json():
    schema_path = CHART / 'values.schema.json'

    assert json.loads(schema_path.read_text(encoding='utf-8'))['$schema'].endswith(
        'draft-07/schema#'
    )
