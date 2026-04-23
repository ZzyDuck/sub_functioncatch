import asyncio
from playwright.async_api import async_playwright

async def check_page_structure(url):
    """检查页面结构，查看菜单元素"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ]
        )
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        # 访问页面
        await page.goto(url, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(3000)
        
        # 滚动页面
        await page.evaluate("window.scrollBy(0, window.innerHeight)")
        await page.wait_for_timeout(1000)
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(1000)
        
        # 检查页面标题
        title = await page.title()
        print(f"页面标题: {title}")
        
        # 检查当前URL
        current_url = page.url
        print(f"当前URL: {current_url}")
        
        # 尝试查找菜单相关元素
        print("\n查找菜单相关元素:")
        
        # 尝试各种菜单选择器
        menu_selectors = [
            '.el-tabs__item.is-left',  # 左侧垂直 Tab 菜单
            '.el-menu-item',  # 二级菜单
            '.el-submenu > .el-submenu__title',
            '.menu-item',
            '.nav-item',
            '.sidebar-item',
            '[role="menuitem"]',
            'div',
            'li',
            'a'
        ]
        
        for selector in menu_selectors:
            elements = await page.query_selector_all(selector)
            if elements:
                print(f"\n找到 {len(elements)} 个 '{selector}' 元素:")
                for i, el in enumerate(elements[:10]):  # 只显示前10个
                    try:
                        text = await el.inner_text()
                        text = text.strip()
                        if text:
                            print(f"  [{i+1}] {text[:50]}")
                    except:
                        pass
        
        # 保存页面HTML
        html = await page.content()
        with open('page_structure.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("\n页面HTML已保存到 page_structure.html")
        
        await browser.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python check_page_structure.py <url>")
        sys.exit(1)
    
    url = sys.argv[1]
    asyncio.run(check_page_structure(url))
