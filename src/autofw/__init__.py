"""
Framework package initializer.
"""

from autofw.core.config import AutomationConfig
from autofw.core.constants import Platform
from autofw.core.exceptions import AutomationException
from autofw.driver_factory import DriverFactory
from autofw.healing import HealingOrchestrator
from autofw.locator import Locator, LocatorManager
from autofw.pages import BasePage
from autofw.elements import BaseElement

__all__ = [
    "AutomationConfig",
    "Platform",
    "AutomationException",
    "DriverFactory",
    "HealingOrchestrator",
    "Locator",
    "LocatorManager",
    "BasePage",
    "BaseElement",
]
