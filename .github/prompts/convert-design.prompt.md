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

### 步骤 2：检查 Package 记忆文件（阻断）

在转换前**必须确认**以下文件存在于磁盘：

- `data/memories/repo/fairygui-packages/INDEX.md`
- `data/memories/repo/fairygui-packages/Common.md`

**决策**：
- 任一文件**不存在** → **停止流程**，先调用 **FairyGUI Package Reviewer** Agent 执行全量包扫描：
  ```
  review fairygui packages
  ```
  等待其完成后，确认两个文件均已生成，再进入步骤 3。
- 文件均存在但**超过 7 天未更新** → 重新运行 **FairyGUI Package Reviewer**，更新记忆后继续。
- 文件存在且有效 → 读取 `Common.md` 获取复用组件清单，直接进入步骤 3。

> ⚠️ 不得跳过此步骤，缺少记忆文件会导致转换时错误引用或遗漏 Common 包组件。

### 步骤 3：获取设计图层数据

通过 MCP 工具获取完整设计数据：

1. `mcp_lanhu_lanhu_get_ai_analyze_design_result` → 获取完整图层树（mode="full"）
2. `mcp_lanhu_lanhu_get_design_slices` → 获取切图下载链接
3. 解析图层树，识别需要复用 Common 包的元素（遮罩、按钮、红点等）

### 步骤 4：执行转换

调用 `mcp_lanhu_lanhu_get_fairygui_project` 或直接调用 `fairygui_converter.py` 执行转换：

- 按照 `fairygui-reuse-in-conversion.instructions.md` 的复用规则，优先引用 Common 包组件
- 生成目录：`data/uiProject/assets/{DesignName}/`

**切片资源处理**（必执行）：

| 条件 | 操作 |
|------|------|
| `total_slices > 0` | 遍历 `slice_list`，将每个切片下载到 `images/`，在 `package.xml` 中注册 `<image>` 资源 |
| `total_slices = 0` | 将设计稿概览截图从 `data/lanhu_designs/{pid}/{name}.png` 复制到 `效果图/`；告知用户实际素材需美术手动提供 |

> `get_ai_analyze_design_result` 调用后会自动将设计截图缓存到 `data/lanhu_designs/{pid}/{design_name}.png`。

### 步骤 4.5：创建 Package 记忆文件

转换完成后，必须创建工作区磁盘记忆文件：

```
data/memories/repo/fairygui-packages/{PackageName}.md
```

按照 `fairygui-memory-write.instructions.md` 中的模板，内容包含：包 ID、导出组件、图片资源、跨包依赖、切片是否需美术补充、技术备注。

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
- [ ] Common 包组件正确复用（无重复实现遮罩/红点/按钮）- [ ] 切片已处理：`total_slices>0` 时已下载到 `images/`；`=0` 时效果图已复制且已告知用户
- [ ] `data/memories/repo/fairygui-packages/{Name}.md` 已创建- [ ] 校验报告无 ERROR
