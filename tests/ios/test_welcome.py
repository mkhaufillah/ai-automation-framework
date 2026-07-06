"""
Example iOS page object + test for a fictional login/onboarding flow.
"""

import pytest

from autofw.locator import Locator
from autofw.pages import BasePage
from autofw.core.config import AutomationConfig
from autofw.driver_factory import DriverFactory
from autofw.healing import HealingOrchestrator


# ---------------------------------------------------------------------------
# Page object
# ---------------------------------------------------------------------------

class WelcomePage(BasePage):
    """
    iOS welcome / login screen — example page object.
    """

    WELCOME_TITLE = Locator(
        name="Welcome title",
        ios={"accessibility_id": "welcomeTitle"},
        description="Welcome screen title label",
    )

    EMAIL_FIELD = Locator(
        name="Email input",
        ios={"accessibility_id": "emailTextField"},
        description="Email input text field",
    )

    CONTINUE_BUTTON = Locator(
        name="Continue button",
        ios={"accessibility_id": "continueButton"},
        description="Continue CTA button after entering email",
    )

    def enter_email(self, email: str) -> "WelcomePage":
        """Enter email and continue."""
        self.element(self.EMAIL_FIELD).type(email)
        self.element(self.CONTINUE_BUTTON).click()
        return self

    def is_welcome_screen(self) -> bool:
        """Check if we're on the welcome screen."""
        return self.element(self.WELCOME_TITLE).is_visible()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.ios
@pytest.mark.smoke
class TestiOSWelcome:
    """iOS welcome screen tests."""

    @pytest.fixture
    def welcome_page(
        self,
        autofw_driver_factory: DriverFactory,
        autofw_config: AutomationConfig,
        autofw_healing: HealingOrchestrator,
    ) -> WelcomePage:
        return WelcomePage(autofw_driver_factory, autofw_config, autofw_healing)

    def test_welcome_screen_loads(self, welcome_page: WelcomePage):
        """Verify the welcome screen renders."""
        assert welcome_page.is_welcome_screen(), \
            "Welcome screen should be visible"

    def test_email_entry(self, welcome_page: WelcomePage):
        """Test entering an email address."""
        welcome_page.enter_email("test@example.com")
        # Verify we moved past email entry
