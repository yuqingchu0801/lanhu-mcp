---
applyTo: "**/uiProject/assets/**/*.xml, **/uiProject/assets/**/package.xml"
---

# FairyGUI 资源校验规则

对从蓝湖设计稿转换生成的 FairyGUI Package 进行完整性、一致性和规范性校验，确保生成质量。

---

## 一、设计一致性检查

> 目的：验证生成的 FairyGUI 组件与蓝湖设计稿在尺寸、颜色、文本、布局上保持一致。

### 1.1 组件尺寸校验

- 顶级组件的 `size="W,H"` 必须与蓝湖设计稿的 artboard/frame 尺寸吻合，允许 ±2px 误差。
- 子元素的 `size="{w},{h}"` 与设计层的 `width`/`height` 偏差不得超过 2px。
- 若组件有 `pivot="0.5,0.5"`（弹窗类），核查其相对于父容器的居中位置是否正确。

```
校验逻辑：
  design_w, design_h = 从蓝湖 schema JSON 的根节点 width/height 取值
  fairy_w, fairy_h   = 从组件 XML 的 size="W,H" 解析
  PASS if abs(fairy_w - design_w) <= 2 and abs(fairy_h - design_h) <= 2
  FAIL otherwise → 报告差异值
```

### 1.2 颜色值校验

- FairyGUI 文本使用 `color="{#RRGGBB}"` 格式，应与蓝湖设计的字色 `rgba(r,g,b,1)` 相符。
- 图片填充/背景色若通过 image 元素实现，检查其是否对应正确的资源。
- 半透明遮罩类元素（alpha < 1）应使用 `#AARRGGBB`，AA 值由 `round(alpha * 255)` 得出。

颜色格式转换参考：
```
rgba(255, 200, 50, 1.0) → #FFC832
rgba(0, 0, 0, 0.6)      → #99000000
#ffffff                 → #FFFFFF
```

### 1.3 文本内容与样式校验

- `<text>` 节点的 `fontSize` 应与设计稿字号（`px` 单位）一致，允许 ±1px。
- `<text>` 节点若有 `bold="true"` 标记，对应设计稿字重应 ≥ 600（bold/black）。
- `autoSize` 属性：设计稿文字有固定高度区域时，必须设置 `autoSize="shrink"` 或 `autoSize="none"`，禁止保留默认缩放行为对固定布局造成遮挡。

### 1.4 图片资源校验

- 组件 XML 中所有 `<image>` 元素，其 `src="{id}"` 必须能在同包或依赖包的 `package.xml` 中找到对应 `id`。
- `fileName="{path/name.png}"` 对应的实际文件必须存在于 `res/` 目录中（或工程已下载完毕后）。
- 禁止 `fileName` 引用蓝湖 CDN 远程地址（`https://` 开头的路径），所有图片必须是本地路径。

#### package.xml 中 `<image>` 的 name / path 格式校验（必须检查）

```
校验规则：
  对每条 <image name="..." path="..."> 条目：

  RULE-IMG-01  name 必须包含文件扩展名
    PASS if name.endswith(".png") or name.endswith(".jpg")
    FAIL → ❌ ERROR：name="{name}" 缺少扩展名，应为 "{name}.png"

  RULE-IMG-02  path 只能是目录路径，不得包含文件名
    PASS if path.endswith("/") and "." not in path.split("/")[-2]
    FAIL → ❌ ERROR：path="{path}" 包含文件名，应只保留目录部分，如 "/res/"

  ❌ 错误示例：name="icon_bg"       path="/res/icon_bg.png/"
  ✅ 正确示例：name="icon_bg.png"   path="/res/"
```

#### 组件 XML 中 `<image>` / `<component>` 元素必须包含 src 属性

```
校验规则：
  对 displayList 中每个 <image> 和 <component> 元素：

  RULE-SRC-01  显示元素必须包含 src 属性且指向当前包有效资源
    PASS if element has src attribute
         and src value exists as an id in current package.xml or declared dependency package
    FAIL（无 src）→ ❌ ERROR：<{tag} id="{id}"> 缺少 src 属性，FairyGUI 运行时无法定位资源
    FAIL（悬空 src）→ ❌ ERROR：src="{src}" 在本包及依赖包中均无对应资源

  ⚠️ 特别注意：FairyGUI 编辑器有时会自动在 displayList 中插入跨包垃圾元素
     （特征：xy 坐标为负值如 xy="-503,-116"，src 指向外包 ID 如 ye4xv02）
     此类元素必须删除，并同步清理 package.xml 中被污染的条目。
```

> FairyGUI 编辑器以 `path + name` 拼接物理路径，若 `path` 中嵌入了文件名，会产生路径双重嵌套（`/res/icon_bg.png/icon_bg.png`），导致资源无法加载。

### 1.5 布局位置校验

- 所有子元素的 `xy="{x},{y}"` 坐标应与蓝湖设计层位置基本吻合（允许 ±2px 布局误差）。
- 绝对定位坐标参考系：以父容器左上角为原点（与蓝湖 Schema 的 `left`/`top` 一致）。
- 若设计中使用了 `overflow:hidden`，对应 FairyGUI 组件应设置 `overflow="hidden"`。

---

## 二、资源重复检查

> 目的：避免重复创建已有的公共组件/图片，消除冗余资源。

### 2.1 图片名称重复检测

跨包扫描所有 `package.xml` 中的 `<image name="...">` 条目：

- 同名图片若出现在多个 Package 中，且不是真正的跨包导出复用（即两个包都创建了物理相同的.png文件），则**标记为重复**。
- 重复文件的判定：文件名完全相同（不区分大小写），且一方已在 Common 包中 `exported="true"`。

```
检测规则：
  如果 image_name in common_exported_images
    且当前包也声明了同名 image
    且 当前包没有通过 <component src=...> 引用 Common 同名资源
  → ❌ WARN：不应重复定义已在 Common 导出的图片，应改用引用
```

### 2.2 公共组件重复创建检测

以下 Common 包的功能性组件，**禁止**在其他 Package 中重新实现等价版本：

| 功能描述 | Common 已有组件 | 重复迹象关键词 |
|---------|---------------|-------------|
| 全屏半透明黑色遮罩 | `WindowMask.xml` | 名含 mask / 遮罩 / shadow，size ≥ 700×1000，颜色 #xx000000 |
| 全屏加载等待转圈 | `ModalWaiting.xml` | 名含 loading / waiting / 等待，全屏尺寸 |
| 小型加载转圈 | `LoadWaiting.xml` | 名含 loading / spinner，尺寸 ≤ 100×100 |
| 右上角红点角标 | `RedDot.xml` | 名含 red / dot / 红点，尺寸 ≤ 30×30，纯圆形 |
| 通用确认弹窗 | `AlertView.xml` | 名含 alert / tip / confirm / 提示，含 yes/no 按钮 |
| 通用确认按钮 | `BCommonConfirmBtn.xml` | 名含 confirm / ok / 确认，尺寸约 282×81 |
| 通用取消按钮 | `BCommonCanelBtn.xml` | 名含 cancel / close / 取消，同类尺寸 |

检测方法：
1. 枚举目标包中所有 `component` 元素，逐一检查命名和尺寸是否命中上表
2. 若命中，进一步检查该组件内部是否包含对应 Common 组件的 `src` 引用
3. 若**没有引用 Common**，判定为重复创建 → ❌ ERROR

### 2.3 九宫格图片重复

若两个不同包都声明了 `scale="9grid"` 且 `scale9grid` 参数完全相同的图片，
且两者尺寸与视觉功能相近（如同为弹窗底框、同为按钮背景），
应合并至 Common 包并统一引用。

---

## 三、组件引用正确性检查

> 目的：确保跨包引用格式正确，依赖关系完整声明。

### 3.1 src ID 有效性

每个 `<component src="{id}">` 或 `<image src="{id}">` 中：

- `src` ID 必须能在**当前包的 package.xml** 或**依赖包的 package.xml** 中找到对应资源。
- 若 `src` 为短 ID（5-8 个字母数字字符），且在当前包和所有依赖包中均无法匹配 → ❌ ERROR：悬空引用

### 3.2 fileName 路径有效性

- `fileName="{PackageName}/{路径/ComponentName.xml}"` 格式：
  - `PackageName` 对应的目录必须在 `data/uiProject/assets/` 下存在
  - 路径末尾的 `.xml` 文件必须在该目录中存在
- `fileName="{name.xml}"` 无目录前缀格式，则文件应在当前包根路径下
- fileName 中**不应**包含空格、中文字符或绝对路径前缀

### 3.3 跨包依赖声明

若组件 XML 中存在引用其他包组件（`fileName` 包含不属于当前包的目录名），
则当前包的 `package.xml` 中必须在 `<publish>` 标签声明该依赖：

```xml
<!-- ✅ 正确 -->
<publish dependencies="yez16kc6"/>

<!-- ❌ 错误：引用了 Common(yez16kc6) 的组件，但未声明依赖 -->
```

依赖检查逻辑：
```
  解析组件 XML → 收集所有跨包 src ID → 查询 package.xml 中的依赖包 ID 集合
  如果存在 src ID 属于包 P 但 P.id 未在 dependencies 中 → ❌ ERROR
```

### 3.4 循环引用检测

- 若 Package A 依赖 Package B，Package B 又依赖 Package A → ❌ ERROR：循环依赖
- 同包内，若组件 A 的 `displayList` 中嵌套了组件 A 自身 → ❌ ERROR：自引用

### 3.5 defaultItem 有效性（列表类）

`<list defaultItem="ui://{packageId}{resourceId}">` 中：
- `packageId` 应能在已知包中找到对应包
- `resourceId` 应是该包中 `exported="true"` 的组件 ID

---

## 四、导出规则检查

> 目的：确保 package.xml 导出配置准确无遗漏，不多不少。

### 4.1 必须导出的组件

以下情况的组件**必须**标记 `exported="true"`：

- 文件名以 `View.xml` 结尾的**顶级页面组件**（如 `BagView.xml`, `ArenaView.xml`）
- 被其他 Package 的 `displayList` 引用的组件
- 列表的 item 模板组件（被 `defaultItem` 引用）

### 4.2 不应过度导出

以下情况的组件**通常不应**标记 `exported="true"`：

- 名称含 `_popup`、`_item`（内部弹出层或内部列表项，无外部使用场景）
- 包内私有辅助组件（名称前缀为 `_` 或 `Priv`）
- 初始转换阶段临时生成的组件（名称为 `n{数字}` 形式）

### 4.3 孤立资源（package.xml 中有但文件不存在）

扫描 `package.xml` 中声明的所有资源：
```
对每条 <component name="Foo.xml" path="/bar/"> 条目：
  预期文件路径 = assets/{PackageName}/bar/Foo.xml
  若文件不存在 → ❌ ERROR：孤立资源声明，package.xml 与实际文件不匹配
```

### 4.4 未注册资源（文件存在但 package.xml 无记录）

扫描目录内所有 `.xml` 文件（非 `package.xml`）：
```
若某 .xml 文件不在 package.xml 的 <resources> 声明中 → ⚠️ WARN：未注册组件文件
```

> 未注册的文件不会被 FairyGUI 识别为包内资源，通常意味着遗漏了声明。

---

## 五、命名规范检查

> 目的：保持命名一致性，便于后续维护和检索。

### 5.1 View 组件命名

- 顶级页面组件（功能视图入口）文件名**必须**以 `View.xml` 结尾。
  - ✅ `BagView.xml`, `ArenaMainView.xml`
  - ❌ `Bag.xml`, `Arena_main.xml`

### 5.2 按钮组件命名

- 按钮组件（`extention="Button"` 或逻辑上为可点击按钮）应遵循以下模式之一：
  - 前缀 `B`（业务级按钮）：`BCommonConfirmBtn.xml`
  - 后缀 `Btn`：`CloseBtn.xml`, `TabBtn.xml`
  - 后缀 `Button`：`CommonButton.xml`

### 5.3 Item 组件命名

- 列表项模板组件**应**包含 `Item` 字样：
  - ✅ `RankItem.xml`, `ItemMailRow.xml`
  - ❌ `Row.xml`, `Cell.xml`（语义不明，无法快速识别为列表项）

### 5.4 目录路径规范

- 组件分类目录名应使用英文小写，单词间用 `_` 或 `/` 分隔，不使用中文。
- 图片资源统一放在 `res/` 子目录，不允许 `.png` 文件放置在工程根目录。

### 5.5 元素 ID 规范

- 组件 XML 内的元素 `id` 应为以 `n` 开头的字母数字字符串（如 `n1`, `n2a3b`）。
- 禁止使用中文或空格作为 `name` 属性值（FairyGUI 编辑器在路径解析时会报错）。

---

## 六、Common 组件复用检查（最高优先级）

> 每次转换生成新 Package 时，优先检查以下列表，若有命中则替换为 Common 引用。

| 检查点 | 触发条件 | 正确做法 |
|-------|---------|---------|
| 全屏遮罩 | 存在 size ≥ 700×1000 的半透明黑色图片 | 替换为 `src="douy3" fileName="WindowMask.xml"` |
| 红点角标 | 存在直径 ≤ 30 的红色圆形 image | 替换为 `src="pxfbo4hc" fileName="reddot/RedDot.xml"` |
| 旋转加载 | 存在含旋转动画/loading 字样的组件 | 替换为 `src="douya" fileName="ModalWaiting.xml"` |
| 骨骼动画容器 | 存在名为 spine 的空 loader 占位 | 替换为 `src="hnpio4gx" fileName="SpineAni.xml"` |
| 确认按钮 | 存在橙色实心矩形按钮（约 282×81） | 替换为 `src="klomijo62q" fileName="new/Button/BCommonConfirmBtn.xml"` |
| 取消按钮 | 存在描边空心矩形按钮（约 282×81） | 替换为 `src="klomijo62o" fileName="new/Button/BCommonCanelBtn.xml"` |

---

## 七、校验报告格式

校验完成后，输出如下格式的总结报告：

```
========================================
FairyGUI Asset Validation Report
Package: {PackageName}  Date: {YYYY-MM-DD}
========================================

[PASS] 设计一致性：组件尺寸 ✓  颜色 ✓  文本 ✓
[PASS] 资源引用：src ID 有效 ✓  fileName 路径存在 ✓
[PASS] 依赖声明：跨包依赖已在 publish 中声明 ✓

[WARN] 资源重复：发现 2 处可能重复：
  - 图片 black_mask.png 已在 Common 导出，当前包重复声明
  - 组件 WinMask.xml 与 Common/WindowMask.xml 功能重复

[ERROR] 导出规则：
  - MainView.xml 未标记 exported="true"（顶级视图必须导出）
  - 未注册组件：assets/Bag/temp_test.xml 未在 package.xml 中声明

[ERROR] 命名规范：
  - 文件 main.xml 应重命名为 BagView.xml（顶级View需有View后缀）

========================================
总计：0 ERROR  1 WARN  （ERROR 必须修复，WARN 建议修复）
========================================
```

---

## 附：快速修复建议

| 错误类型 | 一键修复方式 |
|---------|-----------|
| 缺少 exported | 在 package.xml 对应条目添加 `exported="true"` |
| 缺少依赖声明 | 在 `<publish>` 中追加对应包 ID，逗号分隔 |
| 重复创建遮罩 | 删除本地组件，改用 Common WindowMask 引用 |
| 孤立资源声明 | 从 package.xml 删除该条目，或补充对应 xml 文件 |
| 未注册文件 | 在 package.xml `<resources>` 中添加对应 `<component>` 条目 |
