import re
from pathlib import Path

import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPOSITORY_ROOT / '.github' / 'workflows' / 'ci.yml'


def _load_workflow() -> dict:
    return yaml.load(WORKFLOW.read_text(encoding='utf-8'), Loader=yaml.BaseLoader)


def _steps(job: dict) -> list[dict]:
    return job['steps']


def test_ci_workflow_runs_ruff_pytest_and_gitleaks():
    workflow = _load_workflow()
    steps = _steps(workflow['jobs']['test'])
    commands = [step.get('run', '') for step in steps]
    actions = [step.get('uses', '') for step in steps]

    assert any('ruff check .' in command for command in commands)
    assert any('pytest -q' in command for command in commands)
    assert any(reference.startswith('gitleaks/gitleaks-action@') for reference in actions)


def test_ci_installs_the_combined_development_requirements():
    workflow = _load_workflow()
    install_step = next(
        step
        for step in _steps(workflow['jobs']['test'])
        if step.get('name') == 'Install dependencies'
    )

    assert install_step['run'] == 'python -m pip install -r requirements.txt'


def test_ci_image_build_precedes_strict_high_critical_trivy_scan():
    workflow = _load_workflow()
    image_job = workflow['jobs']['image']
    assert image_job['needs'] == 'test'
    steps = _steps(image_job)
    build_step = next(
        step for step in steps if step.get('name') == 'Build Docker image for scanning'
    )
    scan_step = next(step for step in steps if step.get('name') == 'Scan image for vulnerabilities')

    assert build_step['with']['context'] == '.'
    assert build_step['with']['load'] == 'true'
    assert scan_step['with']['severity'] == 'CRITICAL,HIGH'
    assert scan_step['with']['exit-code'] == '1'
    assert steps.index(build_step) < steps.index(scan_step)


def test_all_github_actions_are_pinned_to_full_commit_shas():
    workflow = _load_workflow()

    for job in workflow['jobs'].values():
        for step in _steps(job):
            action = step.get('uses')
            if action:
                assert re.search(r'@[0-9a-f]{40}$', action), action


def test_ghcr_publishing_and_image_handoff_remain_disabled():
    workflow = _load_workflow()
    image_steps = _steps(workflow['jobs']['image'])
    publish_job = workflow['jobs']['publish']

    assert set(workflow['on']) == {'push', 'pull_request'}
    assert publish_job['if'].rstrip().endswith('false }}')
    assert publish_job['permissions']['packages'] == 'write'
    assert workflow['permissions']['contents'] == 'read'
    assert workflow['jobs']['test']['permissions'] == {'contents': 'read'}
    assert workflow['jobs']['image']['permissions'] == {'contents': 'read'}
    gated_handoff_steps = [
        step
        for step in image_steps
        if step.get('name')
        in {
            'Export the scanned image for the gated publishing job',
            'Calculate the scanned image archive checksum',
            'Upload the scanned image for the gated publishing job',
        }
    ]
    assert len(gated_handoff_steps) == 3
    assert all(
        step.get('if') == '${{ false }}'
        for step in gated_handoff_steps
    )


def test_ci_secret_handling_keeps_gitleaks_comments_and_artifact_upload_off():
    workflow = _load_workflow()
    gitleaks = next(
        step
        for step in _steps(workflow['jobs']['test'])
        if step.get('uses', '').startswith('gitleaks/gitleaks-action@')
    )

    assert gitleaks['env']['GITLEAKS_ENABLE_COMMENTS'] == 'false'
    assert gitleaks['env']['GITLEAKS_ENABLE_UPLOAD_ARTIFACT'] == 'false'
    assert gitleaks['env']['GITLEAKS_ENABLE_SUMMARY'] == 'false'
