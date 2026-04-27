import asyncio
from playwright.async_api import async_playwright
from urllib.parse import urlparse, urljoin
from typing import Dict, Set
import json

class MenuCrawler:
    """专注于菜单结构发现的爬虫"""
    
    def __init__(self, start_url: str, wait_time: int = 2000, username: str = None, password: str = None):
        self.start_url = start_url
        self.base_domain = urlparse(start_url).netloc
        self.wait_time = wait_time    # 每次点击后等待时间(ms)
        self.username = username      # 登录用户名
        self.password = password      # 登录密码
        
        self.visited_urls: Set[str] = set()
        self.visited_menus: Set[str] = set()
        self.menu_tree: Dict = {"首页": {"url": "/home", "children": {}}}
    
    def _normalize_hash_url(self, url: str) -> str:
        """规范化SPA的hash路由URL"""
        if '#' in url:
            parts = url.split('#')
            base = parts[0]
            hash_part = parts[1] if len(parts) > 1 else ''
            # 确保hash部分格式正确：#/path 而不是 #path
            if hash_part and not hash_part.startswith('/'):
                hash_part = '/' + hash_part
            return base + '#' + hash_part
        return url
    
    async def run(self) -> Dict:
        """运行菜单爬虫"""
        async with async_playwright() as p:
            # 使用有头模式，确保所有动态内容都能加载
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
            
            # 执行登录
            login_success = False
            if self.username and self.password:
                print("\n🔐 正在执行登录...")
                login_success = await self._login(page)
                if login_success:
                    print("✅ 登录完成")
                else:
                    print("❌ 登录未完成")
            
            # 初始化
            if login_success:
                initial_url = self._normalize_hash_url(page.url)
                print(f"\n📍 登录后开始爬取: {initial_url}")
            else:
                initial_url = self._normalize_hash_url(self.start_url)
                print(f"\n📍 开始爬取: {initial_url}")
            
            # 开始构建菜单树
            await self._build_menu_tree(page, initial_url, self.menu_tree["首页"]["children"])
            
            await browser.close()
        
        return self.menu_tree
    
    async def _build_menu_tree(self, page, current_url: str, parent_node: Dict):
        """构建菜单树"""
        if current_url in self.visited_urls:
            return
        
        self.visited_urls.add(current_url)
        print(f"\n📍 处理页面: {current_url}")
        
        try:
            # 访问页面
            await page.goto(current_url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(3000)  # 延长等待时间
            
            # 滚动页面加载所有内容
            await self._scroll_page(page)
            
            # 提取一级菜单
            level1_menus = await self._extract_level1_menus(page)
            print(f"   找到 {len(level1_menus)} 个一级菜单")
            

            
            for menu_info in level1_menus:
                menu_name = menu_info["text"]
                menu_key = f"{current_url}|{menu_name}"
                
                if menu_key in self.visited_menus:
                    continue
                self.visited_menus.add(menu_key)
                
                # 点击菜单，进入新页面
                before_url = page.url
                menu_url = before_url  # 默认使用当前URL
                
                try:
                    # 定位并点击菜单
                    if menu_info.get("selector"):
                        el = page.locator(menu_info["selector"]).first
                    else:
                        el = page.locator(f'text="{menu_name}"').first
                    await el.scroll_into_view_if_needed()
                    await el.evaluate("element => element.click()")
                    
                    # 等待URL变化
                    after_url = before_url
                    for i in range(5):  # 延长等待时间
                        await page.wait_for_timeout(1000)
                        current_page_url = page.url
                        if current_page_url != before_url:
                            after_url = current_page_url
                            print(f"   ✅ 跳转到: {after_url}")
                            break
                    else:
                        # 即使URL未变化，也继续处理，可能是SPA应用的前端路由变化
                        print("   ℹ️ URL未变化，继续处理")
                        after_url = page.url
                    
                    # 使用跳转后的URL
                    menu_url = after_url
                    print(f"   一级菜单: {menu_name} -> {menu_url}")
                    
                    # 创建菜单项
                    parent_node[menu_name] = {
                        "url": menu_url,
                        "children": {}
                    }
                    
                    # 提取二级菜单
                    level2_menus = await self._extract_level2_menus(page)
                    print(f"   找到 {len(level2_menus)} 个二级菜单")
                    
                    # 保存当前一级菜单页面的URL
                    current_level1_url = page.url
                    
                    # 重新获取当前页面的二级菜单元素
                    current_level2_menus = await self._extract_level2_menus(page)
                    print(f"   重新获取到 {len(current_level2_menus)} 个二级菜单")
                    
                    for submenu_info in level2_menus:
                        submenu_name = submenu_info["text"]
                        submenu_key = f"{current_level1_url}|{submenu_name}"
                        
                        if submenu_key in self.visited_menus:
                            continue
                        self.visited_menus.add(submenu_key)
                        
                        # 点击二级菜单
                        submenu_before_url = page.url
                        submenu_url = submenu_before_url
                        
                        try:
                            # 检查是否有子菜单
                            has_submenu = submenu_info.get("hasSubmenu", False)
                            print(f"   📍 二级菜单是否有子菜单: {has_submenu}")
                            
                            # 每次点击前重新查找元素
                            print(f"   📍 查找二级菜单: {submenu_name}")
                            
                            # 根据是否有子菜单选择不同的定位方式
                            if has_submenu:
                                # 对于有子菜单的项，查找 li.el-submenu 容器
                                sub_el = page.locator(f'li.el-submenu:has-text("{submenu_name}")').first
                                element_exists = await sub_el.count() > 0
                                
                                if not element_exists:
                                    # 备选：通过 .el-submenu__title 查找其父元素
                                    title_el = page.locator(f'.el-submenu__title:has-text("{submenu_name}")').first
                                    if await title_el.count() > 0:
                                        sub_el = title_el.locator('xpath=..').first
                                        element_exists = True
                            else:
                                # 对于普通菜单项，直接通过文本定位
                                sub_el = page.locator(f'text="{submenu_name}"').first
                                element_exists = await sub_el.count() > 0
                                
                                if not element_exists:
                                    # 如果文本定位失败，尝试通过选择器定位
                                    if submenu_info.get("selector"):
                                        sub_el = page.locator(submenu_info["selector"]).first
                                        element_exists = await sub_el.count() > 0
                            
                            print(f"   📍 二级菜单元素存在: {element_exists}")
                            
                            if element_exists:
                                await sub_el.scroll_into_view_if_needed()
                                print(f"   📍 滚动到二级菜单元素")
                                
                                if has_submenu:
                                    # 有子菜单的二级菜单不生成 URL（设置为空字符串）
                                    parent_node[menu_name]["children"][submenu_name] = {
                                        "url": "",  # 不生成 URL
                                        "children": {}
                                    }
                                    print(f"   📍 创建二级菜单节点: {submenu_name}")
                                    
                                    # 可展开菜单：点击展开
                                    await sub_el.evaluate("element => element.click()")
                                    print(f"   📍 点击展开二级菜单: {submenu_name}")
                                    await page.wait_for_timeout(1000)
                                    
                                    # 提取三级菜单
                                    level3_menus = await self._extract_level3_menus(page, sub_el)
                                    print(f"   📍 找到 {len(level3_menus)} 个三级菜单")
                                    
                                    # 处理三级菜单
                                    for level3_info in level3_menus:
                                        level3_name = level3_info["text"]
                                        level3_key = f"{current_level1_url}|{submenu_name}|{level3_name}"
                                        
                                        if level3_key in self.visited_menus:
                                            continue
                                        self.visited_menus.add(level3_key)
                                        
                                        print(f"   📍 查找三级菜单: {level3_name}")
                                        
                                        # 定位三级菜单元素
                                        level3_el = page.locator(f'text="{level3_name}"').first
                                        level3_exists = await level3_el.count() > 0
                                        
                                        if not level3_exists:
                                            if level3_info.get("selector"):
                                                level3_el = page.locator(level3_info["selector"]).first
                                                level3_exists = await level3_el.count() > 0
                                        
                                        print(f"   📍 三级菜单元素存在: {level3_exists}")
                                        
                                        # 过滤掉不属于当前二级菜单的三级菜单
                                        if level3_name in ['登录策略', '密码策略', '远程访问管理']:
                                            print(f"   ℹ️ 跳过不属于当前二级菜单的项: {level3_name}")
                                            continue
                                        
                                        if level3_exists:
                                            try:
                                                # 直接使用 JavaScript 点击，不检查可见性
                                                await level3_el.evaluate("element => element.click()")
                                                print(f"   📍 点击三级菜单: {level3_name}")
                                                
                                                # 等待URL变化
                                                level3_before_url = page.url
                                                level3_after_url = level3_before_url
                                                level3_url_changed = False
                                                print(f"   📍 点击前URL: {level3_before_url}")
                                                
                                                for k in range(5):
                                                    await page.wait_for_timeout(1000)
                                                    current_level3_url = page.url
                                                    # print(f"   📍 第 {k+1} 次检查URL: {current_level3_url}")
                                                    if current_level3_url != level3_before_url:
                                                        level3_after_url = current_level3_url
                                                        level3_url_changed = True
                                                        print(f"   ✅ 跳转到: {level3_after_url}")
                                                        await page.wait_for_timeout(2000)
                                                        break
                                                else:
                                                    print("   ℹ️ 三级菜单URL未变化，继续处理")
                                                    level3_after_url = page.url
                                                
                                                # 创建三级菜单项
                                                parent_node[menu_name]["children"][submenu_name]["children"][level3_name] = {
                                                    "url": level3_after_url
                                                }
                                                print(f"   三级菜单: {level3_name} -> {level3_after_url}")
                                                
                                                # 仅在URL变化时返回上一级
                                                if level3_url_changed:
                                                    await page.go_back()
                                                    await page.wait_for_timeout(self.wait_time)
                                                    await page.wait_for_timeout(1000)
                                            except Exception as level3_e:
                                                print(f"   ❌ 处理三级菜单 {level3_name} 时出错: {str(level3_e)[:50]}")
                                else:
                                    # 直接点击跳转
                                    await sub_el.evaluate("element => element.click()")
                                    print(f"   📍 点击二级菜单: {submenu_name}")
                                    
                                    # 等待URL变化
                                    submenu_after_url = submenu_before_url
                                    url_changed = False
                                    print(f"   📍 点击前URL: {submenu_before_url}")
                                    
                                    for j in range(5):  # 延长等待时间
                                        await page.wait_for_timeout(1000)
                                        current_sub_url = page.url
                                        print(f"   📍 第 {j+1} 次检查URL: {current_sub_url}")
                                        if current_sub_url != submenu_before_url:
                                            submenu_after_url = current_sub_url
                                            url_changed = True
                                            print(f"   ✅ 跳转到: {submenu_after_url}")
                                            # 增加1-2秒等待，确保页面完全加载
                                            await page.wait_for_timeout(2000)
                                            break
                                    else:
                                        # 即使URL未变化，也继续处理
                                        print("   ℹ️ 二级菜单URL未变化，继续处理")
                                        submenu_after_url = page.url
                                    
                                    # 使用跳转后的URL
                                    submenu_url = submenu_after_url
                                    print(f"   二级菜单: {submenu_name} -> {submenu_url}")
                                    
                                    # 创建子菜单项
                                    parent_node[menu_name]["children"][submenu_name] = {
                                        "url": submenu_url
                                    }
                                    
                                    # 仅在URL变化时返回上一级
                                    if url_changed:
                                        # 使用page.go_back()返回，而不是page.goto()
                                        await page.go_back()
                                        await page.wait_for_timeout(self.wait_time)
                                        # 等待页面稳定
                                        await page.wait_for_timeout(1000)
                            else:
                                print(f"   ❌ 二级菜单元素不存在: {submenu_name}")
                                # 创建子菜单项
                                parent_node[menu_name]["children"][submenu_name] = {
                                    "url": submenu_before_url
                                }
                        
                        except Exception as sub_e:
                            print(f"   ❌ 处理二级菜单 {submenu_name} 时出错: {str(sub_e)[:50]}")
                            # 尝试返回一级菜单页面
                            try:
                                await page.goto(current_level1_url, wait_until='networkidle', timeout=10000)
                                await page.wait_for_timeout(self.wait_time)
                            except:
                                pass
                    
                    # 返回原页面
                    await page.goto(current_url, wait_until='networkidle', timeout=10000)
                    await page.wait_for_timeout(self.wait_time)
                    
                except Exception as e:
                    print(f"   ❌ 处理菜单 {menu_name} 时出错: {str(e)[:50]}")
                    # 尝试返回原页面
                    try:
                        await page.goto(current_url, wait_until='networkidle', timeout=10000)
                        await page.wait_for_timeout(self.wait_time)
                    except:
                        pass
        
        except Exception as e:
            print(f"   ❌ 访问页面出错: {str(e)[:50]}")
    
    async def _extract_level1_menus(self, page):
        """提取一级菜单"""
        return await page.evaluate(r"""
            () => {
                const menus = [];
                const menuTextSet = new Set();
                const menuSelectors = [
                    '.el-tabs__item.is-left',  // 左侧垂直 Tab 菜单
                    '#tab-xxx',  // id为tab-xxx的元素
                    '.el-submenu > .el-submenu__title',
                    '.menu-item',
                    '.nav-item',
                    '.sidebar-item',
                    '.ant-menu-item-group-title',
                    '.el-menu-item-group > .el-menu-item-group__title',
                    '.el-menu--vertical > .el-menu-item',
                    '.sidebar > .menu > .item',
                    '.nav > .item',
                    '[role="menuitem"]',
                    '.el-menu-item',
                    '.menu > li > a',
                    '.nav > li > a',
                    '.sidebar > ul > li > a',
                    '.el-menu > .el-menu-item',
                    '.el-menu--horizontal > .el-menu-item'
                ];
                
                for (const selector of menuSelectors) {
                    document.querySelectorAll(selector).forEach(el => {
                        const text = (el.innerText || '').trim();
                        if (text && text.length < 50 && !menuTextSet.has(text)) {
                            menuTextSet.add(text);
                            // 生成选择器
                            let selector = '';
                            if (el.id) {
                                selector = `#${el.id}`;
                            } else if (el.className && el.className.trim()) {
                                selector = `.${el.className.trim().replace(/\s+/g, '.')}`;
                            } else {
                                selector = el.tagName.toLowerCase();
                            }
                            menus.push({ 
                                text: text, 
                                selector: selector,
                                tag: el.tagName,
                                className: el.className,
                                id: el.id
                            });
                        }
                    });
                }
                return menus;
            }
        """)
    
    async def _extract_level2_menus(self, page):
        """提取二级菜单"""
        return await page.evaluate(r"""
            () => {
                const menus = [];
                const menuTextSet = new Set();
                const menuSelectors = [
                    '.el-menu > .el-menu-item',  // 直接子元素
                    '.el-menu > .el-submenu',  // 选择整个子菜单容器
                    '.el-menu--vertical > .el-menu-item',
                    '.el-menu--vertical > .el-submenu',  // 选择整个子菜单容器
                    '.sidebar > .menu > .item',
                    '.nav > .item',
                    '.menu > li',
                    '.nav > li'
                ];
                
                for (const selector of menuSelectors) {
                    document.querySelectorAll(selector).forEach(el => {
                        // 过滤掉内嵌菜单中的元素
                        if (el.closest('.el-menu--inline')) {
                            return;  // 跳过，这是三级菜单
                        }
                        
                        // 获取菜单文本
                        let text = '';
                        if (el.classList.contains('el-submenu')) {
                            // 对于子菜单容器，获取标题文本
                            const titleEl = el.querySelector('.el-submenu__title');
                            text = titleEl ? (titleEl.innerText || '').trim() : '';
                        } else {
                            // 对于普通菜单项，直接获取文本
                            text = (el.innerText || '').trim();
                        }
                        
                        if (text && text.length < 50 && !menuTextSet.has(text)) {
                            menuTextSet.add(text);
                            // 生成选择器
                            let selector = '';
                            if (el.id) {
                                selector = `#${el.id}`;
                            } else if (el.className && el.className.trim()) {
                                selector = `.${el.className.trim().replace(/\s+/g, '.')}`;
                            } else {
                                selector = el.tagName.toLowerCase();
                            }
                            // 检查是否有子菜单
                            const hasSubmenu = el.classList.contains('el-submenu');
                            menus.push({ 
                                text: text, 
                                selector: selector,
                                tag: el.tagName,
                                className: el.className,
                                id: el.id,
                                hasSubmenu: hasSubmenu
                            });
                        }
                    });
                }
                return menus;
            }
        """)
    
    async def _extract_level3_menus(self, page, submenu_element):
        """提取三级菜单"""
        # 获取二级菜单元素的DOM句柄
        element_handle = await submenu_element.element_handle()
        
        # 添加调试信息
        debug_info = await page.evaluate(r"""
            (submenuEl) => {
                // 调试信息
                const debug = {
                    elementTag: submenuEl.tagName,
                    elementClass: submenuEl.className,
                    elementText: submenuEl.innerText.trim(),
                    hasUl: submenuEl.querySelector('ul') !== null,
                    ulClass: submenuEl.querySelector('ul') ? submenuEl.querySelector('ul').className : 'none',
                    menuItemCount: submenuEl.querySelectorAll('.el-menu-item').length
                };
                
                // 提取菜单
                const menus = [];
                const menuTextSet = new Set();
                
                // 只提取当前二级菜单下的直接子菜单
                const menuItems = submenuEl.querySelectorAll('.el-menu-item');
                
                // 处理普通菜单项
                menuItems.forEach(el => {
                    const text = (el.innerText || '').trim();
                    if (text && text.length < 50 && !menuTextSet.has(text)) {
                        menuTextSet.add(text);
                        // 生成选择器
                        let selector = '';
                        if (el.id) {
                            selector = `#${el.id}`;
                        } else if (el.className && el.className.trim()) {
                            selector = `.${el.className.trim().replace(/\s+/g, '.')}`;
                        } else {
                            selector = el.tagName.toLowerCase();
                        }
                        menus.push({ 
                            text: text, 
                            selector: selector,
                            tag: el.tagName,
                            className: el.className,
                            id: el.id
                        });
                    }
                });
                
                return { debug, menus };
            }
        """, element_handle)
        
        # 打印调试信息
        print(f"   📍 二级菜单元素: {debug_info['debug']['elementTag']}.{debug_info['debug']['elementClass']}")
        print(f"   📍 二级菜单文本: {debug_info['debug']['elementText']}")
        print(f"   📍 包含ul: {debug_info['debug']['hasUl']}")
        print(f"   📍 ul类名: {debug_info['debug']['ulClass']}")
        print(f"   📍 菜单项数量: {debug_info['debug']['menuItemCount']}")
        
        return debug_info['menus']
    
    async def _get_menu_url(self, page, menu_info):
        """获取菜单的URL"""
        # 优先从属性中获取URL
        url = await page.evaluate("""
            (menuInfo) => {
                const el = document.querySelector(menuInfo.selector) || 
                          document.querySelector(`text="${menuInfo.text}"`);
                if (!el) return '';
                
                // 从属性中获取URL
                const url = el.getAttribute('data-url') || 
                           el.getAttribute('to') || 
                           el.getAttribute('href');
                
                if (url) return url;
                
                // 从id属性推断URL
                if (el.id && el.id.startsWith('tab-')) {
                    return '/' + el.id.replace('tab-', '');
                }
                
                return '';
            }
        """, menu_info)
        
        if url:
            # 处理相对路径
            if not url.startswith('http'):
                url = urljoin(self.start_url, url)
            return url
        
        # 如果没有URL，返回当前页面URL
        return page.url
    
    async def _scroll_page(self, page, max_scrolls: int = 10):
        """滚动页面加载动态内容"""
        for i in range(max_scrolls):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await page.wait_for_timeout(500)
        
        # 滚动到顶部
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(500)
    
    async def _login(self, page):
        """执行登录操作，返回登录是否成功"""
        # 访问登录页面
        login_url = "http://10.28.149.50:9432/login/v1/#/login"
        await page.goto(login_url, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(self.wait_time)
        
        try:
            # 找到用户名输入框
            username_input = page.locator('input[placeholder="请输入帐号/手机号/邮箱"]').first
            await username_input.fill(self.username)
            
            # 找到密码输入框
            password_input = page.locator('input[placeholder="请输入密码"]').first
            await password_input.fill(self.password)
            
            # 找到登录按钮并点击
            login_button = page.locator('button:has-text("登录")').first
            await login_button.click()
            
            # 等待登录完成
            await page.wait_for_timeout(self.wait_time * 2)
            
            # 检查是否登录成功
            if "login" not in page.url.lower():
                print("✅ 登录成功!")
                return True
            else:
                print("❌ 登录失败，仍在登录页面")
                return False
            
        except Exception as e:
            print(f"❌ 登录失败: {str(e)[:50]}")
            return False

# 测试代码
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python menu_crawler.py <start_url> [username] [password]")
        sys.exit(1)
    
    start_url = sys.argv[1]
    username = sys.argv[2] if len(sys.argv) > 2 else None
    password = sys.argv[3] if len(sys.argv) > 3 else None
    
    # 如果没有提供密码，使用默认密码
    if username == "admin" and not password:
        password = "Asiainfo1@3"
    
    crawler = MenuCrawler(start_url, username=username, password=password)
    menu_tree = asyncio.run(crawler.run())
    
    # 输出菜单树到JSON文件
    with open('menu_tree.json', 'w', encoding='utf-8') as f:
        json.dump(menu_tree, f, ensure_ascii=False, indent=2)
    
    print("\n✅ 菜单树已生成并保存到 menu_tree.json")
    print("\n菜单树结构:")
    print(json.dumps(menu_tree, ensure_ascii=False, indent=2))
