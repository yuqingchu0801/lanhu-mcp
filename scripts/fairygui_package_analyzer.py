#!/usr/bin/env python3
"""
FairyGUI Package 批量分析器

扫描 FairyGUI 工程 assets 目录，为每个 Package 生成结构化记忆文件。

用法：
    python scripts/fairygui_package_analyzer.py
    python scripts/fairygui_package_analyzer.py --assets data/uiProject/assets --output memories/repo/fairygui-packages
    python scripts/fairygui_package_analyzer.py --package Common   # 只分析指定包
    python scripts/fairygui_package_analyzer.py --json             # 同时生成 JSON 格式

输出：
    memories/repo/fairygui-packages/{PackageName}.md    每个 Package 的 Markdown 记忆文件
    memories/repo/fairygui-packages/INDEX.md            包汇总索引文件
    memories/repo/fairygui-packages/{PackageName}.json  (可选) 机器可读的 JSON 格式
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
import xml.etree.ElementTree as ET


# ──────────────────────────────────────────────────────────────────────────────
# 辅助函数
# ──────────────────────────────────────────────────────────────────────────────

def _infer_usage(name: str, size: str, extention: str, controllers: list, children_names: list) -> str:
    """根据组件特征推断用途描述。"""
    name_lower = name.lower()
    children_lower = [c.lower() for c in children_names]

    if 'windowmask' in name_lower or 'othermask' in name_lower:
        return "全屏遮罩层（弹窗背景用）"
    if 'modalwaiting' in name_lower:
        return "全屏加载等待遮罩（含旋转动画）"
    if 'loadwaiting' in name_lower or 'loading' in name_lower:
        return "加载等待动画组件"
    if 'reddot' in name_lower:
        return "红点/角标提示徽标"
    if 'holder' in name_lower:
        return "动态内容占位容器（由外部填充子节点）"
    if 'spineani' in name_lower:
        return "Spine 骨骼动画占位组件"
    if 'alertview' in name_lower or 'alerttips' in name_lower:
        return "通用确认/取消弹窗（支持双按钮和可选勾选框）"
    if 'alert' in name_lower or 'dialog' in name_lower or 'confirm' in name_lower:
        return "确认弹窗"
    if 'frame' in name_lower and ('title' in children_lower or 'closeBtn' in children_names):
        return "弹窗/窗口框架（含标题栏和关闭按钮）"
    if extention == 'Button':
        size_parts = size.split(',') if size else []
        if len(size_parts) == 2:
            try:
                w, h = int(size_parts[0]), int(size_parts[1])
                if w > 200:
                    return f"宽幅普通按钮（{w}×{h}）"
                return f"图标型按钮（{w}×{h}）"
            except ValueError:
                pass
        return "通用按钮组件"
    if 'progress' in name_lower or 'bar' in name_lower:
        return "进度条组件"
    if 'checkbox' in name_lower or 'check' in name_lower:
        return "复选框组件"
    if 'combobox' in name_lower:
        return "下拉选择框组件"
    if 'tab' in name_lower:
        return "标签页/选项卡按钮"
    if 'scrollrichtext' in name_lower:
        return "可滚动富文本组件"
    if name_lower.endswith('view'):
        return f"{name.replace('View', '')} 功能界面（完整视图）"
    if name_lower.endswith('item'):
        return f"{name.replace('Item', '')} 列表项/格子组件"
    if name_lower.endswith('comp'):
        return f"{name.replace('Comp', '')} 子功能组件"
    if name_lower.endswith('btn'):
        return f"{name.replace('Btn', '')} 按钮组件"
    return "业务功能组件（详见对应 XML 文件）"


def _infer_reusability(package_name: str, exported_count: int) -> str:
    """推断包的可复用程度。"""
    if package_name.lower() == 'common':
        return '高（全局通用基础组件库）'
    high_reuse = {'ui', 'mainui', 'font', 'effect'}
    if package_name.lower() in high_reuse:
        return '高'
    if exported_count >= 10:
        return '中（含较多可导出组件）'
    if exported_count >= 3:
        return '中'
    return '低（业务专属组件）'


def _infer_package_purpose(package_name: str) -> str:
    """根据包名推断功能领域。"""
    mapping = {
        'common': '全局通用基础组件（按钮、弹窗框架、遮罩、进度条、红点等）',
        'mainui': '主界面 UI 组件（主城、底部导航栏等）',
        'hero': '英雄系统 UI 组件（英雄列表、详情、技能等）',
        'battle': '战斗场景 UI 组件（HP 条、技能栏、战斗结算等）',
        'battlepass': '战令/通行证 UI 组件',
        'bag': '背包/仓库 UI 组件',
        'arena': '竞技场 UI 组件',
        'chat': '聊天 UI 组件',
        'shop': '商城 UI 组件',
        'mail': '邮件 UI 组件',
        'friend': '好友系统 UI 组件',
        'rank': '排行榜 UI 组件',
        'task': '任务系统 UI 组件',
        'guide': '新手引导 UI 组件',
        'setting': '设置界面 UI 组件',
        'profile': '个人信息 UI 组件',
        'union': '公会/联盟 UI 组件',
        'account': '账号相关 UI 组件（服务器选择、年龄提示等）',
        'notice': '公告通知 UI 组件',
        'draw': '抽卡/召唤 UI 组件',
        'fund': '基金/付费 UI 组件',
        'daydreward': '每日奖励 UI 组件',
        'dailyrecharge': '每日充值 UI 组件',
        'redpack': '红包活动 UI 组件',
        'energy': '体力系统 UI 组件',
        'afk': '挂机系统 UI 组件',
        'gemraw': '钻石抽卡 UI 组件',
        'talentskill': '天赋技能 UI 组件',
        'maindungeon': '主线地图/关卡 UI 组件',
        'debug': '调试用临时 UI 组件',
        'font': '字体资源包',
        'effect': '特效/动效资源包',
    }
    return mapping.get(package_name.lower(), f'{package_name} 功能域 UI 组件')


def _infer_image_usage(img_name: str, path: str) -> str:
    """根据图片名和路径推断用途。"""
    name = img_name.lower()
    if name.startswith('btn_'):
        return "按钮切图"
    if name.startswith('icon_'):
        return "图标"
    if name.startswith('pnl_'):
        return "面板/容器背景"
    if name.startswith('bg_') or '/bg/' in path:
        return "背景图片"
    if name.startswith('line_') or '/line/' in path:
        return "分隔线"
    if name.startswith('prg_'):
        if '$bar' in name:
            return "进度条填充条"
        return "进度条底框"
    if name.startswith('img_'):
        return "通用图片"
    if name.startswith('fnt_') or name.endswith('.fnt'):
        return "位图字体"
    if '效果图' in path or name.startswith('@@') or name.startswith('z_'):
        return "设计效果图（非运行时资源）"
    return "图片资源"


# ──────────────────────────────────────────────────────────────────────────────
# Package 分析核心
# ──────────────────────────────────────────────────────────────────────────────

def analyze_component_xml(xml_path: Path) -> dict:
    """
    分析单个组件 XML 文件，提取关键属性。

    Returns:
        {size, extention, pivot, controllers, key_children}
    """
    result = {
        'size': '',
        'extention': '',
        'pivot': '',
        'controllers': [],
        'key_children': [],
    }
    if not xml_path.exists():
        return result

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        result['size'] = root.attrib.get('size', '')
        result['extention'] = root.attrib.get('extention', '')
        result['pivot'] = root.attrib.get('pivot', '')

        # 收集控制器信息
        for ctrl in root.findall('controller'):
            ctrl_name = ctrl.attrib.get('name', '')
            pages_raw = ctrl.attrib.get('pages', '')
            # pages 格式：index,name,index,name,...
            parts = pages_raw.split(',')
            page_names = [parts[i] for i in range(1, len(parts), 2) if i < len(parts)]
            result['controllers'].append({
                'name': ctrl_name,
                'pages': page_names,
            })

        # 收集 displayList 的直接子元素名（关键子元素）
        display_list = root.find('displayList')
        if display_list is not None:
            for child in display_list:
                child_name = child.attrib.get('name', '')
                if child_name:
                    result['key_children'].append(child_name)

    except ET.ParseError:
        pass

    return result


def analyze_package(assets_dir: Path, package_name: str) -> dict:
    """
    分析指定 Package，返回结构化数据。

    Returns:
        {
            'package_name': str,
            'package_id': str,
            'purpose': str,
            'reusability': str,
            'exported_components': [
                {id, name, path, size, extention, pivot, controllers, key_children, usage}
            ],
            'exported_images': [
                {id, name, path, scale9grid, usage}
            ],
            'fonts': [
                {id, name, path}
            ],
            'all_components': int,   # 总组件数（含非导出）
            'dependencies': [],      # 声明的依赖包 ID 列表
        }
    """
    package_dir = assets_dir / package_name
    package_xml_path = package_dir / 'package.xml'

    if not package_xml_path.exists():
        return {}

    result = {
        'package_name': package_name,
        'package_id': '',
        'purpose': _infer_package_purpose(package_name),
        'exported_components': [],
        'exported_images': [],
        'fonts': [],
        'all_components': 0,
        'dependencies': [],
    }

    try:
        tree = ET.parse(package_xml_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"  [ERROR] 解析 {package_xml_path} 失败: {e}", file=sys.stderr)
        return result

    result['package_id'] = root.attrib.get('id', '')

    resources = root.find('resources')
    if resources is None:
        return result

    component_count = 0
    for elem in resources:
        tag = elem.tag
        elem_id = elem.attrib.get('id', '')
        elem_name = elem.attrib.get('name', '')
        elem_path = elem.attrib.get('path', '/')
        exported = elem.attrib.get('exported', 'false').lower() == 'true'

        if tag == 'component':
            component_count += 1
            if exported:
                # 构建 xml 文件的相对路径（去掉 path 开头的 /，拼接 name）
                rel_path = elem_path.lstrip('/')
                xml_rel = rel_path + elem_name if rel_path else elem_name
                xml_full_path = package_dir / xml_rel

                comp_info = analyze_component_xml(xml_full_path)
                usage = _infer_usage(
                    name=elem_name.replace('.xml', ''),
                    size=comp_info['size'],
                    extention=comp_info['extention'],
                    controllers=[c['name'] for c in comp_info['controllers']],
                    children_names=comp_info['key_children'],
                )
                result['exported_components'].append({
                    'id': elem_id,
                    'name': elem_name,
                    'path': elem_path,
                    'size': comp_info['size'],
                    'extention': comp_info['extention'],
                    'pivot': comp_info['pivot'],
                    'controllers': comp_info['controllers'],
                    'key_children': comp_info['key_children'],
                    'usage': usage,
                })

        elif tag == 'image':
            if exported:
                scale9grid = elem.attrib.get('scale9grid', '')
                # 过滤设计效果图（路径中含"效果图"或名称以特殊符号开头）
                is_design_img = ('效果图' in elem_path or
                                 elem_name.startswith('@@') or
                                 elem_name.lower().startswith('z_') or
                                 '临时' in elem_name)
                if not is_design_img:
                    usage = _infer_image_usage(elem_name, elem_path)
                    result['exported_images'].append({
                        'id': elem_id,
                        'name': elem_name,
                        'path': elem_path,
                        'scale9grid': scale9grid,
                        'usage': usage,
                    })

        elif tag == 'font':
            if exported:
                result['fonts'].append({
                    'id': elem_id,
                    'name': elem_name,
                    'path': elem_path,
                })

    result['all_components'] = component_count

    # 检查依赖声明
    publish_elem = root.find('publish')
    if publish_elem is not None:
        deps_raw = publish_elem.attrib.get('dependencies', '')
        if deps_raw:
            result['dependencies'] = [d.strip() for d in deps_raw.split(',') if d.strip()]

    result['reusability'] = _infer_reusability(
        package_name, len(result['exported_components'])
    )

    return result


# ──────────────────────────────────────────────────────────────────────────────
# Markdown 生成
# ──────────────────────────────────────────────────────────────────────────────

def generate_package_markdown(pkg: dict) -> str:
    """将 Package 分析结果生成 Markdown 格式的记忆文件内容。"""
    lines = []
    today = date.today().isoformat()
    name = pkg['package_name']

    lines.append(f"# {name} Package 记忆\n")
    lines.append(f"> 最后更新：{today}\n")

    # 基本信息
    lines.append("## 基本信息\n")
    lines.append(f"- **包 ID**：`{pkg['package_id']}`")
    lines.append(f"- **资源路径**：`data/uiProject/assets/{name}/`")
    lines.append(f"- **用途**：{pkg['purpose']}")
    lines.append(f"- **可复用程度**：{pkg['reusability']}")
    lines.append(f"- **总组件数**：{pkg['all_components']}（导出：{len(pkg['exported_components'])}）\n")

    # 导出组件清单
    if pkg['exported_components']:
        lines.append("---\n")
        lines.append("## 导出组件清单\n")
        for comp in pkg['exported_components']:
            comp_name = comp['name'].replace('.xml', '')
            lines.append(f"### {comp_name}\n")
            lines.append(f"- **资源 ID**：`{comp['id']}`")
            full_path = comp['path'].strip('/') + '/' + comp['name'] if comp['path'] and comp['path'] != '/' else comp['name']
            lines.append(f"- **包内路径**：`{full_path}`")

            if comp['size']:
                w, h = comp['size'].split(',') if ',' in comp['size'] else (comp['size'], '?')
                lines.append(f"- **默认尺寸**：`{w} × {h}`")
            else:
                lines.append(f"- **默认尺寸**：`-`")

            lines.append(f"- **扩展类型**：`{comp['extention']}`" if comp['extention'] else "- **扩展类型**：`-`（普通容器组件）")
            lines.append(f"- **锚点**：`{comp['pivot']}`" if comp['pivot'] else "- **锚点**：`-`")

            if comp['controllers']:
                ctrl_strs = []
                for c in comp['controllers']:
                    pages_str = ', '.join(c['pages']) if c['pages'] else '-'
                    ctrl_strs.append(f"`{c['name']}`: {pages_str}")
                lines.append(f"- **控制器**：{' | '.join(ctrl_strs)}")
            else:
                lines.append("- **控制器**：`-`")

            lines.append(f"- **用途说明**：{comp['usage']}")

            # 引用方式
            file_name = full_path if comp['path'] and comp['path'] != '/' else comp['name']
            lines.append("- **引用方式**：")
            lines.append("  ```xml")
            lines.append(f'  <component src="{comp["id"]}" fileName="{file_name}"')
            lines.append(f'             xy="{{x}},{{y}}" size="{comp["size"] if comp["size"] else "{w},{h}"}" />')
            lines.append("  ```\n")

    # 导出图片资源
    if pkg['exported_images']:
        lines.append("---\n")
        lines.append("## 导出图片资源\n")
        lines.append("| 资源名 | ID | 路径 | 九宫格参数 | 用途 |")
        lines.append("|--------|----|------|-----------|------|")
        for img in pkg['exported_images']:
            sg = f"`{img['scale9grid']}`" if img['scale9grid'] else "`-`"
            lines.append(f"| `{img['name']}` | `{img['id']}` | `{img['path']}` | {sg} | {img['usage']} |")
        lines.append("")

    # 字体资源
    if pkg['fonts']:
        lines.append("---\n")
        lines.append("## 字体资源\n")
        lines.append("| 字体名 | ID | 路径 |")
        lines.append("|--------|----|------|")
        for fnt in pkg['fonts']:
            lines.append(f"| `{fnt['name']}` | `{fnt['id']}` | `{fnt['path']}` |")
        lines.append("")

    # 复用建议
    lines.append("---\n")
    lines.append("## 复用建议\n")

    if name.lower() == 'common':
        lines.append("- **何时引用此 Package**：所有新 Package 均应优先检索 Common，用于获取通用弹窗框架、按钮、遮罩层、红点等基础组件。")
        lines.append("- **优先使用组件**：`AlertView`、`WindowMask`、`CommonButton` 系列、`RedDot`、`ModalWaiting`、`Holder`")
        lines.append("- **注意事项**：引用 Common 组件时，需在新 Package 的 `package.xml` 中声明 `<publish dependencies=\"yez16kc6\"/>`")
    elif pkg['exported_components']:
        top_names = [c['name'].replace('.xml', '') for c in pkg['exported_components'][:3]]
        lines.append(f"- **何时引用此 Package**：开发 {pkg['purpose']} 相关新界面时，参考此包中的现有组件和规范。")
        lines.append(f"- **优先使用组件**：`{'`, `'.join(top_names)}`")
        if pkg['package_id']:
            lines.append(f"- **注意事项**：引用此包组件时，需在新 Package 中声明 `<publish dependencies=\"{pkg['package_id']}\"/>`")
    else:
        lines.append("- **何时引用此 Package**：开发同类功能时，可参考此包的 UI 规范和组件设计。")
        lines.append("- **注意事项**：此包中无导出组件，不建议跨包引用。")
    lines.append("")

    # 跨包依赖
    if pkg['dependencies']:
        lines.append("---\n")
        lines.append("## 跨包依赖\n")
        lines.append(f"此包在 `package.xml` 中声明了对以下 Package 的依赖：\n")
        lines.append("| 依赖包 ID | 说明 |")
        lines.append("|---------|------|")
        for dep_id in pkg['dependencies']:
            lines.append(f"| `{dep_id}` | 引用了该包的导出资源 |")
        lines.append("")

    return '\n'.join(lines)


def generate_index_markdown(all_packages: list, assets_dir: Path) -> str:
    """生成所有 Package 的汇总索引文件。"""
    today = date.today().isoformat()
    lines = []
    lines.append("# FairyGUI 工程 Package 索引\n")
    lines.append(f"> 最后更新：{today}")
    lines.append(f"> 工程路径：`{assets_dir}`\n")
    lines.append("---\n")
    lines.append("## Package 快速检索表\n")
    lines.append("| Package | 包 ID | 用途 | 复用程度 | 导出组件数 |")
    lines.append("|---------|-------|------|---------|-----------|")

    for pkg in sorted(all_packages, key=lambda p: (p.get('reusability', '') != '高（全局通用基础组件库）', p['package_name'])):
        exported = len(pkg.get('exported_components', []))
        reuse = pkg.get('reusability', '-')
        purpose = pkg.get('purpose', '-')
        # 缩短用途描述
        if len(purpose) > 20:
            purpose = purpose[:18] + '…'
        lines.append(f"| {pkg['package_name']} | `{pkg['package_id']}` | {purpose} | {reuse} | {exported} |")
    lines.append("")

    # 蓝湖设计快速复用指引（Common 包关键组件）
    common_pkg = next((p for p in all_packages if p['package_name'].lower() == 'common'), None)
    if common_pkg:
        lines.append("---\n")
        lines.append("## 蓝湖设计解析快速复用指引\n")
        lines.append("解析新蓝湖设计稿生成 FairyGUI 工程时，以下元素**优先复用** Common 包组件：\n")
        lines.append("| 设计元素 | 推荐复用组件 | 包 | 资源 ID |")
        lines.append("|---------|-----------|-----|--------|")

        # 从 Common 导出组件中提取常见的可复用条目
        component_map = {c['name'].replace('.xml', ''): c['id'] for c in common_pkg.get('exported_components', [])}
        quick_map = [
            ("全屏半透明遮罩", "WindowMask", "Common"),
            ("全屏加载等待", "ModalWaiting", "Common"),
            ("小型加载等待", "LoadWaiting", "Common"),
            ("通用确认/取消弹窗", "AlertView", "Common"),
            ("确认主按钮（橙色）", "BCommonConfirmBtn", "Common/new/Button"),
            ("取消次按钮", "BCommonCanelBtn", "Common/new/Button"),
            ("通用图标按钮", "CommonButton", "Common/button"),
            ("标签页/切换按钮", "TabButton1", "Common/button"),
            ("切换开关按钮", "CommonBtnSwitch", "Common/button"),
            ("红点角标提示", "RedDot", "Common/reddot"),
            ("Spine 动画占位", "SpineAni", "Common"),
            ("内容占位容器", "Holder", "Common"),
            ("通用列表项格子", "Item", "Common"),
            ("复选框", "CheckBox_2", "Common/checkbox"),
        ]
        for desc, comp_key, loc in quick_map:
            comp_id = component_map.get(comp_key, '查 Common.md')
            lines.append(f"| {desc} | `{comp_key}.xml` | {loc} | `{comp_id}` |")
        lines.append("")

    # 各包记忆文件链接
    lines.append("---\n")
    lines.append("## 各包详细记忆文件\n")
    for pkg in sorted(all_packages, key=lambda p: p['package_name']):
        reuse_short = pkg.get('reusability', '-').split('（')[0]
        lines.append(f"- [{pkg['package_name']}.md]({pkg['package_name']}.md) — {pkg.get('purpose', '')[:30]}…（{reuse_short}）")
    lines.append("")

    return '\n'.join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# 主程序
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='FairyGUI Package 批量分析器 - 生成结构化记忆文件'
    )
    parser.add_argument(
        '--assets',
        default='data/uiProject/assets',
        help='FairyGUI assets 目录路径（默认：data/uiProject/assets）'
    )
    parser.add_argument(
        '--output',
        default='memories/repo/fairygui-packages',
        help='记忆文件输出目录（默认：memories/repo/fairygui-packages）'
    )
    parser.add_argument(
        '--package',
        default=None,
        help='只分析指定 Package 名称（不指定则分析全部）'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='同时生成 JSON 格式的记忆文件'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='显示详细的分析日志'
    )
    args = parser.parse_args()

    # 解析路径（相对于脚本所在目录的父目录，即项目根目录）
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    assets_dir = (project_root / args.assets).resolve()
    output_dir = (project_root / args.output).resolve()

    if not assets_dir.exists():
        print(f"[ERROR] assets 目录不存在: {assets_dir}", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # 确定要分析的 Package 列表
    if args.package:
        package_names = [args.package]
    else:
        package_names = [
            d.name for d in sorted(assets_dir.iterdir())
            if d.is_dir() and (d / 'package.xml').exists()
        ]

    print(f"[INFO] 发现 {len(package_names)} 个 Package 待分析")
    print(f"[INFO] 输出目录：{output_dir}\n")

    all_packages = []

    for pkg_name in package_names:
        print(f"  → 分析 {pkg_name} ...", end='', flush=True)
        pkg_data = analyze_package(assets_dir, pkg_name)

        if not pkg_data:
            print(f" [跳过，无有效数据]")
            continue

        exported_comp_count = len(pkg_data.get('exported_components', []))
        exported_img_count = len(pkg_data.get('exported_images', []))

        if args.verbose:
            print(f"\n     包 ID: {pkg_data['package_id']}")
            print(f"     导出组件: {exported_comp_count} | 导出图片: {exported_img_count}")
        else:
            print(f" 组件={exported_comp_count}, 图片={exported_img_count}", end='')

        # 写入 Markdown 记忆文件
        md_content = generate_package_markdown(pkg_data)
        md_path = output_dir / f"{pkg_name}.md"
        md_path.write_text(md_content, encoding='utf-8')

        # 写入 JSON 格式（可选）
        if args.json:
            json_path = output_dir / f"{pkg_name}.json"
            json_path.write_text(
                json.dumps(pkg_data, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )

        print(f" [OK]")
        all_packages.append(pkg_data)

    # 生成汇总索引
    if all_packages and not args.package:
        print(f"\n[INFO] 生成 INDEX.md ...")
        index_content = generate_index_markdown(all_packages, assets_dir)
        (output_dir / 'INDEX.md').write_text(index_content, encoding='utf-8')
        print(f"[INFO] 生成完成！共处理 {len(all_packages)} 个 Package")
    elif args.package and all_packages:
        print(f"\n[INFO] Package '{args.package}' 分析完成：{output_dir / args.package}.md")
    else:
        print(f"\n[WARN] 未找到任何有效 Package")

    print(f"\n输出目录：{output_dir}")


if __name__ == '__main__':
    main()
