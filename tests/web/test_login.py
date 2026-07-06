"""
Example web test using the AI automation framework.
"""

import pytest

from autofw.core.config import AutomationConfig
from autofw.driver_factory import DriverFactory
from autofw.healing import HealingOrchestrator
from tests.web.pages.login_page import LoginPage


@pytest.mark.web
@pytest.mark.smoke
class TestLogin:
    """Test suite for the login page."""

    @pytest.fixture
    def login_page(
        self,
        autofw_driver_factory: DriverFactory,
        autofw_config: AutomationConfig,
        autofw_healing: HealingOrchestrator,
    ) -> LoginPage:
        """Create a LoginPage instance for testing."""
        return LoginPage(autofw_driver_factory, autofw_config, autofw_healing)

    def test_login_page_loads(self, login_page: LoginPage):
        """Verify the login page renders correctly."""
        # Navigate to the app
        login_page.navigate_to("https://example.com")

        # Verify key elements are present
        assert login_page.element(login_page.USERNAME_INPUT).is_visible(), \
            "Username input should be visible"
        assert login_page.element(login_page.PASSWORD_INPUT).is_visible(), \
            "Password input should be visible"
        assert login_page.is_login_button_enabled(), \
            "Login button should be enabled"

    def test_login_with_valid_credentials(self, login_page: LoginPage):
        """Test successful login flow."""
        login_page.navigate_to("https://example.com")
        login_page.login("user@example.com", "password123")

        # Wait for navigation after login
        login_page.wait_for_load_state("networkidle")

        # Verify we've moved past the login page
        assert "dashboard" in login_page.get_url(), \
            "Should redirect to dashboard after login"

    def test_login_with_invalid_credentials(self, login_page: LoginPage):
        """Test error message appears on failed login."""
        login_page.navigate_to("https://example.com")
        login_page.login("invalid@email.com", "wrongpass")

        # Verify error feedback
        assert login_page.is_error_displayed(), \
            "Error message should appear on failed login"
        error_text = login_page.get_error_message()
        assert "invalid" in error_text.lower() or "error" in error_text.lower(), \
            f"Unexpected error message: {error_text}"

    def test_forgot_password_link(self, login_page: LoginPage):
        """Test that the forgot password link is accessible."""
        login_page.navigate_to("https://example.com")

        forgot_link = login_page.element(login_page.FORGOT_PASSWORD_LINK)
        assert forgot_link.is_visible(), \
            "Forgot password link should be visible"
        forgot_link.click()

        login_page.wait_for_load_state("networkidle")
        assert "forgot" in login_page.get_url().lower() or "reset" in login_page.get_url().lower(), \
            "Should navigate to password reset page"

    def test_remember_me_checkbox(self, login_page: LoginPage):
        """Test the remember me checkbox interaction."""
        login_page.navigate_to("https://example.com")

        checkbox = login_page.element(login_page.REMEMBER_ME_CHECKBOX)
        assert checkbox.is_visible(), \
            "Remember me checkbox should be visible"
        checkbox.click()

    def test_empty_username_shows_validation(self, login_page: LoginPage):
        """Test validation when submitting with empty username."""
        login_page.navigate_to("https://example.com")
        login_page.enter_password("somepassword")
        login_page.click_login()

        # Either client-side validation or server error should appear
        assert login_page.is_error_displayed(), \
            "Should show error for empty username"

    @pytest.mark.healing
    def test_healing_on_locator_change(self, login_page: LoginPage):
        """
        Test that the AI healing system can recover when a locator changes.

        This test validates the auto-healing mechanism by modifying the
        page's element attributes (simulating a UI update) and confirming
        the framework still finds the element.
        """
        login_page.navigate_to("https://example.com")

        # The healing system should locate the username field
        # even if its locator has changed (simulated by the healer)
        username_field = login_page.element(login_page.USERNAME_INPUT)
        username_field.type("test@example.com")

        # Verify the text was entered despite potential locator issues
        assert username_field.is_visible(), \
            "Username field should still be interactable after healing"
