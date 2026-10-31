"""
SettingsStore: persistent API key storage for the Hearsay gateway.

Keys are stored in a local .env file (HEARSAY_<PROVIDER>_KEY=value).
They are also readable from environment variables as fallback.
Keys are never returned to the caller after save — only a boolean
"is configured" status is exposed externally.

Supported providers: gemini, openai, groq, custom
Custom providers also store a base URL (HEARSAY_CUSTOM_BASE_URL).
"""

import os
import re
from pathlib import Path
from typing import Optional, Dict

SUPPORTED_PROVIDERS = {"gemini", "openai", "groq", "custom"}

# Environment variable name pattern: HEARSAY_<PROVIDER>_KEY
_KEY_ENV_PATTERN = "HEARSAY_{provider}_KEY"
_BASE_URL_ENV = "HEARSAY_CUSTOM_BASE_URL"


def _default_env_path() -> Path:
    """Returns the .env file path, overridable via HEARSAY_ENV_PATH env var."""
    override = os.environ.get("HEARSAY_ENV_PATH")
    if override:
        return Path(override)
    # Repo root: two levels up from this file (hearsay/proxy/ -> hearsay/ -> repo root)
    return Path(__file__).resolve().parent.parent.parent / ".env"


class SettingsStore:
    def __init__(self, env_path: Optional[Path] = None) -> None:
        self._env_path = env_path or _default_env_path()

    def _read_env_file(self) -> Dict[str, str]:
        """Parses the .env file into a dict. Returns {} if file does not exist."""
        if not self._env_path.exists():
            return {}
        result: Dict[str, str] = {}
        for line in self._env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                result[k.strip()] = v.strip()
        return result

    def _write_env_file(self, data: Dict[str, str]) -> None:
        """Writes the dict back to the .env file, one KEY=value per line."""
        self._env_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"{k}={v}" for k, v in sorted(data.items())]
        self._env_path.write_text("\n".join(lines) + "\n")

    def save_api_key(self, provider: str, key: str, base_url: Optional[str] = None) -> None:
        """
        Saves the API key for the given provider to the .env file.
        Also saves base_url if provider == 'custom' and base_url is provided.
        """
        provider = provider.lower()
        env_data = self._read_env_file()
        env_key = _KEY_ENV_PATTERN.format(provider=provider.upper())
        env_data[env_key] = key
        if provider == "custom" and base_url:
            env_data[_BASE_URL_ENV] = base_url
        self._write_env_file(env_data)
        # Also set in current process environment so gateway picks it up immediately
        os.environ[env_key] = key
        if provider == "custom" and base_url:
            os.environ[_BASE_URL_ENV] = base_url

    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Returns the API key for the given provider.
        Checks .env file first, then os.environ. Returns None if not found.
        """
        provider = provider.lower()
        env_key = _KEY_ENV_PATTERN.format(provider=provider.upper())
        # Check .env file first
        file_data = self._read_env_file()
        if env_key in file_data and file_data[env_key].strip():
            return file_data[env_key].strip()
        # Fall back to process environment
        val = os.environ.get(env_key, "").strip()
        return val or None

    def get_base_url(self, provider: str) -> Optional[str]:
        """Returns the base URL for custom providers."""
        if provider.lower() != "custom":
            return None
        file_data = self._read_env_file()
        if _BASE_URL_ENV in file_data:
            return file_data[_BASE_URL_ENV].strip() or None
        return os.environ.get(_BASE_URL_ENV, "").strip() or None

    def get_status(self) -> Dict[str, bool]:
        """
        Returns a dict of {provider: is_configured} for all supported providers.
        Never returns key values — only booleans.
        """
        return {
            provider: self.get_api_key(provider) is not None
            for provider in sorted(SUPPORTED_PROVIDERS)
        }
