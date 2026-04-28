import json
import os
import sys
import asyncio
from typing import Any, List

from dotenv import load_dotenv
import requests

# 添加项目根目录到 Python 路径
current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(current_dir)

# 加载 .env 文件
load_dotenv()

from schema import FeatureItem
from extractors.feature_extractor import FeatureExtractor

AI_API_KEY = os.getenv("AI_API_KEY") 
AI_MODEL = os.getenv("AI_MODEL", "qwen-plus") 
DASHSCOPE_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"  

if not AI_API_KEY:
    raise RuntimeError("请在环境变量中配置 AI_API_KEY")


def call_ai(messages: List[dict[str, str]], temperature: float = 0.2, max_tokens: int = 5000) -> str:
    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json",
    }
    # 构建适合阿里云 DashScope 的请求格式
    payload = {
        "model": AI_MODEL,
        "input": {
            "messages": messages
        },
        "parameters": {
            "temperature": temperature,
            "max_tokens": max_tokens,
            "result_format": "message"
        }
    }
    try:
        response = requests.post(DASHSCOPE_URL, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data["output"]["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"API 调用错误: {e}")
        print(f"响应内容: {response.text if 'response' in locals() else '无响应'}")
        print(f"请求体: {payload}")
        raise


def parse_json_text(text: str) -> Any:
    # 清理文本开头和结尾的空白
    text = text.strip()
    
    # 优先查找并提取被 ```json ... ``` 或 ``` ... ``` 包裹的代码块
    import re
    code_block_pattern = r'```(?:json)?\n([\s\S]*?)```'
    matches = re.findall(code_block_pattern, text)
    if matches:
        for match in matches:
            code_content = match.strip()
            if code_content:
                text = code_content
                break
    
    # 尝试直接解析整个文本
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 寻找 JSON 边界：第一个 [ 或 { 作为起始点
        start_bracket = text.find("[")
        start_brace = text.find("{")
        
        # 选择最早出现的起始符
        start = -1
        is_array = False
        if start_bracket != -1 and (start_brace == -1 or start_bracket < start_brace):
            start = start_bracket
            is_array = True
        elif start_brace != -1:
            start = start_brace
        
        if start != -1:
            # 找到匹配的结束符
            if is_array:
                end = text.rfind("]")
            else:
                end = text.rfind("}")
            
            if end != -1 and end > start:
                candidate = text[start : end + 1]
                
                # 清理和修复候选 JSON
                # 移除注释
                candidate = re.sub(r'//.*', '', candidate)
                candidate = re.sub(r'#.*', '', candidate)
                candidate = re.sub(r'/*[\s\S]*?*/', '', candidate)
                
                # 将 Python 格式的 None、True、False 替换为 JSON 格式
                candidate = re.sub(r'\bNone\b', 'null', candidate)
                candidate = re.sub(r'\bTrue\b', 'true', candidate)
                candidate = re.sub(r'\bFalse\b', 'false', candidate)
                
                # 修复对象或数组末尾多余的逗号
                candidate = re.sub(r'\s*,\s*}', '}', candidate)
                candidate = re.sub(r'\s*,\s*\]', ']', candidate)
                
                # 确保完整性：检查是否以 [ 或 { 开头，并以 ] 或 } 结尾
                candidate = candidate.strip()
                if (candidate.startswith('[') and candidate.endswith(']')) or (candidate.startswith('{') and candidate.endswith('}')):
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        # 尝试处理中文标点和特殊字符
                        candidate = candidate.replace('‘', '"').replace('’', '"')
                        candidate = candidate.replace('"', '"').replace('"', '"')
                        candidate = candidate.replace('，', ',').replace('。', '.')
                        
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError as e:
                            print(f"JSON 解析失败: {e}")
                            print(f"原始文本: {text[:500]}...")
                            print(f"提取的候选: {candidate[:500]}...")
                            return []
                else:
                    print(f"JSON 内容不完整，缺少起始或结束符: {candidate[:500]}...")
                    return []
            else:
                print(f"未找到有效的 JSON 结束符")
                return []
        else:
            print(f"未找到有效的 JSON 起始符: {text[:500]}...")
            return []
    # 如果所有尝试都失败，返回空列表
    return []


def extract_features(urls: List[str]) -> List[FeatureItem]:
    prompt = f"""
你是一个专业的网站功能分析专家。请对以下 URL 进行深度遍历分析，并以纯 JSON 数组格式输出结果。

## URL 列表
{json.dumps(urls, ensure_ascii=False, indent=2)}

## 分析要求

### 1. 深度遍历顺序
- 先完整分析第一个 URL 的所有功能（从页面顶部到底部）
- 再分析第二个 URL，以此类推
- 不要交叉分析，保持模块独立

### 2. 细粒度提取（重要！）
必须提取页面上的**每一个可交互元素**，包括但不限于：
- **按钮**：登录按钮、注册按钮、搜索按钮、筛选按钮、加载更多按钮、应征按钮、购买按钮
- **输入框**：搜索输入框、用户名输入框、密码输入框、筛选条件输入框
- **链接**：导航菜单链接、分页链接、详情链接、标签链接
- **列表项**：企划列表项、橱窗列表项、作品列表项、活动列表项
- **筛选器**：下拉筛选、价格区间筛选、分类筛选、排序筛选
- **表单**：发布企划表单、注册表单、联系表单
- **弹窗/模态框**：详情弹窗、确认弹窗、登录弹窗
- **分页组件**：上一页、下一页、页码跳转
- **图标功能**：收藏、点赞、分享、举报

### 3. 四级层级结构
每个功能点必须归属到四级层级中：

| 层级 | 含义 | 示例 |
|------|------|------|
| 一级功能 | 网站主要模块 | 企划管理、橱窗管理、作品管理 |
| 二级功能 | 模块下的子模块 | 企划浏览、企划筛选、企划详情 |
| 三级功能 | 具体功能点 | 企划列表、价格筛选、应征操作 |
| 四级功能 | 最细粒度操作 | 点击应征按钮、输入价格最小值 |

### 4. 功能描述格式
必须具体描述用户操作和系统响应，格式：`用户[操作][目标元素]，系统[响应行为]`

**正确示例**：
- "用户点击「登录」按钮，系统弹出登录表单"
- "用户在搜索框输入关键词，系统实时展示匹配结果"
- "用户点击企划列表中的「应征」按钮，系统弹出确认弹窗"
- "用户选择价格区间「1k-3k」，系统筛选并刷新列表"

**错误示例**（太笼统）：
- "用户可以进行搜索" ❌
- "支持企划管理" ❌

### 5. 输出格式（纯 JSON 数组）
每个功能点必须包含以下字段：
- module：模块名（用于分类）
- function_name：功能名称
- level1：一级功能
- level2：二级功能
- level3：三级功能
- level4：四级功能
- description：功能描述
- importance：重要程度（高/中/低）

严格要求：只输出一个纯 JSON 数组，不要包含任何解释、Markdown 代码块标记或额外的文字。

返回格式示例：
[{"module":"首页门户","function_name":"Logo点击","level1":"首页门户","level2":"导航栏","level3":"","level4":"","description":"用户点击 Logo，系统返回首页","importance":"高"}]
"""
    messages = [
        {"role": "system", "content": "你是一个负责网站功能分析的助手。"},
        {"role": "user", "content": prompt},
    ]
    raw = call_ai(messages, temperature=0.2)
    print(f"AI 返回的原始内容: {raw[:500]}...")
    items = parse_json_text(raw)
    print(f"解析后的 items: {items}")
    features: List[FeatureItem] = []
    # 确保 items 是可迭代的
    if items is not None:
        for item in items:
            features.append(
                FeatureItem(
                    module=item.get("module", ""),
                    function_name=item.get("function_name", ""),
                    level1=item.get("level1", ""),
                    level2=item.get("level2", ""),
                    level3=item.get("level3", ""),
                    level4=item.get("level4", ""),
                    description=item.get("description", ""),
                    importance=item.get("importance", ""),
                    url=urls[0] if urls else "",
                )
            )
    print(f"提取的功能点数量: {len(features)}")
    return features


async def extract_features_from_url(url: str) -> List[FeatureItem]:
    print(f"  正在分析: {url}")
    
    extractor = FeatureExtractor(headless=True)
    page_data = await extractor.extract_full_page(url)
    
    return _ai_analyze_structured_data(url, page_data)


def _ai_analyze_structured_data(url: str, data: dict) -> List[FeatureItem]:
    """AI 分析结构化数据，生成功能点"""
    
    # 提取按钮信息
    buttons = data.get('buttons', [])
    visible_buttons = [b for b in buttons if b.get('visible', True)]
    
    prompt = f"""
**任务：基于页面上的按钮，生成功能点清单**

## 页面 URL
{url}

## 页面标题
{data.get('title', '')}

## 页面上的按钮（共 {len(visible_buttons)} 个）
{json.dumps(visible_buttons[:50], ensure_ascii=False, indent=2)}

**重要规则：**
1. 只根据上面列出的按钮生成功能点
2. 不要添加任何没有在按钮列表中出现的功能
3. 不要根据 URL 猜测功能
4. 每个按钮生成一个功能点

## 按钮到功能的映射规则
- 按钮文本包含"新增/添加" → 功能名称"新增数据"，描述"用户点击「按钮文本」按钮，系统弹出新增表单"
- 按钮文本包含"编辑/修改" → 功能名称"编辑数据"，描述"用户点击「按钮文本」按钮，系统弹出编辑表单"
- 按钮文本包含"删除" → 功能名称"删除数据"，描述"用户点击「按钮文本」按钮，系统弹出确认删除弹窗"
- 按钮文本包含"搜索/查询" → 功能名称"查询数据"，描述"用户点击「按钮文本」按钮，系统刷新列表"
- 按钮文本包含"刷新" → 功能名称"刷新页面"，描述"用户点击「按钮文本」按钮，系统重新加载数据"
- 其他按钮 → 使用按钮文本作为功能名称

## 输出格式
[{{
  "module": "{data.get('title', '')}",
  "function_name": "功能名称",
  "level1": "",
  "level2": "",
  "level3": "",
  "level4": "",
  "description": "用户点击「按钮文本」，系统执行操作",
  "importance": "高/中/低",
  "url": "{url}"
}}]

只输出 JSON 数组，不要有任何其他文字。
"""
    
    messages = [
        {"role": "system", "content": "你是网站功能分析专家，只根据提供的按钮数据输出 JSON 数组。"},
        {"role": "user", "content": prompt}
    ]
    
    raw = call_ai(messages, temperature=0.2)
    print(f"AI 原始返回: {raw[:500]}")
    
    items = parse_json_text(raw)
    
    features = []
    for item in items:
        features.append(FeatureItem(
            module=item.get("module", data.get('title', '')),
            function_name=item.get("function_name", ""),
            level1=item.get("level1", ""),
            level2=item.get("level2", ""),
            level3=item.get("level3", ""),
            level4=item.get("level4", ""),
            description=item.get("description", ""),
            importance=item.get("importance", "中"),
            url=url,
        ))
    
    return features