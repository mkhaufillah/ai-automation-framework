"""
Example iOS page object + test for a fictional login/onboarding flow.
"""

import pytest

from autofw.core.config import AutomationConfig
from autofw.driver_factory import DriverFactory
from autofw.healing import HealingOrchestrator
from tests.ios.pages.sample_page import SampleiOSPage

@pytest.mark.ios
class TestiOSSample:
    """iOS sample screen tests."""

    @pytest.fixture
    def sample_page(
        self,
        autofw_driver_factory: DriverFactory,
        autofw_config: AutomationConfig,
        autofw_healing: HealingOrchestrator,
    ) -> SampleiOSPage:
        return SampleiOSPage(autofw_driver_factory, autofw_config, autofw_healing)

    def test_email_entry(self, sample_page: SampleiOSPage):
        """Test entering an email address."""
        sample_page.enter_email("test@example.com")
        # Verify we moved past email entry
