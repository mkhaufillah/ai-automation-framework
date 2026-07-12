"""
Multi-platform locator definition.

A single logical element can have different locator strategies per platform.
The framework picks the right one at runtime.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class Locator:
    """
    A multi-platform element locator.

    Example:
        >>> login_btn = Locator(
        ...     name="Login button",
        ...     web={"role": "button", "name": "Log in"},
        ...     android={"accessibility_id": "loginButton"},
        ...     ios={"accessibility_id": "loginButton"},
        ...     description="Primary login CTA on the landing page",
        ... )
    """

    name: str
    """Human-readable name (used in AI healing context & logs)."""

    web: dict[str, Any] = field(default_factory=dict)
    """Playwright locator dict, e.g. {"role": "button", "name": "Submit"}."""

    android: dict[str, Any] = field(default_factory=dict)
    """Appium Android locator, e.g. {"accessibility_id": "login"}."""

    ios: dict[str, Any] = field(default_factory=dict)
    """Appium iOS locator, e.g. {"accessibility_id": "login"}."""

    description: str = ""
    """Contextual description of what this element does — used for AI healing hints."""

    parent_page: str = ""
    """Page object class name this locator belongs to (for context)."""

    learned: dict[str, Any] = field(default_factory=dict)
    """Runtime: healed/re-learned locator for the current session."""

    def for_platform(self, platform: str) -> dict[str, Any]:
        """Return the locator dict for the given platform.

        Prefers a learned (healed) locator if available for this platform.
        """
        if platform in self.learned:
            return self.learned[platform]
        return getattr(self, platform, {})

    def has_strategy(self, platform: str) -> bool:
        """Check if this locator has any strategy for the given platform."""
        return bool(self.for_platform(platform))

    def to_healing_context(self, platform: str) -> dict[str, Any]:
        """Serialize for the AI healer — what we know about this element."""
        return {
            "name": self.name,
            "description": self.description,
            "page": self.parent_page,
            "original_locator": self.for_platform(platform),
            "platform": platform,
        }

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, default=str)


class LocatorManager:
    """Loads and caches locators from JSON/YAML files."""
    def __init__(self, locators_dir: str | Path = "locators/"):
        self._locators_dir = Path(locators_dir)
        self._cache: dict[str, Locator] = {}

    def load(self, name: str) -> Locator | None:
        """Load a single locator by name from the locators directory."""
        if name in self._cache:
            return self._cache[name]

        for ext in (".json",):
            path = self._locators_dir / f"{name}{ext}"
            if path.exists():
                locator = self._from_file(path)
                self._cache[name] = locator
                return locator

        return None

    def load_all(self) -> dict[str, Locator]:
        """Load all locator files from the directory."""
        if not self._locators_dir.exists():
            return {}

        for path in sorted(self._locators_dir.rglob("*.json")):
            name = path.stem
            if name not in self._cache:
                self._cache[name] = self._from_file(path)

        return dict(self._cache)

    def save(self, locator: Locator) -> None:
        """Persist a single locator to disk."""
        self._locators_dir.mkdir(parents=True, exist_ok=True)
        path = self._locators_dir / f"{locator.name}.json"
        with open(path, "w") as f:
            f.write(locator.to_json())
        self._cache[locator.name] = locator

    @staticmethod
    def _from_file(path: Path) -> Locator:
        with open(path) as f:
            data = json.load(f)
        return Locator(**data)
