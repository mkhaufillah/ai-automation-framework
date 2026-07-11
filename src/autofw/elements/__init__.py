"""
Unified element operations with built-in AI healing.

Provides a single API for interacting with elements across all platforms.
When element resolution fails, the healing pipeline auto-triggers.
"""

from __future__ import annotations

import base64
import logging
from typing import Any, Callable, Optional

from playwright.sync_api import Locator as PwLocator, Page as PwPage
from appium.webdriver import Remote as MobileDriver
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import NoSuchElementException, TimeoutException as SelTimeoutException

from autofw.core.constants import DEFAULT_TIMEOUT_MS
from autofw.core.exceptions import ElementException, HealingException
from autofw.healing import HealingOrchestrator
from autofw.locator import Locator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Strategy → driver method mapping
# ---------------------------------------------------------------------------

PLAYWRIGHT_RESOLVERS: dict[str, Callable[..., PwLocator]] = {
    "css": lambda page, v, **kw: page.locator(v, **kw),
    "xpath": lambda page, v, **kw: page.locator(v, **kw),
    "text": lambda page, v, **kw: page.get_by_text(v, exact=True, **kw),
    "role": lambda page, d, **kw: page.get_by_role(d["role"], name=d.get("name"), **kw),
    "label": lambda page, v, **kw: page.get_by_label(v, exact=True, **kw),
    "placeholder": lambda page, v, **kw: page.get_by_placeholder(v, **kw),
    "test_id": lambda page, v, **kw: page.get_by_test_id(v, **kw),
    "alt_text": lambda page, v, **kw: page.get_by_alt_text(v, **kw),
    "title": lambda page, v, **kw: page.locator(f'[title="{v}"]', **kw),
    "id": lambda page, v, **kw: page.locator(f"#{v}", **kw),
}

APPIUM_BY_MAP: dict[str, str] = {
    "accessibility_id": AppiumBy.ACCESSIBILITY_ID,
    "id": AppiumBy.ID,
    "xpath": AppiumBy.XPATH,
    "class_name": AppiumBy.CLASS_NAME,
    "android_ui_automator": AppiumBy.ANDROID_UIAUTOMATOR,
    "ios_predicate": AppiumBy.IOS_PREDICATE,
    "ios_class_chain": AppiumBy.IOS_CLASS_CHAIN,
    "name": AppiumBy.NAME,
}


class BaseElement:
    """
    Unified element with cross-platform support and AI auto-healing.

    Usage:
        login_btn = BaseElement(
            locator=LoginPage.LOGIN_BUTTON,
            page=login_page,
            name="Login button",
        )
        login_btn.click()
        login_btn.type("hello")
    """

    def __init__(
        self,
        locator: Locator,
        page: Any,  # BasePage instance
        name: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT_MS,
    ):
        self._locator_def = locator
        self._page = page
        self._name = name or locator.name
        self._timeout = timeout
        self._healed_locator: Optional[dict[str, Any]] = None
        self._healing_source: Optional[str] = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return self._name

    @property
    def was_healed(self) -> bool:
        return self._healed_locator is not None

    @property
    def healing_source(self) -> Optional[str]:
        return self._healing_source

    @property
    def _driver(self) -> Any:
        """Shortcut to the underlying driver."""
        return self._page.driver

    @property
    def _platform(self) -> str:
        return self._page.platform

    # ------------------------------------------------------------------
    # Public interaction API
    # ------------------------------------------------------------------

    def click(self, **kwargs) -> "BaseElement":
        """Click the element with auto-healing."""
        self._execute("click", **kwargs)
        return self

    def type(self, text: str, **kwargs) -> "BaseElement":
        """Type text into the element with auto-healing."""
        self._execute("fill" if self._is_web else "type", text=text, **kwargs)
        return self

    def clear(self, **kwargs) -> "BaseElement":
        """Clear the element."""
        self._execute("clear", **kwargs)
        return self

    def get_text(self, **kwargs) -> str:
        """Get visible text content."""
        return self._execute("text_content" if self._is_web else "text", **kwargs)

    def get_attribute(self, name: str, **kwargs) -> Optional[str]:
        """Get element attribute value."""
        return self._execute("get_attribute", attr_name=name, **kwargs)

    def is_visible(self, **kwargs) -> bool:
        """Check if element is visible."""
        try:
            self._execute("is_visible", **kwargs)
            return True
        except ElementException:
            return False

    def is_enabled(self, **kwargs) -> bool:
        """Check if element is enabled."""
        try:
            self._execute("is_enabled", **kwargs)
            return True
        except ElementException:
            return False

    def wait_until_visible(self, timeout: Optional[int] = None, **kwargs) -> "BaseElement":
        """Wait for element to be visible."""
        self._execute("wait_for_visible", timeout=timeout, **kwargs)
        return self

    def hover(self, **kwargs) -> "BaseElement":
        """Hover over the element."""
        self._execute("hover", **kwargs)
        return self

    def scroll_into_view(self, **kwargs) -> "BaseElement":
        """Scroll element into view."""
        self._execute("scroll_into_view", **kwargs)
        return self

    def select_option(self, value: str, **kwargs) -> "BaseElement":
        """Select an option from a dropdown/select."""
        self._execute("select_option", select_value=value, **kwargs)
        return self

    # ------------------------------------------------------------------
    # Internal — execution with healing
    # ------------------------------------------------------------------

    @property
    def _is_web(self) -> bool:
        return self._platform == "web"

    def _execute(self, action: str, **kwargs) -> Any:
        """Execute an action with automatic healing on failure."""
        try:
            element = self._resolve_element()
            return self._perform_action(element, action, **kwargs)
        except (ElementException, HealingException) as e:
            raise e
        except Exception as e:
            logger.warning(
                "[%s] Action '%s' failed on '%s': %s. Attempting healing...",
                self._platform,
                action,
                self._name,
                e,
            )
            return self._heal_and_retry(action, **kwargs)

    def _resolve_element(self) -> Any:
        """Resolve the element using current (or healed) locator."""
        locator_dict = self._healed_locator or self._locator_def.for_platform(self._platform)

        if self._is_web:
            return self._resolve_playwright(locator_dict)
        else:
            return self._resolve_appium(locator_dict)

    def _resolve_playwright(self, locator_dict: dict[str, Any]) -> PwLocator:
        """Resolve element via Playwright."""
        page: PwPage = self._driver

        for strategy_key, value_or_dict in locator_dict.items():
            resolver = PLAYWRIGHT_RESOLVERS.get(strategy_key)
            if resolver:
                try:
                    if strategy_key == "role":
                        element = resolver(page, value_or_dict)
                    else:
                        element = resolver(page, value_or_dict)
                    element.wait_for(state="attached", timeout=self._timeout)
                    return element
                except Exception:
                    continue

        raise ElementException(
            f"Could not resolve '{self._name}' with any Playwright strategy: {locator_dict}"
        )

    def _resolve_appium(self, locator_dict: dict[str, Any]) -> Any:
        """Resolve element via Appium."""
        driver: MobileDriver = self._driver

        for strategy_key, value in locator_dict.items():
            by = APPIUM_BY_MAP.get(strategy_key)
            if by:
                try:
                    return driver.find_element(by, value)
                except (NoSuchElementException, Exception):
                    continue

        raise ElementException(
            f"Could not resolve '{self._name}' with any Appium strategy: {locator_dict}"
        )

    def _perform_action(self, element: Any, action: str, **kwargs) -> Any:
        """Perform a named action on a resolved element."""
        if self._is_web:
            return self._perform_playwright_action(element, action, **kwargs)
        return self._perform_appium_action(element, action, **kwargs)

    def _perform_playwright_action(self, el: PwLocator, action: str, **kwargs) -> Any:
        actions = {
            "click": lambda: el.click(**{k: v for k, v in kwargs.items() if k != "text"}),
            "fill": lambda: el.fill(kwargs["text"]),
            "type": lambda: el.fill(kwargs["text"]),
            "clear": lambda: el.clear(),
            "text_content": lambda: el.text_content(),
            "inner_text": lambda: el.inner_text(),
            "get_attribute": lambda: el.get_attribute(kwargs["attr_name"]),
            "is_visible": lambda: el.is_visible(),
            "is_enabled": lambda: el.is_enabled(),
            "wait_for_visible": lambda: el.wait_for(state="visible", timeout=kwargs.get("timeout", self._timeout)),
            "hover": lambda: el.hover(),
            "scroll_into_view": lambda: el.scroll_into_view_if_needed(),
            "select_option": lambda: el.select_option(kwargs["select_value"]),
            "input_value": lambda: el.input_value(),
        }
        fn = actions.get(action)
        if fn is None:
            raise ElementException(f"Unknown Playwright action: {action}")
        return fn()

    def _perform_appium_action(self, el: Any, action: str, **kwargs) -> Any:
        actions = {
            "click": lambda: el.click(),
            "type": lambda: el.send_keys(kwargs["text"]),
            "clear": lambda: el.clear(),
            "text": lambda: el.text,
            "get_attribute": lambda: el.get_attribute(kwargs["attr_name"]),
            "is_visible": lambda: el.is_displayed(),
            "is_enabled": lambda: el.is_enabled(),
            "hover": lambda: None,  # Appium has no direct hover
            "scroll_into_view": lambda: el.location_once_scrolled_into_view,
            "select_option": lambda: el.send_keys(kwargs["select_value"]),
        }
        fn = actions.get(action)
        if fn is None:
            raise ElementException(f"Unknown Appium action: {action}")
        return fn()

    def _heal_and_retry(self, action: str, **kwargs) -> Any:
        """
        Trigger the healing pipeline and retry the action once.

        Captures page source (and screenshot for web) as context for the healer.
        """
        orchestrator: HealingOrchestrator = self._page.healing_orchestrator
        element_context = self._locator_def.to_healing_context(self._platform)

        # Capture page source
        try:
            if self._is_web:
                page_source = self._driver.content()
            else:
                page_source = self._driver.page_source
        except Exception as e:
            logger.warning("Page source capture failed: %s", e)
            page_source = ""

        # Screenshot capture function
        def _get_screenshot() -> str:
            if self._is_web:
                return base64.b64encode(self._driver.screenshot(full_page=True)).decode("utf-8")
            else:
                return base64.b64encode(self._driver.get_screenshot_as_png()).decode("utf-8")

        try:
            result = orchestrator.heal(
                platform=self._platform,
                element_context=element_context,
                page_source=page_source,
                get_screenshot=_get_screenshot if self._page.config.healing.llm.include_screenshot else None,
            )
        except HealingException:
            raise ElementException(
                f"All healing methods failed for '{self._name}' "
                f"(action: {action})"
            )

        healed_locator = result["locator"]
        self._healed_locator = healed_locator
        self._healing_source = result.get("source", "unknown")

        logger.info(
            "[HEAL] '%s' healed via %s: %s — %s",
            self._name,
            result["source"],
            healed_locator,
            result.get("reason", ""),
        )

        # Retry with healed locator
        element = self._resolve_element()
        return self._perform_action(element, action, **kwargs)
