"""
Base page object with unified cross-platform API.

All page objects should inherit from BasePage and define Locator class attributes.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Type

from autofw.core.config import AutomationConfig
from autofw.core.constants import Platform, DEFAULT_TIMEOUT_MS
from autofw.driver_factory import DriverFactory
from autofw.healing import HealingOrchestrator
from autofw.locator import Locator
from autofw.elements import BaseElement

logger = logging.getLogger(__name__)


class BasePage:
    """
    Base class for all page objects.

    Provides:
      - Unified driver access (Playwright Page or Appium Remote)
      - Element creation with auto-healing
      - Platform detection
      - Navigation and page-level utilities

    Example:
        class LoginPage(BasePage):
            USERNAME = Locator(
                name="Username field",
                web={"placeholder": "Username"},
                android={"accessibility_id": "usernameInput"},
                ios={"accessibility_id": "usernameInput"},
                description="Username text input on login page",
            )
            PASSWORD = Locator(...)
            LOGIN_BTN = Locator(...)

            def login(self, username: str, password: str):
                self.element(self.USERNAME).type(username)
                self.element(self.PASSWORD).type(password)
                self.element(self.LOGIN_BTN).click()
    """

    def __init__(
        self,
        driver_factory: DriverFactory,
        config: AutomationConfig,
        healing_orchestrator: HealingOrchestrator,
    ):
        self._driver_factory = driver_factory
        self._config = config
        self._healing_orch = healing_orchestrator

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def driver(self) -> Any:
        """Get the underlying driver (Playwright Page or Appium Remote)."""
        return self._driver_factory.raw_driver

    @property
    def config(self) -> AutomationConfig:
        return self._config

    @property
    def platform(self) -> str:
        return self._config.platform

    @property
    def healing_orchestrator(self) -> HealingOrchestrator:
        return self._healing_orch

    # ------------------------------------------------------------------
    # Element factory
    # ------------------------------------------------------------------

    def element(
        self,
        locator: Locator,
        name: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT_MS,
    ) -> BaseElement:
        """
        Create a BaseElement from a Locator definition.

        This is the primary way page objects interact with elements.
        Healing is built-in and automatic.
        """
        return BaseElement(
            locator=locator,
            page=self,
            name=name,
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Page-level actions
    # ------------------------------------------------------------------

    def navigate(self, url: str) -> "BasePage":
        """Navigate to a URL (web only)."""
        if self.platform != "web":
            raise NotImplementedError("navigate() is only available on web platform")
        self.driver.goto(url, wait_until="networkidle")
        logger.info("Navigated to: %s", url)
        return self

    def refresh(self) -> "BasePage":
        """Refresh the current page."""
        if self.platform == "web":
            self.driver.reload()
        logger.info("Page refreshed")
        return self

    def get_title(self) -> str:
        """Get the page title."""
        if self.platform == "web":
            return self.driver.title()
        return ""

    def get_url(self) -> str:
        """Get the current URL (web only)."""
        if self.platform == "web":
            return self.driver.url
        return ""

    def get_source(self) -> str:
        """Get page source (HTML for web, XML for mobile)."""
        if self.platform == "web":
            return self.driver.content()
        return self.driver.page_source

    def take_screenshot(self, path: Optional[str] = None) -> bytes:
        """Capture a screenshot."""
        if self.platform == "web":
            return self.driver.screenshot(path=path, full_page=True)
        return self.driver.get_screenshot_as_png()

    def wait_for_load_state(self, state: str = "networkidle") -> "BasePage":
        """Wait for page to reach a given load state (web only)."""
        if self.platform == "web":
            self.driver.wait_for_load_state(state)
        return self

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def is_current_page(self, url_contains: str = "", title_contains: str = "") -> bool:
        """Check if we're on the expected page by URL or title."""
        if url_contains and url_contains in self.get_url():
            return True
        if title_contains and title_contains in self.get_title():
            return True
        return False

    def handle_alert(self, accept: bool = True, prompt_text: str = "") -> Optional[str]:
        """Handle a JavaScript alert/prompt (web only)."""
        if self.platform != "web":
            return None

        dialog = self.driver.on("dialog", lambda d: None)  # dummy listener
        try:
            # Playwright auto-dismisses dialogs; we need a different approach
            self.driver.evaluate("window.confirm = () => true")
        except Exception:
            pass
        return None

    def execute_script(self, script: str, *args) -> Any:
        """Execute JavaScript (web only)."""
        if self.platform == "web":
            return self.driver.evaluate(script, *args)
        return None
