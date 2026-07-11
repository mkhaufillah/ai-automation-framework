"""
Configuration management for the automation framework.

Loads from config.yaml, environment variables, and provides
a typed configuration object for all framework components.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import ClassVar, Literal, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class _HeuristicConfig(BaseSettings):
    enabled: bool = True
    max_attempts: int = 3


class _LLMConfig(BaseSettings):
    enabled: bool = True
    provider: Literal["openai", "litellm", "gemini", "anthropic", "opencode"] = "openai"
    model: str = "gpt-4o-mini"
    api_key: str = ""
    api_base: str = ""
    temperature: float = 0.1
    max_tokens: int = 500
    timeout: int = 15
    include_screenshot: bool = True
    include_page_source: bool = True

    @property
    def resolved_api_key(self) -> str:
        return self.api_key or os.getenv("HEALING_API_KEY") or os.getenv("OPENAI_API_KEY", "")


class _HealingCacheConfig(BaseSettings):
    enabled: bool = True
    db_path: str = ".healing_cache.json"


class _HealingConfig(BaseSettings):
    enabled: bool = True
    heuristics: _HeuristicConfig = _HeuristicConfig()
    llm: _LLMConfig = _LLMConfig()
    cache: _HealingCacheConfig = _HealingCacheConfig()


class _WebConfig(BaseSettings):
    browser: str = "chromium"
    headless: bool = False
    viewport: dict = Field(default_factory=lambda: {"width": 1280, "height": 720})
    locale: str = "en-US"
    timezone: str = "Asia/Jakarta"
    record_video: bool = False
    screenshot_on_failure: bool = True
    trace_on_failure: bool = True
    base_url: str = ""


class _AndroidConfig(BaseSettings):
    appium_url: str = "http://localhost:4723"
    app: str = ""
    app_package: str = ""
    app_activity: str = ""
    automation_name: str = "UiAutomator2"
    platform_version: str = ""
    device_name: str = ""
    udid: str = ""
    no_reset: bool = True
    full_reset: bool = False
    auto_grant_permissions: bool = True
    adb_exec_timeout: int = 30000
    system_port: int = 8200


class _IOSConfig(BaseSettings):
    appium_url: str = "http://localhost:4723"
    app: str = ""
    bundle_id: str = ""
    automation_name: str = "XCUITest"
    platform_version: str = ""
    device_name: str = ""
    udid: str = ""
    no_reset: bool = True
    full_reset: bool = False
    wda_port: int = 8100


class _ReportingConfig(BaseSettings):
    enabled: bool = True
    output_dir: str = "reports/"
    format: str = "html"
    screenshots: bool = True


class _LoggingConfig(BaseSettings):
    level: str = "INFO"
    file: str = "logs/framework.log"
    format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"


class AutomationConfig(BaseSettings):
    """Central configuration — loads from config.yaml + env overrides."""

    model_config = SettingsConfigDict(
        env_prefix="AUTOFW_",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    # Config file path (set at runtime, not from env)
    _config_path: ClassVar[Optional[Path]] = None

    platform: str = "web"
    web: _WebConfig = _WebConfig()
    android: _AndroidConfig = _AndroidConfig()
    ios: _IOSConfig = _IOSConfig()
    healing: _HealingConfig = _HealingConfig()
    reporting: _ReportingConfig = _ReportingConfig()
    logging: _LoggingConfig = _LoggingConfig()

    @classmethod
    def load(cls, path: str | Path = "config/config.yaml") -> "AutomationConfig":
        """Load configuration from YAML file with env overrides."""
        config_path = Path(path)
        cls._config_path = config_path

        if config_path.exists():
            with open(config_path) as f:
                raw = yaml.safe_load(f) or {}
        else:
            raw = {}

        # Flatten nested dicts for pydantic; pydantic_settings handles deep nesting
        # with env_nested_delimiter, but for YAML load we construct directly.
        return cls(**raw)

    def save(self, path: str | Path | None = None) -> None:
        """Write current config back to YAML (for runtime updates)."""
        target = Path(path or self._config_path or "config/config.yaml")
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w") as f:
            yaml.dump(
                self.model_dump(mode="python"),
                f,
                default_flow_style=False,
                allow_unicode=True,
                indent=2,
            )

    @property
    def is_mobile(self) -> bool:
        return self.platform in ("android", "ios")

    @property
    def is_android(self) -> bool:
        return self.platform == "android"

    @property
    def is_ios(self) -> bool:
        return self.platform == "ios"

    @property
    def is_web(self) -> bool:
        return self.platform == "web"

    @property
    def appium_url(self) -> str:
        if self.is_android:
            return self.android.appium_url
        return self.ios.appium_url
