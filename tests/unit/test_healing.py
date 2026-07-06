"""
Unit tests for the healing module — no browser required.
"""

import tempfile
from pathlib import Path

import pytest

from autofw.core.config import AutomationConfig
from autofw.healing.heuristics import HeuristicHealer
from autofw.healing.cache import HealingCache
from autofw.healing import HealingOrchestrator
from autofw.locator import Locator


# ---------------------------------------------------------------------------
# Heuristic Healer
# ---------------------------------------------------------------------------

class TestHeuristicHealer:
    """Validate heuristic fallback strategies."""

    def test_reset_tracks_attempts(self):
        healer = HeuristicHealer(max_attempts=3)
        assert healer.exhausted is False
        assert healer._attempt_count == 0

        healer.heal("web", {"css": "#login-btn"})
        assert healer._attempt_count == 1

        healer.reset()
        assert healer._attempt_count == 0

    def test_web_fallback_order(self):
        """Web fallbacks should go through priority: test_id → id → role → ..."""
        healer = HeuristicHealer(max_attempts=3)

        r1 = healer.heal("web", {"css": "#login-btn"})
        # First fallback should be the first strategy
        # that isn't 'css' in WEB_LOCATOR_PRIORITY
        assert "test_id" in r1 or "id" in r1 or "role" in r1

    def test_android_fallback(self):
        healer = HeuristicHealer(max_attempts=2)
        r1 = healer.heal("android", {"id": "com.example:id/btn"})
        assert "accessibility_id" in r1 or "name" in r1 or "xpath" in r1

    def test_ios_fallback(self):
        healer = HeuristicHealer(max_attempts=2)
        r1 = healer.heal("ios", {"class_name": "XCUIElementTypeButton"})
        assert "accessibility_id" in r1 or "id" in r1 or "name" in r1

    def test_role_locator_prefers_name(self):
        """Role locators should use the 'name' field for value."""
        healer = HeuristicHealer(max_attempts=1)
        result = healer.heal("web", {"role": "button", "name": "Sign in"})

        # The 'test_id' or fallback should contain 'Sign in' as value
        values = " ".join(str(v) for v in result.values())
        assert "Sign in" in values


# ---------------------------------------------------------------------------
# Healing Cache
# ---------------------------------------------------------------------------

class TestHealingCache:
    """Validate persistence of healed locators."""

    def test_cache_hit_and_miss(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            cache_path = f.name

        try:
            cache = HealingCache(cache_path)

            # Miss
            assert cache.get("LoginPage", "USERNAME", "web") is None

            # Set
            cache.set("LoginPage", "USERNAME", "web",
                      {"test_id": "email-input"}, "high", "test")

            # Hit
            loaded = cache.get("LoginPage", "USERNAME", "web")
            assert loaded == {"test_id": "email-input"}

            # Invalidate
            cache.invalidate("LoginPage", "USERNAME", "web")
            assert cache.get("LoginPage", "USERNAME", "web") is None

        finally:
            Path(cache_path).unlink(missing_ok=True)

    def test_clear_cache(self):
        cache = HealingCache("/tmp/test_clear_cache.json")
        cache.set("P", "E", "web", {"css": "#x"})
        assert len(cache.get_all()) == 1
        cache.clear()
        assert len(cache.get_all()) == 0


# ---------------------------------------------------------------------------
# Healing Orchestrator (wired but no LLM)
# ---------------------------------------------------------------------------

class TestHealingOrchestrator:
    """Validate the full healing pipeline (heuristics only, no LLM)."""

    @pytest.fixture
    def config(self):
        cfg = AutomationConfig.load("config/config.yaml")
        cfg.healing.llm.enabled = False  # Skip LLM for unit tests
        cfg.healing.heuristics.enabled = True
        cfg.healing.heuristics.max_attempts = 3
        cfg.healing.cache.enabled = True
        cfg.healing.cache.db_path = "/tmp/test_orch_cache.json"
        return cfg

    @pytest.fixture
    def orchestrator(self, config):
        orch = HealingOrchestrator(config)
        yield orch
        orch.cache.clear()

    def test_heuristic_healing_returns_locator(self, orchestrator):
        result = orchestrator.heal(
            platform="web",
            element_context={
                "name": "login_btn",
                "page": "LoginPage",
                "original_locator": {"role": "button", "name": "Sign in"},
            },
            page_source="<html><body><button>Sign in</button></body></html>",
        )

        assert "locator" in result
        assert result["source"] == "heuristic"
        assert result["confidence"] == "medium"

    def test_healing_caches_result(self, orchestrator):
        """After first heal, the result should be cached."""
        ctx = {
            "name": "cache_test",
            "page": "TestPage",
            "original_locator": {"css": "#my-btn"},
        }

        # First call — heuristics
        r1 = orchestrator.heal("web", ctx, "<html></html>")
        assert r1["source"] == "heuristic"

        # Second call — should come from cache
        ctx2 = ctx.copy()
        r2 = orchestrator.heal("web", ctx2, "<html></html>")
        assert r2["source"] == "cache", f"Expected cache, got {r2['source']}"

    def test_healing_uses_locator_context(self, orchestrator):
        """The locator's description and name should influence healing."""
        locator = Locator(
            name="submit_order",
            web={"css": "#old-selector"},
            description="Submit button on checkout page",
            parent_page="CheckoutPage",
        )

        ctx = locator.to_healing_context("web")
        result = orchestrator.heal(
            platform="web",
            element_context=ctx,
            page_source="<html><body><button>Submit Order</button></body></html>",
        )

        assert result["locator"] is not None
