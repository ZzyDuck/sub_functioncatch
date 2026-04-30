import json
import os
import sys
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
functioncatch_dir = parent_dir
env_path = os.path.join(functioncatch_dir, '.env')
load_dotenv(env_path)

sys.path.insert(0, functioncatch_dir)
from feishu_service import FeishuClient

def find_merge_ranges(rows, merge_columns):
    """找出需要合并的单元格范围（从第二行开始，跳过标题行）"""
    merges = []
    
    for col_idx in merge_columns:
        if col_idx >= len(rows[0]):
            continue
        
        start_row = 0
        while start_row < len(rows):
            current_value = rows[start_row][col_idx]
            
            if current_value == "":
                start_row += 1
                continue
            
            end_row = start_row
            while end_row + 1 < len(rows) and rows[end_row + 1][col_idx] == current_value:
                end_row += 1
            
            if end_row > start_row:
                merges.append({
                    "start_row": start_row + 1,
                    "end_row": end_row + 1,
                    "start_col": col_idx,
                    "end_col": col_idx
                })
            
            start_row = end_row + 1
    
    return merges

def convert_menu_tree_to_rows(data, level1="", level2="", level3="", level4=""):
    rows = []
    for key, value in data.items():
        url = value.get("url", "")
        if "children" in value:
            if level1 == "":
                rows.extend(convert_menu_tree_to_rows(value["children"], key, "", "", ""))
            elif level2 == "":
                rows.extend(convert_menu_tree_to_rows(value["children"], level1, key, "", ""))
            elif level3 == "":
                rows.extend(convert_menu_tree_to_rows(value["children"], level1, level2, key, ""))
            else:
                rows.extend(convert_menu_tree_to_rows(value["children"], level1, level2, level3, key))
        else:
            rows.append([level1, level2, level3, key, url, "", ""])
    return rows

def export_to_feishu(json_path, app_id, app_secret):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"共读取到数据: {len(data) if isinstance(data, list) else '树形结构'}")
    
    file_name = os.path.basename(json_path)
    
    merge_columns = []
    
    if file_name == "menu_tree.json":
        headers = ["一级菜单", "二级菜单", "三级菜单", "四级菜单", "URL", "功能点", "功能点描述"]
        rows = convert_menu_tree_to_rows(data)
        title = "菜单树结构"
        sheet_name = "菜单列表"
        merge_columns = [0, 1, 2, 3]
    
    elif file_name == "function_analysis353.json":
        headers = ["一级菜单", "二级菜单", "三级菜单", "四级菜单", "URL", "功能点", "功能点描述"]
        rows = []
        for fp in data:
            row = [
                fp.get("level1", "") or "",
                fp.get("level2", "") or "",
                fp.get("level3", "") or "",
                fp.get("level4", "") or "",
                fp.get("url", "") or "",
                fp.get("功能点", "") or "",
                fp.get("功能点描述", "") or ""
            ]
            rows.append(row)
        title = f"功能点分析结果_{len(rows)}条"
        sheet_name = "功能点列表"
        merge_columns = [0, 1, 2, 3]
    
    elif file_name == "home_test_results.json":
        headers = ["用例ID", "测试项", "模块", "状态", "消息", "URL", "执行时间", "实际结果"]
        rows = []
        for item in data:
            rows.append([
                item.get("id", ""),
                item.get("title", ""),
                item.get("module", ""),
                item.get("status", ""),
                item.get("message", ""),
                item.get("details", {}).get("url", ""),
                item.get("details", {}).get("executed_at", ""),
                item.get("details", {}).get("actual_result", "")
            ])
        title = "首页测试结果"
        sheet_name = "测试结果"
        merge_columns = []
    
    elif file_name == "test_cases_full.json" or file_name == "test_cases_v2.json":
        headers = ["用例ID", "测试项", "模块", "优先级", "测试类型", "前置条件", "步骤", "预期结果"]
        rows = []
        for item in data:
            steps = "\n".join(item.get("steps", []))
            expected = "\n".join(item.get("expected_results", []))
            rows.append([
                item.get("case_id", ""),
                item.get("title", ""),
                item.get("module_name", ""),
                item.get("priority", ""),
                item.get("test_type", ""),
                item.get("preconditions", ""),
                steps,
                expected
            ])
        title = "完整测试用例"
        sheet_name = "测试用例"
        merge_columns = []
    
    else:
        if isinstance(data, list) and len(data) > 0 and "level1" in data[0]:
            headers = ["一级菜单", "二级菜单", "三级菜单", "四级菜单", "URL", "功能点", "功能点描述"]
            rows = []
            for item in data:
                rows.append([
                    item.get("level1", ""),
                    item.get("level2", ""),
                    item.get("level3", ""),
                    item.get("level4", ""),
                    item.get("url", ""),
                    item.get("功能点", ""),
                    item.get("功能点描述", "")
                ])
            title = f"数据导出_{len(data)}条"
            sheet_name = "数据列表"
            merge_columns = [0, 1, 2, 3]
        else:
            headers = ["一级菜单", "二级菜单", "三级菜单", "四级菜单", "URL", "功能点", "功能点描述"]
            rows = []
            for item in data:
                rows.append([
                    item.get("level1", ""),
                    item.get("level2", ""),
                    item.get("level3", ""),
                    item.get("level4", ""),
                    item.get("url", ""),
                    item.get("功能点", ""),
                    item.get("功能点描述", "")
                ])
            title = f"数据导出_{len(data)}条"
            sheet_name = "数据列表"
            merge_columns = [0, 1, 2, 3]
    
    client = FeishuClient(app_id, app_secret)
    
    print(f"正在创建飞书表格: {title}")
    spreadsheet_token = client.create_sheet_with_rows(title, headers, rows, sheet_name)
    
    metainfo = client.get_spreadsheet_metainfo(spreadsheet_token)
    sheets = metainfo.get("data", {}).get("sheets", [])
    sheet_id = sheets[0].get("sheetId")
    
    if merge_columns:
        merges = find_merge_ranges(rows, merge_columns)
        if merges:
            print(f"正在合并 {len(merges)} 个单元格区域...")
            try:
                client.merge_cells(spreadsheet_token, sheet_id, merges)
                print("单元格合并完成")
            except Exception as e:
                print(f"警告: 合并单元格失败 - {e}")
    else:
        print("无需合并单元格")
    
    print("正在设置表格公开分享权限...")
    try:
        client.share_spreadsheet(spreadsheet_token, allow_edit=True)
        print("公开分享权限设置成功")
    except Exception as e:
        print(f"警告: 设置公开分享权限失败 - {e}")
    
    url = client.sheet_url(spreadsheet_token)
    print(f"\n飞书表格创建成功！")
    print(f"表格链接: {url}")
    print(f"表格Token: {spreadsheet_token}")
    
    return spreadsheet_token, url

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='将JSON数据导出到飞书表格')
    parser.add_argument('--json_path', type=str, required=True, help='JSON文件路径')
    parser.add_argument('--app_id', type=str, default=os.getenv('FEISHU_APP_ID'), help='飞书应用ID')
    parser.add_argument('--app_secret', type=str, default=os.getenv('FEISHU_APP_SECRET'), help='飞书应用密钥')
    
    args = parser.parse_args()
    
    if not args.app_id or not args.app_secret:
        print("错误: 飞书凭证未提供")
        sys.exit(1)
    
    export_to_feishu(args.json_path, args.app_id, args.app_secret)
