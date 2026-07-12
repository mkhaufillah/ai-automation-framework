import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        print("Navigating to whatsapp web...")
        await page.goto("https://web.whatsapp.com")
        print("Waiting for network idle...")
        await page.wait_for_load_state("networkidle")
        print("Waiting 5 seconds for page to render...")
        await page.wait_for_timeout(5000)
        
        # search for qr code
        locators = [
            "//*[@data-testid='qrcode']",
            "//*[@data-testid='link-device-qr-code']",
            "canvas"
        ]
        
        for loc in locators:
            count = await page.locator(loc).count()
            print(f"Locator {loc} found {count} times")
            
        print("Page title:", await page.title())
        await browser.close()

asyncio.run(run())
