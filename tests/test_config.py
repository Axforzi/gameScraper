"""Settings tests (REQ-CFG-1..4).

Defaults must reproduce today's hardcoded values so a bare deploy behaves
exactly like the current app; every value is overridable via the environment,
and a missing SECRET_KEY fails fast unless debug mode is on.
"""

from dataclasses import FrozenInstanceError

import pytest

from src.config import Settings


def test_defaults_match_current_app() -> None:
    settings = Settings()
    assert settings.country == "VE"
    assert settings.locale == "es-ES"
    assert settings.currency == "USD"
    assert settings.gog_country == "US"
    assert settings.gog_locale == "en-US"
    assert settings.gog_currency == "USD"
    assert settings.secret_key is None
    assert settings.host == "0.0.0.0"
    assert settings.port == 5000
    assert settings.debug is False
    assert settings.spider_timeout == 60.0
    assert settings.download_delay == 1.0
    assert settings.waitress_threads == 16


def test_from_env_reads_all_overrides() -> None:
    env = {
        "COUNTRY": "AR",
        "LOCALE": "es-AR",
        "CURRENCY": "ARS",
        "GOG_COUNTRY": "GB",
        "GOG_LOCALE": "en-GB",
        "GOG_CURRENCY": "GBP",
        "SECRET_KEY": "s3cr3t",
        "HOST": "127.0.0.1",
        "PORT": "8080",
        "DEBUG": "true",
        "SPIDER_TIMEOUT": "5.5",
        "DOWNLOAD_DELAY": "0.5",
        "WAITRESS_THREADS": "24",
    }
    settings = Settings.from_env(env)

    assert settings.country == "AR"
    assert settings.locale == "es-AR"
    assert settings.currency == "ARS"
    assert settings.gog_country == "GB"
    assert settings.gog_locale == "en-GB"
    assert settings.gog_currency == "GBP"
    assert settings.secret_key == "s3cr3t"
    assert settings.host == "127.0.0.1"
    assert settings.port == 8080
    assert settings.debug is True
    assert settings.spider_timeout == 5.5
    assert settings.download_delay == 0.5
    assert settings.waitress_threads == 24


def test_from_env_falls_back_to_defaults_on_empty_env() -> None:
    settings = Settings.from_env({}, require_secret=False)
    assert settings.country == "VE"
    assert settings.port == 5000
    assert settings.spider_timeout == 60.0
    assert settings.waitress_threads == 16
    assert settings.secret_key is None


@pytest.mark.parametrize("debug_value", ["1", "true", "yes", "on"])
def test_from_env_accepts_truthy_debug_values(debug_value: str) -> None:
    settings = Settings.from_env({"DEBUG": debug_value})
    assert settings.debug is True


def test_from_env_fails_fast_without_secret_key() -> None:
    with pytest.raises(RuntimeError, match="SECRET_KEY is not set"):
        Settings.from_env({})


def test_from_env_skips_secret_requirement_when_disabled() -> None:
    settings = Settings.from_env({}, require_secret=False)
    assert settings.secret_key is None


def test_from_env_rejects_empty_secret_key() -> None:
    with pytest.raises(RuntimeError, match="SECRET_KEY is not set"):
        Settings.from_env({"SECRET_KEY": ""})


def test_settings_is_frozen() -> None:
    settings = Settings()
    with pytest.raises(FrozenInstanceError):
        settings.country = "AR"  # type: ignore[misc]