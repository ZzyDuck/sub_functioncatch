---
name: "extract-features"
description: "Extracts features from web pages based on menu tree JSON and outputs to Feishu spreadsheet. Invoke when user needs to analyze page features and export them to Feishu."
---

# 功能点提取器 Skill

## 基本信息

- **Skill 名称**: extract-features
- **触发命令**: /extract-features
- **参数**: 
  - `--input` (必填): 菜单树 JSON 文件路径，如 data/menu_tree.json

## 功能描述

读取菜单树 JSON 文件，分析每个页面的功能点，输出到飞书表格。

**核心原则**：只分析页面的主内容区域（菜单栏/导航栏之外的区域），因为这些已经在菜单树中覆盖了。

## 执行步骤

1. 解析 JSON 文件，提取所有包含 URL 的节点
2. 初始化浏览器（只执行一次，复用浏览器实例）
3. 分析每个页面，提取功能点
4. 输出到飞书表格
5. 保存 JSON 文件并输出统计信息

## 使用示例

```bash
/extract-features --input data/menu_tree.json
```