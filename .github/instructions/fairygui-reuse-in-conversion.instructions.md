---
applyTo: "fairygui_converter.py, lanhu_mcp_server.py, **/fairygui/**/*.py"
---

# FairyGUI 转换时的 Package 复用指引

在将蓝湖（Lanhu）设计稿转换为 FairyGUI 工程时，**优先复用** `/data/memories/repo/fairygui-packages/` 中记录的现有 Package 组件，避免重复造轮子。

---

## 复用检索流程

```
1. 识别设计元素 → 判断是弹窗/按钮/遮罩层/进度条/红点/列表项等通用类型
2. 加载 Package 记忆索引 → 读取 /data/memories/repo/fairygui-packages/INDEX.md
3. 定向查阅 → 根据元素类型，读取对应 Package 的 .md 记忆文件
4. 获取精确引用信息 → 从记忆文件中取出 src ID 和 fileName
5. 生成引用 XML → 用 src + fileName 格式替代重新生成
```

---

## 常见设计元素与复用目标对应表

### 遮罩 / 背景层

| 设计特征 | 复用目标 | src ID | fileName |
|---------|---------|--------|---------|
| 全屏半透明黑色遮罩 | `WindowMask.xml` | `douy3` | `WindowMask.xml` |
| 全屏点击关闭遮罩（另一种） | `WindowOtherMask.xml` | 查 Common.md | `WindowOtherMask.xml` |

### 弹窗框架

| 设计特征 | 复用目标 | 包 |
|---------|---------|-----|
| 标准弹窗（带标题栏 + 关闭按钮 + 内容区） | `CommonFrame4.xml` | Common/new/Frame |
| 确认/取消双按钮弹窗（可选勾选框） | `AlertView.xml` | Common |

### 按钮类

| 设计特征 | 复用目标 | src ID | fileName |
|---------|---------|--------|---------|
| 主要/确认操作按钮（实心橙色，约 282×81） | `BCommonConfirmBtn.xml` | `klomijo62q` | `new/Button/BCommonConfirmBtn.xml` |
| 次要/取消操作按钮（描边） | `BCommonCanelBtn.xml` | `klomijo62o` | `new/Button/BCommonCanelBtn.xml` |
| 通用图标按钮（方形，支持 title + icon） | `CommonButton.xml` | `md0644c` | `button/CommonButton.xml` |
| 切换型按钮（开关） | `CommonBtnSwitch.xml` | 查 Common.md | `button/CommonBtnSwitch.xml` |
| 标签页按钮 | `TabButton1.xml` | 查 Common.md | `button/TabButton1.xml` |

### 功能组件

| 设计特征 | 复用目标 | src ID | fileName |
|---------|---------|--------|---------|
| 右上角红点角标 | `RedDot.xml` | `pxfbo4hc` | `reddot/RedDot.xml` |
| 全屏加载遮罩（带旋转动画） | `ModalWaiting.xml` | `douya` | `ModalWaiting.xml` |
| 小尺寸加载等待 | `LoadWaiting.xml` | `mvpbjo53l` | `LoadWaiting.xml` |
| Spine 骨骼动画占位 | `SpineAni.xml` | `hnpio4gx` | `SpineAni.xml` |
| 内容动态占位容器 | `Holder.xml` | `douyd` | `Holder.xml` |
| 通用列表项格子 | `Item.xml` | `h5ukijo5c0` | `Item.xml` |
| 进度条（条形） | `prg_com_js_01` 系列 | 查 Common.md | - |
| 复选框 | `CheckBox_2.xml` | `i8e585` | `checkbox/CheckBox_2.xml` |

---

## FairyGUI XML 跨包组件引用格式

```xml
<!-- ✅ 正确：通过 src + fileName 引用已有组件 -->
<component id="{elementId}" name="{elementName}"
           src="{resourceId}" fileName="{PackageName/路径/ComponentName.xml}"
           xy="{x},{y}" [size="{w},{h}"]/>

<!-- ✅ 示例：引用 Common 包的全屏弹窗遮罩 -->
<component id="n1" name="mask"
           src="douy3" fileName="WindowMask.xml"
           xy="0,0" size="720,1280">
  <relation target="" sidePair="width-width,height-height"/>
</component>

<!-- ✅ 示例：引用 Common 包的确认按钮 -->
<component id="n2" name="btnConfirm"
           src="klomijo62q" fileName="new/Button/BCommonConfirmBtn.xml"
           xy="338,431" size="282,81"/>

<!-- ✅ 示例：引用 Common 包的红点（通常挂载在按钮右上角） -->
<component id="n3" name="RedDot"
           src="pxfbo4hc" fileName="reddot/RedDot.xml"
           xy="86,14" visible="false">
  <relation target="" sidePair="right-right,top-top"/>
</component>

<!-- ❌ 错误：重复生成已有的通用组件 -->
<!-- 不要把 WindowMask 或 CommonButton 重新生成为新的 image/component -->
```

---

## package.xml 跨包依赖声明

当新生成的 Package 引用了 Common 或其他包的组件时，**必须**在 `package.xml` 的 `<publish>` 标签中声明依赖：

```xml
<packageDescription id="{newPackageId}">
  <resources>
    <!-- 本包的组件和图片资源 ... -->
    <component id="{ownId}" name="MyView.xml" path="/" exported="true"/>
  </resources>
  <!-- 声明对其他包的依赖（逗号分隔多个包 ID） -->
  <publish dependencies="yez16kc6"/>
  <!-- yez16kc6 = Common 包 ID -->
</packageDescription>
```

---

## 边界判断：复用 vs 新建

| 情况 | 操作 |
|------|------|
| 设计元素外观和功能与现有组件**高度一致** | ✅ **直接复用**，引用现有 src + fileName |
| 外观有差异但**功能结构相同**（如同类型按钮换了配色） | 🔄 **基于现有组件参考**，生成时采用相同的结构模式 |
| 是**全新的业务专属**组件，无对应现有组件 | ➕ **新建**，但内部的按钮/遮罩/红点等子元素仍应复用 Common |
| 图片资源**素材完全不同** | ➕ **新建** image 资源，下载蓝湖素材 |

---

## 在 convert_lanhu_to_fairygui_project 中集成复用

当 `fairygui_converter.py` 被调用生成新 Package 时，在 `displayList` 中应用以下策略：

```python
# 生成弹窗遮罩时，优先使用已有 WindowMask
# 而非生成新的全屏黑色 image 元素
REUSE_MAP = {
    # 格式: 匹配条件 -> {src, fileName, 默认尺寸}
    "WindowMask": {
        "src": "douy3",
        "fileName": "WindowMask.xml",
        "packageId": "yez16kc6",  # Common 包 ID
        "defaultSize": "720,1280",
    },
    "RedDot": {
        "src": "pxfbo4hc",
        "fileName": "reddot/RedDot.xml",
        "packageId": "yez16kc6",
        "defaultSize": "20,20",
    },
    # ... 其他可复用组件
}
```

---

## 记忆文件维护提醒

- 每次新增 Package 后，必须在工作区磁盘创建记忆文件：`data/memories/repo/fairygui-packages/{Name}.md`
- 每次修改 Common 包组件后，同步更新 INDEX.md 中的快速复用表
- 在 `data/memories/repo/fairygui-packages/INDEX.md` 中保持最新的包 ID 映射

## 切片资源处理规则

| `total_slices` | 操作 |
|----------------|------|
| `> 0` | 遍历 `slice_list`，将每个切片 URL 下载到 `images/`，并在 `package.xml` 中注册 `<image>` 资源 |
| `= 0` | 将 `data/lanhu_designs/{pid}/{design_name}.png`（`get_ai_analyze_design_result` 的缓存）复制到包的 `效果图/` 目录；在 `package.xml` 中为 `images/` 下的图片仅保留占位注册，并告知用户实际素材需美术提供 |

> `get_ai_analyze_design_result` 调用时会自动将设计概览截图缓存到 `data/lanhu_designs/{pid}/{design_name}.png`，即使 `total_slices=0` 也有截图可用。
