import json
import os
import re

HIGH_PRIORITY_KEYWORDS = ["新增", "删除", "授权", "加锁", "解锁", "创建", "导入", "启用", "停用", "修改", "编辑", "绑定", "审批", "应急", "切换"]
MEDIUM_PRIORITY_KEYWORDS = ["搜索", "查询", "筛选", "导出", "列表", "查看", "统计", "排序", "浏览"]
LOW_PRIORITY_KEYWORDS = ["刷新", "取消", "重置", "更多", "切换至", "收缩", "展开"]

def classify_priority(func_name):
    for kw in HIGH_PRIORITY_KEYWORDS:
        if kw in func_name:
            return "高"
    for kw in MEDIUM_PRIORITY_KEYWORDS:
        if kw in func_name:
            return "中"
    for kw in LOW_PRIORITY_KEYWORDS:
        if kw in func_name:
            return "低"
    return "中"

def get_design_technique(func_name, priority):
    if priority == "高":
        return "场景法+错误猜测"
    elif "搜索" in func_name or "查询" in func_name or "筛选" in func_name:
        return "等价类划分"
    elif "排序" in func_name:
        return "边界值分析"
    elif "统计" in func_name:
        return "等价类划分"
    else:
        return "场景法"

def generate_positive_case(fp, case_id, priority):
    func_name = fp["功能点"]
    func_desc = fp["功能点描述"]
    level1 = fp.get("level1", "") or ""
    level2 = fp.get("level2", "") or ""
    level3 = fp.get("level3", "") or ""
    level4 = fp.get("level4", "") or ""
    url = fp.get("url", "") or ""

    module = f"{level1}/{level2}"
    if level3:
        module += f"/{level3}"
    if level4:
        module += f"/{level4}"

    title = f"验证{func_name}功能正常可用"

    steps = []
    expected = []

    if "新增" in func_name or "创建" in func_name:
        entity = func_name.replace("新增", "").replace("创建", "")
        steps = [
            f"登录系统，进入{module}页面",
            f"点击「{func_name}」按钮",
            f"在弹窗中填写{entity}的必填信息",
            "点击确定/保存按钮"
        ]
        expected = [
            f"成功创建{entity}，列表中显示新增记录",
            "页面提示操作成功"
        ]
    elif "删除" in func_name:
        entity = func_name.replace("删除", "")
        steps = [
            f"登录系统，进入{module}页面",
            f"选择一条或多条{entity}记录",
            f"点击「{func_name}」按钮",
            "在确认弹窗中点击确定"
        ]
        expected = [
            f"选中的{entity}记录被成功删除",
            "列表中不再显示已删除记录"
        ]
    elif "搜索" in func_name or "查询" in func_name:
        entity = func_name.replace("搜索", "").replace("查询", "")
        steps = [
            f"登录系统，进入{module}页面",
            f"在搜索框中输入有效的{entity}关键字",
            "点击搜索/查询按钮"
        ]
        expected = [
            f"列表显示匹配{entity}关键字的记录",
            "搜索结果与输入条件一致"
        ]
    elif "筛选" in func_name:
        steps = [
            f"登录系统，进入{module}页面",
            "点击筛选按钮",
            "设置筛选条件",
            "点击确认筛选"
        ]
        expected = [
            "列表按筛选条件过滤显示",
            "结果符合筛选条件"
        ]
    elif "导出" in func_name:
        entity = func_name.replace("导出", "")
        steps = [
            f"登录系统，进入{module}页面",
            f"点击「{func_name}」按钮",
            "选择导出范围和格式"
        ]
        expected = [
            f"成功下载{entity}Excel文件",
            "文件内容与列表数据一致"
        ]
    elif "导入" in func_name:
        entity = func_name.replace("导入", "")
        steps = [
            f"登录系统，进入{module}页面",
            f"点击「{func_name}」按钮",
            "选择符合模板格式的Excel文件上传",
            "点击确认导入"
        ]
        expected = [
            f"成功导入{entity}数据",
            "列表中显示导入的记录"
        ]
    elif "授权" in func_name:
        steps = [
            f"登录系统，进入{module}页面",
            "选择目标用户/资源",
            f"点击「{func_name}」按钮",
            "配置权限并确认"
        ]
        expected = [
            "权限分配成功",
            "目标用户/资源拥有对应权限"
        ]
    elif "修改" in func_name or "编辑" in func_name:
        entity = func_name.replace("修改", "").replace("编辑", "")
        steps = [
            f"登录系统，进入{module}页面",
            f"选择一条{entity}记录，点击编辑按钮",
            "修改需要更新的字段",
            "点击保存按钮"
        ]
        expected = [
            f"{entity}信息更新成功",
            "列表中显示更新后的数据"
        ]
    elif "启用" in func_name or "停用" in func_name:
        action = "启用" if "启用" in func_name else "停用"
        entity = func_name.replace("启用", "").replace("停用", "")
        steps = [
            f"登录系统，进入{module}页面",
            f"选择需要{action}的{entity}记录",
            f"点击「{func_name}」按钮",
            "在确认弹窗中点击确定"
        ]
        expected = [
            f"{entity}{action}成功",
            f"列表中{entity}状态变更为已{action}"
        ]
    elif "加锁" in func_name or "解锁" in func_name:
        action = "锁定" if "加锁" in func_name else "解锁"
        entity = func_name.replace("加锁", "").replace("解锁", "")
        steps = [
            f"登录系统，进入{module}页面",
            f"选择需要{action}的{entity}记录",
            f"点击「{func_name}」按钮",
            "在确认弹窗中点击确定"
        ]
        expected = [
            f"{entity}{action}成功",
            f"列表中{entity}状态变更为已{action}"
        ]
    elif "绑定" in func_name:
        entity = func_name.replace("绑定", "")
        steps = [
            f"登录系统，进入{module}页面",
            f"选择目标{entity}，点击「{func_name}」按钮",
            "选择绑定对象并确认"
        ]
        expected = [
            f"{entity}绑定成功",
            "绑定关系在列表中正确显示"
        ]
    elif "审批" in func_name:
        steps = [
            f"登录系统，进入{module}页面",
            "查看待审批申请列表",
            "选择一条申请，点击审批按钮",
            "填写审批意见并提交"
        ]
        expected = [
            "审批操作成功",
            "申请状态更新为已审批"
        ]
    elif "统计" in func_name:
        steps = [
            f"登录系统，进入{module}页面",
            "查看统计区域数据"
        ]
        expected = [
            "统计数据正确显示",
            "数据与实际记录数一致"
        ]
    elif "列表" in func_name:
        steps = [
            f"登录系统，进入{module}页面",
            "查看列表数据展示"
        ]
        expected = [
            "列表正确展示各列数据",
            "分页功能正常"
        ]
    elif "排序" in func_name:
        steps = [
            f"登录系统，进入{module}页面",
            f"点击「{func_name}」按钮"
        ]
        expected = [
            "列表按指定规则排序",
            "排序结果正确"
        ]
    elif "查看" in func_name:
        steps = [
            f"登录系统，进入{module}页面",
            f"查看{func_name.replace('查看', '')}信息"
        ]
        expected = [
            "信息正确显示",
            "数据内容完整"
        ]
    elif "切换" in func_name:
        steps = [
            f"登录系统，进入{module}页面",
            f"点击「{func_name}」"
        ]
        expected = [
            "成功切换到目标视图/标签页",
            "目标内容正确显示"
        ]
    elif "应急" in func_name:
        steps = [
            f"登录系统，进入{module}页面",
            f"操作「{func_name}」开关或按钮",
            "确认操作"
        ]
        expected = [
            "应急模式状态切换成功",
            "页面状态显示正确"
        ]
    else:
        steps = [
            f"登录系统，进入{module}页面",
            f"执行「{func_name}」操作"
        ]
        expected = [
            f"{func_name}功能正常执行",
            "操作结果符合预期"
        ]

    return {
        "case_id": case_id,
        "title": title,
        "module_name": module,
        "priority": priority,
        "test_type": "功能测试",
        "design_technique": get_design_technique(func_name, priority),
        "preconditions": f"已登录系统，具有{module}相关操作权限",
        "steps": steps,
        "expected_results": expected
    }

def generate_negative_case(fp, case_id, priority):
    func_name = fp["功能点"]
    func_desc = fp["功能点描述"]
    level1 = fp.get("level1", "") or ""
    level2 = fp.get("level2", "") or ""
    level3 = fp.get("level3", "") or ""
    level4 = fp.get("level4", "") or ""

    module = f"{level1}/{level2}"
    if level3:
        module += f"/{level3}"
    if level4:
        module += f"/{level4}"

    title = f"验证{func_name}异常场景处理"

    steps = []
    expected = []

    if "新增" in func_name or "创建" in func_name:
        entity = func_name.replace("新增", "").replace("创建", "")
        steps = [
            f"登录系统，进入{module}页面",
            f"点击「{func_name}」按钮",
            "不填写必填字段，直接点击确定"
        ]
        expected = [
            "系统提示必填字段不能为空",
            f"不创建无效的{entity}记录"
        ]
    elif "删除" in func_name:
        entity = func_name.replace("删除", "")
        steps = [
            f"登录系统，进入{module}页面",
            f"点击「{func_name}」按钮",
            "在确认弹窗中点击取消"
        ]
        expected = [
            "取消删除操作",
            f"{entity}记录未被删除"
        ]
    elif "搜索" in func_name or "查询" in func_name:
        entity = func_name.replace("搜索", "").replace("查询", "")
        steps = [
            f"登录系统，进入{module}页面",
            f"在搜索框中输入不存在的{entity}关键字",
            "点击搜索/查询按钮"
        ]
        expected = [
            "列表显示空数据或提示无匹配结果",
            "页面不报错"
        ]
    elif "导入" in func_name:
        entity = func_name.replace("导入", "")
        steps = [
            f"登录系统，进入{module}页面",
            f"点击「{func_name}」按钮",
            "上传格式错误的文件"
        ]
        expected = [
            "系统提示文件格式不正确",
            "不执行导入操作"
        ]
    elif "导出" in func_name:
        steps = [
            f"登录系统，进入{module}页面",
            "在列表无数据时",
            f"点击「{func_name}」按钮"
        ]
        expected = [
            "系统提示无数据可导出或导出空文件",
            "页面不报错"
        ]
    elif "授权" in func_name:
        steps = [
            f"登录系统，进入{module}页面",
            "不选择任何用户/资源",
            f"点击「{func_name}」按钮"
        ]
        expected = [
            "系统提示请先选择操作对象",
            "不执行授权操作"
        ]
    elif "修改" in func_name or "编辑" in func_name:
        steps = [
            f"登录系统，进入{module}页面",
            "清空必填字段",
            "点击保存按钮"
        ]
        expected = [
            "系统提示必填字段不能为空",
            "不保存无效数据"
        ]
    elif "启用" in func_name or "停用" in func_name:
        steps = [
            f"登录系统，进入{module}页面",
            "不选择任何记录",
            f"点击「{func_name}」按钮"
        ]
        expected = [
            "系统提示请先选择记录",
            "不执行操作"
        ]
    elif "加锁" in func_name or "解锁" in func_name:
        steps = [
            f"登录系统，进入{module}页面",
            "不选择任何用户",
            f"点击「{func_name}」按钮"
        ]
        expected = [
            "系统提示请先选择用户",
            "不执行操作"
        ]
    elif "绑定" in func_name:
        steps = [
            f"登录系统，进入{module}页面",
            f"点击「{func_name}」但不选择绑定对象",
            "点击确定"
        ]
        expected = [
            "系统提示请选择绑定对象",
            "不执行绑定操作"
        ]
    elif "审批" in func_name:
        steps = [
            f"登录系统，进入{module}页面",
            "选择一条申请，点击审批按钮",
            "不填写审批意见直接提交"
        ]
        expected = [
            "系统提示审批意见不能为空",
            "不提交审批结果"
        ]
    elif "应急" in func_name:
        steps = [
            f"登录系统，进入{module}页面",
            f"操作「{func_name}」",
            "快速重复切换状态"
        ]
        expected = [
            "系统正确处理快速切换",
            "最终状态与最后一次操作一致"
        ]
    else:
        steps = [
            f"登录系统，进入{module}页面",
            f"在异常条件下执行「{func_name}」操作"
        ]
        expected = [
            "系统正确处理异常情况",
            "不产生数据错误"
        ]

    return {
        "case_id": case_id,
        "title": title,
        "module_name": module,
        "priority": priority,
        "test_type": "异常测试",
        "design_technique": "错误猜测",
        "preconditions": f"已登录系统，具有{module}相关操作权限",
        "steps": steps,
        "expected_results": expected
    }

def generate_test_cases(function_points):
    test_cases = []
    case_counter = 1

    for fp in function_points:
        func_name = fp["功能点"]
        priority = classify_priority(func_name)

        case_id = f"TC-{case_counter:04d}"
        positive_case = generate_positive_case(fp, case_id, priority)
        test_cases.append(positive_case)
        case_counter += 1

        if priority == "高":
            case_id = f"TC-{case_counter:04d}"
            negative_case = generate_negative_case(fp, case_id, priority)
            test_cases.append(negative_case)
            case_counter += 1

    return test_cases

if __name__ == "__main__":
    json_path = r"d:\projects\sub_functioncatch\data\function_analysis416.json"
    with open(json_path, 'r', encoding='utf-8') as f:
        function_points = json.load(f)

    print(f"共读取到 {len(function_points)} 个功能点")

    test_cases = generate_test_cases(function_points)

    high_count = sum(1 for tc in test_cases if tc["priority"] == "高")
    mid_count = sum(1 for tc in test_cases if tc["priority"] == "中")
    low_count = sum(1 for tc in test_cases if tc["priority"] == "低")

    print(f"共生成 {len(test_cases)} 条测试用例")
    print(f"  高优先级: {high_count} 条")
    print(f"  中优先级: {mid_count} 条")
    print(f"  低优先级: {low_count} 条")

   #  output_path = r"d:\projects\sub_functioncatch\data\test_cases_full.json" 第一版
    output_path = r"d:\projects\sub_functioncatch\data\test_cases_v2.json" # 第二版
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(test_cases, f, ensure_ascii=False, indent=2)

    print(f"测试用例已保存到: {output_path}")
