class StaticExtractor:
    def __init__(self, client):
        self.client = client

    async def extract(self) -> dict:
        return await self.client.evaluate("""
            () => ({
                buttons: Array.from(document.querySelectorAll('button,[role="button"],input[type="submit"],input[type="button"],input[type="reset"]')).map(b => ({
                    text: (b.innerText||b.value||'').trim(),
                    visible: b.offsetParent !== null,
                    type: b.type || 'button'
                })).filter(b=>b.visible),
                forms: Array.from(document.querySelectorAll('form')).map(f => ({
                    action: f.action,
                    method: f.method,
                    inputs: Array.from(f.querySelectorAll('input,select,textarea')).map(i=> ({
                        name: i.name,
                        type: i.type || (i.tagName === 'SELECT' ? 'select' : (i.tagName === 'TEXTAREA' ? 'textarea' : '')),
                        placeholder: i.placeholder || '',
                        checked: i.checked || false,
                        required: i.required || false
                    }))
                })),
                links: Array.from(document.querySelectorAll('a[href]')).map(a => ({
                    text: (a.innerText||'').trim().slice(0,100),
                    href: a.href,
                    visible: a.offsetParent !== null
                })).filter(l=>l.href && !l.href.startsWith('javascript:') && l.visible),
                headings: Array.from(document.querySelectorAll('h1,h2,h3')).map(h => ({
                    level: parseInt(h.tagName[1]),
                    text: (h.innerText||'').trim(),
                    visible: h.offsetParent !== null
                })).filter(h=>h.text && h.visible)
            })
        """)