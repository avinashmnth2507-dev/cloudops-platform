import hashlib
import os
import subprocess
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPOSITORY_ROOT / 'scripts' / 'bootstrap-calico.sh'
CRD_NAME = 'v3_projectcalico_org.yaml'
OPERATOR_NAME = 'tigera-operator.yaml'
INSTALLATION_NAME = 'installation.yaml'


def _write_kubectl_stub(path: Path) -> None:
    path.write_text(
        '#!/bin/sh\n'
        'printf \'%s\\n\' "$*" >> "$KUBECTL_CALLS"\n'
        'if [ "$1" = config ]; then\n'
        '  printf \'%s\\n\' "$KUBECTL_CONTEXTS"\n'
        '  exit 0\n'
        'fi\n'
        'if [ "$1" = --context ]; then shift 2; fi\n'
        'if [ "$1" = apply ] && [ "$2" = -f ]; then\n'
        '  input="$3"\n'
        '  cat "$input" > "$KUBECTL_APPLIED_DIR/${input##*/}"\n'
        '  if [ "${MUTATE_ARTIFACTS_ON_FIRST_APPLY:-0}" = 1 ] &&\n'
        '    [ ! -e "$KUBECTL_MUTATION_MARKER" ]; then\n'
        '    printf \'tampered\' > "$CALICO_ARTIFACT_DIR/v3_projectcalico_org.yaml"\n'
        '    printf \'tampered\' > "$CALICO_ARTIFACT_DIR/tigera-operator.yaml"\n'
        '    printf \'tampered\' > "$CALICO_INSTALLATION_FILE"\n'
        '    : > "$KUBECTL_MUTATION_MARKER"\n'
        '  fi\n'
        'fi\n',
        encoding='utf-8',
    )
    path.chmod(0o700)


@pytest.fixture
def calico_inputs(tmp_path):
    artifact_dir = tmp_path / 'artifacts'
    artifact_dir.mkdir()
    crd_bytes = b'apiVersion: apiextensions.k8s.io/v1\nkind: CustomResourceDefinition\n'
    operator_bytes = b'apiVersion: apps/v1\nkind: Deployment\n'
    (artifact_dir / CRD_NAME).write_bytes(crd_bytes)
    (artifact_dir / OPERATOR_NAME).write_bytes(operator_bytes)

    fixture_root = tmp_path / 'project'
    fixture_scripts = fixture_root / 'scripts'
    fixture_scripts.mkdir(parents=True)
    fixture_installation_dir = fixture_root / 'k8s' / 'calico'
    fixture_installation_dir.mkdir(parents=True)
    script_fixture = fixture_scripts / 'bootstrap-calico.sh'
    script_fixture.write_bytes(SCRIPT.read_bytes())
    script_fixture.chmod(0o700)
    installation_file = fixture_installation_dir / INSTALLATION_NAME
    installation_bytes = b'apiVersion: operator.tigera.io/v1\nkind: Installation\n'
    installation_file.write_bytes(installation_bytes)

    kubectl_stub = tmp_path / 'kubectl-stub'
    _write_kubectl_stub(kubectl_stub)
    calls_file = tmp_path / 'kubectl-calls.txt'
    applied_dir = tmp_path / 'applied'
    applied_dir.mkdir()

    env = os.environ.copy()
    env.update(
        {
            'CALICO_ARTIFACT_DIR': str(artifact_dir),
            'KUBE_CONTEXT': 'test-context-only',
            'APPROVED_CRD_SHA256': hashlib.sha256(crd_bytes).hexdigest(),
            'APPROVED_OPERATOR_SHA256': hashlib.sha256(operator_bytes).hexdigest(),
            'APPROVED_INSTALLATION_SHA256': hashlib.sha256(installation_bytes).hexdigest(),
            'TEST_BOOTSTRAP_SCRIPT': str(script_fixture),
            'CALICO_INSTALLATION_FILE': str(installation_file),
            'KUBECTL_BIN': str(kubectl_stub),
            'KUBECTL_CALLS': str(calls_file),
            'KUBECTL_CONTEXTS': 'test-context-only',
            'KUBECTL_APPLIED_DIR': str(applied_dir),
            'KUBECTL_MUTATION_MARKER': str(tmp_path / 'mutated'),
            'TMPDIR': str(tmp_path),
        }
    )
    return artifact_dir, env, calls_file, applied_dir


def _run_script(env: dict[str, str], mode: str = '--validate-only') -> subprocess.CompletedProcess:
    return subprocess.run(
        ['bash', env.get('TEST_BOOTSTRAP_SCRIPT', str(SCRIPT)), mode],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


@pytest.mark.parametrize('directory_kind', ['missing', 'symlink'])
def test_missing_or_symlinked_artifact_directory_fails_before_kubectl(
    calico_inputs, tmp_path, directory_kind
):
    artifact_dir, env, calls_file, _ = calico_inputs
    if directory_kind == 'missing':
        artifact_dir.rename(tmp_path / 'saved-artifacts')
    else:
        real_dir = tmp_path / 'real-artifacts'
        artifact_dir.rename(real_dir)
        artifact_dir.symlink_to(real_dir, target_is_directory=True)

    result = _run_script(env)

    assert result.returncode != 0
    assert not calls_file.exists()


@pytest.mark.parametrize('missing_name', [CRD_NAME, OPERATOR_NAME])
def test_missing_manifest_fails_before_kubectl(calico_inputs, missing_name):
    artifact_dir, env, calls_file, _ = calico_inputs
    (artifact_dir / missing_name).unlink()

    result = _run_script(env)

    assert result.returncode != 0
    assert not calls_file.exists()


@pytest.mark.parametrize('empty_name', [CRD_NAME, OPERATOR_NAME])
def test_empty_manifest_fails_before_kubectl(calico_inputs, empty_name):
    artifact_dir, env, calls_file, _ = calico_inputs
    (artifact_dir / empty_name).write_bytes(b'')

    result = _run_script(env)

    assert result.returncode != 0
    assert not calls_file.exists()


@pytest.mark.parametrize('symlink_name', [CRD_NAME, OPERATOR_NAME])
def test_symlinked_manifest_fails_before_kubectl(calico_inputs, tmp_path, symlink_name):
    artifact_dir, env, calls_file, _ = calico_inputs
    manifest = artifact_dir / symlink_name
    target = tmp_path / f'{symlink_name}.target'
    manifest.rename(target)
    manifest.symlink_to(target)

    result = _run_script(env)

    assert result.returncode != 0
    assert not calls_file.exists()


@pytest.mark.parametrize('extra_name', ['unexpected.yaml', '.hidden-input'])
def test_unexpected_artifact_entry_fails_before_kubectl(calico_inputs, extra_name):
    artifact_dir, env, calls_file, _ = calico_inputs
    (artifact_dir / extra_name).write_text('unexpected\n', encoding='utf-8')

    result = _run_script(env)

    assert result.returncode != 0
    assert not calls_file.exists()


@pytest.mark.parametrize(
    'checksum_name',
    ['APPROVED_CRD_SHA256', 'APPROVED_OPERATOR_SHA256', 'APPROVED_INSTALLATION_SHA256'],
)
def test_missing_approved_checksum_fails_before_kubectl(calico_inputs, checksum_name):
    _, env, calls_file, _ = calico_inputs
    env.pop(checksum_name)

    result = _run_script(env)

    assert result.returncode != 0
    assert not calls_file.exists()


@pytest.mark.parametrize(
    'checksum_name',
    ['APPROVED_CRD_SHA256', 'APPROVED_OPERATOR_SHA256', 'APPROVED_INSTALLATION_SHA256'],
)
@pytest.mark.parametrize('malformed_value', ['not-a-hash', 'a' * 63, 'g' * 64])
def test_malformed_approved_checksum_fails_before_kubectl(
    calico_inputs, checksum_name, malformed_value
):
    _, env, calls_file, _ = calico_inputs
    env[checksum_name] = malformed_value

    result = _run_script(env)

    assert result.returncode != 0
    assert not calls_file.exists()


@pytest.mark.parametrize(
    'checksum_name',
    ['APPROVED_CRD_SHA256', 'APPROVED_OPERATOR_SHA256', 'APPROVED_INSTALLATION_SHA256'],
)
def test_incorrect_approved_checksum_fails_before_kubectl(calico_inputs, checksum_name):
    _, env, calls_file, _ = calico_inputs
    env[checksum_name] = '0' * 64

    result = _run_script(env)

    assert result.returncode != 0
    assert not calls_file.exists()


def test_apply_mode_does_not_run_any_kubectl_command_before_checksum_validation(calico_inputs):
    _, env, calls_file, _ = calico_inputs
    env['APPROVED_INSTALLATION_SHA256'] = '0' * 64

    result = _run_script(env, '--apply')

    assert result.returncode != 0
    assert not calls_file.exists()


@pytest.mark.parametrize(
    'failure', ['missing', 'malformed', 'mismatched', 'modified-content']
)
def test_rejected_installation_integrity_never_invokes_kubectl(calico_inputs, failure):
    _, env, calls_file, _ = calico_inputs
    if failure == 'missing':
        env.pop('APPROVED_INSTALLATION_SHA256')
    elif failure == 'malformed':
        env['APPROVED_INSTALLATION_SHA256'] = 'g' * 64
    elif failure == 'mismatched':
        env['APPROVED_INSTALLATION_SHA256'] = '0' * 64
    else:
        installation_file = Path(env['CALICO_INSTALLATION_FILE'])
        installation_file.write_bytes(b'apiVersion: v1\nkind: Modified\n')

    result = _run_script(env, '--apply')

    assert result.returncode != 0
    assert not calls_file.exists()


def test_modified_installation_content_fails_checksum_validation(calico_inputs):
    _, env, calls_file, _ = calico_inputs
    installation_file = Path(env['CALICO_INSTALLATION_FILE'])
    installation_file.write_bytes(b'apiVersion: v1\nkind: Modified\n')

    result = _run_script(env)

    assert result.returncode != 0
    assert 'Installation resource SHA-256' in result.stderr
    assert not calls_file.exists()


def test_matching_installation_checksum_passes_offline_validation(calico_inputs):
    _, env, calls_file, _ = calico_inputs

    result = _run_script(env)

    assert result.returncode == 0, result.stderr
    assert 'passed local validation' in result.stdout
    assert not calls_file.exists()


def test_valid_inputs_reach_validation_boundary_without_kubectl(calico_inputs):
    _, env, calls_file, _ = calico_inputs

    result = _run_script(env, '--validate-only')

    assert result.returncode == 0, result.stderr
    assert 'passed local validation' in result.stdout
    assert not calls_file.exists()


def test_apply_mode_uses_stubbed_kubectl_in_required_order(calico_inputs):
    _, env, calls_file, _ = calico_inputs

    result = _run_script(env, '--apply')

    assert result.returncode == 0, result.stderr
    calls = calls_file.read_text(encoding='utf-8').splitlines()
    assert calls[0] == 'config get-contexts --output=name'
    apply_paths = [call.split(' -f ', 1)[1] for call in calls if 'apply -f ' in call]
    assert [Path(path).name for path in apply_paths] == [
        CRD_NAME,
        OPERATOR_NAME,
        INSTALLATION_NAME,
    ]
    assert all(Path(path).parent != Path(env['CALICO_ARTIFACT_DIR']) for path in apply_paths[:2])
    assert (
        'wait --for=condition=Established --timeout=120s crd/installations.operator.tigera.io'
        in calls[2]
    )
    assert (
        'rollout status --namespace=tigera-operator deployment/tigera-operator --timeout=180s'
        in calls[4]
    )
    assert 'wait --for=condition=Available --timeout=300s tigerastatus/calico' in calls[6]
    assert (
        'rollout status --namespace=calico-system daemonset/calico-node --timeout=300s'
        in calls[7]
    )
    assert (
        'rollout status --namespace=calico-system deployment/calico-kube-controllers --timeout=300s'
        in calls[8]
    )
    assert 'wait --for=condition=Ready --timeout=300s nodes --all' in calls[9]
    assert all(call.startswith('--context test-context-only ') for call in calls[1:])


def test_apply_uses_verified_snapshots_if_original_manifests_change_after_verification(
    calico_inputs,
):
    artifact_dir, env, _, applied_dir = calico_inputs
    original_crd = (artifact_dir / CRD_NAME).read_bytes()
    original_operator = (artifact_dir / OPERATOR_NAME).read_bytes()
    installation_file = Path(env['CALICO_INSTALLATION_FILE'])
    original_installation = installation_file.read_bytes()
    env['MUTATE_ARTIFACTS_ON_FIRST_APPLY'] = '1'

    result = _run_script(env, '--apply')

    assert result.returncode == 0, result.stderr
    assert (artifact_dir / CRD_NAME).read_bytes() == b'tampered'
    assert (artifact_dir / OPERATOR_NAME).read_bytes() == b'tampered'
    assert installation_file.read_bytes() == b'tampered'
    assert (applied_dir / CRD_NAME).read_bytes() == original_crd
    assert (applied_dir / OPERATOR_NAME).read_bytes() == original_operator
    assert (applied_dir / INSTALLATION_NAME).read_bytes() == original_installation


def test_unknown_kube_context_stops_before_any_apply(calico_inputs):
    _, env, calls_file, _ = calico_inputs
    env['KUBE_CONTEXT'] = 'not-configured'

    result = _run_script(env, '--apply')

    assert result.returncode != 0
    assert 'does not name a configured context' in result.stderr
    calls = calls_file.read_text(encoding='utf-8').splitlines()
    assert calls == ['config get-contexts --output=name']


def test_research_candidate_checksums_are_not_embedded_as_approved_values():
    script = SCRIPT.read_text(encoding='utf-8')

    assert '5306c2c6d9fd6762d804f9da51c049b8269c33498a364c5df0eed555aba026bd' not in script
    assert 'aef423b36aef8cf86567f92bbe5eea4b4ca105a6fc7dbf43de599c6fa70388ba' not in script
    assert 'APPROVED_CRD_SHA256' in script
    assert 'APPROVED_OPERATOR_SHA256' in script
    assert 'APPROVED_INSTALLATION_SHA256' in script
