import json
import re
import shlex
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = REPOSITORY_ROOT / 'Dockerfile'
DOCKERIGNORE = REPOSITORY_ROOT / '.dockerignore'
REQUIREMENTS = REPOSITORY_ROOT / 'requirements.txt'
RUNTIME_REQUIREMENTS = REPOSITORY_ROOT / 'requirements-runtime.txt'
RUNTIME_INPUT = REPOSITORY_ROOT / 'requirements-runtime.in'
DEVELOPMENT_INPUT = REPOSITORY_ROOT / 'requirements-dev.in'
LOCKING_DOCUMENT = REPOSITORY_ROOT / 'docs' / 'python-dependency-locking.md'

DIRECT_PIN = re.compile(
    r'(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)'
    r'(?:\[[A-Za-z0-9][A-Za-z0-9._,-]*\])?'
    r'==(?P<version>[A-Za-z0-9][A-Za-z0-9.!+_-]*)'
)


def _requirement_lines(path: Path) -> list[str]:
    return [
        content
        for line in path.read_text(encoding='utf-8').splitlines()
        if (content := line.partition('#')[0].strip())
    ]


def _pinned_dependencies(path: Path) -> dict[str, str]:
    lines = _requirement_lines(path)
    dependencies = {}
    for line in lines:
        match = DIRECT_PIN.fullmatch(line)
        assert match, f'{path.name} contains a non-exact direct package pin: {line}'
        name = re.sub(r'[-_.]+', '-', match.group('name')).lower()
        assert name not in dependencies, f'{path.name} repeats package {name}'
        dependencies[name] = line
    return dependencies


def _instructions(text: str) -> list[tuple[str, str]]:
    logical_lines: list[str] = []
    pending = ''
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        if pending:
            pending = f'{pending} {line}'
        else:
            pending = line
        if pending.endswith('\\'):
            pending = pending.removesuffix('\\').rstrip()
            continue
        logical_lines.append(pending)
        pending = ''
    assert not pending, 'Dockerfile ends with an incomplete continuation'

    parsed = []
    for line in logical_lines:
        match = re.match(r'^([A-Za-z]+)\s+(.+)$', line)
        assert match, f'unrecognized Dockerfile instruction: {line}'
        parsed.append((match.group(1).upper(), match.group(2).strip()))
    return parsed


def test_production_image_uses_digest_pinned_base_and_non_root_runtime():
    instructions = _instructions(DOCKERFILE.read_text(encoding='utf-8'))
    from_instructions = [body for name, body in instructions if name == 'FROM']
    user_instructions = [body for name, body in instructions if name == 'USER']

    assert len(from_instructions) == 1
    assert re.fullmatch(r'\S+@sha256:[0-9a-f]{64}', from_instructions[0])
    assert user_instructions[-1] == '10001:10001'
    assert instructions.index(('USER', '10001:10001')) > max(
        index for index, (name, _) in enumerate(instructions) if name == 'RUN'
    )


def test_production_image_copy_and_runtime_contract_are_constrained():
    instructions = _instructions(DOCKERFILE.read_text(encoding='utf-8'))
    copy_sources = [tuple(shlex.split(body)) for name, body in instructions if name == 'COPY']
    add_sources = [body for name, body in instructions if name == 'ADD']
    exposed_ports = [body for name, body in instructions if name == 'EXPOSE']
    commands = [body for name, body in instructions if name == 'CMD']
    health_checks = [body for name, body in instructions if name == 'HEALTHCHECK']

    assert copy_sources == [('requirements-runtime.txt', '.'), ('app', './app')]
    assert not add_sources
    assert exposed_ports == ['8000']
    assert len(commands) == 1
    assert json.loads(commands[0]) == [
        'uvicorn',
        'app.main:app',
        '--host',
        '0.0.0.0',
        '--port',
        '8000',
    ]
    assert len(health_checks) == 1
    assert 'http://127.0.0.1:8000/health' in health_checks[0]


def test_runtime_dependencies_use_exact_version_pins():
    dependencies = _pinned_dependencies(RUNTIME_REQUIREMENTS)

    assert dependencies


def test_runtime_dependencies_match_the_combined_ci_requirements():
    runtime = _pinned_dependencies(RUNTIME_REQUIREMENTS)
    combined = _pinned_dependencies(REQUIREMENTS)

    assert {name: combined.get(name) for name in runtime} == runtime


def test_development_dependencies_are_not_in_the_runtime_requirements():
    runtime = _pinned_dependencies(RUNTIME_REQUIREMENTS)
    combined = _pinned_dependencies(REQUIREMENTS)
    development_only = set(combined) - set(runtime)

    assert {'httpx', 'pytest', 'ruff'} <= development_only
    assert {'httpx', 'pytest', 'ruff'}.isdisjoint(runtime)


def test_canonical_dependency_inputs_exist_and_runtime_matches_active_requirements():
    assert RUNTIME_INPUT.is_file()
    assert DEVELOPMENT_INPUT.is_file()
    assert _pinned_dependencies(RUNTIME_INPUT) == _pinned_dependencies(
        RUNTIME_REQUIREMENTS
    )


def test_development_input_includes_runtime_and_only_existing_development_dependencies():
    lines = _requirement_lines(DEVELOPMENT_INPUT)

    assert lines[0] == '-r requirements-runtime.in'
    assert lines[1:] == [
        'httpx==0.28.1',
        'pytest==8.4.2',
        'ruff==0.13.2',
    ]


def test_canonical_inputs_preserve_all_existing_direct_dependency_versions():
    expected_runtime = {
        'fastapi': 'fastapi==0.133.0',
        'starlette': 'starlette==1.3.1',
        'uvicorn': 'uvicorn[standard]==0.36.0',
        'prometheus-client': 'prometheus-client==0.23.1',
        'pydantic-settings': 'pydantic-settings==2.11.0',
    }
    expected_development = {
        **expected_runtime,
        'httpx': 'httpx==0.28.1',
        'pytest': 'pytest==8.4.2',
        'ruff': 'ruff==0.13.2',
    }

    assert _pinned_dependencies(RUNTIME_INPUT) == expected_runtime
    assert _pinned_dependencies(REQUIREMENTS) == expected_development


def test_canonical_inputs_reject_unapproved_requirement_sources():
    forbidden_prefixes = (
        '-',
        'git+',
        'hg+',
        'svn+',
        'bzr+',
        'file:',
        'http:',
        'https:',
        './',
        '../',
        '/',
    )
    for path in (RUNTIME_INPUT, DEVELOPMENT_INPUT):
        lines = _requirement_lines(path)
        if path == DEVELOPMENT_INPUT:
            assert lines[0] == '-r requirements-runtime.in'
            lines = lines[1:]
        assert lines
        for line in lines:
            assert not line.startswith(forbidden_prefixes), (
                f'{path.name} contains an editable, source, path, or index directive: {line}'
            )
            assert ' @ ' not in line, f'{path.name} contains a direct URL requirement: {line}'
            assert DIRECT_PIN.fullmatch(line), (
                f'{path.name} contains an unreviewed requirement form: {line}'
            )


def test_dependency_locking_is_documented_as_inactive_until_verified():
    documentation = LOCKING_DOCUMENT.read_text(encoding='utf-8')
    assert (
        'Dependency locking is not yet implemented. Production and CI continue using '
        'their existing requirements files.'
    ) in documentation
    assert not (REPOSITORY_ROOT / 'requirements-runtime-alpine-py313-amd64.lock').exists()
    assert not (REPOSITORY_ROOT / 'requirements-dev-ubuntu-py313.lock').exists()


def test_dependency_inputs_contain_only_direct_pins_and_no_unapproved_sources():
    forbidden_prefixes = (
        '-',
        'git+',
        'hg+',
        'svn+',
        'bzr+',
        'file:',
        'http:',
        'https:',
        './',
        '../',
        '/',
    )
    for path in (REQUIREMENTS, RUNTIME_REQUIREMENTS):
        lines = _requirement_lines(path)
        assert lines
        for line in lines:
            assert not line.startswith(forbidden_prefixes), (
                f'{path.name} contains an editable, source, path, or index directive: {line}'
            )
            assert ' @ ' not in line, f'{path.name} contains a direct URL requirement: {line}'
            assert DIRECT_PIN.fullmatch(line), (
                f'{path.name} contains an unreviewed requirement form: {line}'
            )


def test_production_image_installs_runtime_requirements_binary_only():
    instructions = _instructions(DOCKERFILE.read_text(encoding='utf-8'))
    install_commands = [
        body for name, body in instructions if name == 'RUN' and 'pip install' in body
    ]

    assert len(install_commands) == 1
    install = install_commands[0]
    assert 'pip install' in install
    assert '--only-binary=:all:' in install
    assert re.search(r'(?:^|\s)-r\s+requirements-runtime\.txt(?:\s|$)', install)


def test_dockerignore_excludes_local_environment_and_credential_material():
    entries = {
        line.strip()
        for line in DOCKERIGNORE.read_text(encoding='utf-8').splitlines()
        if line.strip() and not line.lstrip().startswith('#')
    }
    required = {
        '.env',
        '.env.*',
        '.aws/',
        '.kube/',
        'credentials',
        'credentials.*',
        '*.pem',
        '*.key',
        '*.p12',
        '*.pfx',
        'id_rsa',
        'id_ed25519',
        'id_ecdsa',
        'id_dsa',
    }

    assert required <= entries
