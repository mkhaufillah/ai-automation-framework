"""
Example iOS page object + test.
"""

from autofw.locator import Locator
from autofw.pages import BasePage


class SampleiOSPage(BasePage):
    """
    iOS sample page screen — example page object.
    """

    EMAIL_FIELD = Locator(
        name="Email input",
        ios={"accessibility_id": "emailTextField"},
        description="Email input text field",
    )

    CONTINUE_BUTTON = Locator(
        name="Continue button",
        ios={"accessibility_id": "continueButton"},
        description="Continue CTA button after entering email",
    )

    def enter_email(self, email: str) -> "SampleiOSPage":
        """Enter email and continue."""
        self.element(self.EMAIL_FIELD).type(email)
        self.element(self.CONTINUE_BUTTON).click()
        return self
