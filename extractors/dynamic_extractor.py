import asyncio


class DynamicExtractor:
    def __init__(self, client):
        self.client = client

    async def scroll(self, max_scrolls=5):
        for _ in range(max_scrolls):
            await self.client.evaluate("window.scrollBy(0,800)")
            await asyncio.sleep(1)
        await self.client.evaluate("window.scrollTo(0,0)")

    async def click_tabs(self) -> list:
        return await self.client.evaluate("""
            () => {
                const results = [];
                for (const tab of document.querySelectorAll('[role="tab"],.tab,[data-toggle="tab"]')) {
                    if(!tab.offsetParent) continue;
                    const name = tab.innerText || '';
                    tab.click();
                    const panel = document.querySelector('[role="tabpanel"],.tab-pane.active');
                    results.push({tab: name, content: panel ? panel.innerText.slice(0,500) : ''});
                }
                return results;
            }
        """)

    async def click_load_more(self, max_clicks=3) -> int:
        clicked = 0
        for _ in range(max_clicks):
            ok = await self.client.evaluate("""
                () => {
                    for(const btn of document.querySelectorAll('button:has-text("加载更多"),.load-more')){
                        if(btn.offsetParent){ btn.click(); return true; }
                    }
                    return false;
                }
            """)
            if not ok:
                break
            clicked += 1
            await asyncio.sleep(1.5)
        return clicked

    async def extract_popups(self) -> list:
        return await self.client.evaluate("""
            () => {
                const popups = [];
                for(const trigger of document.querySelectorAll('button:has-text("登录"),button:has-text("注册"),[data-toggle="modal"]')){
                    if(!trigger.offsetParent) continue;
                    const text = trigger.innerText || '';
                    trigger.click();
                    const modal = document.querySelector('.modal,.dialog,[role="dialog"]');
                    if(modal && modal.offsetParent){
                        popups.push({trigger: text, content: modal.innerText.slice(0,500)});
                        modal.querySelector('.close,[aria-label="Close"]')?.click();
                    }
                }
                return popups;
            }
        """)