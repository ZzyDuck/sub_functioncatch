import json
import os
import sys
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
grandparent_dir = os.path.dirname(parent_dir)
root_dir = os.path.dirname(grandparent_dir)
env_path = os.path.join(root_dir, '.env')
load_dotenv(env_path)

sys.path.insert(0, root_dir)
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

def export_to_feishu(json_path, app_id, app_secret):
    with open(json_path, 'r', encoding='utf-8') as f:
        function_points = json.load(f)
    
    print(f"共读取到 {len(function_points)} 个功能点")
    
    headers = ["一级菜单", "二级菜单", "三级菜单", "四级菜单", "URL", "功能点", "功能点描述"]
    
    rows = []
    for fp in function_points:
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
    
    client = FeishuClient(app_id, app_secret)
    
    title = f"功能点分析结果_{len(function_points)}条"
    sheet_name = "功能点列表"
    
    print(f"正在创建飞书表格: {title}")
    spreadsheet_token = client.create_sheet_with_rows(title, headers, rows, sheet_name)
    
    metainfo = client.get_spreadsheet_metainfo(spreadsheet_token)
    sheets = metainfo.get("data", {}).get("sheets", [])
    sheet_id = sheets[0].get("sheetId")
    
    merge_columns = [0, 1, 2, 3]
    merges = find_merge_ranges(rows, merge_columns)
    
    if merges:
        print(f"正在合并 {len(merges)} 个单元格区域...")
        try:
            client.merge_cells(spreadsheet_token, sheet_id, merges)
            print("单元格合并完成")
        except Exception as e:
            print(f"警告: 合并单元格失败 - {e}")
    
    url = client.sheet_url(spreadsheet_token)
    print(f"\n飞书表格创建成功！")
    print(f"表格链接: {url}")
    print(f"表格Token: {spreadsheet_token}")
    
    return spreadsheet_token, url

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='将功能点分析结果导出到飞书表格')
    parser.add_argument('--json_path', type=str, 
                        default=r'd:\my_file\工作\AsiaInfo\aitrae\SDD3\functioncatch\.trae\skills\function-analyzer\data\function_analysis.json',
                        help='功能点分析JSON文件路径')
    parser.add_argument('--app_id', type=str, default=os.getenv('FEISHU_APP_ID'), help='飞书应用ID')
    parser.add_argument('--app_secret', type=str, default=os.getenv('FEISHU_APP_SECRET'), help='飞书应用密钥')
    
    args = parser.parse_args()
    
    if not args.app_id or not args.app_secret:
        print("错误: 飞书凭证未提供")
        sys.exit(1)
    
    export_to_feishu(args.json_path, args.app_id, args.app_secret)