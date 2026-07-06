"""
pytest conftest — framework fixtures and hooks.

Provides:
  - autofw_config: Loads config.yaml
  - autofw_driver_factory: Creates/manages driver lifecycle
  - autofw_healing: Sets up the healing orchestrator
  - page objects as fixtures
  - Automatic reporting on failure
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Generator, Optional

import pytest
from _pytest.config.argparsing import Parser
from _pytest.nodes import Item

from autofw.core.config import AutomationConfig
from autofw.core.constants import Platform
from autofw.core.exceptions import AutomationException
from autofw.driver_factory import DriverFactory
from autofw.healing import HealingOrchestrator
from autofw.utils.logger import setup_logging

logger = logging.getLogger(__name__)


def pytest_addoption(parser: Parser) -> None:
    """Add custom CLI options."""
    parser.addoption(
        "--platform",
        action="store",
        default=None,
        help="Override platform: web, android, ios",
    )
    parser.addoption(
        "--config",
        action="store",
        default="config/config.yaml",
        help="Path to config YAML file",
    )
    parser.addoption(
        "--heal-cache",
        action="store",
        default=None,
        help="Path to healing cache file (default: from config)",
    )
    parser.addoption(
        "--disable-healing",
        action="store_true",
        default=False,
        help="Disable AI auto-healing for this run",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Configure the framework at session start."""
    # Setup logging early
    log_config_path = config.getoption("--config")
    try:
        cfg = AutomationConfig.load(log_config_path)
        setup_logging(level=cfg.logging.level, file_path=cfg.logging.file)
    except Exception:
        setup_logging()  # fallback to defaults

    # Register custom markers
    config.addinivalue_line("markers", "web: Web tests using Playwright")
    config.addinivalue_line("markers", "android: Android native tests using Appium")
    config.addinivalue_line("markers", "ios: iOS native tests using Appium")
    config.addinivalue_line("markers", "healing: AI healing tests")
    config.addinivalue_line("markers", "smoke: Smoke tests")
    config.addinivalue_line("markers", "regression: Regression tests")


def pytest_collection_modifyitems(items: list[Item]) -> None:
    """Auto-skip tests that don't match the current platform."""
    platform_marker_map = {
        "web": "web",
        "android": "android",
        "ios": "ios",
    }

    for item in items:
        # Skip if platform marker doesn't match config
        marker = item.get_closest_marker("web") or item.get_closest_marker("android") or item.get_closest_marker("ios")
        if marker:
            item.user_properties.append(("platform", marker.name))


# ---------------------------------------------------------------------------
# Session-scoped fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def autofw_config(request: pytest.FixtureRequest) -> AutomationConfig:
    """Load configuration from YAML with CLI overrides."""
    config_path = request.config.getoption("--config")
    cfg = AutomationConfig.load(config_path)

    # CLI override: platform
    cli_platform = request.config.getoption("--platform")
    if cli_platform:
        cfg.platform = cli_platform

    # CLI override: disable healing
    if request.config.getoption("--disable-healing"):
        cfg.healing.enabled = False

    # CLI override: healing cache path
    cli_cache = request.config.getoption("--heal-cache")
    if cli_cache:
        cfg.healing.cache.db_path = cli_cache

    logger.info(
        "Framework configured: platform=%s, healing=%s, config=%s",
        cfg.platform,
        cfg.healing.enabled,
        config_path,
    )
    return cfg


@pytest.fixture(scope="session")
def autofw_driver_factory(
    autofw_config: AutomationConfig,
) -> Generator[DriverFactory, None, None]:
    """Create and manage the driver lifecycle."""
    factory = DriverFactory(autofw_config)
    try:
        factory.create_driver()
        logger.info("Driver created: platform=%s", autofw_config.platform)
        yield factory
    finally:
        factory.quit_driver()
        logger.info("Driver quit.")


@pytest.fixture(scope="session")
def autofw_healing(
    autofw_config: AutomationConfig,
) -> Optional[HealingOrchestrator]:
    """Set up the healing orchestrator."""
    if not autofw_config.healing.enabled:
        logger.info("AI healing is DISABLED")
        return None
    orchestrator = HealingOrchestrator(autofw_config)
    logger.info(
        "Healing orchestrator ready: heuristics=%s, llm=%s, cache=%s",
        autofw_config.healing.heuristics.enabled,
        autofw_config.healing.llm.enabled,
        autofw_config.healing.cache.enabled,
    )
    return orchestrator


@pytest.fixture
def healing(request: pytest.FixtureRequest) -> Optional[HealingOrchestrator]:
    """Fixture-level access to healing orchestrator."""
    return request.getfixturevalue("autofw_healing")


# ---------------------------------------------------------------------------
# Hooks for screenshots on failure
# ---------------------------------------------------------------------------


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: Item, call: Any) -> Generator:
    """Capture screenshot on test failure."""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        # Try to get the driver factory from the request
        try:
            config = item.config
            factory = item._request.getfixturevalue("autofw_driver_factory")
            driver = factory.raw_driver

            # Save screenshot
            from autofw.utils import save_screenshot
            test_name = item.nodeid.replace("::", "_").replace("/", "_").replace(".", "_")
            screenshot_path = save_screenshot(
                driver,
                config.platform,
                name=f"FAILED_{test_name}",
                output_dir="reports/screenshots/",
            )

            if screenshot_path:
                report.user_properties.append(("screenshot", screenshot_path))
                logger.error("Test failed — screenshot saved: %s", screenshot_path)

            # Save page source for debugging
            try:
                if config.platform == "web":
                    source = driver.content()
                else:
                    source = driver.page_source

                source_dir = Path("reports/sources/")
                source_dir.mkdir(parents=True, exist_ok=True)
                source_path = source_dir / f"FAILED_{test_name}.html"
                source_path.write_text(source)
                report.user_properties.append(("page_source", str(source_path)))
            except Exception:
                pass

            # Save healing cache summary
            if config.healing.enabled:
                try:
                    healing = item._request.getfixturevalue("autofw_healing")
                    if healing and healing.cache:
                        cache_data = healing.cache.get_all()
                        if cache_data:
                            cache_dir = Path("reports/healing/")
                            cache_dir.mkdir(parents=True, exist_ok=True)
                            cache_path = cache_dir / f"healing_cache_{test_name}.json"
                            with open(cache_path, "w") as f:
                                json.dump(cache_data, f, indent=2, default=str)
                            report.user_properties.append(("healing_cache", str(cache_path)))
                except Exception:
                    pass

        except Exception as e:
            logger.warning("Failed to capture failure artifacts: %s", e)
