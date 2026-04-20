import asyncio
import subprocess
import sys
import time
import os
from core.cdp_client import CDPClient
from core.anti_detection import get_launch_args, get_anti_detection_script
from extractors.static_extractor import StaticExtractor
from extractors.dynamic_extractor import DynamicExtractor


class FeatureExtractor:
    def __init__(self, headless=False, port=9222):
        self.headless = headless
        self.port = port

    def _start_chrome(self, url=None):
        if sys.platform == 'win32':
            cmd = f'start chrome --remote-debugging-port={self.port} --user-data-dir=%TEMP%\\chrome-profile-stable'
            for arg in get_launch_args():
                cmd += f' {arg}'
            if self.headless:
                cmd += ' --headless'
            if url:
                cmd += f' {url}'
            subprocess.Popen(cmd, shell=True)
        else:
            cmd = ['google-chrome', f'--remote-debugging-port={self.port}',
                  '--user-data-dir=/tmp/chrome-profile-stable'] + get_launch_args()
            if self.headless:
                cmd.append('--headless')
            if url:
                cmd.append(url)
            subprocess.Popen(cmd)
        time.sleep(3)

    async def extract_full_page(self, url: str) -> dict:
        self._start_chrome(url)

        client = CDPClient(self.port)
        await client.connect(url)

        await client.evaluate(get_anti_detection_script())
        
        # 执行登录
        await self._login(client)

        dynamic = DynamicExtractor(client)
        static = StaticExtractor(client)

        await dynamic.scroll()
        tabs = await dynamic.click_tabs()
        load_more = await dynamic.click_load_more()
        popups = await dynamic.extract_popups()
        elements = await static.extract()
        
        # 在关闭连接前获取页面标题
        title = await client.evaluate("document.title")

        await client.close()

        return {
            "url": url,
            "title": title,
            "buttons": elements.get("buttons", []),
            "forms": elements.get("forms", []),
            "links": elements.get("links", []),
            "headings": elements.get("headings", []),
            "tabs": tabs,
            "popups": popups,
            "load_more_clicked": load_more,
        }
    
    async def _login(self, client):
        """执行登录操作"""
        username = os.getenv("USERNAME")
        password = os.getenv("PASSWORD")
        
        if not username or not password:
            return
        
        # 检查当前页面是否是登录页面
        current_url = await client.evaluate("window.location.href")
        if "login" in current_url.lower():
            print("  执行登录...")
            
            # 等待页面加载
            await asyncio.sleep(2)
            
            # 填写用户名
            try:
                await client.evaluate('document.querySelector("input[placeholder=\"请输入帐号/手机号/邮箱\"]").value = "' + username + '"')
            except:
                try:
                    await client.evaluate('document.querySelector("input[type=\"text\"]").value = "' + username + '"')
                except:
                    pass
            
            # 填写密码
            try:
                await client.evaluate('document.querySelector("input[placeholder=\"请输入密码\"]").value = "' + password + '"')
            except:
                try:
                    await client.evaluate('document.querySelector("input[type=\"password\"]").value = "' + password + '"')
                except:
                    pass
            
            # 点击登录按钮
            try:
                await client.evaluate('document.querySelector("button:has-text(\"登录\")").click()')
            except:
                try:
                    await client.evaluate('document.querySelector("button[type=\"submit\"]").click()')
                except:
                    try:
                        await client.evaluate('document.querySelector("button").click()')
                    except:
                        pass
            
            # 等待登录完成
            await asyncio.sleep(5)