import json
import os
import sys
import asyncio
from typing import List, Dict, Any

# 添加项目根目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, project_root)
print(f"Added project root to path: {project_root}")
print(f"Current Python path: {sys.path}")

from dotenv import load_dotenv
from ai_service import _ai_analyze_structured_data
from feishu_service import FeishuClient
from extractors.feature_extractor import FeatureExtractor
from schema import FeatureItem

# 加载 .env 文件
load_dotenv()

class FeatureExtractorSkill:
    def __init__(self, input_file: str):
        self.input_file = input_file
        self.feishu_client = FeishuClient(
            os.getenv("FEISHU_APP_ID"),
            os.getenv("FEISHU_APP_SECRET")
        )
        self.page_extractor = None
        self.root_name = "功能点"
        
    def parse_menu_tree(self) -> List[Dict[str, Any]]:
        """解析菜单树 JSON 文件"""
        with open(self.input_file, 'r', encoding='utf-8') as f:
            menu_data = json.load(f)
        
        nodes = []
        
        # 处理根节点
        for root_name, root_data in menu_data.items():
            self.root_name = root_name
            
            def traverse(name: str, data: Dict[str, Any], path: List[str], levels: Dict[str, str]):
                current_path = path + [name]
                current_levels = levels.copy()
                
                level = len(current_path) - 1
                if level == 0:
                    current_levels["level1"] = name
                elif level == 1:
                    current_levels["level2"] = name
                elif level == 2:
                    current_levels["level3"] = name
                elif level == 3:
                    current_levels["level4"] = name
                
                if "url" in data and data["url"]:
                    nodes.append({
                        "menu_path": " > ".join(current_path),
                        "url": data["url"],
                        **current_levels
                    })
                
                if "children" in data:
                    for child_name, child_data in data["children"].items():
                        traverse(child_name, child_data, current_path, current_levels)
            
            traverse(root_name, root_data, [], {"level1": "", "level2": "", "level3": "", "level4": ""})
        
        return nodes
    
    async def initialize_extractor(self):
        """初始化浏览器"""
        # 定义需要排除的选择器，包括菜单和导航栏
        exclude_selectors = [
            'header', 'nav', '.navbar', '.sidebar', '.menu',
            '.el-menu', '.el-tabs__header', '.vab-side-bar',
            '.fixed-header', '.right-panel', '.left-panel',
            '.vab-layout-header', '.vab-side-bar-container'
        ]
        self.page_extractor = FeatureExtractor(headless=True, reuse_browser=True, exclude_selectors=exclude_selectors)
    
    async def analyze_page(self, node: Dict[str, Any]) -> List[FeatureItem]:
        """分析单个页面"""
        try:
            print(f"正在分析页面: {node['menu_path']} - {node['url']}")
            
            # 直接访问 iframe 的真实 URL
            # 从 HTML 中，iframe 的 URL 格式是 /user/v1/#/user/userManage
            # 完整 URL 应该是 `http://10.28.149.50:9432/user/v1/#/user/userManage`
            iframe_url = node['url'].replace('/iam/v1/', '/user/v1/')
            print(f"  尝试直接访问 iframe URL: {iframe_url}")
            
            # 提取页面数据
            page_data = await self.page_extractor.extract_full_page(iframe_url)
            
            # 检查是否有实际数据
            total_elements = (len(page_data.get('buttons', [])) + 
                             len(page_data.get('links', [])) + 
                             len(page_data.get('forms', [])))
            
            if total_elements == 0:
                print(f"页面 {iframe_url} 没有提取到任何可交互元素，跳过 AI 分析")
                return []
            
            # 调用 AI 分析
            ai_features = _ai_analyze_structured_data(iframe_url, page_data)
            
            # 关联菜单层级
            for feature in ai_features:
                if not feature.level1:
                    feature.level1 = node.get("level1", "")
                if not feature.level2:
                    feature.level2 = node.get("level2", "")
                if not feature.level3:
                    feature.level3 = node.get("level3", "")
                if not feature.level4:
                    feature.level4 = node.get("level4", "")
                # 用 menu_path 覆盖 module
                feature.module = node['menu_path']
            
            return ai_features
        except Exception as e:
            print(f"分析页面失败: {node['url']} - {e}")
            return []
    
    def create_feishu_sheet(self, features: List[FeatureItem]) -> str:
        """创建飞书表格"""
        headers = ["模块", "功能名称", "一级功能", "二级功能", "三级功能", "四级功能", "功能描述", "重要程度", "URL"]
        
        rows = []
        for feature in features:
            row = [
                feature.module,
                feature.function_name,
                feature.level1,
                feature.level2 or "",
                feature.level3 or "",
                feature.level4 or "",
                feature.description,
                feature.importance,
                feature.url
            ]
            rows.append(row)
        
        spreadsheet_token = self.feishu_client.create_sheet_with_rows(
            f"{self.root_name}功能点清单",
            headers,
            rows
        )
        
        return self.feishu_client.sheet_url(spreadsheet_token)
    
    def save_features_json(self, features: List[FeatureItem]):
        """保存功能点到 JSON 文件"""
        features_data = []
        for feature in features:
            features_data.append({
                "module": feature.module,
                "function_name": feature.function_name,
                "level1": feature.level1,
                "level2": feature.level2,
                "level3": feature.level3,
                "level4": feature.level4,
                "description": feature.description,
                "importance": feature.importance,
                "url": feature.url
            })
        
        os.makedirs("data", exist_ok=True)
        with open("data/features.json", 'w', encoding='utf-8') as f:
            json.dump(features_data, f, ensure_ascii=False, indent=2)
    
    def generate_statistics(self, features: List[FeatureItem]) -> Dict[str, int]:
        """生成统计信息"""
        stats = {
            "新增数据": 0,
            "编辑数据": 0,
            "删除数据": 0,
            "查询数据": 0
        }
        
        for feature in features:
            desc = feature.description.lower()
            if "新增" in desc or "添加" in desc or "创建" in desc:
                stats["新增数据"] += 1
            elif "编辑" in desc or "修改" in desc or "更新" in desc:
                stats["编辑数据"] += 1
            elif "删除" in desc or "移除" in desc:
                stats["删除数据"] += 1
            elif "查询" in desc or "搜索" in desc or "查看" in desc:
                stats["查询数据"] += 1
        
        return stats
    
    async def run(self):
        """运行整个流程"""
        try:
            # 步骤 1: 解析 JSON
            print(f"正在解析菜单树文件: {self.input_file}")
            nodes = self.parse_menu_tree()
            print(f"提取到 {len(nodes)} 个页面节点")
            
            if not nodes:
                print("未找到包含 URL 的节点")
                return
            
            # 步骤 2: 初始化浏览器
            print("正在初始化浏览器...")
            await self.initialize_extractor()
            
            # 步骤 3: 分析每个页面
            all_features = []
            for node in nodes:
                features = await self.analyze_page(node)
                all_features.extend(features)
            
            if not all_features:
                print("未提取到任何功能点")
                return
            
            # 步骤 4: 输出到飞书表格
            print("正在创建飞书表格...")
            sheet_url = self.create_feishu_sheet(all_features)
            
            # 步骤 5: 保存 JSON 文件
            self.save_features_json(all_features)
            
            # 生成统计信息
            stats = self.generate_statistics(all_features)
            
            # 输出结果
            print("\n✅ 功能点提取完成")
            print(f"📁 输入文件: {self.input_file}")
            print(f"🔗 分析页面: {len(nodes)} 个")
            print("📊 功能点统计:")
            for key, value in stats.items():
                print(f"   - {key}: {value} 个")
            print(f"📄 输出文件: data/features.json")
            print(f"📊 飞书表格: `{sheet_url}`")
            
        finally:
            # 关闭浏览器
            if self.page_extractor:
                await self.page_extractor.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="功能点提取器")
    parser.add_argument("--input", required=True, help="菜单树 JSON 文件路径")
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"错误: 文件不存在 - {args.input}")
        sys.exit(1)
    
    skill = FeatureExtractorSkill(args.input)
    asyncio.run(skill.run())


if __name__ == "__main__":
    main()