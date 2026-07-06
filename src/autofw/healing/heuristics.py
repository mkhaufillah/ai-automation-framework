"""
Heuristic fallback strategies for element location.

When the primary locator fails, these heuristics try alternative strategies
before invoking the LLM healer — saves time and API cost.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from autofw.core.constants import (
    ANDROID_SPECIFIC_PRIORITY,
    IOS_SPECIFIC_PRIORITY,
    WEB_LOCATOR_PRIORITY,
    LocatorStrategy,
)
from autofw.core.exceptions import HeuristicHealingException

logger = logging.getLogger(__name__)


class HeuristicHealer:
    """
    Tries alternative locator strategies when the primary locator fails.

    Strategy resolution order (for web):
        test_id → id → role → label → placeholder → css → xpath → text → alt_text → title
    """

    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max_attempts
        self._attempt_count = 0

    @property
    def exhausted(self) -> bool:
        return self._attempt_count >= self.max_attempts

    def reset(self) -> None:
        self._attempt_count = 0

    def heal(
        self,
        platform: str,
        original_locator: dict[str, Any],
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Attempt to find the element using alternative strategies.

        Args:
            platform: 'web', 'android', or 'ios'
            original_locator: The locator dict that failed
            context: Optional additional context (page title, visible text, etc.)

        Returns:
            A new locator dict with an alternative strategy

        Raises:
            HeuristicHealingException: when all fallback strategies are exhausted
        """
        if self.exhausted:
            raise HeuristicHealingException(
                f"Heuristic healing exhausted after {self.max_attempts} attempts"
            )

        self._attempt_count += 1
        strategy_priority = self._get_priority(platform)

        # Determine original strategy
        original_strategy = self._detect_strategy(original_locator)
        fallbacks = [s for s in strategy_priority if s != original_strategy]

        if self._attempt_count > len(fallbacks):
            raise HeuristicHealingException("All heuristic fallbacks exhausted")

        chosen_strategy = fallbacks[self._attempt_count - 1]
        original_value = self._get_locator_value(original_locator)

        healed = self._build_fallback_locator(chosen_strategy, original_value, original_locator, context)

        logger.info(
            "Heuristic attempt #%d: %s → %s",
            self._attempt_count,
            original_strategy.value,
            chosen_strategy.value,
        )
        return healed

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_priority(self, platform: str) -> list[LocatorStrategy]:
        if platform == "android":
            return ANDROID_SPECIFIC_PRIORITY
        elif platform == "ios":
            return IOS_SPECIFIC_PRIORITY
        return WEB_LOCATOR_PRIORITY

    @staticmethod
    def _detect_strategy(locator: dict[str, Any]) -> LocatorStrategy:
        """Detect which strategy a locator dict uses."""
        key_map = {
            "css": LocatorStrategy.CSS,
            "css_selector": LocatorStrategy.CSS,
            "xpath": LocatorStrategy.XPATH,
            "text": LocatorStrategy.TEXT,
            "role": LocatorStrategy.ROLE,
            "label": LocatorStrategy.LABEL,
            "placeholder": LocatorStrategy.PLACEHOLDER,
            "test_id": LocatorStrategy.TEST_ID,
            "data_test_id": LocatorStrategy.TEST_ID,
            "alt": LocatorStrategy.ALT_TEXT,
            "alt_text": LocatorStrategy.ALT_TEXT,
            "title": LocatorStrategy.TITLE,
            "id": LocatorStrategy.ID,
            "name": LocatorStrategy.NAME,
            "class_name": LocatorStrategy.CLASS_NAME,
            "accessibility_id": LocatorStrategy.ACCESSIBILITY_ID,
            "android_ui_automator": LocatorStrategy.ANDROID_UI_AUTOMATOR,
            "ios_predicate": LocatorStrategy.IOS_PREDICATE,
            "ios_class_chain": LocatorStrategy.IOS_CLASS_CHAIN,
        }
        for key, strategy in key_map.items():
            if key in locator:
                return strategy
        return LocatorStrategy.CUSTOM

    @staticmethod
    def _get_locator_value(locator: dict[str, Any]) -> str:
        """Extract the best candidate value from a locator dict.

        For role-based locators like {"role": "button", "name": "Submit"},
        prefer the 'name' value (the visible/accessible text).
        For single-key locators like {"css": "#my-id"}, use that value.
        """
        # Prefer 'name' or 'text' or 'label' or 'placeholder' or 'value'
        for preferred in ("name", "text", "label", "placeholder", "value"):
            if preferred in locator and isinstance(locator[preferred], str) and locator[preferred]:
                return locator[preferred]

        # Fallback: first string value
        for v in locator.values():
            if isinstance(v, str) and v:
                return v
        return ""

    @staticmethod
    def _build_fallback_locator(
        strategy: LocatorStrategy,
        original_value: str,
        original_locator: dict[str, Any],
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Build a fallback locator dict for the given strategy."""
        # For web strategies
        strategy_to_key = {
            LocatorStrategy.CSS: "css",
            LocatorStrategy.XPATH: "xpath",
            LocatorStrategy.TEXT: "text",
            LocatorStrategy.ROLE: "role",
            LocatorStrategy.LABEL: "label",
            LocatorStrategy.PLACEHOLDER: "placeholder",
            LocatorStrategy.TEST_ID: "test_id",
            LocatorStrategy.ALT_TEXT: "alt_text",
            LocatorStrategy.TITLE: "title",
            LocatorStrategy.ID: "id",
            LocatorStrategy.NAME: "name",
            LocatorStrategy.CLASS_NAME: "class_name",
            LocatorStrategy.ACCESSIBILITY_ID: "accessibility_id",
            LocatorStrategy.ANDROID_UI_AUTOMATOR: "android_ui_automator",
            LocatorStrategy.IOS_PREDICATE: "ios_predicate",
            LocatorStrategy.IOS_CLASS_CHAIN: "ios_class_chain",
        }

        key = strategy_to_key.get(strategy, strategy.value)

        # Try to derive the value intelligently
        if strategy == LocatorStrategy.XPATH:
            if original_value and not original_value.startswith("//"):
                return {"xpath": f"//*[contains(text(), '{original_value}')]"}
            return {"xpath": original_value or "//*"}

        if strategy == LocatorStrategy.TEXT and original_value:
            return {"text": original_value}

        if strategy == LocatorStrategy.ROLE:
            # If original had a role/name, preserve name
            name = original_locator.get("name", original_value)
            return {"role": original_locator.get("role", "button"), "name": name}

        # Use original value for the new key
        if original_value:
            return {key: original_value}

        # If context has page text, try text match
        if context and "visible_texts" in context and context["visible_texts"]:
            for text in context["visible_texts"][:5]:
                if strategy == LocatorStrategy.XPATH:
                    return {"xpath": f"//*[contains(text(), '{text}')]"}
                if strategy == LocatorStrategy.TEXT:
                    return {"text": text}

        return {key: original_value or "*"}
