"""
Example Android page object + test.
"""

import pytest

from autofw.core.config import AutomationConfig
from autofw.driver_factory import DriverFactory
from autofw.healing import HealingOrchestrator
from tests.android.pages.sample_page import SampleAndroidPage


@pytest.mark.android
class TestAndroidSample:
    """Android sample tests."""

    @pytest.fixture
    def sample_page(
        self,
        autofw_driver_factory: DriverFactory,
        autofw_config: AutomationConfig,
        autofw_healing: HealingOrchestrator,
    ) -> SampleAndroidPage:
        return SampleAndroidPage(autofw_driver_factory, autofw_config, autofw_healing)

    def test_sample_page_skip(self, sample_page: SampleAndroidPage):
        """Test that skipping the sample page works."""
        sample_page.skip_sample_page()
        # Verify we're past the sample page (app main screen)

    @pytest.mark.healing
    def test_healing_on_changed_element(self, sample_page: SampleAndroidPage):
        """Test AI healing on Android when locator fails."""
        # Even if skip button locator has changed,
        # the healing system should find it
        skip = sample_page.element(sample_page.SKIP_BUTTON)
        assert skip.is_visible(), "Skip button should be found via healing if needed"
        skip.click()
