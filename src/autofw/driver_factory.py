"""
Driver factory — creates and manages Playwright (web) and Appium (mobile) drivers.

Usage:
    factory = DriverFactory(config)
    driver = factory.create_driver()
    # ... use driver ...
    factory.quit_driver()
"""

from __future__ import annotations

import atexit
from typing import Any, Optional

from appium import webdriver as appium_webdriver
from appium.options.android import UiAutomator2Options
from appium.options.ios import XCUITestOptions
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from autofw.core.config import AutomationConfig
from autofw.core.constants import Platform
from autofw.core.exceptions import DriverException


class DriverFactory:
    """Factory that creates the appropriate driver based on config."""

    def __init__(self, config: AutomationConfig):
        self.config = config
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._appium_driver: Optional[appium_webdriver.Remote] = None

        atexit.register(self.quit_driver)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def page(self) -> Page:
        """The active Playwright Page (web only)."""
        if self._page is None:
            raise DriverException("No active Playwright page. Call create_driver() first.")
        return self._page

    @property
    def mobile_driver(self) -> appium_webdriver.Remote:
        """The active Appium driver (mobile only)."""
        if self._appium_driver is None:
            raise DriverException("No active Appium driver. Call create_driver() first.")
        return self._appium_driver

    @property
    def raw_driver(self) -> Any:
        """Return whatever driver is active (Page for web, Remote for mobile)."""
        if self.config.is_web:
            return self.page
        return self.mobile_driver

    def create_driver(self) -> Any:
        """Create the appropriate driver based on the current platform config."""
        platform = self.config.platform
        if platform == Platform.WEB:
            return self._create_playwright()
        elif platform == Platform.ANDROID:
            return self._create_android()
        elif platform == Platform.IOS:
            return self._create_ios()
        else:
            raise DriverException(f"Unsupported platform: {platform}")

    def quit_driver(self) -> None:
        """Tear down all drivers cleanly."""
        if self._appium_driver:
            try:
                self._appium_driver.quit()
            except Exception:
                pass
            self._appium_driver = None

        if self._page:
            try:
                self._page.close()
            except Exception:
                pass
            self._page = None

        if self._context:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None

        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None

        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    # ------------------------------------------------------------------
    # Playwright (Web)
    # ------------------------------------------------------------------

    def _create_playwright(self) -> Page:
        if self._page:
            return self._page

        try:
            self._playwright = sync_playwright().start()
        except Exception as e:
            raise DriverException(f"Failed to start Playwright: {e}") from e

        wc = self.config.web
        browser_type = getattr(self._playwright, wc.browser, None)
        if browser_type is None:
            raise DriverException(f"Unsupported browser: {wc.browser}")

        try:
            self._browser = browser_type.launch(
                headless=wc.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-gpu",
                ],
            )
        except Exception as e:
            raise DriverException(f"Failed to launch {wc.browser}: {e}") from e

        self._context = self._browser.new_context(
            viewport={"width": wc.viewport["width"], "height": wc.viewport["height"]},
            locale=wc.locale,
            timezone_id=wc.timezone,
            record_video_dir="videos/" if wc.record_video else None,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        self._page = self._context.new_page()

        if wc.base_url:
            self._page.set_default_timeout(30_000)

        return self._page

    # ------------------------------------------------------------------
    # Appium — Android
    # ------------------------------------------------------------------

    def _create_android(self) -> appium_webdriver.Remote:
        if self._appium_driver:
            return self._appium_driver

        ac = self.config.android
        options = UiAutomator2Options()

        options.platform_name = "Android"
        options.automation_name = ac.automation_name

        if ac.app:
            options.app = ac.app
        if ac.app_package:
            options.app_package = ac.app_package
        if ac.app_activity:
            options.app_activity = ac.app_activity
        if ac.platform_version:
            options.platform_version = ac.platform_version
        if ac.device_name:
            options.device_name = ac.device_name
        if ac.udid:
            options.udid = ac.udid

        options.no_reset = ac.no_reset
        options.full_reset = ac.full_reset
        options.auto_grant_permissions = ac.auto_grant_permissions
        options.adb_exec_timeout = ac.adb_exec_timeout
        options.system_port = ac.system_port

        try:
            self._appium_driver = appium_webdriver.Remote(
                command_executor=ac.appium_url,
                options=options,
            )
        except Exception as e:
            raise DriverException(f"Failed to start Android driver: {e}") from e

        self._appium_driver.implicitly_wait(10)
        return self._appium_driver

    # ------------------------------------------------------------------
    # Appium — iOS
    # ------------------------------------------------------------------

    def _create_ios(self) -> appium_webdriver.Remote:
        if self._appium_driver:
            return self._appium_driver

        ic = self.config.ios
        options = XCUITestOptions()

        options.platform_name = "iOS"
        options.automation_name = ic.automation_name

        if ic.app:
            options.app = ic.app
        if ic.bundle_id:
            options.bundle_id = ic.bundle_id
        if ic.platform_version:
            options.platform_version = ic.platform_version
        if ic.device_name:
            options.device_name = ic.device_name
        if ic.udid:
            options.udid = ic.udid

        options.no_reset = ic.no_reset
        options.full_reset = ic.full_reset
        options.wda_port = ic.wda_port

        try:
            self._appium_driver = appium_webdriver.Remote(
                command_executor=ic.appium_url,
                options=options,
            )
        except Exception as e:
            raise DriverException(f"Failed to start iOS driver: {e}") from e

        self._appium_driver.implicitly_wait(10)
        return self._appium_driver
