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
        """Call the LLM API (OpenAI-compatible, LiteLLM, Gemini, Anthropic, or OpenCode)."""
        if self.config.provider == "litellm":
            return self._call_litellm(messages)
        elif self.config.provider == "gemini":
            return self._call_gemini(messages, api_key)
        elif self.config.provider == "anthropic":
            return self._call_anthropic(messages, api_key)
        elif self.config.provider == "opencode":
            return self._call_opencode(messages, api_key)
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

    def _call_gemini(self, messages: list[dict[str, Any]], api_key: str) -> str:
        """Call Google Gemini API."""
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise ImportError("Please install google-genai to use the gemini provider.")

        client = genai.Client(api_key=api_key)
        
        system_instruction = None
        gemini_contents = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                parts = []
                if isinstance(msg["content"], list):
                    for item in msg["content"]:
                        if item["type"] == "text":
                            parts.append(types.Part.from_text(text=item["text"]))
                        elif item["type"] == "image_url":
                            b64_data = item["image_url"]["url"].split(",", 1)[1]
                            image_bytes = base64.b64decode(b64_data)
                            parts.append(types.Part.from_bytes(data=image_bytes, mime_type="image/png"))
                else:
                    parts.append(types.Part.from_text(text=msg["content"]))
                gemini_contents.append(types.Content(role="user", parts=parts))

        config = types.GenerateContentConfig(
            temperature=self.config.temperature,
            max_output_tokens=self.config.max_tokens,
            system_instruction=system_instruction,
        )

        response = client.models.generate_content(
            model=self.config.model,
            contents=gemini_contents,
            config=config,
        )
        return response.text

    def _call_anthropic(self, messages: list[dict[str, Any]], api_key: str) -> str:
        """Call Anthropic API."""
        try:
            import anthropic
        except ImportError:
            raise ImportError("Please install anthropic to use the anthropic provider.")

        client = anthropic.Anthropic(api_key=api_key)
        if self.config.api_base:
            client.base_url = self.config.api_base

        system_instruction = ""
        anthropic_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                content_parts = []
                if isinstance(msg["content"], list):
                    for item in msg["content"]:
                        if item["type"] == "text":
                            content_parts.append({"type": "text", "text": item["text"]})
                        elif item["type"] == "image_url":
                            b64_data = item["image_url"]["url"].split(",", 1)[1]
                            content_parts.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": b64_data,
                                }
                            })
                else:
                    content_parts.append({"type": "text", "text": msg["content"]})
                
                anthropic_messages.append({"role": "user", "content": content_parts})

        response = client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            system=system_instruction,
            messages=anthropic_messages,
        )
        return response.content[0].text

    def _call_opencode(self, messages: list[dict[str, Any]], api_key: str) -> str:
        """Call OpenCode API."""
        import requests
        
        url = self.config.api_base or "https://api.opencode.so/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=self.config.timeout)
        response.raise_for_status()
        
        return response.json()["choices"][0]["message"]["content"]

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
