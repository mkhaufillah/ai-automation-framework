"""
Screenshot utilities for capturing and encoding page state.
"""

from __future__ import annotations

import base64
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def capture_screenshot_base64(driver: Any, platform: str, full_page: bool = True) -> str:
    """Capture a screenshot and return it as a base64-encoded string."""
    try:
        if platform == "web":
            return base64.b64encode(driver.screenshot(full_page=full_page)).decode("utf-8")
        else:
            return base64.b64encode(driver.get_screenshot_as_png()).decode("utf-8")
    except Exception as e:
        logger.warning("Screenshot capture failed: %s", e)
        return ""


def save_screenshot(
    driver: Any,
    platform: str,
    name: str = "screenshot",
    output_dir: str = "reports/screenshots/",
) -> Optional[str]:
    """Save a screenshot to disk and return the file path."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}_{timestamp}.png"
    filepath = out / filename

    try:
        if platform == "web":
            driver.screenshot(path=str(filepath), full_page=True)
        else:
            driver.get_screenshot_as_file(str(filepath))
        logger.info("Screenshot saved: %s", filepath)
        return str(filepath)
    except Exception as e:
        logger.error("Failed to save screenshot: %s", e)
        return None
