import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('http://10.28.149.50:9432/iam/v1/#/home/homeManage', wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(3000)

        elements = await page.evaluate("""
            () => {
                const elements = [];
                const selectors = [
                    'button', 'a[href]', 'input[type="button"]', 'input[type="submit"]',
                    '[role="button"]', '[role="link"]', '[role="menuitem"]',
                    '.btn', '.menu-item', '.nav-item'
                ];
                for (const selector of selectors) {
                    document.querySelectorAll(selector).forEach(el => {
                        const text = (el.innerText || el.value || '').trim();
                        if (el.offsetParent !== null) {
                            elements.push({
                                tag: el.tagName,
                                text: text,
                                href: el.href || '',
                                className: el.className || ''
                            });
                        }
                    });
                }
                return elements;
            }
        """)

        print(f'找到 {len(elements)} 个元素')
        for i, el in enumerate(elements[:10]):
            print(f'{i+1}. tag={el["tag"]}, text={el["text"][:30]}, href={el["href"][:50]}')

        await browser.close()

asyncio.run(test())