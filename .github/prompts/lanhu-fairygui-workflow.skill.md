---
name: lanhu-fairygui-workflow
description: "**WORKFLOW SKILL** — 执行蓝湖设计稿完整转换为 FairyGUI Package 的步骤指引。USE FOR: 蓝湖URL转FairyGUI、设计稿转换、新建Package、治理+扫描+转换+校验一键流程。INVOKES: Lanhu Design Governor, FairyGUI Package Reviewer, FairyGUI Asset Validator sub-agents; MCP tools mcp_lanhu_*; fairygui_converter.py."
---

# 蓝湖 → FairyGUI 转换工作流 Skill

## 触发条件

用户提到以下任一意图时激活此 Skill：
- "把蓝湖设计稿转成 FairyGUI"
- "将设计稿生成 Package"
- "convert design to fairygui"
- 提供蓝湖 URL + 要求生成 XML 工程

---

## 执行路径

### 路径 A：完整一键流程（推荐）

直接使用编排 Agent：

```
@Lanhu-to-FairyGUI Workflow convert design {URL 或设计名}
```

该 Agent 自动串联以下四步：
1. ✅ 命名治理（`Lanhu Design Governor`）
2. 📦 Package 记忆扫描（`FairyGUI Package Reviewer`）  
3. 🔄 设计转换（`fairygui_converter.py` + MCP 工具）
4. 🔍 资源校验（`FairyGUI Asset Validator`）

### 路径 B：分步执行

| 步骤 | 命令 | Agent/工具 |
|------|------|-----------|
| 治理检查 | `govern design {URL}` | `Lanhu Design Governor` |
| 扫描包记忆 | `review fairygui packages` | `FairyGUI Package Reviewer` |
| 执行转换 | `mcp_lanhu_lanhu_get_fairygui_project` | MCP 工具 |
| 校验输出 | `validate fairygui package {Name}` | `FairyGUI Asset Validator` |

---

## 关键阻断点

```
R-001 中文命名 ERROR → 必须修复，不可跳过
↓
若仅有 WARN → 询问用户，用户确认后继续
↓
记忆文件不存在 → 先运行 FairyGUI Package Reviewer
↓
校验 ERROR → 触发自动修复（仅安全类型）
```

---

## 常用 MCP 工具调用示例

```python
# 1. 获取设计列表
designs = mcp_lanhu_lanhu_get_designs()

# 2. 获取完整图层数据
data = mcp_lanhu_lanhu_get_ai_analyze_design_result(
    design_id="xxx", mode="full"
)

# 3. 获取切图下载链接
slices = mcp_lanhu_lanhu_get_design_slices(design_id="xxx")

# 4. 直接获取 FairyGUI 转换结果
result = mcp_lanhu_lanhu_get_fairygui_project(
    design_id="xxx",
    output_dir="data/uiProject/assets/MyPackage"
)
```

---

## Common 包快速复用表

| 设计元素 | Component | src | fileName |
|---------|-----------|-----|---------|
| 全屏黑色遮罩 | WindowMask | `douy3` | `WindowMask.xml` |
| 全屏加载转圈 | ModalWaiting | `douya` | `ModalWaiting.xml` |
| 小型加载等待 | LoadWaiting | `mvpbjo53l` | `LoadWaiting.xml` |
| 右上角红点 | RedDot | `pxfbo4hc` | `reddot/RedDot.xml` |
| 主确认按钮 | BCommonConfirmBtn | `klomijo62q` | `new/Button/BCommonConfirmBtn.xml` |
| 次取消按钮 | BCommonCanelBtn | `klomijo62o` | `new/Button/BCommonCanelBtn.xml` |
| 通用图标按钮 | CommonButton | `md0644c` | `button/CommonButton.xml` |
| 通用弹窗框架 | CommonFrame4 | 查 Common.md | `new/Frame/CommonFrame4.xml` |
| 确认弹窗 | AlertView | 查 Common.md | `AlertView.xml` |

> 🚨 表中未列的组件，**必须读取** `data/memories/repo/fairygui-packages/Common.md` 获取精确 ID，严禁猜测。

---

## 错误快速排查

| 现象 | 可能原因 | 解决方案 |
|------|---------|---------|
| XML 解析报错 | 生成的 XML 格式异常 | 查找报错行号，检查特殊字符转义 |
| src ID 找不到 | 引用了不存在的资源 ID | 重新从 `package.xml` 或记忆文件读取 |
| fileName 含 https:// | 图片未本地化 | 下载图片到 `res/` 目录，更新 fileName |
| 缺少 dependencies 声明 | 跨包引用但未声明依赖 | 在 `<publish>` 追加 Common 包 ID `yez16kc6` |
| 转换后组件尺寸错位 | 设计稿坐标系差异 | 检查蓝湖 schema 中 `left/top` 是否为绝对坐标 |
