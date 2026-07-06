"""
Example web page object for a fictional login page.

Illustrates best practices for defining locators and page interactions.
"""

from autofw.locator import Locator
from autofw.pages import BasePage


class LoginPage(BasePage):
    """
    Login page — example page object.

    Usage:
        login_page = LoginPage(driver_factory, config, healing)
        login_page.navigate("https://example.com/login")
        login_page.login("user@example.com", "securePass123!")
    """

    # ------------------------------------------------------------------
    # Locators
    # ------------------------------------------------------------------

    URL = "/login"

    USERNAME_INPUT = Locator(
        name="Username/Email input",
        web={"placeholder": "Email address"},
        android={"accessibility_id": "emailInput"},
        ios={"accessibility_id": "emailInput"},
        description="Email or username text field on the login form",
    )

    PASSWORD_INPUT = Locator(
        name="Password input",
        web={"placeholder": "Password"},
        android={"accessibility_id": "passwordInput"},
        ios={"accessibility_id": "passwordInput"},
        description="Password field on the login form",
    )

    LOGIN_BUTTON = Locator(
        name="Login button",
        web={"role": "button", "name": "Sign in"},
        android={"accessibility_id": "loginButton"},
        ios={"accessibility_id": "loginButton"},
        description="Primary sign-in CTA button",
    )

    ERROR_MESSAGE = Locator(
        name="Login error message",
        web={"test_id": "login-error"},
        android={"id": "com.example.app:id/errorText"},
        ios={"accessibility_id": "errorLabel"},
        description="Error message shown on failed login",
    )

    FORGOT_PASSWORD_LINK = Locator(
        name="Forgot password link",
        web={"role": "link", "name": "Forgot password?"},
        android={"accessibility_id": "forgotPasswordLink"},
        ios={"accessibility_id": "forgotPasswordLink"},
        description="Forgot password navigation link",
    )

    REMEMBER_ME_CHECKBOX = Locator(
        name="Remember me checkbox",
        web={"label": "Remember me"},
        android={"accessibility_id": "rememberMeCheck"},
        ios={"accessibility_id": "rememberMeCheck"},
        description="Remember me toggle checkbox",
    )

    # ------------------------------------------------------------------
    # Page actions
    # ------------------------------------------------------------------

    def navigate_to(self, base_url: str) -> "LoginPage":
        """Navigate to the login page."""
        self.navigate(f"{base_url}{self.URL}")
        self.wait_for_load_state("networkidle")
        return self

    def enter_username(self, username: str) -> "LoginPage":
        """Type username into the email field."""
        self.element(self.USERNAME_INPUT).type(username)
        return self

    def enter_password(self, password: str) -> "LoginPage":
        """Type password into the password field."""
        self.element(self.PASSWORD_INPUT).type(password)
        return self

    def click_login(self) -> "LoginPage":
        """Click the sign-in button."""
        self.element(self.LOGIN_BUTTON).click()
        return self

    def login(self, username: str, password: str) -> "LoginPage":
        """Complete login flow: enter credentials + submit."""
        return (
            self.enter_username(username)
            .enter_password(password)
            .click_login()
        )

    def get_error_message(self) -> str:
        """Get the error message text (empty string if not visible)."""
        try:
            return self.element(self.ERROR_MESSAGE).get_text()
        except Exception:
            return ""

    def is_login_button_enabled(self) -> bool:
        """Check if the login button is clickable."""
        return self.element(self.LOGIN_BUTTON).is_enabled()

    def is_error_displayed(self) -> bool:
        """Check if login error is showing."""
        return self.element(self.ERROR_MESSAGE).is_visible()
