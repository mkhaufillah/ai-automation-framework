import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://web.whatsapp.com")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(5000)
        
        content = await page.content()
        idx = content.find("link-device-qr-code")
        print(f"Total size: {len(content)}")
        print(f"Index of QR code: {idx}")
        await browser.close()

asyncio.run(run())
