import json
import os

def is_high_priority(feature_name, feature_desc):
    high_keywords = ['新增', '授权', '删除', '登录', '密码', '审批', '策略', '安全', '金库', '认证', '权限', '绑定']
    return any(k in feature_name or k in feature_desc for k in high_keywords)

def is_medium_priority(feature_name, feature_desc):
    medium_keywords = ['搜索', '查询', '导出', '导入', '查看', '统计', '切换', '筛选', '排序']
    return any(k in feature_name or k in feature_desc for k in medium_keywords)

def generate_test_cases(function_points):
    test_cases = []
    case_id = 1
    
    for fp in function_points:
        level1 = fp.get("level1", "")
        level2 = fp.get("level2", "")
        level3 = fp.get("level3", "")
        feature_name = fp.get("功能点", "")
        feature_desc = fp.get("功能点描述", "")
        url = fp.get("url", "")
        
        if not feature_name or not feature_desc:
            continue
        
        module_name = f"{level1}-{level2}"
        if level3:
            module_name += f"-{level3}"
        
        if is_high_priority(feature_name, feature_desc):
            priority = "high"
            test_cases.extend(generate_high_priority_cases(case_id, module_name, feature_name, feature_desc, url))
            case_id += 2
        elif is_medium_priority(feature_name, feature_desc):
            priority = "medium"
            test_cases.append(generate_medium_priority_case(case_id, module_name, feature_name, feature_desc, url))
            case_id += 1
        else:
            priority = "low"
            test_cases.append(generate_low_priority_case(case_id, module_name, feature_name, feature_desc, url))
            case_id += 1
    
    return test_cases

def generate_high_priority_cases(case_id, module_name, feature_name, feature_desc, url):
    cases = []
    
    cases.append({
        "case_id": f"TC-{str(case_id).zfill(4)}",
        "title": f"{feature_name}_正向",
        "module_name": module_name,
        "priority": "high",
        "test_type": "功能测试",
        "design_technique": "等价类划分",
        "preconditions": "已登录系统，具有相应操作权限",
        "steps": [
            f"1. 登录系统，进入{module_name.split('-')[1]}页面",
            f"2. 执行{feature_name}操作",
            f"3. 验证操作结果"
        ],
        "expected_results": [
            f"{feature_name}操作成功",
            "系统提示操作成功",
            "相关数据正确更新"
        ],
        "test_data": {},
        "remarks": f"URL: {url}"
    })
    
    cases.append({
        "case_id": f"TC-{str(case_id+1).zfill(4)}",
        "title": f"{feature_name}_异常",
        "module_name": module_name,
        "priority": "high",
        "test_type": "功能测试",
        "design_technique": "错误猜测法",
        "preconditions": "已登录系统，具有相应操作权限",
        "steps": [
            f"1. 登录系统，进入{module_name.split('-')[1]}页面",
            f"2. 执行{feature_name}操作（输入无效参数/无权限/重复操作）",
            f"3. 验证系统响应"
        ],
        "expected_results": [
            "系统拒绝执行操作",
            "显示明确的错误提示信息",
            "数据未被修改"
        ],
        "test_data": {},
        "remarks": f"URL: {url}"
    })
    
    return cases

def generate_medium_priority_case(case_id, module_name, feature_name, feature_desc, url):
    return {
        "case_id": f"TC-{str(case_id).zfill(4)}",
        "title": feature_name,
        "module_name": module_name,
        "priority": "medium",
        "test_type": "功能测试",
        "design_technique": "等价类划分",
        "preconditions": "已登录系统，具有相应操作权限",
        "steps": [
            f"1. 登录系统，进入{module_name.split('-')[1]}页面",
            f"2. 执行{feature_name}操作",
            f"3. 验证显示结果"
        ],
        "expected_results": [
            f"{feature_name}功能正常执行",
            "结果正确展示"
        ],
        "test_data": {},
        "remarks": f"URL: {url}"
    }

def generate_low_priority_case(case_id, module_name, feature_name, feature_desc, url):
    return {
        "case_id": f"TC-{str(case_id).zfill(4)}",
        "title": feature_name,
        "module_name": module_name,
        "priority": "low",
        "test_type": "功能测试",
        "design_technique": "等价类划分",
        "preconditions": "已登录系统，具有相应操作权限",
        "steps": [
            f"1. 登录系统，进入{module_name.split('-')[1]}页面",
            f"2. 执行{feature_name}操作",
            f"3. 验证功能效果"
        ],
        "expected_results": [
            f"{feature_name}功能正常执行"
        ],
        "test_data": {},
        "remarks": f"URL: {url}"
    }

if __name__ == "__main__":
    json_path = r'd:\my_file\工作\AsiaInfo\aitrae\SDD3\FunctionCatch\data\function_analysis353.json'
    
    with open(json_path, 'r', encoding='utf-8') as f:
        function_points = json.load(f)
    
    print(f"读取到 {len(function_points)} 个功能点")
    
    high_count = sum(1 for fp in function_points if is_high_priority(fp.get('功能点',''), fp.get('功能点描述','')))
    medium_count = sum(1 for fp in function_points if is_medium_priority(fp.get('功能点',''), fp.get('功能点描述','')))
    print(f"高优先级: {high_count}, 中优先级: {medium_count}, 低优先级: {len(function_points)-high_count-medium_count}")
    
    test_cases = generate_test_cases(function_points)
    
    output_path = r'd:\my_file\工作\AsiaInfo\aitrae\SDD3\FunctionCatch\data\test_cases_v2.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(test_cases, f, ensure_ascii=False, indent=2)
    
    print(f"已生成 {len(test_cases)} 条测试用例，保存至 {output_path}")
