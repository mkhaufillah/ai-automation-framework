"""
Example web page object.

Illustrates best practices for defining locators and page interactions.
"""

from autofw.locator import Locator
from autofw.pages import BasePage


class SampleWebPage(BasePage):
    """
    Sample page — example page object.

    Usage:
        sample_page = SampleWebPage(driver_factory, config, healing)
        sample_page.navigate("https://example.com/sample")
        sample_page.enter_username("user@example.com")
    """

    URL = "/sample"

    USERNAME_INPUT = Locator(
        name="Username/Email input",
        web={"placeholder": "Email address"},
        description="Email or username text field on the login form",
    )

    def navigate_to(self, base_url: str) -> "SampleWebPage":
        """Navigate to the sample page."""
        self.navigate(f"{base_url}{self.URL}")
        self.wait_for_load_state("networkidle")
        return self

    def enter_username(self, username: str) -> "SampleWebPage":
        """Type username into the email field."""
        self.element(self.USERNAME_INPUT).type(username)
        return self
