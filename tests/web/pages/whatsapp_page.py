"""
Example web page object.

Illustrates best practices for defining locators and page interactions.
"""

from autofw.locator import Locator
from autofw.pages import BasePage
from tests.web.pages.sample_page import SampleWebPage


class WhatsappWebPage(BasePage):
    """
    WhatsApp page — example page object.

    Usage:
        whatsapp_page = WhatsappWebPage(driver_factory, config, healing)
        whatsapp_page.navigate("https://web.whatsapp.com")
    """

    URL = ""

    USERNAME_INPUT = Locator(
        name="Username/Email input",
        web={"placeholder": "Email address"},
        description="Email or username text field on the login form",
    )

    def navigate_to(self, base_url: str) -> "WhatsappWebPage":
        """Navigate to the WhatsApp page."""
        self.navigate(f"{base_url}{self.URL}")
        self.wait_for_load_state("networkidle")
        return self
