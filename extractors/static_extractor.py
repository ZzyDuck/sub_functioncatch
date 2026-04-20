class StaticExtractor:
    def __init__(self, client):
        self.client = client

    async def extract(self) -> dict:
        return await self.client.evaluate("""
            () => ({
                buttons: Array.from(document.querySelectorAll('button,[role="button"],input[type="submit"]')).map(b => ({
                    text: (b.innerText||b.value||'').trim(),
                    visible: b.offsetParent !== null
                })).filter(b=>b.text),
                forms: Array.from(document.querySelectorAll('form')).map(f => ({
                    action: f.action,
                    method: f.method,
                    inputs: Array.from(f.querySelectorAll('input')).map(i=>i.name)
                })),
                links: Array.from(document.querySelectorAll('a[href]')).map(a => ({
                    text: (a.innerText||'').trim().slice(0,100),
                    href: a.href
                })).filter(l=>l.href && !l.href.startsWith('javascript:')),
                headings: Array.from(document.querySelectorAll('h1,h2,h3')).map(h => ({
                    level: parseInt(h.tagName[1]),
                    text: (h.innerText||'').trim()
                })).filter(h=>h.text)
            })
        """)