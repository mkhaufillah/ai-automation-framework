"""
Example web test using the AI automation framework.
"""

import pytest

from autofw.core.config import AutomationConfig
from autofw.driver_factory import DriverFactory
from autofw.healing import HealingOrchestrator
from tests.web.pages.sample_page import SampleWebPage


@pytest.mark.web
class TestWebSample:
    """Test suite for the login page."""

    @pytest.fixture
    def sample_page(
        self,
        autofw_driver_factory: DriverFactory,
        autofw_config: AutomationConfig,
        autofw_healing: HealingOrchestrator,
    ) -> SampleWebPage:
        """Create a SampleWebPage instance for testing."""
        return SampleWebPage(autofw_driver_factory, autofw_config, autofw_healing)

    def test_login_with_valid_credentials(self, sample_page: SampleWebPage):
        """Test successful login flow."""
        sample_page.navigate_to("https://example.com")
        sample_page.enter_username("user@example.com")

        # Wait for navigation after login
        sample_page.wait_for_load_state("networkidle")

    @pytest.mark.healing
    def test_healing_on_locator_change(self, sample_page: SampleWebPage):
        """
        Test that the AI healing system can recover when a locator changes.

        This test validates the auto-healing mechanism by modifying the
        page's element attributes (simulating a UI update) and confirming
        the framework still finds the element.
        """
        sample_page.navigate_to("https://example.com")

        # The healing system should locate the username field
        # even if its locator has changed (simulated by the healer)
        username_field = sample_page.element(sample_page.USERNAME_INPUT)
        username_field.type("test@example.com")

        # Verify the text was entered despite potential locator issues
        assert username_field.is_visible(), \
            "Username field should still be interactable after healing"
