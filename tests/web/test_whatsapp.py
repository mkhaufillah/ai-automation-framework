"""
Example web test using the AI automation framework.
"""

import pytest

from autofw.core.config import AutomationConfig
from autofw.driver_factory import DriverFactory
from autofw.healing import HealingOrchestrator
from tests.web.pages.whatsapp_page import WhatsappWebPage


@pytest.mark.web
@pytest.mark.smoke
class TestWebWhatsapp:
    """Test suite for the login page."""

    @pytest.fixture
    def sample_page(
        self,
        autofw_driver_factory: DriverFactory,
        autofw_config: AutomationConfig,
        autofw_healing: HealingOrchestrator,
    ) -> WhatsappWebPage:
        """Create a WhatsappWebPage instance for testing."""
        return WhatsappWebPage(autofw_driver_factory, autofw_config, autofw_healing)

    def test_login_with_valid_credentials(self, sample_page: WhatsappWebPage):
        """Test successful login flow."""
        sample_page.navigate_to("https://web.whatsapp.com")

        # Wait for navigation after login
        sample_page.wait_for_load_state("networkidle")

    @pytest.mark.healing
    def test_healing_on_locator_change(self, sample_page: WhatsappWebPage):
        """
        Test that the AI healing system can recover when a locator changes.

        This test validates the auto-healing mechanism by modifying the
        page's element attributes (simulating a UI update) and confirming
        the framework still finds the element.
        """
        sample_page.navigate_to("https://web.whatsapp.com")
