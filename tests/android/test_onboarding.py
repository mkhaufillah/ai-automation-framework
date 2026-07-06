"""
Example Android page object + test for a fictional onboarding flow.
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

class OnboardingPage(BasePage):
    """
    Android onboarding flow — example page object.
    """

    SKIP_BUTTON = Locator(
        name="Skip onboarding",
        android={"accessibility_id": "skipButton"},
        description="Skip button on the onboarding carousel",
    )

    NEXT_BUTTON = Locator(
        name="Next button",
        android={"accessibility_id": "nextButton"},
        description="Next button to advance onboarding",
    )

    GET_STARTED_BUTTON = Locator(
        name="Get started",
        android={"accessibility_id": "getStartedButton"},
        description="Final CTA to complete onboarding",
    )

    ONBOARDING_TITLE = Locator(
        name="Onboarding title",
        android={"id": "com.example.app:id/titleText"},
        description="Title text on each onboarding screen",
    )

    def skip_onboarding(self) -> "OnboardingPage":
        """Skip the entire onboarding flow."""
        self.element(self.SKIP_BUTTON).click()
        return self

    def go_through_onboarding(self, steps: int = 3) -> "OnboardingPage":
        """Tap 'Next' through all onboarding screens, then tap 'Get started'."""
        for _ in range(steps):
            self.element(self.NEXT_BUTTON).click()
        self.element(self.GET_STARTED_BUTTON).click()
        return self


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.android
@pytest.mark.smoke
class TestAndroidOnboarding:
    """Android onboarding tests."""

    @pytest.fixture
    def onboarding_page(
        self,
        autofw_driver_factory: DriverFactory,
        autofw_config: AutomationConfig,
        autofw_healing: HealingOrchestrator,
    ) -> OnboardingPage:
        return OnboardingPage(autofw_driver_factory, autofw_config, autofw_healing)

    def test_onboarding_skip(self, onboarding_page: OnboardingPage):
        """Test that skipping onboarding works."""
        onboarding_page.skip_onboarding()
        # Verify we're past onboarding (app main screen)

    def test_onboarding_complete(self, onboarding_page: OnboardingPage):
        """Test completing the full onboarding flow."""
        onboarding_page.go_through_onboarding(steps=3)
        # Verify we landed on the main screen

    @pytest.mark.healing
    def test_healing_on_changed_element(self, onboarding_page: OnboardingPage):
        """Test AI healing on Android when locator fails."""
        # Even if skip button locator has changed,
        # the healing system should find it
        skip = onboarding_page.element(onboarding_page.SKIP_BUTTON)
        assert skip.is_visible(), "Skip button should be found via healing if needed"
        skip.click()
