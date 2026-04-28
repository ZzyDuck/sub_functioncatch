# 功能点提取器 Skill

## 基本信息

- **Skill 名称**: extract-features
- **触发命令**: /extract-features
- **参数**: 
  - `--input` (必填): 菜单树 JSON 文件路径，如 data/menu_tree.json

## 功能描述

读取菜单树 JSON 文件，分析每个页面的功能点，输出到飞书表格。

**核心原则**：只分析页面的主内容区域（菜单栏/导航栏之外的区域），因为这些已经在菜单树中覆盖了。

## 可复用的现有模块

| 文件 | 用途 |
|------|------|
| .env | 存储飞书配置、大模型配置、网站账号密码 |
| ai_service.py | 提供 `_ai_analyze_structured_data(url, page_data)` 函数，用于 AI 分析 |
| feishu_service.py | 提供 `FeishuClient` 类，用于创建飞书表格 |
| extractors/feature_extractor.py | 提供 `FeatureExtractor` 类，用于提取页面数据 |

## 执行步骤

### 第1步：解析 JSON

递归遍历 menu_tree.json，提取所有包含 url 的节点，记录：

| 字段 | 说明 |
|------|------|
| menu_path | 完整路径，用 > 连接（如 "首页 > 用户中心 > 用户管理"） |
| url | 页面地址 |
| level1 | 一级菜单名称 |
| level2 | 二级菜单名称 |
| level3 | 三级菜单名称 |
| level4 | 四级菜单名称 |

### 第2步：初始化浏览器（只执行一次）

创建 `FeatureExtractor` 实例，设置 `reuse_browser=True`

- 实例内部会自动登录（从 .env 读取 USERNAME 和 PASSWORD）
- 复用同一个浏览器实例，避免每个页面都重新登录

### 第3步：分析每个页面

对每个 URL：

#### 3.1 提取页面数据

```python
page_data = await page_extractor.extract_full_page(url)
```

该方法返回的 page_data 包含：
- title：页面标题
- buttons：按钮列表（含 text、visible）
- links：链接列表
- forms：表单列表
- headings：标题层级
- tabs：Tab 切换
- popups：弹窗信息

#### 3.2 调用 AI 分析

```python
from ai_service import _ai_analyze_structured_data
ai_features = _ai_analyze_structured_data(url, page_data)
```

返回 `List[FeatureItem]`，每个 `FeatureItem` 包含：
- module：模块名
- function_name：功能名称
- level1、level2、level3、level4：层级
- description：功能描述
- importance：重要程度
- url：页面 URL

#### 3.3 关联菜单层级

由于 `_ai_analyze_structured_data` 返回的 level1-level4 可能为空，需要用菜单树中的层级信息填充：

```python
if not ai_feature.level1:
    ai_feature.level1 = node["level1"]
if not ai_feature.level2:
    ai_feature.level2 = node["level2"]
if not ai_feature.level3:
    ai_feature.level3 = node["level3"]
if not ai_feature.level4:
    ai_feature.level4 = node["level4"]
```

同时，module 字段用 menu_path 覆盖。

#### 3.4 转换为飞书表格行格式

```python
row = [
    node["menu_path"],           # 模块
    ai_feature.function_name,    # 功能名称
    ai_feature.level1,           # 一级功能
    ai_feature.level2,           # 二级功能
    ai_feature.level3,           # 三级功能
    ai_feature.level4,           # 四级功能
    ai_feature.description,      # 功能描述
    ai_feature.importance,       # 重要程度
    ai_feature.url               # URL
]
```

### 第4步：输出到飞书表格

- 复用已有的 `FeishuClient`（从 .env 读取 FEISHU_APP_ID 和 FEISHU_APP_SECRET）
- 表格标题：{根节点名称}功能点清单
- 调用 `create_sheet_with_rows(headers, rows)` 创建表格
- 输出表格链接

### 第5步：保存 JSON 文件

- 将所有功能点保存到 data/features.json
- 输出统计信息（分析页面数、功能点数量、分类统计）

## 输出示例

```
✅ 功能点提取完成
📁 输入文件: data/menu_tree.json
🔗 分析页面: 23 个
📊 功能点统计:
   - 新增数据: 8 个
   - 编辑数据: 6 个
   - 删除数据: 8 个
   - 查询数据: 5 个
📄 输出文件: data/features.json
📊 飞书表格: `https://sheet.feishu.cn/sheet/xxx` 
```

## 注意事项

- **浏览器复用**：`FeatureExtractor` 需要设置 `reuse_browser=True`，避免每个页面都重新启动浏览器和重复登录
- **主内容区域**：`FeatureExtractor` 默认会提取整个页面，但它的 `extract_full_page` 方法已经使用了 `exclude_selectors` 参数来排除菜单和导航区域
- **错误处理**：单个页面分析失败不应中断整个流程，记录错误后继续下一个

## 使用示例

```bash
/extract-features --input data/menu_tree.json
```