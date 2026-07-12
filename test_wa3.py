import asyncio
from playwright.async_api import async_playwright
import re

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://web.whatsapp.com")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(5000)
        
        page_source = await page.content()
        minified = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', page_source, flags=re.IGNORECASE | re.DOTALL)
        minified = re.sub(r'<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>', '', minified, flags=re.IGNORECASE | re.DOTALL)
        minified = re.sub(r'<svg[^>]*>.*?</svg>', '<svg></svg>', minified, flags=re.IGNORECASE | re.DOTALL)
        minified = re.sub(r'<!--.*?-->', '', minified, flags=re.DOTALL)

        idx = minified.find("link-device-qr-code")
        print(f"Minified size: {len(minified)}")
        print(f"Index of QR code: {idx}")
        await browser.close()

asyncio.run(run())
