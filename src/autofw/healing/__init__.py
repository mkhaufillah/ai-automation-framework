"""
Orchestrator for element healing.

Combines heuristic fallbacks → LLM healing → caching in a single pipeline.

Flow:
  1. Primary locator fails → HeuristicHealer tries N alternative strategies
  2. All heuristics fail → LLMHealer analyzes screenshot + page source
  3. LLM returns corrected locator → cached for future runs
  4. All healing fails → raise final ElementException
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from autofw.core.config import AutomationConfig
from autofw.core.exceptions import (
    HeuristicHealingException,
    LLMHealingException,
    HealingException,
)
from autofw.healing.ai_healer import LLMHealer
from autofw.healing.cache import HealingCache
from autofw.healing.heuristics import HeuristicHealer

logger = logging.getLogger(__name__)


class HealingOrchestrator:
    """
    Coordinates the full healing pipeline.

    Usage:
        orchestrator = HealingOrchestrator(config)
        result = orchestrator.heal(
            platform="web",
            element_context={"name": "login_btn", ...},
            page_source="<html>...</html>",
            get_screenshot=lambda: capture_base64(),
        )
    """

    def __init__(self, config: AutomationConfig):
        self.config = config
        self.heuristic_healer = HeuristicHealer(
            max_attempts=config.healing.heuristics.max_attempts,
        )
        self.llm_healer = LLMHealer(config) if config.healing.llm.enabled else None
        self.cache = HealingCache(config.healing.cache.db_path) if config.healing.cache.enabled else None

    def heal(
        self,
        platform: str,
        element_context: dict[str, Any],
        page_source: str,
        get_screenshot: Optional[callable] = None,
    ) -> dict[str, Any]:
        """
        Run the full healing pipeline.

        Returns:
            A dict with:
              - "locator": the healed locator dict
              - "source": "cache" | "heuristic" | "llm" | "failed"
              - "reason": explanation string
              - "confidence": "high" | "medium" | "low"

        Raises:
            HealingException: when all healing methods fail
        """
        page_name = element_context.get("page", "unknown")
        element_name = element_context.get("name", "unknown")

        # ---- Phase 0: Check cache first ----
        if self.cache:
            cached = self.cache.get(page_name, element_name, platform)
            if cached:
                logger.info("[HEAL] Cache hit for %s.%s", page_name, element_name)
                return {
                    "locator": cached,
                    "source": "cache",
                    "reason": "Reused previously healed locator from cache",
                    "confidence": "high",
                }

        # ---- Phase 1: Heuristic fallbacks ----
        if self.config.healing.heuristics.enabled:
            self.heuristic_healer.reset()
            for attempt in range(self.config.healing.heuristics.max_attempts):
                try:
                    healed = self.heuristic_healer.heal(platform, element_context.get("original_locator", {}))
                    logger.info("[HEAL] Heuristic attempt #%d produced: %s", attempt + 1, healed)

                    # Cache it so subsequent calls skip heuristics too
                    if self.cache:
                        self.cache.set(
                            page_name=page_name,
                            element_name=element_name,
                            platform=platform,
                            locator=healed,
                            confidence="medium",
                            reason=f"Heuristic fallback attempt #{attempt + 1}",
                        )

                    return {
                        "locator": healed,
                        "source": "heuristic",
                        "reason": f"Heuristic fallback attempt #{attempt + 1}",
                        "confidence": "medium",
                    }
                except HeuristicHealingException:
                    break
                except Exception as e:
                    logger.warning("[HEAL] Heuristic attempt #%d failed: %s", attempt + 1, e)

        # ---- Phase 2: LLM healing ----
        if self.llm_healer:
            screenshot_b64 = None
            if get_screenshot and self.config.healing.llm.include_screenshot:
                try:
                    screenshot_b64 = get_screenshot()
                except Exception as e:
                    logger.warning("[HEAL] Screenshot capture failed: %s", e)

            try:
                llm_result = self.llm_healer.heal(
                    element_context=element_context,
                    platform=platform,
                    page_source=page_source,
                    screenshot_base64=screenshot_b64,
                )
                healed_locator = llm_result.get("locator", {})
                confidence = llm_result.get("confidence", "medium")
                reason = llm_result.get("reason", "LLM-healed locator")

                # Cache it
                if self.cache and healed_locator:
                    self.cache.set(
                        page_name=page_name,
                        element_name=element_name,
                        platform=platform,
                        locator=healed_locator,
                        confidence=confidence,
                        reason=reason,
                    )

                return {
                    "locator": healed_locator,
                    "source": "llm",
                    "reason": reason,
                    "confidence": confidence,
                }
            except LLMHealingException as e:
                logger.error("[HEAL] LLM healing failed: %s", e)
            except Exception as e:
                logger.error("[HEAL] Unexpected LLM healing error: %s", e)

        # ---- Phase 3: All methods failed ----
        raise HealingException(
            f"All healing methods failed for '{element_name}' on page '{page_name}' "
            f"(platform: {platform})"
        )
