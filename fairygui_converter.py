#!/usr/bin/env python3
"""
FairyGUI 6.x 工程生成器

蓝湖设计稿（Lanhu Schema JSON / Sketch JSON）→ FairyGUI 编辑器工程
目标：FairyGUI 6.1.3 + Laya 3.x

生成目录结构：
    {output_dir}/
    ├── {design_name}.fairy           # 项目入口（type="laya3"）
    ├── UI/
    │   ├── package.xml               # 包描述符（含资源列表）
    │   ├── {design_name}.xml         # 主组件 XML
    │   └── res/                      # 图片资源目录（待下载填充）
    └── settings/
        ├── BuildTargets.xml          # Laya 3.x 发布配置
        └── GlobalRelations.xml       # 空关系表
"""

import re
import uuid
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional


# ──────────────────────────────────────────────────────────────────────────────
# 1. 颜色工具
# ──────────────────────────────────────────────────────────────────────────────

def rgba_to_fairygui(css_color: str) -> Optional[str]:
    """
    将 CSS 颜色字符串转换为 FairyGUI #AARRGGBB 格式。

    支持：
      rgba(r, g, b, a)  →  #AARRGGBB（a=1 时省略 AA → #RRGGBB）
      rgb(r, g, b)      →  #RRGGBB
      #rrggbb           →  #RRGGBB（直通，大写）
      #aarrggbb         →  #AARRGGBB（直通，大写）

    返回 None 表示无效输入。
    """
    if not css_color:
        return None
    css_color = str(css_color).strip()

    # rgba(r, g, b, a)
    m = re.match(
        r'rgba\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\)',
        css_color, re.I
    )
    if m:
        r = max(0, min(255, int(round(float(m.group(1))))))
        g = max(0, min(255, int(round(float(m.group(2))))))
        b = max(0, min(255, int(round(float(m.group(3))))))
        a = max(0.0, min(1.0, float(m.group(4))))
        aa = int(round(a * 255))
        if aa == 255:
            return f'#{r:02X}{g:02X}{b:02X}'
        return f'#{aa:02X}{r:02X}{g:02X}{b:02X}'

    # rgb(r, g, b)
    m = re.match(r'rgb\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\)', css_color, re.I)
    if m:
        r = max(0, min(255, int(round(float(m.group(1))))))
        g = max(0, min(255, int(round(float(m.group(2))))))
        b = max(0, min(255, int(round(float(m.group(3))))))
        return f'#{r:02X}{g:02X}{b:02X}'

    # #rrggbb 或 #aarrggbb
    m = re.match(r'^#([0-9a-fA-F]{6}|[0-9a-fA-F]{8})$', css_color)
    if m:
        return '#' + m.group(1).upper()

    return None


# ──────────────────────────────────────────────────────────────────────────────
# 2. ID 生成器
# ──────────────────────────────────────────────────────────────────────────────

class NodeIdGenerator:
    """全局递增 ID 生成器，输出 n1, n2, n3..."""
    def __init__(self):
        self._counter = 0

    def next(self) -> str:
        self._counter += 1
        return f'n{self._counter}'


# ──────────────────────────────────────────────────────────────────────────────
# 3. CSS 值解析工具
# ──────────────────────────────────────────────────────────────────────────────

def _parse_numeric(value, default: float = 0.0) -> float:
    """从 CSS 值（如 '24px', '1.5', 24）中提取数字。"""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    s = re.sub(r'(px|em|rem|%|pt|vw|vh)$', '', s)
    try:
        return float(s)
    except ValueError:
        return default


def _merge_style(node: dict) -> dict:
    """合并节点的 style 与 props.style，props.style 优先。"""
    base = dict(node.get('style') or {})
    props_style = (node.get('props') or {}).get('style') or {}
    base.update(props_style)
    # alignJustify 合并
    aj = node.get('alignJustify') or {}
    if aj.get('justifyContent') and 'justifyContent' not in base:
        base['justifyContent'] = aj['justifyContent']
    if aj.get('alignItems') and 'alignItems' not in base:
        base['alignItems'] = aj['alignItems']
    return base


def _is_flex(style: dict) -> bool:
    return style.get('display') == 'flex' or style.get('flexDirection') is not None


def _get_loop_arr(node: dict) -> list:
    if not node:
        return []
    arr = node.get('loop') or node.get('loopData')
    return arr if isinstance(arr, list) else []


def _xml_escape(s: str) -> str:
    """转义 XML attribute 特殊字符。"""
    if not s:
        return ''
    return (str(s)
            .replace('&', '&amp;')
            .replace('"', '&quot;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace("'", '&apos;'))


def _sanitize_name(name: str) -> str:
    """将 CSS 类名转为合法的 FairyGUI 组件/元素名。"""
    if not name:
        return 'item'
    # 去掉循环后缀 -0/-1/...
    name = re.sub(r'-\d+$', '', name)
    # 替换非字母数字下划线字符为下划线
    return re.sub(r'[^a-zA-Z0-9_]', '_', name) or 'item'


def _resolve_loop_placeholder(value: str, loop_item: dict) -> str:
    """this.item.xxx → loop_item.get('xxx', '')"""
    if not value or not isinstance(loop_item, dict):
        return value or ''
    s = str(value).strip()
    m = re.match(r'^this\.item\.(\w+)$', s)
    return str(loop_item.get(m.group(1), '')) if m else value


# ──────────────────────────────────────────────────────────────────────────────
# 4. Lanhu Schema → FairyGUI XML 节点（递归）
# ──────────────────────────────────────────────────────────────────────────────

def _build_items_from_lanhu(
    node: dict,
    id_gen: NodeIdGenerator,
    res_list: list,
    indent: int = 4,
    loop_context: tuple = None,
) -> str:
    """
    递归将 Lanhu Schema 节点转换为 FairyGUI displayList XML 子节点字符串。

    Args:
        node:         Lanhu Schema 节点
        id_gen:       全局 ID 生成器
        res_list:     图片资源列表（out 参数，追加）
        indent:       当前缩进空格数
        loop_context: 循环上下文 (loop_arr, current_index)

    Returns:
        XML 字符串片段
    """
    if not node:
        return ''

    sp = ' ' * indent

    loop_item = loop_context[0][loop_context[1]] if loop_context else None
    loop_index = loop_context[1] if loop_context else None

    props = node.get('props') or {}
    class_name = props.get('className', '')
    if loop_index is not None and class_name:
        class_name = f'{class_name}_{loop_index}'

    el_id = id_gen.next()
    el_name = _sanitize_name(class_name) or el_id

    style = _merge_style(node)

    # 解析位置和尺寸
    x = _parse_numeric(style.get('left') or style.get('marginLeft'), 0)
    y = _parse_numeric(style.get('top') or style.get('marginTop'), 0)
    w = _parse_numeric(style.get('width'), 0)
    h = _parse_numeric(style.get('height'), 0)

    # 透明度
    opacity_val = style.get('opacity')
    alpha_str = ''
    if opacity_val is not None:
        a = _parse_numeric(opacity_val, 1.0)
        if a < 0.999:
            alpha_str = f' alpha="{round(a, 4)}"'

    node_type = node.get('type', 'div')
    children = node.get('children') or []

    # ── lanhutext ──
    if node_type == 'lanhutext':
        text = node.get('data', {}).get('value') or props.get('text') or ''
        if loop_item is not None and re.match(r'^this\.item\.\w+$', str(text).strip()):
            text = _resolve_loop_placeholder(str(text), loop_item)
        elif re.match(r'^this\.item\.\w+$', str(text or '').strip()):
            text = ''

        font_size = max(1, int(_parse_numeric(style.get('fontSize'), 14)))
        color = rgba_to_fairygui(str(style.get('color', ''))) or '#333333'
        fw_raw = str(style.get('fontWeight', '')).lower()
        bold = fw_raw in ('bold', '700', '800', '900') or (fw_raw.isdigit() and int(fw_raw) >= 700)
        align_raw = str(style.get('textAlign') or style.get('align', '')).lower()
        align_map_fgui = {'left': 'left', 'center': 'center', 'right': 'right', 'justify': 'left'}
        fg_align = align_map_fgui.get(align_raw, '')

        attrs = f'id="{el_id}" name="{el_name}"'
        if w > 0 or h > 0:
            attrs += f' xy="{int(x)},{int(y)}" size="{int(w)},{int(h)}"'
        else:
            attrs += f' xy="{int(x)},{int(y)}"'
        attrs += f' text="{_xml_escape(str(text))}"'
        attrs += f' fontSize="{font_size}" color="{color}"'
        if bold:
            attrs += ' bold="true"'
        if fg_align and fg_align != 'left':
            attrs += f' align="{fg_align}"'
        attrs += ' autoSize="none"'
        if alpha_str:
            attrs += alpha_str

        text_str = str(text)
        if '\n' in text_str or '\r' in text_str or (h > 0 and font_size > 0 and h > font_size * 1.8):
            attrs += ' singleLine="false"'

        return f'{sp}<text {attrs}/>'

    # ── lanhuimage ──
    if node_type == 'lanhuimage':
        src = node.get('data', {}).get('value') or props.get('src') or ''
        if loop_item is not None and re.match(r'^this\.item\.\w+$', str(src).strip()):
            src = _resolve_loop_placeholder(str(src), loop_item)
        elif re.match(r'^this\.item\.\w+$', str(src or '').strip()):
            src = ''

        file_name_attr = ''
        if src:
            ext = _guess_ext(src)
            res_name = f'{el_name}{ext}'
            local_res_path = f'res/{res_name}'
            existing_paths = {r['local_path'] for r in res_list}
            if local_res_path in existing_paths:
                res_name = f'{el_name}_{el_id}{ext}'
                local_res_path = f'res/{res_name}'
            res_list.append({
                'id': id_gen.next(),
                'name': re.sub(r'\.[^.]+$', '', res_name),
                'local_path': local_res_path,
                'remote_url': src,
                'size': f'{int(w)},{int(h)}' if w and h else '',
            })
            file_name_attr = f' fileName="{local_res_path}"'

        attrs = f'id="{el_id}" name="{el_name}" xy="{int(x)},{int(y)}" size="{int(w)},{int(h)}"'
        if file_name_attr:
            attrs += file_name_attr
        if alpha_str:
            attrs += alpha_str
        return f'{sp}<image {attrs}/>'

    # ── lanhubutton ──
    if node_type == 'lanhubutton':
        title = ''
        for c in children:
            if c and c.get('type') == 'lanhutext':
                title = (
                    c.get('data', {}).get('value')
                    or (c.get('props') or {}).get('text')
                    or ''
                )
                break

        attrs = f'id="{el_id}" name="{el_name}" xy="{int(x)},{int(y)}" size="{int(w)},{int(h)}"'
        attrs += f' title="{_xml_escape(str(title))}"'
        if alpha_str:
            attrs += alpha_str
        return f'{sp}<button {attrs}/>'

    # ── div / container ──
    # 循环展开
    loop_arr = _get_loop_arr(node) if node.get('loopType') else []
    if loop_arr and loop_context is None:
        parts = []
        for i in range(len(loop_arr)):
            ctx = (loop_arr, i)
            loop_el_id = id_gen.next()
            loop_el_name = f'{el_name}_{i}'
            inner = '\n'.join(
                _build_items_from_lanhu(c, id_gen, res_list, indent + 4, ctx)
                for c in children if c
            )
            gap_x = int(w) + 4
            loop_attrs = (
                f'id="{loop_el_id}" name="{loop_el_name}"'
                f' xy="{int(x) + i * gap_x},{int(y)}" size="{int(w)},{int(h)}"'
                ' overflow="visible"'
            )
            parts.append(
                f'{sp}<component {loop_attrs}>\n'
                f'{sp}  <displayList>\n'
                f'{inner}\n'
                f'{sp}  </displayList>\n'
                f'{sp}</component>'
            )
        return '\n'.join(parts)

    # 普通容器：递归子节点
    children_xml = '\n'.join(
        _build_items_from_lanhu(c, id_gen, res_list, indent + 4, loop_context)
        for c in children if c
    )

    overflow_val = str(style.get('overflow', '')).lower()
    overflow_attr = ' overflow="hidden"' if overflow_val == 'hidden' else ' overflow="visible"'

    # 背景色
    bg_attr = ''
    bg_raw = str(style.get('backgroundColor') or style.get('background') or '')
    if bg_raw:
        fg_bg = rgba_to_fairygui(bg_raw)
        if fg_bg:
            bg_attr = f' opaque="true" color="{fg_bg}"'

    component_attrs = (
        f'id="{el_id}" name="{el_name}"'
        f' xy="{int(x)},{int(y)}" size="{int(w)},{int(h)}"'
        f'{overflow_attr}{bg_attr}'
    )
    if alpha_str:
        component_attrs += alpha_str

    lines = [f'{sp}<component {component_attrs}>']
    lines.append(f'{sp}  <displayList>')
    if children_xml.strip():
        lines.append(children_xml)
    lines.append(f'{sp}  </displayList>')

    # Flex → Flow Controller
    if _is_flex(style) and children:
        flex_dir = str(style.get('flexDirection', 'row')).lower()
        axis = 'y' if flex_dir == 'column' else 'x'
        justify = str(style.get('justifyContent', 'flex-start')).lower()
        align_items = str(style.get('alignItems', 'flex-start')).lower()
        gap_val = int(_parse_numeric(
            style.get('gap') or style.get('columnGap') or style.get('rowGap'), 0
        ))

        j_map = {
            'flex-start': 'left', 'flex-end': 'right', 'center': 'center',
            'space-between': 'space-between', 'space-around': 'space-around',
            'space-evenly': 'space-evenly',
        }
        a_map = {'flex-start': 'top', 'flex-end': 'bottom', 'center': 'center'}
        fg_justify = j_map.get(justify, 'left')
        fg_align_items = a_map.get(align_items, 'top')

        lines.append(f'{sp}  <controller name="layout" type="flow">')
        lines.append(f'{sp}    <axis value="{axis}"/>')
        if gap_val:
            lines.append(f'{sp}    <gap value="{gap_val}"/>')
        if axis == 'x':
            lines.append(f'{sp}    <alignH value="{fg_justify}"/>')
            lines.append(f'{sp}    <alignV value="{fg_align_items}"/>')
        else:
            lines.append(f'{sp}    <alignH value="{fg_align_items}"/>')
            lines.append(f'{sp}    <alignV value="{fg_justify}"/>')
        lines.append(f'{sp}  </controller>')

    lines.append(f'{sp}</component>')
    return '\n'.join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# 5. Sketch JSON → FairyGUI XML 节点（递归，fallback 路径）
# ──────────────────────────────────────────────────────────────────────────────

def _build_items_from_sketch(
    layer: dict,
    id_gen: NodeIdGenerator,
    res_list: list,
    scale: float,
    indent: int = 4,
) -> str:
    """
    递归将 Sketch/Figma layer 转为 FairyGUI displayList XML 子节点字符串。
    """
    if not layer or not isinstance(layer, dict):
        return ''
    if layer.get('visible') is False:
        return ''

    sp = ' ' * indent

    def px(v):
        if v is None:
            return 0.0
        return round(float(v) / scale * 10) / 10

    lframe = layer.get('frame') or layer.get('realFrame') or {}
    x = px(lframe.get('x', lframe.get('left', layer.get('left', 0))))
    y = px(lframe.get('y', lframe.get('top', layer.get('top', 0))))
    w = px(lframe.get('width', layer.get('width', 0)))
    h = px(lframe.get('height', layer.get('height', 0)))

    el_id = id_gen.next()
    el_name = _sanitize_name(layer.get('name', '')) or el_id

    xy_attr = f'xy="{int(x)},{int(y)}"'
    size_attr = f'size="{int(w)},{int(h)}"'

    ltype = str(layer.get('type', '')).lower()

    # 透明度
    blend = layer.get('blendOptions') or {}
    op = blend.get('opacity')
    op_val = (op.get('value', 100) if isinstance(op, dict) else op) if op is not None else 100
    alpha_str = ''
    if float(op_val) < 99.9:
        alpha_str = f' alpha="{round(float(op_val) / 100, 4)}"'

    # ── 文字层 ──
    text_obj = layer.get('textInfo') or layer.get('text') or None
    is_text_layer = ltype in ('textlayer', 'text') or (
        text_obj and ltype not in ('group', 'layersection', 'symbolinstence', 'artboard')
    )
    if is_text_layer and text_obj:
        text_content = ''
        font_size = 14
        color_str = '#333333'
        bold = False
        align_str = 'left'

        if isinstance(text_obj, dict) and 'value' in text_obj:
            # artboard 格式
            text_content = str(text_obj.get('value', ''))
            art_style = text_obj.get('style', {})
            art_font = art_style.get('font') or {}
            font_size = max(1, int(round(px(art_font.get('size', 14)))))
            art_color = art_style.get('color') or {}
            if isinstance(art_color, dict) and 'value' in art_color:
                color_str = rgba_to_fairygui(art_color['value']) or '#333333'
            fw = art_font.get('fontWeight', 0)
            bold = int(fw) >= 700 if fw else False
            align_str = str(art_font.get('align', 'left')).lower()
        elif isinstance(text_obj, dict):
            # board 格式 textInfo
            text_content = str(text_obj.get('text', ''))
            font_size = max(1, int(round(px(text_obj.get('size', 14)))))
            color_data = text_obj.get('color') or {}
            if isinstance(color_data, dict) and 'value' in color_data:
                color_str = rgba_to_fairygui(color_data['value']) or '#333333'
            font_style = str(text_obj.get('fontStyleName', '')).lower()
            bold = 'bold' in font_style or bool(text_obj.get('bold'))
            align_str = str(text_obj.get('justification', 'left')).lower()

        attrs = f'id="{el_id}" name="{el_name}" {xy_attr} {size_attr}'
        attrs += f' text="{_xml_escape(text_content)}"'
        attrs += f' fontSize="{font_size}" color="{color_str}"'
        if bold:
            attrs += ' bold="true"'
        if align_str and align_str != 'left':
            attrs += f' align="{align_str}"'
        attrs += ' autoSize="none"'
        if alpha_str:
            attrs += alpha_str
        return f'{sp}<text {attrs}/>'

    # ── 切图/图片层 ──
    images = layer.get('images') or {}
    slice_url = images.get('png_xxxhd') or images.get('svg') or ''

    if ltype in ('layersection', 'symbolinstence') and not slice_url:
        # 有子层但无切图 → 递归为 component
        pass
    elif slice_url:
        ext = '.svg' if slice_url.lower().endswith('.svg') else '.png'
        res_name = f'{el_name}{ext}'
        local_res_path = f'res/{res_name}'
        existing_paths = {r['local_path'] for r in res_list}
        if local_res_path in existing_paths:
            res_name = f'{el_name}_{el_id}{ext}'
            local_res_path = f'res/{res_name}'

        res_list.append({
            'id': id_gen.next(),
            'name': re.sub(r'\.[^.]+$', '', res_name),
            'local_path': local_res_path,
            'remote_url': slice_url,
            'size': f'{int(w)},{int(h)}',
        })
        attrs = f'id="{el_id}" name="{el_name}" {xy_attr} {size_attr} fileName="{local_res_path}"'
        if alpha_str:
            attrs += alpha_str
        return f'{sp}<image {attrs}/>'

    # ── 分组/容器层 → 递归 ──
    sub_layers = layer.get('layers') or []
    if not sub_layers:
        # 叶子节点但无可识别内容 → skip
        return ''

    children_xml = '\n'.join(
        _build_items_from_sketch(c, id_gen, res_list, scale, indent + 4)
        for c in sub_layers if c
    )

    attrs = f'id="{el_id}" name="{el_name}" {xy_attr} {size_attr} overflow="visible"'
    if alpha_str:
        attrs += alpha_str

    lines = [
        f'{sp}<component {attrs}>',
        f'{sp}  <displayList>',
    ]
    if children_xml.strip():
        lines.append(children_xml)
    lines += [f'{sp}  </displayList>', f'{sp}</component>']
    return '\n'.join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# 6. 根节点尺寸提取
# ──────────────────────────────────────────────────────────────────────────────

def _get_root_size_from_lanhu(json_data: dict) -> tuple:
    style = _merge_style(json_data)
    w = int(_parse_numeric(style.get('width'), 375))
    h = int(_parse_numeric(style.get('height'), 812))
    return w, h


def _get_root_size_from_sketch(sketch_data: dict, scale: float) -> tuple:
    def px(v):
        return round(float(v) / scale * 10) / 10 if v is not None else 0

    if 'artboard' in sketch_data:
        art = sketch_data['artboard']
        f = art.get('frame') or art.get('realFrame') or {}
        return int(px(f.get('width', 750))), int(px(f.get('height', 1334)))
    if 'board' in sketch_data:
        b = sketch_data['board']
        return int(px(b.get('width', 750))), int(px(b.get('height', 1334)))
    return 375, 812


# ──────────────────────────────────────────────────────────────────────────────
# 7. 资源文件扩展名推断
# ──────────────────────────────────────────────────────────────────────────────

def _guess_ext(url: str) -> str:
    path = url.split('?')[0].split('/')[-1]
    if '.' in path:
        raw = '.' + path.rsplit('.', 1)[-1].lower()
        if raw in ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'):
            return raw
    return '.png'


# ──────────────────────────────────────────────────────────────────────────────
# 8. XML 文件生成器
# ──────────────────────────────────────────────────────────────────────────────

def build_component_xml(display_list_xml: str, comp_w: int, comp_h: int) -> str:
    """生成 FairyGUI 6.x 组件 XML 文件内容。"""
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<component size="{comp_w},{comp_h}" overflow="visible">\n'
        '  <displayList>\n'
        f'{display_list_xml}\n'
        '  </displayList>\n'
        '</component>\n'
    )


def build_package_xml(package_id: str, resources: list) -> str:
    """
    生成 FairyGUI 6.x UI/package.xml。

    resources: list of dict:
      image:     {type:'image', id, name, local_path, size}
      component: {type:'component', id, name, local_path}
    """
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        f'<packageDescription id="{package_id}">',
        '  <resources>',
    ]
    for r in resources:
        if r.get('type') == 'image':
            size_part = f' size="{r["size"]}"' if r.get('size') else ''
            lines.append(
                f'    <image id="{r["id"]}" name="{r["name"]}"'
                f' path="{r["local_path"]}"{size_part} scale="none"/>'
            )
        else:
            lines.append(
                f'    <component id="{r["id"]}" name="{r["name"]}"'
                f' path="{r["name"]}"/>'
            )
    lines += ['  </resources>', '</packageDescription>', '']
    return '\n'.join(lines)


def build_fairy_project_file(project_name: str) -> str:
    """生成 FairyGUI 6.x .fairy 项目入口文件（Laya 3.x 类型）。"""
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<project type="laya3">\n'
        '  <packageNames>\n'
        '    <item name="UI" path="UI/"/>\n'
        '  </packageNames>\n'
        '</project>\n'
    )


def build_targets_xml() -> str:
    """生成 settings/BuildTargets.xml（Laya 3.x）。"""
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<targets>\n'
        '  <target name="Laya3">\n'
        '    <platform value="laya3"/>\n'
        '    <outputCodeType value="ts"/>\n'
        '    <binderClass value="UIPackage_binder"/>\n'
        '    <codePackage value=""/>\n'
        '  </target>\n'
        '</targets>\n'
    )


def build_global_relations_xml() -> str:
    """生成空的 settings/GlobalRelations.xml。"""
    return '<?xml version="1.0" encoding="utf-8"?>\n<relations/>\n'


# ──────────────────────────────────────────────────────────────────────────────
# 9. 写文件辅助
# ──────────────────────────────────────────────────────────────────────────────

def _write_file(path: Path, content: str, files_created: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    files_created.append(str(path))


# ──────────────────────────────────────────────────────────────────────────────
# 10. 主入口：Lanhu Schema → FairyGUI 工程
# ──────────────────────────────────────────────────────────────────────────────

def convert_lanhu_to_fairygui_project(
    json_data: dict,
    design_name: str,
    output_dir,
    image_url_mapping: dict = None,
) -> dict:
    """
    将蓝湖 Lanhu Schema JSON 转换为 FairyGUI 6.1.3 编辑器工程（Laya 3.x）。

    Args:
        json_data:         蓝湖 Schema JSON（与 convert_lanhu_to_html() 输入相同）
        design_name:       设计图名称（如 "首页_首屏"）
        output_dir:        输出根目录（Path 或 str）
        image_url_mapping: {local_path: remote_url} 图片映射（可选）

    Returns:
        {
          'status':           'success' | 'error',
          'files_created':    [str, ...],      所有已写入的文件绝对路径
          'res_download_map': {local: remote}, 待下载资源映射
          'component_name':   str,
          'component_size':   str,             '375,812'
          'image_count':      int,
          'error':            str,             仅 error 时存在
        }
    """
    try:
        output_dir = Path(output_dir)
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', design_name)
        comp_name = safe_name

        id_gen = NodeIdGenerator()
        res_list: list = []

        comp_w, comp_h = _get_root_size_from_lanhu(json_data)

        # 根节点本身是容器，直接展开其 children
        root_children = json_data.get('children') or [json_data]
        display_items = '\n'.join(
            _build_items_from_lanhu(child, id_gen, res_list, indent=4)
            for child in root_children if child
        )

        component_xml = build_component_xml(display_items, comp_w, comp_h)

        # 将 image_url_mapping 中额外资源合并进 res_list
        if image_url_mapping:
            existing_remotes = {r['remote_url'] for r in res_list}
            for local_path, remote_url in image_url_mapping.items():
                if remote_url not in existing_remotes:
                    fname = Path(local_path).name
                    res_name_no_ext = re.sub(r'\.[^.]+$', '', fname)
                    res_local = f'res/{fname}'
                    res_list.append({
                        'id': id_gen.next(),
                        'name': res_name_no_ext,
                        'local_path': res_local,
                        'remote_url': remote_url,
                        'size': '',
                    })

        package_id = uuid.uuid4().hex[:8]

        pkg_resources = [
            {
                'type': 'image',
                'id': r['id'],
                'name': r['name'],
                'local_path': r['local_path'],
                'size': r.get('size', ''),
            }
            for r in res_list
        ]
        pkg_resources.append({
            'type': 'component',
            'id': id_gen.next(),
            'name': comp_name,
            'local_path': comp_name,
        })

        files_created: list = []
        _write_file(output_dir / f'{safe_name}.fairy', build_fairy_project_file(comp_name), files_created)
        _write_file(output_dir / 'UI' / 'package.xml', build_package_xml(package_id, pkg_resources), files_created)
        _write_file(output_dir / 'UI' / f'{comp_name}.xml', component_xml, files_created)
        _write_file(output_dir / 'settings' / 'BuildTargets.xml', build_targets_xml(), files_created)
        _write_file(output_dir / 'settings' / 'GlobalRelations.xml', build_global_relations_xml(), files_created)
        (output_dir / 'UI' / 'res').mkdir(parents=True, exist_ok=True)

        res_download_map = {
            str(output_dir / 'UI' / r['local_path']): r['remote_url']
            for r in res_list if r.get('remote_url')
        }

        return {
            'status': 'success',
            'files_created': files_created,
            'res_download_map': res_download_map,
            'component_name': comp_name,
            'component_size': f'{comp_w},{comp_h}',
            'image_count': len(res_list),
        }

    except Exception as e:
        import traceback
        return {
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc(),
        }


# ──────────────────────────────────────────────────────────────────────────────
# 11. 主入口：Sketch JSON → FairyGUI 工程（fallback）
# ──────────────────────────────────────────────────────────────────────────────

def convert_sketch_to_fairygui_project(
    sketch_data: dict,
    design_name: str,
    output_dir,
    design_img_url: str = '',
) -> dict:
    """
    将蓝湖 Sketch/Figma JSON 转换为 FairyGUI 6.1.3 编辑器工程（Laya 3.x）。
    这是 Lanhu Schema 路径不可用时的 fallback。

    Args:
        sketch_data:    原始 Sketch JSON（与 convert_sketch_to_html() 输入相同）
        design_name:    设计图名称
        output_dir:     输出根目录
        design_img_url: 设计图原图 URL（可选，作为背景图资源）

    Returns: 同 convert_lanhu_to_fairygui_project
    """
    try:
        output_dir = Path(output_dir)
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', design_name)
        comp_name = safe_name

        device_str = sketch_data.get('device', '')
        scale = 3.0 if '@3x' in device_str else (1.0 if '@1x' in device_str else 2.0)

        id_gen = NodeIdGenerator()
        res_list: list = []

        comp_w, comp_h = _get_root_size_from_sketch(sketch_data, scale)

        raw_layers: list = []
        if 'artboard' in sketch_data:
            raw_layers = sketch_data['artboard'].get('layers', [])
        elif 'board' in sketch_data:
            raw_layers = sketch_data['board'].get('layers', [])

        # reversed：底层先渲染，与 convert_sketch_to_html 保持一致
        display_items = '\n'.join(
            _build_items_from_sketch(layer, id_gen, res_list, scale, indent=4)
            for layer in reversed(raw_layers) if layer
        )

        # 若有设计原图，在 displayList 最前插入背景 image
        if design_img_url:
            bg_res_id = id_gen.next()
            bg_el_id = id_gen.next()
            bg_local = 'res/design_bg.png'
            res_list.append({
                'id': bg_res_id,
                'name': 'design_bg',
                'local_path': bg_local,
                'remote_url': design_img_url.split('?')[0],
                'size': f'{comp_w},{comp_h}',
            })
            bg_item = (
                f'    <image id="{bg_el_id}" name="design_bg"'
                f' xy="0,0" size="{comp_w},{comp_h}" fileName="{bg_local}"/>'
            )
            display_items = bg_item + ('\n' + display_items if display_items.strip() else '')

        component_xml = build_component_xml(display_items, comp_w, comp_h)

        package_id = uuid.uuid4().hex[:8]
        pkg_resources = [
            {
                'type': 'image',
                'id': r['id'],
                'name': r['name'],
                'local_path': r['local_path'],
                'size': r.get('size', ''),
            }
            for r in res_list
        ]
        pkg_resources.append({
            'type': 'component',
            'id': id_gen.next(),
            'name': comp_name,
            'local_path': comp_name,
        })

        files_created: list = []
        _write_file(output_dir / f'{safe_name}.fairy', build_fairy_project_file(comp_name), files_created)
        _write_file(output_dir / 'UI' / 'package.xml', build_package_xml(package_id, pkg_resources), files_created)
        _write_file(output_dir / 'UI' / f'{comp_name}.xml', component_xml, files_created)
        _write_file(output_dir / 'settings' / 'BuildTargets.xml', build_targets_xml(), files_created)
        _write_file(output_dir / 'settings' / 'GlobalRelations.xml', build_global_relations_xml(), files_created)
        (output_dir / 'UI' / 'res').mkdir(parents=True, exist_ok=True)

        res_download_map = {
            str(output_dir / 'UI' / r['local_path']): r['remote_url']
            for r in res_list if r.get('remote_url')
        }

        return {
            'status': 'success',
            'files_created': files_created,
            'res_download_map': res_download_map,
            'component_name': comp_name,
            'component_size': f'{comp_w},{comp_h}',
            'image_count': len(res_list),
        }

    except Exception as e:
        import traceback
        return {
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc(),
        }


# ──────────────────────────────────────────────────────────────────────────────
# 12. 读取现有 FairyGUI 工程信息
# ──────────────────────────────────────────────────────────────────────────────

def read_fairygui_project(project_dir) -> dict:
    """
    读取现有 FairyGUI 工程的结构信息。

    返回 dict:
      valid        bool   -- 是否找到有效工程(有 .fairy 文件)
      project_dir  str    -- 工程根目录路径
      project_name str    -- 工程名(.fairy 文件名去扩展名)
      package_id   str    -- UI/package.xml 中的 id
      components   list   -- [{id, name, path}]
      images       list   -- [{id, name, path, size}]
    """
    project_dir = Path(project_dir)
    result = {
        "valid": False,
        "project_dir": str(project_dir),
        "project_name": "",
        "package_id": "",
        "components": [],
        "images": [],
    }

    fairy_files = list(project_dir.glob("*.fairy"))
    if not fairy_files:
        return result

    result["project_name"] = fairy_files[0].stem
    result["valid"] = True

    pkg_xml = project_dir / "UI" / "package.xml"
    if not pkg_xml.exists():
        return result

    try:
        tree = ET.parse(str(pkg_xml))
        root = tree.getroot()
        result["package_id"] = root.get("id", "")
        resources = root.find("resources")
        if resources is not None:
            for item in resources:
                if item.tag == "image":
                    result["images"].append({
                        "id": item.get("id", ""),
                        "name": item.get("name", ""),
                        "path": item.get("path", item.get("name", "")),
                        "size": item.get("size", ""),
                    })
                elif item.tag == "component":
                    result["components"].append({
                        "id": item.get("id", ""),
                        "name": item.get("name", ""),
                        "path": item.get("path", item.get("name", "")),
                    })
    except Exception:
        pass

    return result


# ──────────────────────────────────────────────────────────────────────────────
# 13. 构建合并后的 package.xml
# ──────────────────────────────────────────────────────────────────────────────

def _build_merged_package_xml(
    project_info: dict,
    new_res_list: list,
    new_comp_name: str,
    new_comp_id: str,
) -> str:
    """
    将新生成的资源列表合并到现有 FairyGUI 工程的 package.xml。

    规则:
      - 图片: 按 path 去重，已存在则保留旧条目，新图片追加
      - 组件: 按 name 去重，同名则覆盖(更新)，新名则追加
    """
    package_id = project_info.get("package_id") or uuid.uuid4().hex[:8]

    existing_img_map = {img["path"]: img for img in project_info.get("images", [])}

    for r in new_res_list:
        if r.get("type") == "image":
            lp = r.get("local_path", r.get("name", ""))
            if lp not in existing_img_map:
                existing_img_map[lp] = {
                    "id": r["id"],
                    "name": r["name"],
                    "path": lp,
                    "size": r.get("size", ""),
                }

    existing_comp_map = {c["name"]: c for c in project_info.get("components", [])}
    existing_comp_map[new_comp_name] = {
        "id": new_comp_id,
        "name": new_comp_name,
        "path": new_comp_name,
    }

    merged_resources = (
        [
            {
                "type": "image",
                "id": v["id"],
                "name": v["name"],
                "local_path": v["path"],
                "size": v.get("size", ""),
            }
            for v in existing_img_map.values()
        ] +
        [
            {
                "type": "component",
                "id": v["id"],
                "name": v["name"],
                "local_path": v["name"],
            }
            for v in existing_comp_map.values()
        ]
    )

    return build_package_xml(package_id, merged_resources)


# ──────────────────────────────────────────────────────────────────────────────
# 14. merge_into_fairygui_project -- Lanhu Schema JSON 路径
# ──────────────────────────────────────────────────────────────────────────────

def merge_into_fairygui_project(
    json_data: dict,
    design_name: str,
    project_dir,
    image_url_mapping: Optional[dict] = None,
) -> dict:
    """
    将蓝湖 Lanhu Schema 设计稿作为新组件合并进现有 FairyGUI 工程。

    不会修改 .fairy 和 settings/ 目录，仅更新 UI/package.xml 和 UI/{design_name}.xml。

    返回 dict 额外含:
      merge_mode  str   -- 'add'(新组件) 或 'update'(覆盖同名组件)
    """
    try:
        project_dir = Path(project_dir)

        project_info = read_fairygui_project(project_dir)
        if not project_info["valid"]:
            return {
                "status": "error",
                "error": f"未找到有效的 FairyGUI 工程({project_dir} 中无 .fairy 文件)",
            }

        comp_name = _sanitize_name(design_name) or "Component"
        existing_names = {c["name"] for c in project_info.get("components", [])}
        merge_mode = "update" if comp_name in existing_names else "add"

        id_gen = NodeIdGenerator()
        res_list: list = []

        layers = json_data.get("layers", json_data.get("children", []))
        w = int(json_data.get("width", json_data.get("frame", {}).get("width", 375)))
        h = int(json_data.get("height", json_data.get("frame", {}).get("height", 667)))

        display_xml_lines = []
        for layer in layers:
            display_xml_lines.append(
                _build_items_from_lanhu(layer, id_gen, res_list, indent=4)
            )
        display_list_xml = "\n".join(filter(None, display_xml_lines))

        comp_xml = build_component_xml(display_list_xml, w, h)

        comp_id_map = {c["name"]: c["id"] for c in project_info.get("components", [])}
        new_comp_id = comp_id_map.get(comp_name) or uuid.uuid4().hex[:8]

        merged_pkg_xml = _build_merged_package_xml(
            project_info, res_list, comp_name, new_comp_id
        )

        files_created: list = []
        files_updated: list = []

        comp_xml_path = project_dir / "UI" / f"{comp_name}.xml"
        if comp_xml_path.exists():
            comp_xml_path.write_text(comp_xml, encoding="utf-8")
            files_updated.append(str(comp_xml_path))
        else:
            _write_file(comp_xml_path, comp_xml, files_created)

        pkg_xml_path = project_dir / "UI" / "package.xml"
        if pkg_xml_path.exists():
            pkg_xml_path.write_text(merged_pkg_xml, encoding="utf-8")
            files_updated.append(str(pkg_xml_path))
        else:
            _write_file(pkg_xml_path, merged_pkg_xml, files_created)

        (project_dir / "UI" / "res").mkdir(parents=True, exist_ok=True)

        res_download_map: dict = {}
        res_dir = project_dir / "UI" / "res"
        for r in res_list:
            if r.get("type") == "image":
                local_path = res_dir / r["local_path"]
                remote_url = (image_url_mapping or {}).get(r["local_path"], "")
                res_download_map[str(local_path)] = remote_url

        return {
            "status": "success",
            "merge_mode": merge_mode,
            "component_name": comp_name,
            "project_name": project_info["project_name"],
            "project_dir": str(project_dir),
            "files_created": files_created,
            "files_updated": files_updated,
            "res_download_map": res_download_map,
            "image_count": len(res_list),
        }

    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


# ──────────────────────────────────────────────────────────────────────────────
# 15. merge_sketch_into_fairygui_project -- Sketch JSON 回退路径
# ──────────────────────────────────────────────────────────────────────────────

def merge_sketch_into_fairygui_project(
    sketch_data: dict,
    design_name: str,
    project_dir,
    design_img_url: str = "",
) -> dict:
    """
    将蓝湖 Sketch JSON 设计稿作为新组件合并进现有 FairyGUI 工程(回退路径)。

    不会修改 .fairy 和 settings/ 目录。
    """
    try:
        project_dir = Path(project_dir)

        project_info = read_fairygui_project(project_dir)
        if not project_info["valid"]:
            return {
                "status": "error",
                "error": f"未找到有效的 FairyGUI 工程({project_dir} 中无 .fairy 文件)",
            }

        comp_name = _sanitize_name(design_name) or "Component"
        existing_names = {c["name"] for c in project_info.get("components", [])}
        merge_mode = "update" if comp_name in existing_names else "add"

        id_gen = NodeIdGenerator()
        res_list: list = []

        artboard = (sketch_data.get("artboards") or [{}])[0]
        layers = artboard.get("layers", sketch_data.get("layers", []))
        frame = artboard.get("frame", {})
        w = int(frame.get("width", 375))
        h = int(frame.get("height", 667))
        scale = sketch_data.get("scale", 1.0)

        if design_img_url:
            bg_img_name = f"{comp_name}_bg.png"
            bg_id = id_gen.next()
            res_list.append({
                "type": "image",
                "id": bg_id,
                "name": bg_img_name,
                "local_path": bg_img_name,
                "size": f"{w},{h}",
            })

        display_xml_lines = []
        for layer in layers:
            display_xml_lines.append(
                _build_items_from_sketch(layer, id_gen, res_list, scale, indent=4)
            )
        display_list_xml = "\n".join(filter(None, display_xml_lines))

        comp_xml = build_component_xml(display_list_xml, w, h)

        comp_id_map = {c["name"]: c["id"] for c in project_info.get("components", [])}
        new_comp_id = comp_id_map.get(comp_name) or uuid.uuid4().hex[:8]

        merged_pkg_xml = _build_merged_package_xml(
            project_info, res_list, comp_name, new_comp_id
        )

        files_created: list = []
        files_updated: list = []

        comp_xml_path = project_dir / "UI" / f"{comp_name}.xml"
        if comp_xml_path.exists():
            comp_xml_path.write_text(comp_xml, encoding="utf-8")
            files_updated.append(str(comp_xml_path))
        else:
            _write_file(comp_xml_path, comp_xml, files_created)

        pkg_xml_path = project_dir / "UI" / "package.xml"
        if pkg_xml_path.exists():
            pkg_xml_path.write_text(merged_pkg_xml, encoding="utf-8")
            files_updated.append(str(pkg_xml_path))
        else:
            _write_file(pkg_xml_path, merged_pkg_xml, files_created)

        (project_dir / "UI" / "res").mkdir(parents=True, exist_ok=True)

        res_download_map: dict = {}
        res_dir = project_dir / "UI" / "res"
        for r in res_list:
            if r.get("type") == "image":
                local_path = res_dir / r["local_path"]
                url = design_img_url if r["local_path"].endswith("_bg.png") else ""
                res_download_map[str(local_path)] = url

        return {
            "status": "success",
            "merge_mode": merge_mode,
            "component_name": comp_name,
            "project_name": project_info["project_name"],
            "project_dir": str(project_dir),
            "files_created": files_created,
            "files_updated": files_updated,
            "res_download_map": res_download_map,
            "image_count": len(res_list),
        }

    except Exception as e:
        import traceback
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }
