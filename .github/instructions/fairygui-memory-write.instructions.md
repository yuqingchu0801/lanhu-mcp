---
applyTo: "data/memories/repo/fairygui-packages/**"
---

# FairyGUI Package 记忆写入格式规范

每个 Package 的记忆文件路径为 `/data/memories/repo/fairygui-packages/{PackageName}.md`。  
包汇总索引文件路径为 `/data/memories/repo/fairygui-packages/INDEX.md`。

---

## 单包记忆文件标准模板

```markdown
# {PackageName} Package 记忆

> 最后更新：{YYYY-MM-DD}

## 基本信息

- **包 ID**：`{packageId}`
- **资源路径**：`data/uiProject/assets/{PackageName}/`
- **用途**：{简短描述此包的功能领域，例如："英雄系统 UI 组件"}
- **可复用程度**：`高` / `中` / `低`
  - 高 = 通用基础组件，可在任何新 Package 中直接引用
  - 中 = 特定功能域组件，相关功能时优先参考
  - 低 = 高度业务专属，通常不跨包复用

---

## 导出组件清单

### {ComponentName}

- **资源 ID**：`{id}`
- **包内路径**：`{path}{ComponentName}.xml`
- **默认尺寸**：`{W} × {H}`
- **扩展类型**：`{extention}` 或 `-`（普通组件）
- **锚点**：`{pivot}` 或 `-`
- **控制器**：`{controllerName}: {page0名}, {page1名}, ...` 或 `-`
- **用途说明**：{根据名称、尺寸、子元素推断其功能，例如："通用确认/取消双按钮弹窗框架，支持可选勾选框"}
- **引用方式**：
  ```xml
  <component src="{id}" fileName="{PackageName}/{路径/ComponentName}.xml"
             xy="{x},{y}" size="{w},{h}"/>
  ```

---

## 导出图片资源

| 资源名 | ID | 路径 | 九宫格参数 | 用途推断 |
|--------|----|------|-----------|---------|
| `{name.png}` | `{id}` | `{path}` | `{scale9grid}` 或 `-` | {描述} |

---

## 字体资源

| 字体名 | ID | 路径 | 说明 |
|--------|----|------|------|
| `{name.fnt}` | `{id}` | `{path}` | {用途，如"伤害数字位图字体"} |

---

## 复用建议

- **何时引用此 Package**：{说明哪些设计场景应检索此 Package}
- **优先使用组件**：{列出最具复用价值的 1~3 个组件名称}
- **注意事项**：{引用此 Package 时需留意的点，如依赖关系、尺寸限制等}

---

## 跨包依赖

此 Package 内的组件依赖以下其他 Package（需要在 `package.xml` 中声明依赖）：

| 依赖 Package | 包 ID | 被使用的组件 | 用途 |
|-------------|-------|------------|------|
| `{PackageName}` | `{id}` | `{ComponentName}` | {描述} |
```

---

## 包索引文件模板（INDEX.md）

```markdown
# FairyGUI 工程 Package 索引

> 最后更新：{YYYY-MM-DD}  
> 工程路径：`data/uiProject/assets/`

---

## Package 快速检索表

| Package | 包 ID | 用途 | 复用程度 | 核心可用组件 |
|---------|-------|------|---------|------------|
| Common | `yez16kc6` | 全局通用基础组件 | **高** | AlertView, CommonButton, WindowMask, RedDot, LoadWaiting |
| MainUI | `{id}` | 主界面 UI | 中 | {核心组件} |
| Hero | `vdw1yrpk` | 英雄系统 | 低 | HeroMainView, HeroDetailView |
| ... | ... | ... | ... | ... |

---

## 蓝湖设计解析快速复用指引

当解析新的蓝湖设计稿并生成 FairyGUI 工程时，**优先**使用以下已有组件：

### 通用弹窗类
| 设计元素 | 推荐复用 | 包 | 资源 ID |
|---------|---------|-----|--------|
| 全屏半透明黑色遮罩 | `WindowMask.xml` | Common | `douy3` |
| 全屏弹窗遮罩（另一种） | `WindowOtherMask.xml` | Common | 查 Common.md |
| 弹窗加载等待 | `ModalWaiting.xml` | Common | `douya` |
| 圆形加载等待 | `LoadWaiting.xml` | Common | `mvpbjo53l` |

### 按钮类
| 设计元素 | 推荐复用 | 包 | 资源 ID |
|---------|---------|-----|--------|
| 确认/主要操作按钮（橙色） | `BCommonConfirmBtn.xml` | Common/new/Button | `klomijo62q` |
| 取消/次要操作按钮 | `BCommonCanelBtn.xml` | Common/new/Button | `klomijo62o` |
| 通用图标按钮 | `CommonButton.xml` | Common/button | `md0644c` |

### 弹窗框架类
| 设计元素 | 推荐复用 | 包 | 说明 |
|---------|---------|-----|------|
| 标准弹窗框架（带关闭按钮） | `CommonFrame4.xml` | Common/new/Frame | 查 Common.md |
| 通用确认/取消弹窗 | `AlertView.xml` | Common | `mu0qo4n5` |

### 通用功能组件
| 设计元素 | 推荐复用 | 包 | 资源 ID |
|---------|---------|-----|--------|
| 红点/角标提示 | `RedDot.xml` | Common/reddot | `pxfbo4hc` |
| Spine 动画占位 | `SpineAni.xml` | Common | `hnpio4gx` |
| 内容占位容器 | `Holder.xml` | Common | `douyd` |
| 通用列表项 | `Item.xml` | Common | `h5ukijo5c0` |

---

## 各包记忆文件

{为每个 Package 生成链接，便于快速跳转}
- [Common.md](Common.md) - 全局通用基础组件
- [Hero.md](Hero.md) - 英雄系统
- ...
```

---

## 写入操作规则

### 写入时机
1. 首次分析 Package → 直接创建新文件
2. 重新分析已有 Package → 先读取现有内容，对比变化，更新修改部分
3. 新增组件时 → 在对应小节追加条目，同步更新 INDEX.md

### 用途推断参考

当组件用途不明确时，依据以下规则推断：

| 组件特征 | 推断 |
|---------|------|
| 名称含 `View`，size 较大（>400×400） | 完整界面/弹窗 |
| 名称含 `Item`，size 较小（<200×150） | 列表项/格子 |
| 名称含 `Comp` | 可复合的功能子组件 |
| 名称含 `Frame`，有 `Holder` 子元素 | 弹窗框架（内容容器） |
| `extention="Button"` | 按钮（直接标注类型） |
| `size="720,1280"` 且只含单一 image | 全屏遮罩/背景 |
| 名称含 `RedDot` | 红点提示徽标 |
| 名称含 `Waiting`/`Loading` | 加载等待动画 |
| 名称含 `Progress`/`Bar` | 进度条 |
| 名称含 `Alert`/`Dialog`/`Confirm` | 确认弹窗 |
| 名称含 `Tab`/`Check`/`Switch` | 切换/选择类控件 |

### 可复用程度判定

- **高**：Common 包所有组件；所有弹窗框架、遮罩、通用按钮
- **中**：特定功能域组件（如 Arena 相关），但其内部 Item 类组件在同域复用较高
- **低**：高度专属的 View 界面（如 `HeroMainView`，只在英雄列表页使用）
