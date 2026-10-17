import json
import re
import shlex
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = REPOSITORY_ROOT / 'Dockerfile'
DOCKERIGNORE = REPOSITORY_ROOT / '.dockerignore'


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
