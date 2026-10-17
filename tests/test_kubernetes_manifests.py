import json
import re
from pathlib import Path

import yaml

from app.main import app
from app.metrics import REQUEST_COUNT, REQUEST_LATENCY

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
K8S = REPOSITORY_ROOT / 'k8s'
NAMESPACE = 'cloudops'


def _load_yaml(path: Path) -> dict:
    with path.open(encoding='utf-8') as source:
        return yaml.safe_load(source)


def _load_yaml_documents(path: Path) -> list[dict]:
    with path.open(encoding='utf-8') as source:
        return [document for document in yaml.safe_load_all(source) if document]


def test_repository_kubernetes_and_monitoring_yaml_parses_offline():
    paths = [*K8S.rglob('*.yaml'), *(REPOSITORY_ROOT / 'monitoring').rglob('*.yaml')]

    assert paths
    for path in paths:
        with path.open(encoding='utf-8') as source:
            documents = [document for document in yaml.safe_load_all(source) if document]
        assert documents, f'{path.relative_to(REPOSITORY_ROOT)} contains no YAML documents'


def test_application_namespace_references_are_consistent():
    namespace = _load_yaml(K8S / 'namespace.yaml')
    assert namespace['metadata']['name'] == NAMESPACE

    namespaced_files = (
        'configmap.yaml',
        'deployment.yaml',
        'service.yaml',
        'ingress.yaml',
        'hpa.yaml',
        'networkpolicy.yaml',
        'serviceaccount.yaml',
    )
    for filename in namespaced_files:
        resources = _load_yaml_documents(K8S / filename)
        assert resources
        assert all(resource['metadata']['namespace'] == NAMESPACE for resource in resources), (
            filename
        )

    deployment = _load_yaml(K8S / 'deployment.yaml')
    config_map_name = deployment['spec']['template']['spec']['containers'][0]['envFrom'][0][
        'configMapRef'
    ]['name']
    config_map = _load_yaml(K8S / 'configmap.yaml')
    assert config_map_name == config_map['metadata']['name']


def test_deployment_service_and_ingress_selectors_and_ports_match():
    deployment = _load_yaml(K8S / 'deployment.yaml')
    service = _load_yaml(K8S / 'service.yaml')
    ingress = _load_yaml(K8S / 'ingress.yaml')
    selector = deployment['spec']['selector']['matchLabels']
    pod_labels = deployment['spec']['template']['metadata']['labels']
    container = deployment['spec']['template']['spec']['containers'][0]
    named_ports = {port['name']: port['containerPort'] for port in container['ports']}
    service_port = service['spec']['ports'][0]

    assert selector == pod_labels
    assert service['spec']['selector'] == selector
    assert service_port['targetPort'] == named_ports['http']
    assert ingress['spec']['rules'][0]['http']['paths'][0]['backend']['service'] == {
        'name': service['metadata']['name'],
        'port': {'number': service_port['port']},
    }


def test_standalone_deployment_has_no_default_image():
    deployment = _load_yaml(K8S / 'deployment.yaml')
    container = deployment['spec']['template']['spec']['containers'][0]

    assert container['image'] == ''


def test_probe_routes_exist_in_the_fastapi_application():
    deployment = _load_yaml(K8S / 'deployment.yaml')
    container = deployment['spec']['template']['spec']['containers'][0]
    application_routes = {route.path for route in app.routes if getattr(route, 'path', None)}

    probe_paths = {
        container['livenessProbe']['httpGet']['path'],
        container['readinessProbe']['httpGet']['path'],
    }
    assert probe_paths == {'/health', '/ready'}
    assert probe_paths <= application_routes
    assert all(
        probe['httpGet']['port'] == 'http'
        for probe in (container['livenessProbe'], container['readinessProbe'])
    )


def _quantity(value: str, resource: str) -> float:
    units = {'': 1, 'm': 0.001} if resource == 'cpu' else {
        'Ki': 1024,
        'Mi': 1024**2,
        'Gi': 1024**3,
    }
    match = re.fullmatch(r'([0-9]+(?:\.[0-9]+)?)(m|Ki|Mi|Gi)?', str(value))
    assert match, f'unsupported resource quantity: {value}'
    amount, suffix = match.groups()
    assert suffix in units
    return float(amount) * units[suffix]


def test_resource_requests_are_positive_and_do_not_exceed_limits():
    deployment = _load_yaml(K8S / 'deployment.yaml')
    resources = deployment['spec']['template']['spec']['containers'][0]['resources']

    assert resources['requests'].keys() == resources['limits'].keys()
    for resource, request in resources['requests'].items():
        assert _quantity(request, resource) > 0
        assert _quantity(request, resource) <= _quantity(resources['limits'][resource], resource)


def test_kubernetes_security_contexts_keep_restricted_runtime_settings():
    deployment = _load_yaml(K8S / 'deployment.yaml')
    pod_spec = deployment['spec']['template']['spec']
    container_security = pod_spec['containers'][0]['securityContext']

    assert pod_spec['automountServiceAccountToken'] is False
    assert pod_spec['securityContext']['seccompProfile']['type'] == 'RuntimeDefault'
    assert container_security['runAsNonRoot'] is True
    assert container_security['runAsUser'] == container_security['runAsGroup'] == 10001
    assert container_security['allowPrivilegeEscalation'] is False
    assert container_security['capabilities']['drop'] == ['ALL']
    assert container_security['readOnlyRootFilesystem'] is True


def test_network_policy_remains_default_deny_for_application_ingress():
    deployment = _load_yaml(K8S / 'deployment.yaml')
    policy = _load_yaml(K8S / 'networkpolicy.yaml')

    assert policy['spec']['podSelector']['matchLabels'] == deployment['spec']['selector'][
        'matchLabels'
    ]
    assert policy['spec']['policyTypes'] == ['Ingress']
    assert policy['spec']['ingress'] == []


def test_prometheus_service_monitor_matches_service_and_scrape_endpoint():
    monitor = _load_yaml(REPOSITORY_ROOT / 'monitoring' / 'service-monitor.yaml')
    service = _load_yaml(K8S / 'service.yaml')
    prometheus_values = _load_yaml(REPOSITORY_ROOT / 'monitoring' / 'prometheus-values.yaml')
    prometheus_spec = prometheus_values['prometheus']['prometheusSpec']
    service_port = service['spec']['ports'][0]
    endpoint = monitor['spec']['endpoints'][0]

    assert monitor['metadata']['namespace'] == service['metadata']['namespace'] == NAMESPACE
    assert service['metadata']['labels'].items() >= monitor['spec']['selector'][
        'matchLabels'
    ].items()
    assert monitor['metadata']['labels'].items() >= prometheus_spec[
        'serviceMonitorSelector'
    ]['matchLabels'].items()
    assert NAMESPACE in prometheus_spec['serviceMonitorNamespaceSelector']['matchExpressions'][
        0
    ]['values']
    assert endpoint['port'] == service_port['name'] == 'http'
    assert endpoint['path'] == '/metrics'
    assert '/metrics' in {route.path for route in app.routes if getattr(route, 'path', None)}


def test_dashboard_json_queries_reference_defined_application_metrics():
    dashboard_path = (
        REPOSITORY_ROOT / 'monitoring' / 'grafana' / 'dashboards' / 'cloudops-dashboard.json'
    )
    dashboard = json.loads(dashboard_path.read_text(encoding='utf-8'))
    expressions = [
        target['expr']
        for panel in dashboard['panels']
        for target in panel['targets']
    ]
    dashboard_metrics = {
        metric
        for expression in expressions
        for metric in re.findall(r'\bcloudops_[a-zA-Z0-9_:]+', expression)
    }
    defined_samples = {
        sample.name
        for collector in (REQUEST_COUNT, REQUEST_LATENCY)
        for metric_family in collector.collect()
        for sample in metric_family.samples
    }

    assert dashboard_metrics
    assert dashboard_metrics <= defined_samples
