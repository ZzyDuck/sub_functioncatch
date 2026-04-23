import asyncio
from collections import deque
from playwright.async_api import async_playwright
from urllib.parse import urlparse, urljoin
from typing import Set, List, Dict
import time
from ai_service import _ai_analyze_structured_data

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
        self.all_features: List[Dict] = []  # 存储所有功能点
        self.url_hierarchy: Dict[str, Dict] = {}  # 存储 URL 的父级关系
    
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
            login_success = False
            if self.username and self.password:
                print("\n🔐 正在执行登录...")
                login_success = await self._login(page)
                if login_success:
                    print("✅ 登录完成")
                else:
                    print("❌ 登录未完成")
            
            # 初始化队列
            url_queue = deque()
            
            # 如果登录成功，使用当前页面URL；否则使用start_url
            if login_success:
                initial_url = self._normalize_hash_url(page.url)
                print(f"\n📍 登录后开始爬取: {initial_url}")
            else:
                initial_url = self._normalize_hash_url(self.start_url)
                print(f"\n📍 开始爬取: {initial_url}")
            
            url_queue.append(initial_url)
            self.discovered_urls.add(initial_url)
            
            # 队列处理
            processed_urls = set()
            while url_queue and len(processed_urls) < self.max_clicks:
                current_url = url_queue.popleft()
                
                # 避免重复处理
                if current_url in processed_urls:
                    continue
                processed_urls.add(current_url)
                
                print(f"\n📍 处理: {current_url}")
                print(f"   队列长度: {len(url_queue)}")
                print(f"   已处理URL: {len(processed_urls)}/{self.max_clicks}")
                
                # 分析当前页面（不需要重新goto，直接分析当前页面）
                try:
                    # ========== 分析当前页面 ==========
                    await self._analyze_current_page(page, current_url)
                    # ==================================
                    
                    # 滚动页面加载所有内容
                    await self._scroll_page(page)
                    
                    # 提取当前页面的所有可交互元素
                    interactable = await self._get_all_interactable_elements(page)
                    print(f"   找到 {len(interactable)} 个可交互元素")
                    
                    # 按优先级排序：导航类 > 按钮 > 链接 > 其他
                    interactable = self._prioritize_elements(interactable)
                    
                    # 遍历每个元素
                    for idx, element_info in enumerate(interactable):
                        if len(processed_urls) >= self.max_clicks:
                            break
                            
                        # 避免重复点击相同元素
                        element_key = f"{element_info['tag']}|{element_info['text']}|{element_info.get('href', '')}"
                        if element_key in self.clicked_elements:
                            continue
                        self.clicked_elements.add(element_key)
                        
                        print(f"   [{idx+1}] 点击: {element_info['text'][:30]}")
                        print(f"      调试: 元素信息: tag={element_info['tag']}, selector={element_info.get('selector', 'N/A')}")
                        
                        try:
                            # 重新获取元素（防止 DOM 变化）
                            try:
                                # 优先使用生成的selector
                                if element_info.get('selector'):
                                    el = page.locator(element_info['selector']).first
                                    print(f"      调试: 使用selector定位成功")
                                else:
                                    # 备用：使用文本定位
                                    el = page.locator(f'text="{element_info["text"]}"').first
                                    print(f"      调试: 使用文本定位成功")
                                await el.scroll_into_view_if_needed()
                            except Exception as loc_err:
                                print(f"      调试: 元素定位失败: {str(loc_err)[:50]}")
                                continue
                            
                            # 记录点击前的状态
                            before_url = page.url
                            print(f"      调试: 点击前 URL: {before_url}")
                            
                            # 确保点击的是真正的路由链接
                            # 检查元素是否是链接或有路由属性
                            is_route_element = False
                            tag = element_info['tag'].upper()
                            href = element_info.get('href')
                            
                            # 检查是否是链接元素
                            if tag == 'A' and href:
                                is_route_element = True
                            # 检查是否有路由相关属性
                            elif any(key in element_info.get('className', '') for key in ['router-link', 'nav-link', 'menu-item']):
                                is_route_element = True
                            
                            print(f"      调试: 是否路由元素: {is_route_element}, 标签: {tag}, href: {href}")
                            
                            # 记录点击前的URL
                            before_url = page.url
                            
                            # 尝试点击
                            try:
                                # 使用 JavaScript 点击，更可靠
                                await el.evaluate("element => element.click()")
                                print(f"      调试: JavaScript 点击成功")
                            except Exception as js_err:
                                print(f"      调试: JS点击失败: {str(js_err)[:50]}")
                                # 备用：使用 Playwright 点击
                                try:
                                    await el.click(timeout=3000)
                                    print(f"      调试: Playwright 点击成功")
                                except Exception as pw_err:
                                    print(f"      调试: Playwright点击失败: {str(pw_err)[:50]}")
                                    continue
                            
                            # 主动轮询 URL 变化，捕获二级菜单的路由变化
                            after_url = before_url
                            for i in range(10):
                                await page.wait_for_timeout(5000)
                                current_url = page.url
                                if current_url != before_url:
                                    print(f"      ✅ 检测到 URL 变化: {current_url}")
                                    after_url = current_url
                                    break
                            
                            after_url_normalized = self._normalize_hash_url(after_url)
                            
                            # 捕获所有发现的路由
                            captured_routes = await page.evaluate("window.__SPA_CRAWLER.routes")
                            print(f"      调试: 捕获到的路由数量: {len(captured_routes) if captured_routes else 0}")
                            if captured_routes:
                                print(f"      捕获到 {len(captured_routes)} 个路由变化")
                                for route in captured_routes:
                                    if route.get('url'):
                                        full_url = urljoin(self.start_url, route['url'])
                                        full_url_normalized = self._normalize_hash_url(full_url)
                                        print(f"      路由: {route['type']} -> {full_url}")
                                        if full_url_normalized not in self.discovered_urls:
                                            self.discovered_urls.add(full_url_normalized)
                                            url_queue.append(full_url_normalized)
                                            print(f"      ✅ 发现新路由: {route['url']}")
                                        elif full_url_normalized not in processed_urls:
                                            # 如果URL已经在discovered_urls中但还没有处理，添加到队列
                                            url_queue.append(full_url_normalized)
                                            print(f"      ✅ 添加未处理路由到队列: {route['url']}")
                                # 清空路由监听器，避免重复检查
                                await page.evaluate("window.__SPA_CRAWLER.routes = []")
                            else:
                                print(f"      调试: 没有捕获到路由变化")
                            
                            # URL 变化了，添加到队列但继续在原页面探索
                            before_url_normalized = self._normalize_hash_url(before_url)
                            if after_url_normalized != before_url_normalized:
                                print(f"      ✅ 跳转到新页面: {after_url_normalized}")
                                
                                # 记录 URL 的层级关系
                                self.url_hierarchy[after_url_normalized] = {
                                    "parent_url": before_url_normalized,
                                    "click_text": element_info['text'],
                                    "depth": self.url_hierarchy.get(before_url_normalized, {}).get("depth", 0) + 1
                                }
                                print(f"      记录层级关系: {element_info['text']} -> {after_url_normalized} (深度: {self.url_hierarchy[after_url_normalized]['depth']})")
                                
                                # 记录新URL但不立即跳出循环
                                if after_url_normalized not in processed_urls:
                                    # 添加到队列末尾，稍后处理
                                    url_queue.append(after_url_normalized)
                                    self.discovered_urls.add(after_url_normalized)
                                    print(f"      添加到队列: {after_url_normalized}")
                                else:
                                    print(f"      已存在队列中: {after_url_normalized}")
                                
                                # 返回原页面，继续探索
                                try:
                                    await page.goto(current_url, wait_until='networkidle', timeout=10000)
                                    await page.wait_for_timeout(self.wait_time)
                                except:
                                    try:
                                        await page.go_back()
                                        await page.wait_for_timeout(self.wait_time)
                                    except:
                                        pass
                            
                        except Exception as e:
                            print(f"      ❌ 点击出错: {str(e)[:50]}")
                            continue
                    
                except Exception as e:
                    print(f"❌ 访问页面出错: {str(e)[:50]}")
                    print(f"   继续处理队列中的其他URL...")
                    continue
            
            await browser.close()
            
        # 构建层级化的功能点结构
        def build_hierarchical_features():
            # 按 URL 分组功能点
            features_by_url = {}
            for feature in self.all_features:
                url = feature.get('url', '')
                if url not in features_by_url:
                    features_by_url[url] = []
                features_by_url[url].append(feature)
            
            # 构建树形结构
            def build_tree(url):
                node = {
                    'url': url,
                    'depth': self.url_hierarchy.get(url, {}).get('depth', 0),
                    'click_text': self.url_hierarchy.get(url, {}).get('click_text', ''),
                    'features': features_by_url.get(url, []),
                    'children': []
                }
                
                # 查找所有子节点
                for child_url, info in self.url_hierarchy.items():
                    if info.get('parent_url') == url:
                        node['children'].append(build_tree(child_url))
                
                return node
            
            # 找到根节点（没有父级的 URL）
            root_urls = []
            for url in self.discovered_urls:
                if url not in self.url_hierarchy:
                    root_urls.append(url)
            
            # 构建树
            hierarchy = []
            for root_url in root_urls:
                hierarchy.append(build_tree(root_url))
            
            return hierarchy
        
        hierarchical_features = build_hierarchical_features()
        
        return {
            'urls': list(self.discovered_urls),
            'routes': list(self.discovered_routes),
            'total': len(self.discovered_urls),
            'features': self.all_features,  # 扁平列表（保持向后兼容）
            'hierarchical_features': hierarchical_features  # 层级结构
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
                    console.log('[SPA Crawler] pushState:', url);
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
                    console.log('[SPA Crawler] replaceState:', url);
                }
                return originalReplace.call(this, state, title, url);
            };
            
            // 监听 hashchange 事件（针对 hash 路由）
            window.addEventListener('hashchange', (e) => {
                window.__SPA_CRAWLER.routes.push({
                    type: 'hashchange',
                    url: e.newURL,
                    timestamp: Date.now()
                });
                console.log('[SPA Crawler] hashchange:', e.newURL);
            });
            
            // 监听 popstate 事件（浏览器前进/后退）
            window.addEventListener('popstate', (e) => {
                window.__SPA_CRAWLER.routes.push({
                    type: 'popstate',
                    url: window.location.href,
                    timestamp: Date.now()
                });
                console.log('[SPA Crawler] popstate:', window.location.href);
            });
            
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
        # 规范化URL
        url = self._normalize_hash_url(url)
        
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
                    after_url_normalized = self._normalize_hash_url(after_url)
                    if after_url_normalized != self._normalize_hash_url(before_url) and after_url_normalized not in self.discovered_urls:
                        print(f"{'  ' * depth}      ✅ 跳转到新页面: {after_url_normalized}")
                        await self._crawl_page(page, after_url_normalized, depth + 1)
                        
                        # 返回原页面
                        current_page_url = self._normalize_hash_url(page.url)
                        if current_page_url != url:
                            try:
                                await page.goto(url, wait_until='networkidle', timeout=10000)
                                await page.wait_for_timeout(self.wait_time)
                            except:
                                try:
                                    await page.go_back()
                                    await page.wait_for_timeout(self.wait_time)
                                except:
                                    pass
                    
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
                            // 生成唯一选择器
                            let selector = '';
                            if (el.id) {
                                selector = `#${el.id}`;
                            } else if (el.className && el.className.trim()) {
                                selector = `.${el.className.trim().replace(/\s+/g, '.')}`;
                            } else if (el.tagName === 'A' && el.href) {
                                selector = `a[href="${el.href}"]`;
                            } else if (el.tagName === 'BUTTON' && text) {
                                selector = `button:has-text("${text}")`;
                            } else {
                                selector = el.tagName.toLowerCase();
                            }
                            
                            elements.push({
                                tag: el.tagName,
                                text: text.slice(0, 100),
                                href: href,
                                className: el.className,
                                id: el.id,
                                selector: selector,
                                type: el.type || ''
                            });
                        }
                    });
                }
                
                return elements;
            }
        """)
    
    def _prioritize_elements(self, elements: List[Dict]) -> List[Dict]:
        """按优先级排序元素，优先点击可能跳转的元素"""
        def get_priority(el):
            text = el['text'].lower()
            tag = el['tag'].upper()
            
            # 1. 链接元素（最可能跳转）
            if tag == 'A' or el.get('href'):
                return 1
            # 2. 导航类按钮
            if tag == 'BUTTON' and any(keyword in text for keyword in ['登录', '注册', '首页', '个人', '设置', '退出', '返回']):
                return 2
            # 3. 其他按钮
            if tag == 'BUTTON':
                return 3
            # 4. 表单输入元素
            if tag in ['INPUT', 'SELECT', 'TEXTAREA']:
                return 4
            # 5. 其他元素
            return 5
        
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
                self.discovered_urls.add(self._normalize_hash_url(url))

    async def _analyze_current_page(self, page, url: str):
        """分析当前页面的功能点 - 针对 IAM 系统优化"""
        print(f"   🤖 正在分析功能点: {url}")
        
        page_data = await page.evaluate("""
            () => {
                // 1. 收集侧边栏菜单（一级）
                const level1Menus = [];
                const menuTextSet = new Set();
                const menuSelectors = [
                    '.el-tabs__item.is-left',  // 左侧垂直 Tab 菜单
                    '.el-tabs__item.is-left > div',  // 左侧垂直 Tab 菜单内的文本容器
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
                            level1Menus.push({ text: text, level: 1 });
                        }
                    });
                }
                
                // 2. 收集侧边栏菜单（二级及更深）
                const level2Menus = [];
                const subMenuTextSet = new Set();
                const subMenuSelectors = [
                    '.el-menu--vertical .el-menu-item',
                    '.el-menu--popup .el-menu-item',
                    '.sub-menu-item',
                    '.dropdown-item',
                    '.menu-item > .submenu > .menu-item',
                    '.el-submenu .el-menu-item',
                    '.sidebar .submenu .item',
                    '.nav .subnav .item',
                    '.el-menu--vertical > .el-submenu > .el-menu > .el-menu-item',
                    '.el-menu-item-group > .el-menu > .el-menu-item',
                    '.menu > li > ul > li > a',
                    '.nav > li > ul > li > a',
                    '.sidebar > ul > li > ul > li > a',
                    '.el-submenu > .el-menu > .el-menu-item',
                    '.dropdown-menu > li > a'
                ];
                
                for (const selector of subMenuSelectors) {
                    document.querySelectorAll(selector).forEach(el => {
                        const text = (el.innerText || '').trim();
                        if (text && text.length < 50 && !subMenuTextSet.has(text)) {
                            subMenuTextSet.add(text);
                            level2Menus.push({ text: text, level: 2 });
                        }
                    });
                }
                
                // 3. 收集顶部导航栏按钮
                const topButtons = [];
                const topSelectors = [
                    '.right-panel i',
                    '.right-panel .el-dropdown',
                    '.top-nav button',
                    '.header-button'
                ];
                
                for (const selector of topSelectors) {
                    document.querySelectorAll(selector).forEach(el => {
                        const className = el.className || '';
                        const text = (el.innerText || '').trim();
                        let buttonText = text;
                        
                        if (!buttonText) {
                            if (className.includes('ri-search-line')) buttonText = '搜索';
                            else if (className.includes('ri-notification-line')) buttonText = '通知';
                            else if (className.includes('ri-question-line')) buttonText = '帮助';
                            else if (className.includes('ri-lock-line')) buttonText = '锁屏';
                            else if (className.includes('ri-fullscreen-fill')) buttonText = '全屏';
                            else if (className.includes('ri-brush-2-line')) buttonText = '主题切换';
                            else if (className.includes('ri-refresh-line')) buttonText = '刷新';
                            else if (className.includes('ri-bookmark-3-fill')) buttonText = '收藏';
                            else if (className.includes('mine_manage')) buttonText = '个人中心/退出登录';
                        }
                        
                        if (buttonText) {
                            topButtons.push({ text: buttonText, location: '顶部导航栏' });
                        }
                    });
                }
                
                // 4. 收集 Tab 页签
                const tabs = [];
                document.querySelectorAll('.el-tabs__item, .tab-item, .nav-tab').forEach(el => {
                    const text = (el.innerText || '').trim();
                    if (text && text.length < 50) {
                        tabs.push({ text: text, type: '页签' });
                    }
                });
                
                // 5. 收集页面内的功能按钮
                const pageButtons = [];
                const buttonSelectors = [
                    '.more_icon',
                    '.el-button--text',
                    '.more_icon span',
                    'button:not(.el-submenu__title)',
                    '.btn'
                ];
                
                for (const selector of buttonSelectors) {
                    document.querySelectorAll(selector).forEach(el => {
                        const text = (el.innerText || '').trim();
                        if (text && text.length < 50) {
                            pageButtons.push({ text: text, location: '页面内' });
                        }
                    });
                }
                
                // 6. 收集所有可点击元素
                const allClickable = [];
                const clickableSelectors = [
                    'button',
                    'a[href]',
                    '[role="button"]',
                    '[role="menuitem"]',
                    '.btn',
                    '.nav-item',
                    '.menu-item',
                    '.sidebar-item',
                    '.ant-menu-item',
                    '.el-menu-item',
                    '[router-link]',
                    '[to]',
                    '[onclick]'
                ];
                
                for (const selector of clickableSelectors) {
                    document.querySelectorAll(selector).forEach(el => {
                        const text = (el.innerText || '').trim();
                        if (text && text.length < 100 && el.offsetParent !== null) {
                            allClickable.push({ text: text });
                        }
                    });
                }
                
                // 映射到 AI 函数期望的格式
                const buttons = [];
                const links = [];
                
                // 合并所有按钮
                topButtons.forEach(btn => buttons.push({ text: btn.text, visible: true }));
                pageButtons.forEach(btn => buttons.push({ text: btn.text, visible: true }));
                
                // 合并所有链接（菜单和可点击元素）
                level1Menus.forEach(menu => links.push({ text: menu.text, href: '#' }));
                level2Menus.forEach(menu => links.push({ text: menu.text, href: '#' }));
                allClickable.forEach(el => {
                    if (el.text) links.push({ text: el.text, href: '#' });
                });
                
                // 提取标题层级
                const headings = [];
                document.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(h => {
                    const text = (h.innerText || '').trim();
                    if (text) {
                        headings.push({ level: h.tagName, text: text });
                    }
                });
                
                // 提取表单
                const forms = Array.from(document.querySelectorAll('form')).map(f => ({
                    action: f.action,
                    inputs: Array.from(f.querySelectorAll('input')).map(i => i.name)
                }));
                
                return {
                    title: document.title,
                    url: window.location.href,
                    buttons: buttons,
                    links: links,
                    headings: headings,
                    forms: forms,
                    tabs: tabs,
                    level1Menus: level1Menus,
                    level2Menus: level2Menus,
                    topButtons: topButtons,
                    pageButtons: pageButtons,
                    clickableElements: allClickable,
                    totalElements: level1Menus.length + level2Menus.length + topButtons.length + tabs.length + pageButtons.length
                };
            }
        """)
        
        print(f"   页面元素统计: 一级菜单={len(page_data.get('level1Menus', []))}, "
            f"二级菜单={len(page_data.get('level2Menus', []))}, "
            f"顶部按钮={len(page_data.get('topButtons', []))}, "
            f"页签={len(page_data.get('tabs', []))}")
        
        features = _ai_analyze_structured_data(url, page_data)
        print(f"   ✅ 提取到 {len(features)} 个功能点")
        
        self.all_features.extend(features)

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

