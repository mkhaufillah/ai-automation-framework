"""
AI-powered element locator healing using LLMs.

When heuristic fallbacks fail, this module:
  1. Captures a screenshot and page source (HTML/XML)
  2. Sends them to an LLM with context about the desired element
  3. Parses the LLM response into a corrected locator
  4. Returns the healed locator for retry
"""

from __future__ import annotations

import base64
import json
import logging
import re
from typing import Any, Optional

from autofw.core.config import AutomationConfig
from autofw.core.exceptions import LLMHealingException

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt template for the LLM healer
# ---------------------------------------------------------------------------

HEALING_SYSTEM_PROMPT = """You are an expert test automation engineer. Your task is to diagnose why an element locator failed and provide a corrected locator.

## Input you will receive:
1. **Element context**: Name, description, page, and the original locator that failed
2. **Platform**: web (Playwright), android (Appium), or ios (Appium)
3. **Page source**: The HTML (web) or XML hierarchy (mobile) of the current page
4. **Screenshot**: (optional) A screenshot of the current page

## Your task:
Analyze the page source and screenshot to find the correct element. Return ONLY a JSON object with the corrected locator.

## Response format — YOU MUST RESPOND WITH VALID JSON ONLY, no markdown wrapping:

For **web** (Playwright), valid locator keys:
- `{"css": "selector"}` — CSS selector
- `{"xpath": "//xpath"}` — XPath expression
- `{"text": "exact text"}` — Text content match
- `{"role": "button", "name": "Submit"}` — ARIA role + accessible name
- `{"label": "Email"}` — Label text (for form fields)
- `{"placeholder": "Enter email"}` — Placeholder text
- `{"test_id": "submit-btn"}` — data-testid attribute
- `{"alt_text": "logo"}` — Alt text on images
- `{"title": "Tooltip"}` — Title attribute

For **android** (Appium), valid locator keys:
- `{"accessibility_id": "login"}` — content-desc / accessibility label
- `{"id": "com.app:id/login"}` — Resource ID
- `{"xpath": "//android.widget.Button[@text='Login']"}` — XPath
- `{"class_name": "android.widget.Button"}` — Class name
- `{"android_ui_automator": "new UiSelector().text(\"Login\")"}` — UiAutomator2

For **ios** (Appium), valid locator keys:
- `{"accessibility_id": "loginButton"}` — accessibility identifier
- `{"id": "loginButton"}` — element name/id
- `{"xpath": "//XCUIElementTypeButton[@name='Login']"}` — XPath
- `{"class_name": "XCUIElementTypeButton"}` — Class name
- `{"ios_predicate": "name == 'Login'"}` — iOS predicate string
- `{"ios_class_chain": "**/XCUIElementTypeButton[`name == 'Login'`]"}` — iOS class chain

## Rules:
1. The page source is the ground truth — use it as your primary reference
2. If a screenshot is provided, use it for visual confirmation
3. Prefer the most stable, least fragile locator (test_id / accessibility_id > text > xpath)
4. If the element seems to have changed (different text, different position), note it in the `reason` field
5. Never return a locator you're not confident about — set `confidence` to "low" if uncertain

## Response JSON schema:
```json
{
  "locator": { "<strategy>": "<value>" },
  "reason": "Brief explanation of what changed and why this new locator works",
  "confidence": "high" | "medium" | "low"
}
```"""


class LLMHealer:
    """
    Uses an LLM to analyze page state and produce a corrected locator.

    Supports:
      - OpenAI API (or any OpenAI-compatible endpoint)
      - LiteLLM (for local models via Ollama, vLLM, etc.)
    """

    def __init__(self, config: AutomationConfig):
        self.config = config.healing.llm

    def heal(
        self,
        element_context: dict[str, Any],
        platform: str,
        page_source: str,
        screenshot_base64: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Attempt to heal a locator using an LLM.

        Args:
            element_context: Dict with name, description, page, original_locator
            platform: 'web', 'android', or 'ios'
            page_source: HTML (web) or XML (mobile) page source
            screenshot_base64: Optional base64-encoded screenshot

        Returns:
            Dict with 'locator', 'reason', and 'confidence' keys.

        Raises:
            LLMHealingException: on API failure or invalid response
        """
        api_key = self.config.resolved_api_key
        if not api_key:
            raise LLMHealingException(
                "LLM healing is enabled but no API key configured. "
                "Set HEALING_API_KEY, OPENAI_API_KEY, or healing.llm.api_key in config."
            )

        messages = self._build_messages(element_context, platform, page_source, screenshot_base64)

        try:
            response = self._call_llm(messages, api_key)
        except Exception as e:
            raise LLMHealingException(f"LLM API call failed: {e}") from e

        result = self._parse_response(response)
        logger.info(
            "LLM healing result for '%s': confidence=%s, reason=%s",
            element_context.get("name", "unknown"),
            result.get("confidence", "unknown"),
            result.get("reason", ""),
        )
        return result

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        element_context: dict[str, Any],
        platform: str,
        page_source: str,
        screenshot_base64: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Build the message list for the LLM chat completion."""

        user_content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    f"## Element Context\n"
                    f"- **Name**: {element_context.get('name', 'unknown')}\n"
                    f"- **Description**: {element_context.get('description', 'N/A')}\n"
                    f"- **Page**: {element_context.get('page', 'N/A')}\n"
                    f"- **Platform**: {platform}\n"
                    f"- **Original Locator**: {json.dumps(element_context.get('original_locator', {}))}\n\n"
                    f"## Page Source\n"
                    f"```\n{page_source[:8000]}\n```\n"
                    f"{'---' if len(page_source) > 8000 else ''}"
                ),
            }
        ]

        if screenshot_base64 and self.config.include_screenshot:
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{screenshot_base64}",
                        "detail": "high",
                    },
                }
            )

        messages = [
            {"role": "system", "content": HEALING_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
        return messages

    def _call_llm(self, messages: list[dict[str, Any]], api_key: str) -> str:
        """Call the LLM API (OpenAI-compatible or LiteLLM)."""
        if self.config.provider == "litellm":
            return self._call_litellm(messages)
        return self._call_openai(messages, api_key)

    def _call_openai(self, messages: list[dict[str, Any]], api_key: str) -> str:
        """Call OpenAI / OpenAI-compatible endpoints."""
        from openai import OpenAI

        kwargs = {"api_key": api_key}
        if self.config.api_base:
            kwargs["base_url"] = self.config.api_base

        client = OpenAI(**kwargs)
        response = client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            timeout=self.config.timeout,
        )
        return response.choices[0].message.content or ""

    def _call_litellm(self, messages: list[dict[str, Any]]) -> str:
        """Call LiteLLM (supports Ollama, vLLM, Anthropic, etc.)."""
        from litellm import completion

        response = completion(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            timeout=self.config.timeout,
            api_key=self.config.resolved_api_key,
            base_url=self.config.api_base or None,
        )
        return response.choices[0].message.content or ""

    def _parse_response(self, raw: str) -> dict[str, Any]:
        """Parse the LLM response into a structured result."""
        # Try to extract JSON from the response (it might have markdown fences)
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not json_match:
            raise LLMHealingException(f"No JSON found in LLM response:\n{raw[:500]}")

        try:
            result = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            raise LLMHealingException(f"Failed to parse LLM response JSON: {e}\nResponse:\n{raw[:500]}")

        if "locator" not in result:
            raise LLMHealingException(f"LLM response missing 'locator' key:\n{result}")

        return result
