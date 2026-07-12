import asyncio
from playwright.async_api import async_playwright
import base64
from autofw.core.config import AutomationConfig
from autofw.healing.ai_healer import LLMHealer

async def run():
    config = AutomationConfig()
    config.healing.llm.enabled = True
    config.healing.llm.provider = "opencode"
    config.healing.llm.model = "kimi-k2.6"
    config.healing.llm.api_base = "https://opencode.ai/zen/go/v1"
    config.healing.llm.include_screenshot = True
    config.healing.llm.include_page_source = True
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://web.whatsapp.com")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(5000)
        
        content = await page.content()
        screenshot = await page.screenshot(full_page=True)
        screenshot_b64 = base64.b64encode(screenshot).decode("utf-8")
        
        healer = LLMHealer(config)
        
        context = {
            "name": "QR Code",
            "description": "QR code for linking device",
            "page": "",
            "original_locator": {"xpath": "//*[@data-testid='link-device-qr-code-1']"}
        }
        
        print("Sending to LLM Healer...")
        res = healer.heal(context, "web", content, screenshot_b64)
        print("Heal result:", res)
        
        await browser.close()

asyncio.run(run())
