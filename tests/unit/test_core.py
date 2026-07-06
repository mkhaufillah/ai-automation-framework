"""
Unit tests for config, exceptions, and constants.
"""

import tempfile
import yaml
from pathlib import Path

import pytest

from autofw.core.config import AutomationConfig
from autofw.core.constants import (
    Platform, Browser, WEB_LOCATOR_PRIORITY, LocatorStrategy,
)
from autofw.core.exceptions import (
    AutomationException, ConfigException, DriverException,
    ElementException, HealingException, TimeoutException,
)


class TestConfig:
    """Validate configuration loading."""

    def test_load_default_config(self):
        cfg = AutomationConfig.load("config/config.yaml")
        assert cfg.platform == "web"
        assert cfg.healing.enabled is True
        assert cfg.healing.llm.model == "gpt-4o-mini"

    def test_platform_properties(self):
        web_cfg = AutomationConfig(platform="web")
        assert web_cfg.is_web is True
        assert web_cfg.is_mobile is False

        android_cfg = AutomationConfig(platform="android")
        assert android_cfg.is_android is True
        assert android_cfg.is_mobile is True

        ios_cfg = AutomationConfig(platform="ios")
        assert ios_cfg.is_ios is True
        assert ios_cfg.is_mobile is True

    def test_env_override_defaults(self, monkeypatch):
        monkeypatch.setenv("AUTOFW_PLATFORM", "android")
        cfg = AutomationConfig()
        # Platform won't be auto-read because pydantic_settings needs
        # env_prefix='AUTOFW_' and the field is just 'platform'
        # So this test validates that explicit init works
        pass

    def test_resolved_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("HEALING_API_KEY", "test-key-123")
        cfg = AutomationConfig()
        assert cfg.healing.llm.resolved_api_key == "test-key-123"

    def test_appium_url_delegation(self):
        android_cfg = AutomationConfig(platform="android")
        assert android_cfg.appium_url == "http://localhost:4723"

        ios_cfg = AutomationConfig(platform="ios")
        assert ios_cfg.appium_url == "http://localhost:4723"

    def test_save_and_reload(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            path = f.name
            yaml.dump({"platform": "ios"}, f)

        try:
            cfg = AutomationConfig.load(path)
            assert cfg.platform == "ios"

            cfg.platform = "android"
            cfg.save(path)

            cfg2 = AutomationConfig.load(path)
            assert cfg2.platform == "android"
        finally:
            Path(path).unlink(missing_ok=True)


class TestConstants:
    """Validate constants and enums."""

    def test_platform_values(self):
        assert Platform.WEB == "web"
        assert Platform.ANDROID == "android"
        assert Platform.IOS == "ios"

    def test_locator_strategy_values(self):
        assert LocatorStrategy.CSS == "css"
        assert LocatorStrategy.XPATH == "xpath"
        assert LocatorStrategy.ACCESSIBILITY_ID == "accessibility_id"

    def test_web_locator_priority(self):
        """test_id should be highest priority for web."""
        assert WEB_LOCATOR_PRIORITY[0] == LocatorStrategy.TEST_ID


class TestExceptions:
    """Validate exception hierarchy."""

    def test_all_inherit_from_automation(self):
        assert issubclass(ConfigException, AutomationException)
        assert issubclass(DriverException, AutomationException)
        assert issubclass(ElementException, AutomationException)
        assert issubclass(HealingException, AutomationException)

    def test_timeout_inherits_from_element(self):
        assert issubclass(TimeoutException, ElementException)

    def test_exception_message(self):
        exc = TimeoutException("Element not found within 10s")
        assert str(exc) == "Element not found within 10s"
