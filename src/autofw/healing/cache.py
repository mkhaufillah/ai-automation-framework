"""
Caching layer for healed locators.

Persists healed locators to disk so the next test run can use them directly
without repeating the healing process.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class HealingCache:
    """
    Simple JSON-based cache for healed locators.

    Cache key: "{page_name}.{element_name}.{platform}"
    Cache value: The healed locator dict + metadata (timestamp, confidence).
    """

    def __init__(self, db_path: str = ".healing_cache.json"):
        self._path = Path(db_path)
        self._data: dict[str, dict[str, Any]] = {}
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, page_name: str, element_name: str, platform: str) -> Optional[dict[str, Any]]:
        """Get a cached healed locator, if available."""
        key = self._key(page_name, element_name, platform)
        entry = self._data.get(key)
        if entry:
            logger.debug("Healing cache HIT: %s", key)
            return entry.get("locator")
        logger.debug("Healing cache MISS: %s", key)
        return None

    def set(
        self,
        page_name: str,
        element_name: str,
        platform: str,
        locator: dict[str, Any],
        confidence: str = "medium",
        reason: str = "",
    ) -> None:
        """Store a healed locator in the cache."""
        key = self._key(page_name, element_name, platform)
        self._data[key] = {
            "locator": locator,
            "confidence": confidence,
            "reason": reason,
            "platform": platform,
            "healed_at": str(__import__("datetime").datetime.now()),
        }
        self._save()
        logger.info("Healing cache SAVED: %s → %s", key, locator)

    def invalidate(self, page_name: str, element_name: str, platform: str) -> None:
        """Remove a cached entry (e.g., if the healed locator also fails)."""
        key = self._key(page_name, element_name, platform)
        self._data.pop(key, None)
        self._save()

    def clear(self) -> None:
        """Clear the entire healing cache."""
        self._data.clear()
        self._save()
        logger.info("Healing cache cleared.")

    def get_all(self) -> dict[str, dict[str, Any]]:
        """Return all cached entries (useful for reporting)."""
        return dict(self._data)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _key(page: str, element: str, platform: str) -> str:
        return f"{page}.{element}.{platform}"

    def _load(self) -> None:
        if self._path.exists() and self._path.stat().st_size > 0:
            try:
                with open(self._path) as f:
                    self._data = json.load(f)
                logger.info("Loaded %d healing cache entries from %s", len(self._data), self._path)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load healing cache: %s", e)
                self._data = {}

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._path, "w") as f:
                json.dump(self._data, f, indent=2, default=str)
        except OSError as e:
            logger.warning("Failed to save healing cache: %s", e)
