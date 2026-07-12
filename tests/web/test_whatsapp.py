"""
Example web test using the AI automation framework.
"""

import pytest

from autofw.core.config import AutomationConfig
from autofw.driver_factory import DriverFactory
from autofw.healing import HealingOrchestrator
from tests.web.pages.whatsapp_page import WhatsappWebPage
from autofw.core.constants import DEFAULT_TIMEOUT_MS


@pytest.mark.web
@pytest.mark.smoke
class TestWebWhatsapp:
    """Test suite for the login page."""

    @pytest.fixture
    def whatsapp_page(
        self,
        autofw_driver_factory: DriverFactory,
        autofw_config: AutomationConfig,
        autofw_healing: HealingOrchestrator,
    ) -> WhatsappWebPage:
        """Create a WhatsappWebPage instance for testing."""
        return WhatsappWebPage(autofw_driver_factory, autofw_config, autofw_healing)

    def test_login_with_valid_credentials(self, whatsapp_page: WhatsappWebPage):
        """Test successful login flow."""
        whatsapp_page.navigate_to("https://web.whatsapp.com")
        whatsapp_page.get_qr_code_data()
        assert whatsapp_page.qr_data is not None, "QR code data should not be None."
        # Wait for 10 seconds to allow user to scan the QR code
        whatsapp_page.printout_qr_code_data(10_000)

    @pytest.mark.healing
    def test_healing_on_locator_change(self, whatsapp_page: WhatsappWebPage):
        """
        Test that the AI healing system can recover when a locator changes.

        This test validates the auto-healing mechanism by modifying the
        page's element attributes (simulating a UI update) and confirming
        the framework still finds the element.
        """
        whatsapp_page.navigate_to("https://web.whatsapp.com")

        whatsapp_page.element(whatsapp_page.QR_CODE).wait_until_visible(
            timeout=DEFAULT_TIMEOUT_MS)
