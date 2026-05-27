# GitHub Copilot 全局指引 — 蓝湖 → FairyGUI 工程

本文件为整个仓库提供全局上下文，Copilot 在所有对话中均会读取。

---

## 项目概述

本项目是一个 **蓝湖设计稿 → FairyGUI 6.x 工程** 的自动化转换 MCP 服务器，运行在 Python 3.11+（FastMCP 框架），配合 VS Code Copilot Agent 模式使用。

| 组件 | 路径 | 职责 |
|------|------|------|
| MCP 服务器 | `lanhu_mcp_server.py` | 蓝湖 API 封装、截图、飞书通知、FairyGUI 转换入口 |
| FairyGUI 转换器 | `fairygui_converter.py` | Lanhu Schema / Sketch JSON → FairyGUI XML |
| FairyGUI 工程资产 | `data/uiProject/assets/` | 现有 FairyGUI Package（Common, Hero, MainUI 等） |
| 设计规范文档 | `data/lanhu-rule/lanhu-Rule.md` | 蓝湖图层命名规范（治理检查依据） |
| Package 记忆文件 | `memories/repo/fairygui-packages/` | 各 Package 可复用组件清单 |

---

## MCP 工具速查

> 使用任何蓝湖数据工具前，先确认 `LANHU_COOKIE` / `DDS_COOKIE` 环境变量已配置。

| MCP 工具 | 用途 |
|---------|------|
| `mcp_lanhu_lanhu_get_designs` | 获取蓝湖项目设计列表 |
| `mcp_lanhu_lanhu_get_pages` | 获取指定设计的页面列表 |
| `mcp_lanhu_lanhu_get_ai_analyze_design_result` | 获取 AI 分析后的设计完整图层树（优先用 mode="full"）|
| `mcp_lanhu_lanhu_get_ai_analyze_page_result` | 获取单页面 AI 分析图层数据 |
| `mcp_lanhu_lanhu_get_design_slices` | 获取切图资源下载链接 |
| `mcp_lanhu_lanhu_get_fairygui_project` | 直接获取 FairyGUI 工程转换结果（完整流程）|
| `mcp_lanhu_lanhu_list_product_documents` | 列出产品文档 |
| `mcp_lanhu_lanhu_say` | 发送评论到蓝湖 |
| `mcp_lanhu_lanhu_resolve_invite_link` | 解析蓝湖邀请链接 |

---

## Agent 协作体系

```
用户输入蓝湖 URL / 设计名
        │
        ▼
┌─────────────────────────────────┐
│  Lanhu Design Governor          │  检查命名规范，阻断 ERROR
│  (.github/agents/)              │
└─────────────────────────────────┘
        │ 通过 ▼
┌─────────────────────────────────┐
│  FairyGUI Package Reviewer      │  扫描现有包，生成/更新复用记忆
│  (.github/agents/)              │
└─────────────────────────────────┘
        │ 记忆就绪 ▼
┌─────────────────────────────────┐
│  转换执行                        │  调用 fairygui_converter.py
│  (by Copilot / lanhu_mcp_server) │  复用 Common 包组件
└─────────────────────────────────┘
        │ 生成完成 ▼
┌─────────────────────────────────┐
│  FairyGUI Asset Validator       │  校验生成质量，输出可修复报告
│  (.github/agents/)              │
└─────────────────────────────────┘
```

**完整串联**：使用 `Lanhu-to-FairyGUI Workflow` Agent（`.github/agents/lanhu-to-fairygui.agent.md`）可一键执行上述全流程。

---

## Instructions 文件导航

| 文件 | 适用范围 | 核心内容 |
|------|---------|---------|
| `fairygui-package-scan.instructions.md` | `package.xml`, `*.xml` | 如何解析 FairyGUI 包文件结构 |
| `fairygui-memory-write.instructions.md` | `memories/repo/fairygui-packages/**` | 记忆文件的书写格式规范 |
| `fairygui-reuse-in-conversion.instructions.md` | `fairygui_converter.py`, `lanhu_mcp_server.py` | 转换时优先复用已有 Package 组件 |
| `fairygui-asset-validator.instructions.md` | `**/uiProject/assets/**/*.xml` | 生成资源的校验规则（7章完整规范）|
| `lanhu-design-governance.instructions.md` | `lanhu_mcp_server.py`, 治理 Agent | 蓝湖命名规范校验规则（R-001~R-006）|

---

## Skills 导航

| Skill 文件 | 触发场景 |
|-----------|---------|
| `.github/prompts/lanhu-fairygui-workflow.skill.md` | 执行蓝湖设计稿完整转换流程的步骤指引 |
| `.github/prompts/fairygui-package-reuse.skill.md` | 查找和引用现有 FairyGUI Package 组件的决策树 |

## Prompts 导航

| Prompt 文件 | 用途 |
|------------|------|
| `.github/prompts/convert-design.prompt.md` | 🔄 完整设计稿转换（含四阶段流程） |
| `.github/prompts/govern-design.prompt.md` | 🔍 命名规范治理检查 |
| `.github/prompts/validate-package.prompt.md` | ✅ Package 资源质量校验 |
| `.github/prompts/refresh-package-memory.prompt.md` | 📦 刷新 Package 记忆文件 |

---

## 关键约束（全局生效）

1. **不修改 Common 包**：`data/uiProject/assets/Common/` 是全局基础，只读，不向其中写入。
2. **不猜测资源 ID**：`src="{id}"` 和 `fileName` 必须从记忆文件或 `package.xml` 中读取，禁止臆造。
3. **命名规范阻断**：设计稿存在 `R-001 ERROR`（中文命名）时，不应推进转换。
4. **本地图片路径**：`fileName` 中禁止出现 `https://` 开头的远程 URL，所有图片必须本地化。
5. **XML 容错**：解析 XML 错误时报告行号，跳过该文件继续，不中断整体流程。

---

## 开发环境

```bash
# 安装依赖
pip install -r requirements.txt
playwright install chromium

# 配置环境变量（复制示例后填入 Cookie）
cp config.example.env .env

# 启动 MCP 服务器（stdio 模式）
python lanhu_mcp_server.py

# 运行测试
pytest tests/ -v
```

- Python 版本：3.11+
- FairyGUI 目标版本：6.1.3 + Laya 3.x
- 编码：UTF-8（所有 XML 文件）
