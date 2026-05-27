---
name: fairygui-package-reuse
description: "**LOOKUP SKILL** — 在 FairyGUI 转换时查找和引用现有 Package 组件的决策树与速查表。USE FOR: 判断某设计元素是否应复用现有组件、获取 src ID 和 fileName、声明跨包依赖。DO NOT USE FOR: 执行实际转换（使用 lanhu-fairygui-workflow skill）；校验 Package 质量（使用 FairyGUI Asset Validator agent）。"
---

# FairyGUI Package 组件复用决策 Skill

## 复用决策树

```
有设计元素需要转换
        │
        ▼
是弹窗遮罩/红点/加载或通用按钮？
        │
        ├── YES → 查下方「Common 包速查表」
        │         直接使用 src + fileName 引用
        │
        └── NO
              │
              ▼
           功能是否与现有组件高度一致？
              │
              ├── YES（仅外观差异，如换色）
              │       → 复用结构，参考已有组件的 XML 结构
              │
              └── NO（全新业务组件）
                      → 新建组件
                        但内部的按钮/遮罩/红点仍应复用 Common
```

---

## Common 包完整速查表

**包 ID**：`yez16kc6`

### 遮罩 & 等待

| 组件名 | src ID | fileName | 默认尺寸 | 触发条件 |
|--------|--------|---------|---------|---------|
| WindowMask | `douy3` | `WindowMask.xml` | 720×1280 | 全屏半透明黑色遮罩 |
| WindowOtherMask | 查 Common.md | `WindowOtherMask.xml` | - | 全屏可点击关闭遮罩 |
| ModalWaiting | `douya` | `ModalWaiting.xml` | 全屏 | 全屏加载转圈（name含loading/waiting）|
| LoadWaiting | `mvpbjo53l` | `LoadWaiting.xml` | ≤100×100 | 小型加载等待 |

### 按钮

| 组件名 | src ID | fileName | 默认尺寸 | 触发条件 |
|--------|--------|---------|---------|---------|
| BCommonConfirmBtn | `klomijo62q` | `new/Button/BCommonConfirmBtn.xml` | 282×81 | 主要确认操作（实心橙色）|
| BCommonCanelBtn | `klomijo62o` | `new/Button/BCommonCanelBtn.xml` | 282×81 | 次要取消操作（描边）|
| CommonButton | `md0644c` | `button/CommonButton.xml` | - | 通用图标按钮（方形）|
| CommonBtnSwitch | 查 Common.md | `button/CommonBtnSwitch.xml` | - | 开关切换按钮 |
| TabButton1 | 查 Common.md | `button/TabButton1.xml` | - | 标签页按钮 |

### 功能组件

| 组件名 | src ID | fileName | 触发条件 |
|--------|--------|---------|---------|
| RedDot | `pxfbo4hc` | `reddot/RedDot.xml` | 右上角红点角标（≤30×30）|
| AlertView | 查 Common.md | `AlertView.xml` | 确认/取消弹窗（含 yes/no 按钮）|
| CommonFrame4 | 查 Common.md | `new/Frame/CommonFrame4.xml` | 标准弹窗框架（含标题栏+关闭按钮）|
| SpineAni | `hnpio4gx` | `SpineAni.xml` | Spine 骨骼动画占位 |
| Holder | `douyd` | `Holder.xml` | 内容动态容器占位 |
| Item | `h5ukijo5c0` | `Item.xml` | 通用列表项格子 |
| CheckBox_2 | `i8e585` | `checkbox/CheckBox_2.xml` | 复选框 |

---

## XML 引用模板

```xml
<!-- 跨包组件引用（必须有 src + fileName）-->
<component id="{elementId}" name="{elementName}"
           src="{resourceId}" fileName="{PackageName/路径/ComponentName.xml}"
           xy="{x},{y}" size="{w},{h}"/>

<!-- 示例：引用遮罩 -->
<component id="n1" name="mask"
           src="douy3" fileName="WindowMask.xml"
           xy="0,0" size="720,1280">
  <relation target="" sidePair="width-width,height-height"/>
</component>

<!-- 示例：引用红点（通常挂载在按钮右上角）-->
<component id="n2" name="RedDot"
           src="pxfbo4hc" fileName="reddot/RedDot.xml"
           xy="86,14" visible="false">
  <relation target="" sidePair="right-right,top-top"/>
</component>
```

---

## package.xml 依赖声明（引用 Common 时必须）

```xml
<packageDescription id="{newPackageId}">
  <resources>
    <!-- 本包资源... -->
  </resources>
  <!-- 引用了 Common 包时，必须声明依赖 -->
  <publish dependencies="yez16kc6"/>
</packageDescription>
```

---

## 复用 vs 新建判断标准

| 情况 | 操作 |
|------|------|
| 外观+功能与现有组件高度一致 | ✅ 直接复用，引用 src + fileName |
| 同类型但配色/尺寸略有差异 | 🔄 参考现有结构新建，内部子元素仍复用 |
| 全新业务专属组件 | ➕ 新建，但按钮/遮罩等子元素复用 Common |
| 图片素材完全不同 | ➕ 新建 image 资源，下载蓝湖切图 |

---

## 查找更多组件

若上述速查表中找不到所需组件：

1. 读取 `memories/repo/fairygui-packages/INDEX.md` —— 获取所有包的快速检索表
2. 读取 `memories/repo/fairygui-packages/{PackageName}.md` —— 获取具体包的组件清单
3. 直接读取 `data/uiProject/assets/{PackageName}/package.xml` —— 获取精确 ID

> 🚨 **禁止猜测 ID**：若记忆文件和 package.xml 中都找不到某 ID，则该组件不可引用，必须新建。
