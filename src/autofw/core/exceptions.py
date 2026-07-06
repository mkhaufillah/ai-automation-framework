"""
Custom exceptions for the automation framework.
"""


class AutomationException(Exception):
    """Base exception for all framework errors."""


class ConfigException(AutomationException):
    """Configuration loading or validation errors."""


class DriverException(AutomationException):
    """WebDriver or Appium driver initialization/fatal errors."""


class ElementException(AutomationException):
    """Element interaction failures."""


class LocatorException(AutomationException):
    """Locator resolution failures."""


class TimeoutException(ElementException):
    """Element not found within timeout."""


class HealingException(AutomationException):
    """AI or heuristic healing failures."""


class HeuristicHealingException(HealingException):
    """Heuristic fallback all exhausted."""


class LLMHealingException(HealingException):
    """LLM-based healing failed (API error, empty response, etc.)."""


class PlatformNotSupported(AutomationException):
    """Requested platform is not configured/supported."""
