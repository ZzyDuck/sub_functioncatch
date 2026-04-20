import asyncio
from playwright.async_api import async_playwright
from urllib.parse import urlparse, urljoin
from typing import Set, List, Dict
import time

class SPACrawler:
    """SPA 应用全面爬虫 - 普适性和全面性优先"""
    
    def __init__(self, start_url: str, max_clicks: int = 100, wait_time: int = 2000, username: str = None, password: str = None):
        self.start_url = start_url
        self.base_domain = urlparse(start_url).netloc
        self.max_clicks = max_clicks  # 最大点击次数
        self.wait_time = wait_time    # 每次点击后等待时间(ms)
        self.username = username      # 登录用户名
        self.password = password      # 登录密码
        
        self.discovered_urls: Set[str] = set()
        self.discovered_routes: Set[str] = set()
        self.clicked_elements: Set[str] = set()  # 记录已点击的元素
        
    async def run(self) -> Dict[str, List[str]]:
        """运行爬虫"""
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
            
            # 监听所有网络请求和导航
            page.on('request', self._handle_request)
            page.on('response', self._handle_response)
            page.on('framenavigated', self._handle_navigation)
            
            # 注入全局监听脚本
            await self._inject_monitors(page)
            
            # 执行登录
            if self.username and self.password:
                print("\n🔐 正在执行登录...")
                await self._login(page)
                print("✅ 登录完成")
            
            # 开始爬取
            await self._crawl_page(page, self.start_url, depth=0)
            
            await browser.close()
            
        return {
            'urls': list(self.discovered_urls),
            'routes': list(self.discovered_routes),
            'total': len(self.discovered_urls)
        }
    
    async def _inject_monitors(self, page):
        """注入 JavaScript 监听器，捕获所有前端路由变化"""
        await page.add_init_script("""
            // 全局存储捕获的信息
            window.__SPA_CRAWLER = {
                routes: [],
                clicks: [],
                popups: [],
                apiCalls: []
            };
            
            // 拦截 Vue Router
            const originalPush = History.prototype.pushState;
            const originalReplace = History.prototype.replaceState;
            
            History.prototype.pushState = function(state, title, url) {
                if (url && url !== window.location.pathname) {
                    window.__SPA_CRAWLER.routes.push({
                        type: 'pushState',
                        url: url,
                        timestamp: Date.now()
                    });
                }
                return originalPush.call(this, state, title, url);
            };
            
            History.prototype.replaceState = function(state, title, url) {
                if (url && url !== window.location.pathname) {
                    window.__SPA_CRAWLER.routes.push({
                        type: 'replaceState',
                        url: url,
                        timestamp: Date.now()
                    });
                }
                return originalReplace.call(this, state, title, url);
            };
            
            // 监听所有点击事件
            document.addEventListener('click', (e) => {
                const target = e.target.closest('button, a, [role="button"], .btn, [onclick]');
                if (target) {
                    window.__SPA_CRAWLER.clicks.push({
                        tag: target.tagName,
                        text: (target.innerText || target.value || '').slice(0, 100),
                        href: target.href || target.getAttribute('to'),
                        className: target.className,
                        id: target.id
                    });
                }
            }, true);
            
            // 监听弹窗/模态框
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === 1) {
                            const isModal = node.matches && (
                                node.matches('.modal, .dialog, [role="dialog"], .popup, .drawer') ||
                                node.querySelector?.('.modal, .dialog, [role="dialog"]')
                            );
                            if (isModal) {
                                window.__SPA_CRAWLER.popups.push({
                                    html: node.outerHTML.slice(0, 500),
                                    timestamp: Date.now()
                                });
                            }
                        }
                    });
                });
            });
            observer.observe(document.body, { childList: true, subtree: true });
            
            console.log('[SPA Crawler] 监听器已注入');
        """)
    
    async def _crawl_page(self, page, url: str, depth: int):
        """递归爬取页面"""
        if url in self.discovered_urls:
            return
        if len(self.discovered_urls) >= self.max_clicks:
            return
        
        print(f"\n{'  ' * depth}📍 访问: {url} (深度 {depth})")
        self.discovered_urls.add(url)
        
        try:
            # 访问页面
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(self.wait_time)
            
            # 滚动页面加载所有内容
            await self._scroll_page(page)
            
            # 提取当前页面的所有可交互元素
            interactable = await self._get_all_interactable_elements(page)
            print(f"{'  ' * depth}   找到 {len(interactable)} 个可交互元素")
            
            # 按优先级排序：导航类 > 按钮 > 链接 > 其他
            interactable = self._prioritize_elements(interactable)
            
            # 遍历每个元素
            for idx, element_info in enumerate(interactable):
                if len(self.discovered_urls) >= self.max_clicks:
                    break
                    
                # 避免重复点击相同元素
                element_key = f"{element_info['tag']}|{element_info['text']}|{element_info.get('href', '')}"
                if element_key in self.clicked_elements:
                    continue
                self.clicked_elements.add(element_key)
                
                print(f"{'  ' * depth}   [{idx+1}] 点击: {element_info['text'][:30]}")
                
                try:
                    # 重新获取元素（防止 DOM 变化）
                    try:
                        el = await page.locator(f'text="{element_info["text"]}"').first
                        await el.scroll_into_view_if_needed()
                    except:
                        continue
                    
                    # 记录点击前的状态
                    before_url = page.url
                    before_routes = await page.evaluate("window.__SPA_CRAWLER.routes.length")
                    
                    # 尝试点击
                    try:
                        # 使用 JavaScript 点击，更可靠
                        await el.evaluate("el => el.click()")
                        await page.wait_for_timeout(self.wait_time)
                    except:
                        # 备用：使用 Playwright 点击
                        try:
                            await el.click(timeout=3000)
                            await page.wait_for_timeout(self.wait_time)
                        except:
                            continue
                    
                    # 检查是否发现新路由
                    after_url = page.url
                    after_routes = await page.evaluate("window.__SPA_CRAWLER.routes.length")
                    
                    # 捕获所有发现的路由
                    captured_routes = await page.evaluate("window.__SPA_CRAWLER.routes")
                    for route in captured_routes:
                        if route['url']:
                            full_url = urljoin(self.start_url, route['url'])
                            if full_url not in self.discovered_urls:
                                self.discovered_urls.add(full_url)
                                print(f"{'  ' * depth}      发现新路由: {route['url']}")
                    
                    # URL 变化了，递归爬取新页面
                    if after_url != before_url and after_url not in self.discovered_urls:
                        print(f"{'  ' * depth}      ✅ 跳转到新页面: {after_url}")
                        await self._crawl_page(page, after_url, depth + 1)
                        
                        # 返回原页面
                        if page.url != url:
                            await page.go_back()
                            await page.wait_for_timeout(self.wait_time)
                    
                    # 检查是否打开弹窗
                    popups = await page.evaluate("window.__SPA_CRAWLER.popups")
                    if len(popups) > after_routes:
                        print(f"{'  ' * depth}      📱 弹窗已打开")
                        # 尝试关闭弹窗
                        try:
                            await page.keyboard.press('Escape')
                            await page.wait_for_timeout(500)
                        except:
                            pass
                    
                except Exception as e:
                    print(f"{'  ' * depth}      ❌ 点击失败: {str(e)[:50]}")
                    continue
                    
        except Exception as e:
            print(f"{'  ' * depth}   ❌ 页面访问失败: {e}")
    
    async def _scroll_page(self, page, max_scrolls: int = 10):
        """滚动页面加载动态内容"""
        for i in range(max_scrolls):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await page.wait_for_timeout(500)
        
        # 滚动到顶部
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(500)
    
    async def _get_all_interactable_elements(self, page) -> List[Dict]:
        """获取页面上所有可交互元素"""
        return await page.evaluate("""
            () => {
                const elements = [];
                const seen = new Set();
                
                // 全面覆盖各种可交互元素
                const selectors = [
                    // 标准按钮和链接
                    'button',
                    'a[href]',
                    'input[type="button"]',
                    'input[type="submit"]',
                    'input[type="reset"]',
                    
                    // ARIA 角色
                    '[role="button"]',
                    '[role="link"]',
                    '[role="menuitem"]',
                    '[role="tab"]',
                    '[role="navigation"] a',
                    
                    // 常见类名
                    '.btn',
                    '.button',
                    '.link',
                    '.nav-item',
                    '.nav-link',
                    '.menu-item',
                    '.dropdown-item',
                    '.tab',
                    '.accordion-button',
                    
                    // 路由相关
                    '[router-link]',
                    '[to]',
                    '[data-to]',
                    '[href^="/"]',
                    
                    // 可点击的 div/span
                    '[onclick]',
                    '[ng-click]',
                    
                    // 导航元素
                    'nav a',
                    'header a',
                    '.navbar a',
                    '.sidebar a',
                    
                    // 表单相关
                    'select',
                    'input:not([type="hidden"])',
                    'textarea'
                ];
                
                for (const selector of selectors) {
                    document.querySelectorAll(selector).forEach(el => {
                        // 检查元素是否可见
                        const rect = el.getBoundingClientRect();
                        const isVisible = rect.width > 0 && rect.height > 0;
                        
                        if (!isVisible) return;
                        
                        // 获取文本
                        let text = (el.innerText || el.value || '').trim();
                        if (!text && el.tagName === 'A') {
                            text = el.href;
                        }
                        // 对于输入框、复选框、单选框等元素，不需要文本内容
                        const inputTypes = ['text', 'password', 'email', 'tel', 'number', 'checkbox', 'radio', 'submit', 'button', 'reset'];
                        if ((!text || text.length > 200) && !((el.tagName === 'INPUT' && inputTypes.includes(el.type)) || el.tagName === 'SELECT' || el.tagName === 'TEXTAREA')) {
                            return;
                        }
                        // 对于没有文本的输入元素，使用占位符或类型作为文本
                        if (!text && (el.tagName === 'INPUT' || el.tagName === 'SELECT' || el.tagName === 'TEXTAREA')) {
                            if (el.placeholder) {
                                text = el.placeholder;
                            } else if (el.type) {
                                text = el.type + ' input';
                            } else {
                                text = el.tagName.toLowerCase();
                            }
                        }
                        
                        // 获取可能的路由
                        let href = el.href || 
                                  el.getAttribute('to') ||
                                  el.getAttribute('data-to') ||
                                  el.getAttribute('router-link');
                        
                        const key = `${el.tagName}|${text}|${href}`;
                        if (!seen.has(key)) {
                            seen.add(key);
                            elements.push({
                                tag: el.tagName,
                                text: text.slice(0, 100),
                                href: href,
                                className: el.className,
                                id: el.id,
                                type: el.type || ''
                            });
                        }
                    });
                }
                
                return elements;
            }
        """)
    
    def _prioritize_elements(self, elements: List[Dict]) -> List[Dict]:
        """按优先级排序元素"""
        def get_priority(el):
            text = el['text'].lower()
            
            # 导航类元素最高优先级
            if any(keyword in text for keyword in ['登录', '注册', '忘记', '首页', '个人', '设置']):
                return 1
            # 按钮类次之
            if el['tag'] in ['BUTTON', 'A']:
                return 2
            # 表单输入
            if el.get('type') in ['text', 'email', 'password']:
                return 3
            # 其他
            return 4
        
        elements.sort(key=get_priority)
        return elements
    
    def _handle_request(self, request):
        """处理网络请求"""
        url = request.url
        if '/api/' in url or '/v1/' in url or '/rest/' in url:
            self.discovered_routes.add(url)
    
    def _handle_response(self, response):
        """处理响应"""
        pass
    
    def _handle_navigation(self, frame):
        """处理导航"""
        if frame.parent_frame is None:  # 主框架
            url = frame.url
            if url and url != 'about:blank':
                self.discovered_urls.add(url)
    
    async def _login(self, page):
        """执行登录操作"""
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
            
        except Exception as e:
            print(f"❌ 登录失败: {str(e)[:50]}")

