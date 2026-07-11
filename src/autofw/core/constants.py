"""
Constants and enumerations for the automation framework.
"""

from __future__ import annotations

from enum import Enum


class Platform(str, Enum):
    """Supported automation platforms."""

    WEB = "web"
    ANDROID = "android"
    IOS = "ios"


class Browser(str, Enum):
    """Supported web browsers for Playwright."""

    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class ElementAction(str, Enum):
    """Element interaction actions — used in healing context for better AI hints."""

    CLICK = "click"
    TYPE = "type"
    CLEAR = "clear"
    GET_TEXT = "get_text"
    GET_ATTRIBUTE = "get_attribute"
    IS_VISIBLE = "is_visible"
    IS_ENABLED = "is_enabled"
    SELECT = "select"
    HOVER = "hover"
    SCROLL_INTO_VIEW = "scroll_into_view"
    WAIT_FOR_VISIBLE = "wait_for_visible"
    WAIT_FOR_ENABLED = "wait_for_enabled"


class LocatorStrategy(str, Enum):
    """Supported locator strategies across platforms."""

    # Playwright web strategies
    CSS = "css"
    XPATH = "xpath"
    TEXT = "text"
    ROLE = "role"
    LABEL = "label"
    PLACEHOLDER = "placeholder"
    TEST_ID = "test_id"
    ALT_TEXT = "alt_text"
    TITLE = "title"
    NTH = "nth"

    # Appium mobile strategies
    ACCESSIBILITY_ID = "accessibility_id"
    ID = "id"
    CLASS_NAME = "class_name"
    NAME = "name"
    ANDROID_UI_AUTOMATOR = "android_ui_automator"
    IOS_PREDICATE = "ios_predicate"
    IOS_CLASS_CHAIN = "ios_class_chain"
    IMAGE = "image"

    # Universal fallbacks
    CUSTOM = "custom"


# Priority order for heuristic fallback — ordered from most reliable to least
WEB_LOCATOR_PRIORITY: list[LocatorStrategy] = [
    LocatorStrategy.TEST_ID,
    LocatorStrategy.ID,
    LocatorStrategy.ROLE,
    LocatorStrategy.LABEL,
    LocatorStrategy.PLACEHOLDER,
    LocatorStrategy.CSS,
    LocatorStrategy.XPATH,
    LocatorStrategy.TEXT,
    LocatorStrategy.ALT_TEXT,
    LocatorStrategy.TITLE,
]

MOBILE_LOCATOR_PRIORITY: list[LocatorStrategy] = [
    LocatorStrategy.ACCESSIBILITY_ID,
    LocatorStrategy.ID,
    LocatorStrategy.NAME,
    LocatorStrategy.XPATH,
    LocatorStrategy.CLASS_NAME,
]

ANDROID_SPECIFIC_PRIORITY: list[LocatorStrategy] = [
    *MOBILE_LOCATOR_PRIORITY,
    LocatorStrategy.ANDROID_UI_AUTOMATOR,
]

IOS_SPECIFIC_PRIORITY: list[LocatorStrategy] = [
    *MOBILE_LOCATOR_PRIORITY,
    LocatorStrategy.IOS_PREDICATE,
    LocatorStrategy.IOS_CLASS_CHAIN,
]


# Maximum retries for element operations
DEFAULT_TIMEOUT_MS = 10_000  # 10 seconds
DEFAULT_POLL_INTERVAL_MS = 500  # 0.5 seconds
AI_HEALING_TIMEOUT_MS = 30_000  # 30 seconds allowed for AI healing
