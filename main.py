import argparse
import json
import os
import asyncio
from typing import List

from dotenv import load_dotenv

# 先加载环境变量，再导入其他模块
load_dotenv(override=True)

from ai_service import extract_features, extract_features_from_url
from spa_crawler import SPACrawler
from schema import FeatureItem
from feishu_service import FeishuClient

def build_feature_rows(features: List[FeatureItem]) -> List[List[str]]:
    rows: List[List[str]] = []
    for item in features:
        rows.append(
            [
                item.module,
                item.function_name,
                item.level1,
                item.level2 or "",
                item.level3 or "",
                item.level4 or "",
                item.description,
                item.importance,
                item.url,
            ]
        )
    return rows

async def main() -> None:
    parser = argparse.ArgumentParser(description="网站功能点提取工具")
    parser.add_argument("--url", required=True, help="起始 URL")
    parser.add_argument("--output", default="features.json", help="功能点输出文件")
    args = parser.parse_args()

    start_url = args.url
    output_file = args.output

    print("开始分析网站功能点...\n")

    # 从环境变量获取登录凭证
    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")
    
    # 初始化爬虫
    crawler = SPACrawler(
        start_url=start_url,
        max_clicks=10,  # 保持与原来相同的最大页面数
        wait_time=2000,
        username=username,
        password=password
    )
    
    # 运行爬虫，直接获取功能点
    results = await crawler.run()
    visited_urls = results['urls']
    all_features = results.get('features', [])  # 直接获取已分析的功能点
    
    print(f"\n已爬取 URL 数量: {len(visited_urls)}")
    print(f"总计提取功能点: {len(all_features)}")

    features = all_features

    # 飞书集成
    feishu_app_id = os.getenv("FEISHU_APP_ID")
    feishu_app_secret = os.getenv("FEISHU_APP_SECRET")
    
    if feishu_app_id and feishu_app_secret:
        print("\n正在创建飞书表格...")
        try:
            feishu = FeishuClient(feishu_app_id, feishu_app_secret)
            feature_rows = build_feature_rows(features)
            
            sheet_token = feishu.create_sheet_with_rows(
                title="网站功能点清单",
                headers=[
                    "模块",
                    "功能名称",
                    "一级功能",
                    "二级功能",
                    "三级功能",
                    "四级功能",
                    "功能描述",
                    "重要程度",
                    "URL",
                ],
                rows=feature_rows,
            )
            print(f"✅ 飞书表格已创建: {feishu.sheet_url(sheet_token)}")
        except Exception as e:
            print(f"⚠️ 飞书表格创建失败: {e}")
    else:
        print("⚠️ 未配置飞书环境变量，跳过飞书表格创建")

    # 保存功能点到文件
    os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
    features_data = [f.__dict__ for f in features]
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(features_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 功能点已保存到 {output_file}")
    print("=" * 50)
    print("功能点提取完成！")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())