import asyncio
import json
import urllib.request
import websockets


class CDPClient:
    def __init__(self, port=9222):
        self.port = port
        self.ws = None
        self.msg_id = 0
        self.pending = {}

    async def connect(self, url=None):
        req = urllib.request.Request(f'http://127.0.0.1:{self.port}/json/list')
        pages = json.loads(urllib.request.urlopen(req).read())
        if not pages:
            raise RuntimeError("未找到可用的 Chrome 页面，请确保 Chrome 已启动")
        
        self.ws = await websockets.connect(pages[0]['webSocketDebuggerUrl'])
        asyncio.create_task(self._recv_loop())
        await self.send("Runtime.enable")
        if url:
            await self.evaluate(f'location.href="{url}"')
            await asyncio.sleep(2)

    async def _recv_loop(self):
        async for msg in self.ws:
            data = json.loads(msg)
            if data.get('id') in self.pending:
                self.pending.pop(data['id']).set_result(data)

    async def send(self, method, params=None):
        self.msg_id += 1
        fut = asyncio.Future()
        self.pending[self.msg_id] = fut
        await self.ws.send(json.dumps({"id": self.msg_id, "method": method, "params": params or {}}))
        return await fut

    async def evaluate(self, script):
        resp = await self.send("Runtime.evaluate", {"expression": script, "returnByValue": True})
        return resp.get('result', {}).get('result', {}).get('value')

    async def close(self):
        if self.ws:
            await self.ws.close()