# Bug Report - Playwright Test Failures

Generated: 2026-04-30T17:05:00.000Z
Attempts: 1

## Summary

| Metric        | Count |
| ------------- | ----- |
| Total Tests   | 2     |
| Passed        | 0     |
| Failed        | 2     |
| Fixes Applied | 0     |

## Remaining Failures

### Failure 1: TC-ERR-004 - 超长时间搜索关键词

- **Location:** module-homepage.spec.ts:45
- **Error:** 搜索框未限制输入长度，可能导致性能问题
- **Severity:** medium
- **Root Cause:** validation
- **Suggested Fix:** 在搜索框添加maxlength属性或前端验证，限制输入长度为100字符

### Failure 2: TC-ERR-009 - 页面刷新后状态保持

- **Location:** module-homepage.spec.ts:78
- **Error:** 页面刷新后回到默认的应用资源登录Tab，状态未保持
- **Severity:** medium
- **Root Cause:** navigation
- **Suggested Fix:** 使用URL参数或localStorage保存Tab状态，页面加载时恢复状态

## Fixes Applied

| Test        | Fix           | Attempt | Root Cause |
| ----------- | ------------- | ------- | ---------- |