import asyncio
from playwright.async_api import async_playwright

async def test_login_and_url_change():
    """测试登录过程和URL变化"""
    async with async_playwright() as p:
        # 启动浏览器
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
        
        # 访问登录页面
        login_url = "http://10.28.149.50:9432/login/v1/#/login"
        print(f"访问登录页面: {login_url}")
        await page.goto(login_url, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(3000)
        
        # 记录登录前的URL
        before_login_url = page.url
        print(f"登录前URL: {before_login_url}")
        
        try:
            # 输入用户名
            print("输入用户名: admin")
            username_input = page.locator('input[placeholder="请输入帐号/手机号/邮箱"]').first
            await username_input.fill("admin")
            
            # 输入密码
            print("输入密码: Asiainfo1@3")
            password_input = page.locator('input[placeholder="请输入密码"]').first
            await password_input.fill("Asiainfo1@3")
            
            # 点击登录按钮
            print("点击登录按钮")
            login_button = page.locator('button:has-text("登录")').first
            await login_button.click()
            
            # 等待登录完成
            print("等待登录完成...")
            await page.wait_for_timeout(5000)
            
            # 记录登录后的URL
            after_login_url = page.url
            print(f"登录后URL: {after_login_url}")
            
            # 检查URL是否变化
            if after_login_url != before_login_url and "login" not in after_login_url.lower():
                print("✅ 登录成功，URL已变化")
            else:
                print("❌ 登录失败，URL未变化")
            
            # 尝试查找菜单
            print("\n尝试查找菜单元素:")
            menu_selectors = [
                '.el-tabs__item.is-left',  # 左侧垂直 Tab 菜单
                '.el-menu-item',  # 二级菜单
                '.el-submenu > .el-submenu__title',
                '.menu-item',
                '.nav-item',
                '.sidebar-item',
                '[role="menuitem"]'
            ]
            
            for selector in menu_selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    print(f"找到 {len(elements)} 个 '{selector}' 元素")
                    for i, el in enumerate(elements[:5]):  # 只显示前5个
                        try:
                            text = await el.inner_text()
                            text = text.strip()
                            if text:
                                print(f"  [{i+1}] {text}")
                        except:
                            pass
            
            # 尝试点击一级菜单和二级菜单
            print("\n尝试点击一级菜单和二级菜单...")
            try:
                # 尝试找到所有一级菜单元素
                menu_elements = await page.query_selector_all('.el-tabs__item.is-left')
                if menu_elements:
                    print(f"找到 {len(menu_elements)} 个一级菜单")
                    
                    # 遍历每个一级菜单
                    for i, menu_el in enumerate(menu_elements):
                        menu_text = await menu_el.inner_text()
                        menu_text = menu_text.strip()
                        print(f"\n[{i+1}] 处理一级菜单: {menu_text}")
                        
                        # 记录点击前的URL
                        before_click_url = page.url
                        print(f"点击前URL: {before_click_url}")
                        
                        # 点击一级菜单
                        await menu_el.click()
                        await page.wait_for_timeout(2000)
                        
                        # 检查URL是否变化
                        after_click_url = page.url
                        if after_click_url != before_click_url:
                            print(f"✅ 点击一级菜单后URL已变化: {after_click_url}")
                        else:
                            print("❌ 点击一级菜单后URL未变化")
                        
                        # 查找二级菜单
                        submenu_elements = await page.query_selector_all('.el-menu-item')
                        if submenu_elements:
                            print(f"找到 {len(submenu_elements)} 个二级菜单")
                            
                            # 遍历每个二级菜单
                            for j, submenu_el in enumerate(submenu_elements):
                                submenu_text = await submenu_el.inner_text()
                                submenu_text = submenu_text.strip()
                                print(f"  [{j+1}] 处理二级菜单: {submenu_text}")
                                
                                # 记录点击前的URL
                                sub_before_url = page.url
                                print(f"  点击前URL: {sub_before_url}")
                                
                                # 点击二级菜单
                                await submenu_el.click()
                                await page.wait_for_timeout(2000)
                                
                                # 检查URL是否变化
                                sub_after_url = page.url
                                if sub_after_url != sub_before_url:
                                    print(f"  ✅ 点击二级菜单后URL已变化: {sub_after_url}")
                                else:
                                    print("  ❌ 点击二级菜单后URL未变化")
                        else:
                            print("未找到二级菜单")
                else:
                    print("未找到一级菜单元素")
            except Exception as e:
                print(f"点击菜单时出错: {str(e)[:50]}")
            
        except Exception as e:
            print(f"登录过程出错: {str(e)[:50]}")
        
        # 关闭浏览器
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_login_and_url_change())
