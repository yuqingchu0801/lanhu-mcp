---
mode: agent
description: 对蓝湖设计稿进行命名规范治理检查，生成修复建议报告
tools:
  - mcp_lanhu_lanhu_get_designs
  - mcp_lanhu_lanhu_get_pages
  - mcp_lanhu_lanhu_get_ai_analyze_design_result
  - mcp_lanhu_lanhu_get_ai_analyze_page_result
  - readFile
---

# 蓝湖设计命名规范治理检查

## 任务描述

对指定蓝湖设计稿的所有图层进行命名规范检查，识别 ERROR/WARN 问题并生成改名建议表。

**目标**：${input:designTarget:请输入蓝湖设计稿 URL 或设计名称}

---

## 规则来源

读取 `data/lanhu-rule/lanhu-Rule.md` 获取最新命名规范，**不使用缓存规则**。

---

## 检查项目

| 规则 | 说明 | 级别 |
|------|------|------|
| R-001 | 禁止中文命名 | ERROR |
| R-002 | 图层尺寸超 1024px → 强制 JPG | WARN |
| R-003 | 组名前缀不合规（Btn$/Com$/Bar$/ChkBtn$）| WARN/ERROR |
| R-004 | 后缀语义标记拼写错误（@icon/@title/@bar）| ERROR |
| R-005 | @9# 九宫格参数格式错误 | ERROR |
| R-006 | 复合后缀顺序错误（@9# 必须在前）| ERROR |
| R-007 | 隐藏节点枚举 | INFO |
| R-008 | 导出文件名重复 | ERROR |

---

## 输出格式

```
─────────────────────────────────────────
  蓝湖命名规范治理报告
─────────────────────────────────────────
  设计页面：{name}    图层总数：{n}
  ERROR {n} · WARN {n} · INFO {n}
  
  [ERROR 详情...]
  [WARN 详情...]
  
  结论：✅ 可进入转换 / ❌ 需先修复
─────────────────────────────────────────
```

若存在 ERROR，额外输出改名建议表：

| 当前名称 | 建议名称 | 规则 | 路径 |
|---------|---------|------|------|
