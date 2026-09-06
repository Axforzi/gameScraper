"""Environment-based application settings (REQ-CFG-1..4).

Defaults reproduce today's hardcoded values so a bare deploy behaves exactly
like the current app; every value can be overridden via environment variables.
``SECRET_KEY`` is required unless debug mode is on, and it is never logged.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

_TRUTHY = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    country: str = "VE"
    locale: str = "es-ES"
    currency: str = "USD"
    gog_country: str = "US"
    gog_locale: str = "en-US"
    gog_currency: str = "USD"
    secret_key: str | None = None
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    spider_timeout: float = 60.0
    download_delay: float = 1.0

    @classmethod
    def from_env(
        cls,
        environ: dict[str, str] | None = None,
        *,
        require_secret: bool = True,
    ) -> Settings:
        """Read configuration from ``environ`` (defaults to ``os.environ``).

        Fails fast when ``SECRET_KEY`` is missing in a non-debug environment
        (REQ-CFG-2). Pass ``require_secret=False`` for non-app consumers such
        as spiders, which never need the secret.
        """
        env = os.environ if environ is None else environ
        debug = env.get("DEBUG", "").strip().lower() in _TRUTHY
        secret_key = env.get("SECRET_KEY") or None
        if require_secret and not secret_key and not debug:
            raise RuntimeError(
                "SECRET_KEY is not set. Export SECRET_KEY before starting the "
                "application (or set DEBUG=1 for local development only)."
            )
        return cls(
            country=env.get("COUNTRY", "VE"),
            locale=env.get("LOCALE", "es-ES"),
            currency=env.get("CURRENCY", "USD"),
            gog_country=env.get("GOG_COUNTRY", "US"),
            gog_locale=env.get("GOG_LOCALE", "en-US"),
            gog_currency=env.get("GOG_CURRENCY", "USD"),
            secret_key=secret_key,
            host=env.get("HOST", "0.0.0.0"),
            port=int(env.get("PORT", "5000")),
            debug=debug,
            spider_timeout=float(env.get("SPIDER_TIMEOUT", "60")),
            download_delay=float(env.get("DOWNLOAD_DELAY", "1")),
        )