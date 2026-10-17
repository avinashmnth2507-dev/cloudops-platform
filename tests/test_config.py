import pytest
from pydantic import ValidationError

from app.config import Settings


@pytest.fixture(autouse=True)
def clear_settings_environment(monkeypatch):
    for variable in ('APP_NAME', 'APP_VERSION', 'ENVIRONMENT'):
        monkeypatch.delenv(variable, raising=False)


def test_settings_trim_surrounding_whitespace_and_keep_defaults():
    settings = Settings(_env_file=None, app_name='  Example Service  ', environment=' test ')

    assert settings.app_name == 'Example Service'
    assert settings.environment == 'test'
    assert settings.app_version == '1.0.0'


def test_settings_accept_trimmed_unicode_environment_values(monkeypatch):
    monkeypatch.setenv('APP_NAME', '  CloudOps ☁️  ')
    monkeypatch.setenv('APP_VERSION', ' 1.0.0-β ')
    monkeypatch.setenv('ENVIRONMENT', ' producción ')

    settings = Settings(_env_file=None)

    assert settings.app_name == 'CloudOps ☁️'
    assert settings.app_version == '1.0.0-β'
    assert settings.environment == 'producción'


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('app_name', '   '),
        ('app_version', ''),
        ('environment', ' \t '),
        ('app_name', 'x' * 101),
        ('app_version', 'x' * 51),
        ('environment', 'x' * 51),
        ('app_name', 'valid\ninvalid'),
        ('environment', 'test\x7fvalue'),
        ('environment', 'test\x85value'),
    ],
)
def test_invalid_display_configuration_fails_validation(field, value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: value})


def test_environment_configuration_is_validated_at_settings_construction(monkeypatch):
    monkeypatch.setenv('APP_NAME', '   ')

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
