# AI Automation Framework 🤖

**Multi-platform automation framework with AI-powered element auto-healing.**

Supports **Web** (Playwright), **Android Native** (Appium), and **iOS Native** (Appium) — all through a unified Python API with automatic element healing when locators fail.

## ✨ Features

| Capability | Description |
|---|---|
| **🌐 Cross-platform** | Single API for Web, Android, iOS |
| **🧠 AI Auto-healing** | When an element locator fails, the framework auto-recovers via heuristic fallbacks → LLM analysis |
| **⚡ Heuristic fallback** | Zero-cost retry with alternative locator strategies (test_id → role → label → css → xpath → text) |
| **🤖 LLM healing** | Sends screenshot + page source to an LLM to determine the correct element |
| **💾 Healing cache** | Persists healed locators so they work on subsequent runs |
| **📦 Page Object Model** | Clean, maintainable page objects with typed locators |
| **📸 Auto-fail artifacts** | Screenshots, page source, and healing reports on failure |
| **🔌 Pluggable LLM** | OpenAI, LiteLLM (Ollama, vLLM, Anthropic, etc.) |

## 📋 Architecture

```
ai-automation-framework/
├── src/autofw/
│   ├── core/              # Config, constants, exceptions
│   ├── locator/           # Multi-platform locator definitions
│   ├── healing/           # Heuristic + LLM healing pipeline
│   ├── elements/          # Unified element with auto-healing
│   ├── pages/             # Base page object
│   ├── utils/             # Logger, wait, screenshot helpers
│   ├── driver_factory.py  # Playwright + Appium driver factory
│   ├── conftest.py        # Pytest fixtures & hooks
│   └── __init__.py
├── config/
│   └── config.yaml        # Global configuration
├── tests/
│   ├── web/               # Web test examples
│   ├── android/           # Android test examples
│   └── ios/               # iOS test examples
├── locators/              # External locator files (optional)
└── requirements.txt
```

## 🚀 Quick Start

### 1. Install

```bash
# Clone / create project
cd ai-automation-framework

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 2. Configure

Edit `config/config.yaml` to set your platform and credentials:

```yaml
platform: web          # web | android | ios

web:
  browser: chromium
  headless: true       # Set false to watch tests run

android:
  appium_url: http://localhost:4723
  app: /path/to/app.apk

ios:
  appium_url: http://localhost:4723
  app: /path/to/app.app

healing:
  enabled: true
  llm:
    api_key: "${OPENAI_API_KEY}"    # Or set env: HEALING_API_KEY
    model: gpt-4o-mini
```

### 3. Write a Page Object

```python
# tests/web/pages/login_page.py
from autofw.locator import Locator
from autofw.pages import BasePage

class LoginPage(BasePage):
    USERNAME_INPUT = Locator(
        name="Username input",
        web={"placeholder": "Email"},
        android={"accessibility_id": "emailInput"},
        ios={"accessibility_id": "emailInput"},
        description="Email text field on login form",
    )

    LOGIN_BUTTON = Locator(
        name="Login button",
        web={"role": "button", "name": "Sign in"},
        android={"accessibility_id": "loginButton"},
        ios={"accessibility_id": "loginButton"},
    )

    def login(self, username: str, password: str):
        self.element(self.USERNAME_INPUT).type(username)
        self.element(self.PASSWORD_INPUT).type(password)
        self.element(self.LOGIN_BUTTON).click()
```

### 4. Write Tests

```python
# tests/web/test_login.py
import pytest

@pytest.mark.web
class TestLogin:
    def test_successful_login(self, login_page):
        login_page.navigate_to("https://example.com")
        login_page.login("user@example.com", "securePass")
        assert "dashboard" in login_page.get_url()
```

### 5. Run

```bash
# Web tests
pytest tests/web/ --platform web -v

# Android tests (with Appium running)
pytest tests/android/ --platform android -v

# iOS tests (with Appium running)
pytest tests/ios/ --platform ios -v

# With healing disabled
pytest tests/web/ --platform web --disable-healing -v
```

## 🧠 How AI Healing Works

```
Element action fails
    │
    ▼
┌──────────────────────┐
│ 1. Heuristic Fallback│  ← Zero-cost, tries alternative locator strategies
│    (3 attempts)      │     (test_id → role → label → css → xpath → text)
└──────────┬───────────┘
           │ all failed
           ▼
┌──────────────────────┐
│ 2. LLM Analysis      │  ← Sends screenshot + page source to LLM
│    (if enabled)      │     Receives corrected locator + confidence score
└──────────┬───────────┘
           │ success
           ▼
┌──────────────────────┐
│ 3. Cache Healed      │  ← Persisted for future runs
│    Locator           │     (no re-healing needed)
└──────────┬───────────┘
           │
           ▼
    Retry action with healed locator
```

## ⚙️ Configuration Reference

### CLI Options

| Flag | Description |
|---|---|
| `--platform web|android|ios` | Override target platform |
| `--config path/to/config.yaml` | Custom config path |
| `--disable-healing` | Disable AI healing |
| `--heal-cache path/to/cache.json` | Custom healing cache path |

### Environment Variables

| Variable | Description |
|---|---|
| `HEALING_API_KEY` | API key for LLM healing |
| `OPENAI_API_KEY` | Fallback API key |
| `AUTOFW_PLATFORM` | Default platform override |

## 🏗️ Project Structure Best Practices

```
project/
├── tests/
│   ├── web/
│   │   ├── pages/         # Page objects for web
│   │   ├── components/    # Reusable component objects
│   │   └── test_*.py      # Web test files
│   ├── android/
│   │   ├── pages/         # Page objects for Android
│   │   └── test_*.py
│   └── ios/
│       ├── pages/         # Page objects for iOS
│       └── test_*.py
├── locators/
│   ├── web/               # External locator JSON files
│   ├── android/
│   └── ios/
├── config/
│   ├── config.yaml        # Base config
│   └── environments/      # Per-environment overrides
└── reports/               # Test reports & artifacts
```

## 📄 License

MIT
