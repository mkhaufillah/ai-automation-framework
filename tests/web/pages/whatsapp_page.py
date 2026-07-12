"""
Example web page object.

Illustrates best practices for defining locators and page interactions.
"""
import io
import logging

from autofw.core.constants import LocatorStrategy, DEFAULT_TIMEOUT_MS
from autofw.locator import Locator
from autofw.pages import BasePage
from qrcode import QRCode

logger = logging.getLogger(__name__)


class WhatsappWebPage(BasePage):
    """
    WhatsApp page — example page object.

    Usage:
        whatsapp_page = WhatsappWebPage(driver_factory, config, healing)
        whatsapp_page.navigate("https://web.whatsapp.com")
    """

    URL = ""

    QR_CODE = Locator(
        name="QR Code",
        web={LocatorStrategy.XPATH: "//*[@data-testid='link-qr-code-hbhy5']"},
        description="QR code for linking device",
    )

    def navigate_to(self, base_url: str) -> "WhatsappWebPage":
        """Navigate to the WhatsApp page."""
        self.navigate(f"{base_url}{self.URL}")
        self.wait_for_load_state("networkidle")
        return self

    def get_qr_code_data(self) -> "WhatsappWebPage":
        """Get the QR code data."""
        self.element(self.QR_CODE).wait_until_visible(
            timeout=DEFAULT_TIMEOUT_MS)
        self.qr_data = self.element(self.QR_CODE).get_attribute("data-ref")
        return self

    def printout_qr_code_data(self, wait_time: int = 10) -> "WhatsappWebPage":
        """Print the QR code data."""
        # Print QR code to terminal for user to scan
        qr = QRCode()
        qr.add_data(self.qr_data)

        # Capture the print output into a string buffer
        buffer = io.StringIO()
        qr.print_ascii(out=buffer, invert=False)
        buffer.seek(0)
        qr_string = buffer.read()

        # Now you can log it or print it normally
        logger.info(qr_string)

        # Wait for a while to allow the user to scan the QR code
        self.wait(wait_time)

        return self
