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