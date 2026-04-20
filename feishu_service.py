import os
import time
from typing import Any, List, Optional

import requests

FEISHU_BASE = "https://open.feishu.cn/open-apis"


class FeishuClient:
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.access_token = None
        self.token_expires_at = 0  # 添加过期时间

    def get_app_access_token(self) -> str:
        """获取 app_access_token（不是 tenant_access_token）"""
        # 检查是否过期
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token

        # 使用正确的 app_access_token 接口
        url = f"{FEISHU_BASE}/auth/v3/app_access_token/internal/"
        response = requests.post(url, json={"app_id": self.app_id, "app_secret": self.app_secret}, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 0:
            raise RuntimeError(f"获取飞书 app_access_token 失败: {data}")
        
        self.access_token = data.get("app_access_token")  # 注意是 app_access_token
        expires_in = data.get("expire", 7200)
        self.token_expires_at = time.time() + expires_in - 300  # 提前5分钟刷新
        return self.access_token

    def _headers(self) -> dict[str, str]:
        token = self.get_app_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def create_spreadsheet(self, title: str, sheet_title: str = "Sheet1") -> str:
        url = f"{FEISHU_BASE}/sheets/v3/spreadsheets"
        payload = {
            "title": title,
            "sheets": [{"title": sheet_title}]
        }
        response = requests.post(url, headers=self._headers(), json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 0:
            raise RuntimeError(f"创建飞书表格失败: {data}")
        
        # 获取 spreadsheet_token
        if "spreadsheet" in data["data"]:
            spreadsheet_token = data["data"]["spreadsheet"]["spreadsheet_token"]
        else:
            spreadsheet_token = data["data"]["spreadsheet_token"]
        return spreadsheet_token

    def share_spreadsheet(self, spreadsheet_token: str, allow_edit: bool = True) -> None:
        """设置表格公开权限 - 使用正确的 API v2"""
        # 使用 v2 版本 API（与 client.py 一致）
        url = f"{FEISHU_BASE}/drive/v2/permissions/{spreadsheet_token}/public?type=sheet"
        
        # 正确的请求体格式（与 client.py 一致）
        payload = {
            "external_access_entity": "open",
            "link_share_entity": "anyone_editable" if allow_edit else "anyone_readable",
            "security_entity": "anyone_can_edit" if allow_edit else "anyone_can_view",
            "comment_entity": "anyone_can_edit" if allow_edit else "anyone_can_view",
            "share_entity": "anyone",
            "copy_entity": "anyone_can_edit" if allow_edit else "anyone_can_view"
        }
        
        response = requests.patch(url, headers=self._headers(), json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 0:
            raise RuntimeError(f"共享飞书表格失败: {data}")

    def batch_update_values(self, spreadsheet_token: str, sheet_id: str, rows: List[List[Any]]) -> None:
        """批量更新值 - 使用正确的 v2 API"""
        import json
        
        # 定义数据清洗函数
        def clean_cell(cell):
            if cell is None:
                return ""
            elif isinstance(cell, bool):
                return "true" if cell else "false"
            elif isinstance(cell, (list, dict)):
                return json.dumps(cell, ensure_ascii=False)
            else:
                return str(cell)
        
        # 清洗所有单元格数据
        cleaned_rows = []
        for row in rows:
            cleaned_row = [clean_cell(cell) for cell in row]
            cleaned_rows.append(cleaned_row)
        
        # 计算范围
        num_rows = len(cleaned_rows)
        num_cols = max(len(row) for row in cleaned_rows) if cleaned_rows else 0
        
        def col_to_letter(col):
            if col <= 0:
                return 'A'
            letter = ''
            temp_col = col
            while temp_col > 0:
                temp_col, remainder = divmod(temp_col - 1, 26)
                letter = chr(65 + remainder) + letter
            return letter
        
        if num_rows > 0 and num_cols > 0:
            end_col = col_to_letter(num_cols)
            range_str = f"{sheet_id}!A1:{end_col}{num_rows}"
        else:
            range_str = f"{sheet_id}!A1"
        
        # 使用 v2 API 和正确的请求体格式
        url = f"{FEISHU_BASE}/sheets/v2/spreadsheets/{spreadsheet_token}/values"
        payload = {
            "valueRange": {
                "range": range_str,
                "values": cleaned_rows
            }
        }
        
        response = requests.put(url, headers=self._headers(), params={"range": range_str}, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 0:
            raise RuntimeError(f"更新飞书表格值失败: {data}")

    def get_spreadsheet_metainfo(self, spreadsheet_token: str) -> dict:
        """获取表格元信息"""
        url = f"{FEISHU_BASE}/sheets/v2/spreadsheets/{spreadsheet_token}/metainfo"
        response = requests.get(url, headers=self._headers(), timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 0:
            raise RuntimeError(f"获取飞书表格元信息失败: {data}")
        return data

    def create_sheet_with_rows(self, title: str, headers: List[str], rows: List[List[Any]], sheet_name: str = "Sheet1") -> str:
        """创建表格并写入数据"""
        # 创建表格，指定工作表名称
        token = self.create_spreadsheet(title, sheet_name)
        
        # 设置公开权限
        try:
            self.share_spreadsheet(token)
        except Exception as e:
            print(f"警告: 设置公开权限失败 - {e}")
        
        # 获取表格元信息，找到正确的 sheet_id（注意字段名是 sheetId）
        metainfo = self.get_spreadsheet_metainfo(token)
        sheets = metainfo.get("data", {}).get("sheets", [])
        if not sheets:
            raise RuntimeError("表格中没有找到工作表")
        
        # 查找匹配的工作表（按名称）
        target_sheet = None
        for sheet in sheets:
            if sheet.get("title") == sheet_name:
                target_sheet = sheet
                break
        
        if not target_sheet:
            target_sheet = sheets[0]
            print(f"警告: 未找到工作表 '{sheet_name}'，使用 '{target_sheet.get('title')}'")
        
        sheet_id = target_sheet.get("sheetId")  # 注意字段名是 sheetId（大写 I）
        print(f"使用的 sheet_id: {sheet_id}")
        
        # 写入数据
        all_rows = [headers] + rows
        self.batch_update_values(token, sheet_id, all_rows)
        
        return token

    def sheet_url(self, spreadsheet_token: str) -> str:
        return f"https://sheet.feishu.cn/sheet/{spreadsheet_token}"

    def update_test_results(self, spreadsheet_token: str, start_row: int, results: List[dict[str, Any]], sheet_name: str = "Sheet1") -> None:
        """更新测试结果"""
        # 先获取正确的 sheet_id
        metainfo = self.get_spreadsheet_metainfo(spreadsheet_token)
        sheets = metainfo.get("data", {}).get("sheets", [])
        
        target_sheet = None
        for sheet in sheets:
            if sheet.get("title") == sheet_name:
                target_sheet = sheet
                break
        
        if not target_sheet:
            target_sheet = sheets[0]
        
        sheet_id = target_sheet.get("sheetId")
        
        values = [[result.get("status", ""), result.get("message", ""), result.get("duration_ms", 0)] for result in results]
        end_row = start_row + len(results) - 1
        range_str = f"{sheet_id}!I{start_row}:K{end_row}"
        
        # 使用正确的更新方法
        url = f"{FEISHU_BASE}/sheets/v2/spreadsheets/{spreadsheet_token}/values"
        payload = {
            "valueRange": {
                "range": range_str,
                "values": values
            }
        }
        
        response = requests.put(url, headers=self._headers(), params={"range": range_str}, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 0:
            raise RuntimeError(f"更新测试结果失败: {data}")

    def read_sheet_content(self, spreadsheet_token: str, sheet_id: str, start_cell: str = "A1", end_cell: str = None) -> List[List[str]]:
        """读取工作表内容"""
        if not end_cell:
            # 先获取元数据，知道表格大小
            metainfo = self.get_spreadsheet_metainfo(spreadsheet_token)
            sheets = metainfo.get("data", {}).get("sheets", [])
            target_sheet = None
            for sheet in sheets:
                if sheet.get("sheetId") == sheet_id:
                    target_sheet = sheet
                    break
            if target_sheet:
                row_count = target_sheet.get("row_count", 100)
                col_count = target_sheet.get("column_count", 20)
                end_col = self._col_to_letter(col_count)
                end_cell = f"{end_col}{row_count}"
        
        range_str = f"{sheet_id}!{start_cell}:{end_cell}"
        url = f"{FEISHU_BASE}/sheets/v2/spreadsheets/{spreadsheet_token}/values/{range_str}"
        
        response = requests.get(url, headers=self._headers(), timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") != 0:
            raise RuntimeError(f"读取表格内容失败: {data}")
        
        return data.get("data", {}).get("valueRange", {}).get("values", [])

    def _col_to_letter(self, col: int) -> str:
        """将列数字转换为字母（如 1->A, 27->AA）"""
        if col <= 0:
            return 'A'
        letter = ''
        temp_col = col
        while temp_col > 0:
            temp_col, remainder = divmod(temp_col - 1, 26)
            letter = chr(65 + remainder) + letter
        return letter