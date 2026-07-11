from autofw.locator import Locator
from autofw.pages import BasePage


class SampleAndroidPage(BasePage):
    """
    Android sample page — example page object.
    """

    SKIP_BUTTON = Locator(
        name="Skip sample page",
        android={"accessibility_id": "skipButton"},
        description="Skip button on the sample page carousel",
    )

    def skip_sample_page(self) -> "SampleAndroidPage":
        """Skip the entire sample page flow."""
        self.element(self.SKIP_BUTTON).click()
        return self
