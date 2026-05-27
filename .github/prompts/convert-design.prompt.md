---
mode: agent
description: 将蓝湖设计稿完整转换为 FairyGUI Package —— 自动执行治理检查、包扫描、转换和校验全流程
tools:
  - mcp_lanhu_lanhu_get_designs
  - mcp_lanhu_lanhu_get_pages
  - mcp_lanhu_lanhu_get_ai_analyze_design_result
  - mcp_lanhu_lanhu_get_ai_analyze_page_result
  - mcp_lanhu_lanhu_get_design_slices
  - mcp_lanhu_lanhu_get_fairygui_project
  - codebase
  - readFile
  - listDir
  - memory
  - runCommands
---

# 蓝湖设计稿 → FairyGUI 完整转换

## 任务描述

将指定蓝湖设计稿转换为规范的 FairyGUI 6.x Package，并输出到 `data/uiProject/assets/` 目录。

**目标设计稿**：${input:designUrl:请输入蓝湖设计稿 URL 或设计名称}

---

## 执行步骤（按序执行，不可跳过）

### 步骤 1：治理检查（命名规范）

调用 **Lanhu Design Governor** Agent 对目标设计稿执行完整的命名规范检查：

```
govern design ${input:designUrl}
```

**判断条件**：
- 若报告中存在任何 `ERROR` → **停止流程**，将错误清单反馈给用户，要求修复后重试
- 若仅有 `WARN` → 列出警告，询问用户是否继续
- 若全部 `PASS` → 直接进入步骤 2

### 步骤 2：扫描现有 Package 记忆

调用 **FairyGUI Package Reviewer** 确保记忆文件是最新的：

```
review fairygui packages
```

重点检查 `data/memories/repo/fairygui-packages/Common.md` 和 `INDEX.md` 是否存在且有效。

### 步骤 3：获取设计图层数据

通过 MCP 工具获取完整设计数据：

1. `mcp_lanhu_lanhu_get_ai_analyze_design_result` → 获取完整图层树（mode="full"）
2. `mcp_lanhu_lanhu_get_design_slices` → 获取切图下载链接
3. 解析图层树，识别需要复用 Common 包的元素（遮罩、按钮、红点等）

### 步骤 4：执行转换

调用 `mcp_lanhu_lanhu_get_fairygui_project` 或直接调用 `fairygui_converter.py` 执行转换：

- 按照 `fairygui-reuse-in-conversion.instructions.md` 的复用规则，优先引用 Common 包组件
- 生成目录：`data/uiProject/assets/{DesignName}/`
- 同步下载切图资源到 `res/` 目录

### 步骤 5：校验生成质量

调用 **FairyGUI Asset Validator** 对生成的 Package 进行完整校验：

```
validate fairygui package {DesignName}
```

- 若校验报告有 `ERROR` → 触发自动修复流程（`fix fairygui issues {DesignName}`）
- 输出最终校验报告

---

## 完成标准

- [ ] 命名规范无 ERROR
- [ ] package.xml 中所有 src ID 有效
- [ ] 无远程 URL 图片引用（fileName 不含 `https://`）
- [ ] Common 包组件正确复用（无重复实现遮罩/红点/按钮）
- [ ] 校验报告无 ERROR
