---
mode: agent
description: 扫描并更新所有 FairyGUI Package 的记忆文件，确保复用信息最新可用
tools:
  - codebase
  - readFile
  - listDir
  - memory
  - runCommands
---

# 刷新 FairyGUI Package 记忆

## 任务描述

扫描 `data/uiProject/assets/` 下所有 Package，为每个包生成/更新记忆文件，供后续设计稿转换时精确复用已有组件。

---

## 执行方式

### 快速批量（推荐）

运行分析脚本自动生成所有包的记忆：

```bash
python scripts/fairygui_package_analyzer.py \
  --assets data/uiProject/assets \
  --output memories/repo/fairygui-packages
```

### 手动单包

调用 **FairyGUI Package Reviewer** Agent：

```
review package ${input:packageName:请输入 Package 名称（如 Common、Hero、MainUI）}
```

### 全部重扫

```
review fairygui packages
```

---

## 关键包优先级

| 优先级 | Package | 说明 |
|-------|---------|------|
| 🔴 最高 | Common | 全局通用组件，所有转换都依赖此包 |
| 🟡 常用 | MainUI, Hero, Battle | 高频业务包 |
| 🟢 一般 | 其余业务包 | 按需更新 |

---

## 输出

更新以下记忆文件：
- `memories/repo/fairygui-packages/INDEX.md` — 包索引快速查询表
- `memories/repo/fairygui-packages/{PackageName}.md` — 每个包的详细组件清单
