import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPOSITORY_ROOT / 'scripts' / 'bootstrap-k3s.sh'
K3S_VERSION = 'v1.36.5+k3s1'


def _create_command_path(
    path: Path,
    *,
    systemctl: bool = True,
) -> None:
    path.mkdir()
    for command in ('mktemp', 'chmod', 'cp', 'rm', 'tr', 'sha256sum', 'shasum'):
        source = shutil.which(command)
        if source:
            (path / command).symlink_to(source)

    uname_stub = path / 'uname'
    uname_stub.write_text(
        '#!/bin/sh\n'
        'case "$1" in\n'
        '  -s) printf \'%s\\n\' "$FAKE_UNAME_OS" ;;\n'
        '  -m) printf \'%s\\n\' "$FAKE_UNAME_ARCH" ;;\n'
        '  *) exit 2 ;;\n'
        'esac\n',
        encoding='utf-8',
    )
    uname_stub.chmod(0o700)

    if systemctl:
        systemctl_stub = path / 'systemctl'
        systemctl_stub.write_text(
            '#!/bin/sh\n'
            ': > "$SYSTEMCTL_EXECUTED_MARKER"\n'
            'exit 99\n',
            encoding='utf-8',
        )
        systemctl_stub.chmod(0o700)


@pytest.fixture
def k3s_inputs(tmp_path):
    artifact_dir = tmp_path / 'artifacts'
    artifact_dir.mkdir()
    binary_bytes = b'synthetic-k3s-binary-input\n'
    installer_bytes = b'#!/bin/sh\n: > "$INSTALLER_EXECUTED_MARKER"\n'
    (artifact_dir / 'k3s').write_bytes(binary_bytes)
    (artifact_dir / 'install.sh').write_bytes(installer_bytes)

    command_path = tmp_path / 'commands'
    _create_command_path(command_path)
    marker = tmp_path / 'systemctl-executed'
    installer_marker = tmp_path / 'installer-executed'
    env = os.environ.copy()
    env.update(
        {
            'K3S_ARTIFACT_DIR': str(artifact_dir),
            'APPROVED_K3S_BINARY_SHA256': hashlib.sha256(binary_bytes).hexdigest(),
            'APPROVED_K3S_INSTALLER_SHA256': hashlib.sha256(installer_bytes).hexdigest(),
            'K3S_INSTALLER_COMMIT': 'a' * 40,
            'PATH': str(command_path),
            'FAKE_UNAME_OS': 'Linux',
            'FAKE_UNAME_ARCH': 'x86_64',
            'SYSTEMCTL_EXECUTED_MARKER': str(marker),
            'INSTALLER_EXECUTED_MARKER': str(installer_marker),
        }
    )
    return artifact_dir, env, command_path, marker, installer_marker


def _run_script(env: dict[str, str], mode: str = '--validate-only') -> subprocess.CompletedProcess:
    return subprocess.run(
        [shutil.which('bash') or '/bin/bash', str(SCRIPT), mode],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


def test_missing_k3s_artifact_fails_closed(k3s_inputs):
    artifact_dir, env, _, _, _ = k3s_inputs
    (artifact_dir / 'k3s').unlink()

    result = _run_script(env)

    assert result.returncode != 0
    assert 'exactly k3s and install.sh' in result.stderr


def test_missing_installer_artifact_fails_closed(k3s_inputs):
    artifact_dir, env, _, _, _ = k3s_inputs
    (artifact_dir / 'install.sh').unlink()

    result = _run_script(env)

    assert result.returncode != 0
    assert 'exactly k3s and install.sh' in result.stderr


def test_missing_artifact_directory_fails_closed(k3s_inputs, tmp_path):
    _, env, _, _, _ = k3s_inputs
    env['K3S_ARTIFACT_DIR'] = str(tmp_path / 'missing-artifacts')

    result = _run_script(env)

    assert result.returncode != 0
    assert 'artifact directory must exist as a real directory' in result.stderr


def test_non_directory_artifact_path_fails_closed(k3s_inputs, tmp_path):
    _, env, _, _, _ = k3s_inputs
    artifact_path = tmp_path / 'artifact-file'
    artifact_path.write_text('not a directory\n', encoding='utf-8')
    env['K3S_ARTIFACT_DIR'] = str(artifact_path)

    result = _run_script(env)

    assert result.returncode != 0
    assert 'artifact directory must exist as a real directory' in result.stderr


def test_symlinked_artifact_directory_fails_closed(k3s_inputs, tmp_path):
    artifact_dir, env, _, _, _ = k3s_inputs
    real_dir = tmp_path / 'real-artifacts'
    artifact_dir.rename(real_dir)
    artifact_dir.symlink_to(real_dir, target_is_directory=True)

    result = _run_script(env)

    assert result.returncode != 0
    assert 'real directory, not a symlink' in result.stderr


@pytest.mark.parametrize('artifact_name', ['k3s', 'install.sh'])
def test_empty_artifact_fails_closed(k3s_inputs, artifact_name):
    artifact_dir, env, _, _, _ = k3s_inputs
    (artifact_dir / artifact_name).write_bytes(b'')

    result = _run_script(env)

    assert result.returncode != 0
    assert 'non-empty regular files' in result.stderr


@pytest.mark.parametrize('artifact_name', ['k3s', 'install.sh'])
def test_symlinked_artifact_fails_closed(k3s_inputs, tmp_path, artifact_name):
    artifact_dir, env, _, _, _ = k3s_inputs
    artifact = artifact_dir / artifact_name
    target = tmp_path / f'{artifact_name}.target'
    artifact.rename(target)
    artifact.symlink_to(target)

    result = _run_script(env)

    assert result.returncode != 0
    assert 'non-empty regular files' in result.stderr


@pytest.mark.parametrize('entry_name', ['unexpected.txt', '.hidden-input'])
def test_unexpected_artifact_entry_fails_closed(k3s_inputs, entry_name):
    artifact_dir, env, _, _, _ = k3s_inputs
    (artifact_dir / entry_name).write_text('unexpected\n', encoding='utf-8')

    result = _run_script(env)

    assert result.returncode != 0
    assert 'exactly k3s and install.sh' in result.stderr


def test_artifact_path_with_shell_metacharacters_is_handled_as_a_path(k3s_inputs, tmp_path):
    artifact_dir, env, _, _, _ = k3s_inputs
    unusual_dir = tmp_path / 'artifacts with spaces;$(touch-marker)'
    artifact_dir.rename(unusual_dir)
    env['K3S_ARTIFACT_DIR'] = str(unusual_dir)

    result = _run_script(env)

    assert result.returncode == 0, result.stderr
    assert unusual_dir.is_dir()


def test_incorrect_architecture_fails_before_artifact_processing(k3s_inputs):
    _, env, _, _, _ = k3s_inputs
    env['FAKE_UNAME_ARCH'] = 'aarch64'

    result = _run_script(env)

    assert result.returncode != 0
    assert 'target must be Linux amd64' in result.stderr


def test_non_linux_platform_fails_closed(k3s_inputs):
    _, env, _, _, _ = k3s_inputs
    env['FAKE_UNAME_OS'] = 'Darwin'

    result = _run_script(env)

    assert result.returncode != 0
    assert 'target must be Linux amd64' in result.stderr


@pytest.mark.parametrize(
    'checksum_name',
    ['APPROVED_K3S_BINARY_SHA256', 'APPROVED_K3S_INSTALLER_SHA256'],
)
def test_missing_approved_checksum_fails_closed(k3s_inputs, checksum_name):
    _, env, _, _, _ = k3s_inputs
    env.pop(checksum_name)

    result = _run_script(env)

    assert result.returncode != 0
    assert 'must be separately approved' in result.stderr


@pytest.mark.parametrize(
    'checksum_name',
    ['APPROVED_K3S_BINARY_SHA256', 'APPROVED_K3S_INSTALLER_SHA256'],
)
@pytest.mark.parametrize('malformed', ['not-a-hash', 'a' * 63, 'g' * 64])
def test_malformed_approved_checksum_fails_closed(k3s_inputs, checksum_name, malformed):
    _, env, _, _, _ = k3s_inputs
    env[checksum_name] = malformed

    result = _run_script(env)

    assert result.returncode != 0
    assert 'exactly 64 hexadecimal characters' in result.stderr


@pytest.mark.parametrize(
    'checksum_name',
    ['APPROVED_K3S_BINARY_SHA256', 'APPROVED_K3S_INSTALLER_SHA256'],
)
def test_incorrect_approved_checksum_fails_closed(k3s_inputs, checksum_name):
    _, env, _, _, _ = k3s_inputs
    env[checksum_name] = '0' * 64

    result = _run_script(env)

    assert result.returncode != 0
    assert 'SHA-256 does not match' in result.stderr


def test_missing_installer_trust_evidence_fails_closed(k3s_inputs):
    _, env, _, _, _ = k3s_inputs
    env.pop('K3S_INSTALLER_COMMIT')

    result = _run_script(env)

    assert result.returncode != 0
    assert 'K3S_INSTALLER_COMMIT must identify' in result.stderr


def test_malformed_installer_commit_fails_closed(k3s_inputs):
    _, env, _, _, _ = k3s_inputs
    env['K3S_INSTALLER_COMMIT'] = 'not-a-commit'

    result = _run_script(env)

    assert result.returncode != 0
    assert 'full 40-character hexadecimal commit ID' in result.stderr


@pytest.mark.parametrize('malformed', ['g' * 40, 'a' * 39, 'a' * 41])
def test_malformed_length_or_nonhex_installer_commit_fails_closed(k3s_inputs, malformed):
    _, env, _, _, _ = k3s_inputs
    env['K3S_INSTALLER_COMMIT'] = malformed

    result = _run_script(env)

    assert result.returncode != 0
    assert 'full 40-character hexadecimal commit ID' in result.stderr


def test_unavailable_systemd_prerequisite_fails_closed(k3s_inputs, tmp_path):
    _, env, command_path, _, _ = k3s_inputs
    reduced_path = tmp_path / 'no-systemctl'
    _create_command_path(reduced_path, systemctl=False)
    env['PATH'] = str(reduced_path)

    result = _run_script(env)

    assert result.returncode != 0
    assert 'systemctl is required' in result.stderr


def test_synthetic_local_inputs_pass_validation_without_execution(k3s_inputs):
    _, env, _, systemctl_marker, installer_marker = k3s_inputs

    result = _run_script(env)

    assert result.returncode == 0, result.stderr
    assert f'{K3S_VERSION} amd64 local inputs passed integrity validation' in result.stdout
    assert not systemctl_marker.exists()
    assert not installer_marker.exists()


def test_install_mode_refuses_even_validated_inputs_without_running_installer(k3s_inputs):
    _, env, _, systemctl_marker, installer_marker = k3s_inputs

    result = _run_script(env, '--install')

    assert result.returncode != 0
    assert 'installation is disabled' in result.stderr
    assert not systemctl_marker.exists()
    assert not installer_marker.exists()


def test_k3s_script_has_no_mutable_installer_download_route():
    script = SCRIPT.read_text(encoding='utf-8')

    assert 'get.k3s.io' not in script
    assert 'curl' not in script
    assert 'wget' not in script
    assert 'installation is disabled' in script


def test_install_mode_rejects_bad_checksum_before_any_installation_command(k3s_inputs):
    _, env, _, systemctl_marker, installer_marker = k3s_inputs
    env['APPROVED_K3S_BINARY_SHA256'] = '0' * 64

    result = _run_script(env, '--install')

    assert result.returncode != 0
    assert 'K3s binary SHA-256 does not match' in result.stderr
    assert 'installation is disabled' not in result.stderr
    assert not systemctl_marker.exists()
    assert not installer_marker.exists()


def test_existing_k3s_network_configuration_is_preserved_as_intent():
    script = SCRIPT.read_text(encoding='utf-8')
    assert "K3S_CLUSTER_CIDR='10.44.0.0/16'" in script
    assert "K3S_SERVICE_CIDR='10.43.0.0/16'" in script
    assert "K3S_CLUSTER_DNS='10.43.0.10'" in script
    assert "K3S_NETWORK_FLAGS='--flannel-backend=none --disable-network-policy'" in script


def test_terraform_user_data_has_no_executable_k3s_installer_route():
    terraform = (REPOSITORY_ROOT / 'terraform' / 'modules' / 'ec2' / 'main.tf').read_text(
        encoding='utf-8'
    )
    assert 'get.k3s.io' not in terraform
    assert 'curl -sfL' not in terraform
    assert 'K3s bootstrap blocked' in terraform
