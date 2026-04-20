import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from playwright.sync_api import sync_playwright

IGNORED_QUERY_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "ref",
    "session_id",
    "sid",
}
SMART_IGNORE_PARAMS = {"page", "offset", "start", "limit", "size", "idx"}
MAX_PAGES = 20


def scroll_page(page, max_scrolls=5, scroll_distance=800, wait_time=1000):
    """
    自动滚动页面，加载更多内容
    - max_scrolls: 最大滚动次数
    - scroll_distance: 每次滚动的距离（像素）
    - wait_time: 滚动后等待时间（毫秒）
    """
    for i in range(max_scrolls):
        page.evaluate(f"window.scrollBy(0, {scroll_distance})")
        page.wait_for_timeout(wait_time)
    # 滚动回顶部，让 AI 分析时从顶部开始
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(500)


def normalize_url(raw_url: str) -> str:
    try:
        parsed = urlparse(raw_url)
        query = parse_qsl(parsed.query, keep_blank_values=True)
        filtered = []
        for key, value in query:
            lower_key = key.lower()
            if lower_key in IGNORED_QUERY_PARAMS:
                continue
            if lower_key in SMART_IGNORE_PARAMS and re.fullmatch(r"\d+", value or ""):
                continue
            filtered.append((key, value))

        filtered.sort()
        normalized_query = urlencode(filtered, doseq=True)
        normalized_parsed = parsed._replace(query=normalized_query, fragment="")
        return urlunparse(normalized_parsed)
    except Exception:
        return raw_url


def is_same_site(base_url: str, target_url: str) -> bool:
    try:
        return urlparse(base_url).netloc == urlparse(target_url).netloc
    except Exception:
        return False


def crawl_site(start_url: str, max_pages: int = MAX_PAGES) -> list[str]:
    visited = set()
    queue = [start_url]

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()

        while queue and len(visited) < max_pages:
            url = queue.pop(0)
            print(f"[Crawler] 访问: {url} (已访问 {len(visited)}/{max_pages})")
            normalized = normalize_url(url)
            if normalized in visited:
                continue

            try:
                page.goto(url, timeout=30000, wait_until="networkidle")
                page.wait_for_timeout(2000)  # 额外等待2秒，确保动态内容加载
                
                # 自动滚动页面，加载滚动后出现的内容
                scroll_page(page, max_scrolls=5, scroll_distance=800, wait_time=1000)
                
                visited.add(normalized)
                hrefs = page.eval_on_selector_all(
                    "a[href]", "elements => elements.map(element => element.href).filter(Boolean)"
                )

                for href in hrefs:
                    if not is_same_site(start_url, href):
                        continue
                    next_normalized = normalize_url(href)
                    if next_normalized not in visited and next_normalized not in queue:
                        queue.append(href)
            except Exception as exc:
                print(f"[Crawler] 访问失败: {url} -> {exc}")

        browser.close()

    return list(visited)