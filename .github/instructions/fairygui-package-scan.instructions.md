---
applyTo: "**/uiProject/assets/**/package.xml, **/uiProject/assets/**/*.xml"
---

# FairyGUI Package 扫描与解析指引

处理 FairyGUI 工程的 `package.xml` 或组件 XML 文件时，遵循以下分析规范。

---

## package.xml 文件结构

```xml
<?xml version="1.0" encoding="utf-8"?>
<packageDescription id="{packageId}" [hasFavorites="true"]>
  <resources>
    <!-- 目录结构 -->
    <folder id="/{path}/" name="{name}" path="/{parent}/"/>

    <!-- 组件资源 -->
    <component id="{id}" name="{Name}.xml" path="/{path}/" [exported="true"]/>

    <!-- 图片资源（可能有九宫格） -->
    <image id="{id}" name="{name}.png" path="/{path}/"
           [exported="true"]
           [scale="9grid" scale9grid="left,top,right,bottom"]/>    <!--
      ⚠️ 关键规则：name 与 path 职责严格分离
        name  = 完整文件名（必须含扩展名），如 "icon_bg.png"
        path  = 所在目录（以 / 结尾），如 "/res/"  或 "/images/button/"
        ❌ 错误示例：name="icon_bg"  path="/res/icon_bg.png/"
        ✅ 正确示例：name="icon_bg.png"  path="/res/"
      FairyGUI 编辑器按 path+name 拼接物理路径，path 中包含文件名会导致资源路径双重嵌套而无法加载。
    -->
    <!-- 字体资源 -->
    <font id="{id}" name="{name}.fnt|.ttf" path="/{path}/" [exported="true"]/>
  </resources>
  <!-- 可选：发布配置 -->
  <publish [name=""] [genCode="true"] [dependencies="{id1},{id2}"]/>
</packageDescription>
```

---

## 必须提取的关键信息

### 包级别
- `packageDescription/@id` — 包唯一 ID（如 `yez16kc6`），跨 Package 引用时必须使用此 ID

### 导出组件（`exported="true"` 的 component）
- `id` — 资源 ID，在 FairyGUI XML 中作为 `src="{id}"` 引用
- `name` — 文件名（含 `.xml` 后缀，如 `AlertView.xml`）
- `path` — 包内目录路径（如 `/button/`）

### 导出图片（`exported="true"` 的 image）
- `id`、`name`、`path` — 同上
- `scale` — 若值为 `9grid`，图片支持九宫格拉伸
- `scale9grid` — 九宫格参数 `"left,top,right,bottom"`（**必须完整记录，转换时直接复用**）

---

## 资源 ID 生成规则

新建 Package 时，所有资源（图片、组件）的 `id` 遵循统一规则：

```
id = {packageId[:4]}v{seq:02d}
```

- **前缀**：取 `packageDescription/@id` 的前 4 个字符，如包 ID 为 `yqc10001` → 前缀 `yqc1`
- **序号**：从 `v01` 开始，图片和组件共享同一顺序命名空间，每个资源按声明顺序递增
- 示例：`yqc1v01`, `yqc1v02`, …, `yqc1v39`（图片），`yqc1v40`（组件）

> ⚠️ 禁止使用 `s001`、`img001` 等自定义前缀，会导致 FairyGUI 编辑器无法识别资源归属。
> ⚠️ 禁止在本包 package.xml 中声明其他包的资源条目（如 `src` 指向外包 ID），FairyGUI 编辑器不会自动注入跨包引用到当前包描述符中。

---

## 组件 XML 文件结构

```xml
<?xml version="1.0" encoding="utf-8"?>
<component size="W,H" [pivot="0.5,0.5"] [extention="Button|ScrollPane|ProgressBar|Label"]
           [overflow="hidden|visible"]>

  <!-- 控制器：定义交互状态 -->
  <controller name="{name}" pages="0,{pageName},1,{pageName}" [exported="true"] selected="0">
    <remark page="0" value="{描述}"/>
  </controller>

  <!-- 主显示列表 -->
  <displayList>
    <!-- 文本 -->
    <text id="{id}" name="{name}" xy="{x},{y}" size="{w},{h}"
          fontSize="{size}" color="{color}" [bold="true"] [autoSize="none|shrink"]/>

    <!-- 富文本 -->
    <richtext id="{id}" name="{name}" xy="{x},{y}" size="{w},{h}" fontSize="{size}"/>

    <!-- 图片（引用本包资源） -->
    <image id="{id}" name="{name}" src="{resourceId}" fileName="{path/name.png}"
           xy="{x},{y}" size="{w},{h}"/>

    <!-- 子组件（引用本包或其他包的组件） -->
    <component id="{id}" name="{name}" src="{resourceId}" fileName="{PackageName/name.xml}"
               xy="{x},{y}" [size="{w},{h}"]/>

    <!-- 加载器（动态加载 Spine/图片） -->
    <loader id="{id}" name="{name}" xy="{x},{y}" size="{w},{h}"
            [url="ui://{packageId}{resourceId}"] [fill="scaleFree"]/>

    <!-- 列表 -->
    <list id="{id}" name="{name}" xy="{x},{y}" size="{w},{h}"
          defaultItem="ui://{packageId}{resourceId}" [layout="flow_h|flow_v"]/>
  </displayList>

  <!-- 按钮扩展配置 -->
  <Button [downEffect="scale" downEffectValue="0.8"]/>

  <!-- 关联约束 -->
  <relation target="{targetId}" sidePair="width-width,height-height"/>
</component>
```

---

## 组件 XML 分析重点

| 属性/元素 | 含义 | 记录要点 |
|-----------|------|---------|
| `size="W,H"` | 组件默认尺寸 | 必须记录，用于布局推断 |
| `extention` | FairyGUI 扩展类型 | `Button`/`ScrollPane`/`ProgressBar`/`Label` |
| `pivot="0.5,0.5"` | 中心锚点 | 弹窗类组件通常有此设置 |
| `controller name="button"` | 按钮状态（up/down/over/selectedOver） | 说明这是可点击按钮 |
| `controller name="ctrlType"` | 业务状态切换 | 记录各 page 含义 |
| 子元素名 `title` | 标题文本占位 | 组件有文字标题 |
| 子元素名 `closeBtn`/`btnClose` | 关闭按钮 | 弹窗类组件 |
| 子元素名 `btnYes`/`btnConfirm` | 确认按钮 | 有业务确认逻辑 |
| 子元素名 `btnNo`/`btnCancel` | 取消按钮 | 有业务取消逻辑 |
| 子元素名 `contentArea`/`Holder` | 内容容器占位 | 可动态填充内容的容器 |
| 子元素名 `list` | 列表容器 | 支持数据列表渲染 |

---

## 命名规范识别

FairyGUI 资源约定命名前缀：

| 前缀 | 含义 |
|------|------|
| `btn_` | 按钮切图资源 |
| `icon_` | 图标资源 |
| `pnl_` | 面板/容器背景图 |
| `bg_` | 全屏/区域背景图 |
| `line_` | 分隔线资源 |
| `prg_` | 进度条图片（含 `$bar` 后缀的是进度填充条） |
| `img_` | 通用图片 |
| `fnt_` | 位图字体（如伤害数字字体） |
| `*View.xml` | 完整视图/弹窗界面 |
| `*Item.xml` | 列表项/数据项组件 |
| `*Comp.xml` | 可复合的子组件 |
| `*Btn.xml` | 按钮组件（含交互逻辑） |
| `*Frame.xml` | 弹窗/窗口框架（通常含标题栏和关闭按钮） |

---

## 组件用途推断规则

当组件名称和结构不够明确时，按以下逻辑推断用途：

| 特征 | 推断用途 |
|------|---------|
| `size="720,1280"`，只含一个 image 子元素 | 全屏遮罩层 |
| `extention="Button"`，size 约 `100,80` ~ `300,100` | 通用按钮 |
| `pivot="0.5,0.5"`，含 `title` + `closeBtn` + `contentArea` | 弹窗框架 |
| 含 `btnYes` 和 `btnNo` | 确认/取消弹窗 |
| 含 `checkbox` 子组件 | 带勾选框的弹窗 |
| 含 `list` 并且 size 较大 | 列表视图 |
| `extention="ProgressBar"`，含 `bar` 子元素 | 进度条组件 |
| name 中含 `RedDot` 或 `reddot` | 红点提示组件 |
| name 中含 `Waiting` 或 `Loading` | 加载等待动画 |
| name 中含 `Item` 且 size 较小 | 列表项/背包格子 |
