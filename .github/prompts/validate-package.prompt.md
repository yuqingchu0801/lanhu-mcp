---
mode: agent
description: 对生成的 FairyGUI Package 资源进行完整质量校验，输出带优先级的修复报告
tools:
  - codebase
  - readFile
  - listDir
  - memory
---

# FairyGUI Package 资源校验

## 任务描述

对指定 Package（或全部 Package）进行完整性、一致性和引用正确性校验。

**目标 Package**：${input:packageName:请输入 Package 名称，留空表示校验全部}

---

## 校验维度

| 维度 | 说明 |
|------|------|
| 设计一致性 | 尺寸、颜色、文本、布局坐标偏差 ≤ 2px |
| 资源重复 | 跨包图片重复、公共组件重复实现 |
| 引用正确性 | src ID 有效、fileName 无远程 URL、跨包依赖已声明 |
| 导出规则 | View 组件必须 exported，内部组件不过度导出 |
| 命名规范 | 元素 name 无中文/空格，View/Btn/Item 后缀规则 |
| Common 复用 | 遮罩/红点/加载/按钮应使用 Common 引用 |

---

## 执行

```
validate fairygui package ${input:packageName}
```

若需自动修复可安全修复的问题：

```
fix fairygui issues ${input:packageName}
```

---

## 输出

```
========================================
FairyGUI Asset Validation Report
Package: {name}  Date: {date}
========================================
[ERROR/WARN/PASS 列表]

总计：{X} ERROR  {Y} WARN
========================================
```

> ⚠️ 约束：校验时只读 Common 包，不修改 Common 包任何内容。
