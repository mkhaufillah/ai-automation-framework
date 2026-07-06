"""
Unit tests for locator system.
"""

import tempfile
from pathlib import Path

import pytest

from autofw.locator import Locator, LocatorManager


class TestLocator:
    """Validate Locator dataclass."""

    def test_creates_with_all_platforms(self):
        loc = Locator(
            name="test_element",
            web={"test_id": "el"},
            android={"accessibility_id": "el"},
            ios={"accessibility_id": "el"},
        )
        assert loc.for_platform("web") == {"test_id": "el"}
        assert loc.for_platform("android") == {"accessibility_id": "el"}
        assert loc.for_platform("ios") == {"accessibility_id": "el"}

    def test_platform_without_locator(self):
        loc = Locator(name="web_only", web={"css": "#btn"})
        assert loc.for_platform("android") == {}

    def test_learned_locator_takes_priority(self):
        loc = Locator(
            name="learned",
            web={"css": "#old"},
        )
        loc.learned["web"] = {"test_id": "new"}
        assert loc.for_platform("web") == {"test_id": "new"}

    def test_healing_context_includes_all_fields(self):
        loc = Locator(
            name="login_btn",
            web={"role": "button", "name": "Login"},
            description="The login button",
            parent_page="LoginPage",
        )
        ctx = loc.to_healing_context("web")
        assert ctx["name"] == "login_btn"
        assert ctx["description"] == "The login button"
        assert ctx["page"] == "LoginPage"
        assert ctx["platform"] == "web"
        assert "original_locator" in ctx

    def test_has_strategy(self):
        loc = Locator(name="multi", web={"css": "#x"}, android={"id": "y"})
        assert loc.has_strategy("web") is True
        assert loc.has_strategy("android") is True
        assert loc.has_strategy("ios") is False


class TestLocatorManager:
    """Validate LocatorManager file I/O."""

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = LocatorManager(tmp)

            loc = Locator(
                name="login_btn",
                web={"test_id": "login-btn"},
                description="Login CTA",
            )
            manager.save(loc)

            loaded = manager.load("login_btn")
            assert loaded is not None
            assert loaded.name == "login_btn"
            assert loaded.web == {"test_id": "login-btn"}

    def test_load_nonexistent(self):
        manager = LocatorManager("/tmp/nonexistent")
        assert manager.load("ghost") is None
