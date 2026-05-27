"""
fairygui_converter 单元测试

覆盖：颜色转换、ID生成、CSS解析、节点XML生成、loop展开、flex控制器、文件生成函数、主入口函数。
"""
import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from fairygui_converter import (
    rgba_to_fairygui,
    NodeIdGenerator,
    _parse_numeric,
    _merge_style,
    _is_flex,
    _get_loop_arr,
    _xml_escape,
    _sanitize_name,
    _guess_ext,
    _build_items_from_lanhu,
    _build_items_from_sketch,
    build_component_xml,
    build_package_xml,
    build_fairy_project_file,
    build_targets_xml,
    build_global_relations_xml,
    convert_lanhu_to_fairygui_project,
    convert_sketch_to_fairygui_project,
)


# ─────────────────────────────────────────────────────────────────────────────
# rgba_to_fairygui
# ─────────────────────────────────────────────────────────────────────────────

class TestRgbaToFairygui:
    def test_opaque_rgba(self):
        assert rgba_to_fairygui('rgba(255, 115, 10, 1)') == '#FF730A'

    def test_opaque_rgba_no_spaces(self):
        assert rgba_to_fairygui('rgba(51,51,51,1)') == '#333333'

    def test_semi_transparent(self):
        result = rgba_to_fairygui('rgba(0, 0, 0, 0.5)')
        assert result == '#80000000'

    def test_fully_transparent(self):
        assert rgba_to_fairygui('rgba(0, 0, 0, 0)') == '#00000000'

    def test_fully_opaque_alpha_255(self):
        # alpha=1.0 → AA byte = 255 → omit AA → #RRGGBB
        r = rgba_to_fairygui('rgba(255,255,255,1)')
        assert r == '#FFFFFF'
        assert len(r) == 7  # no AA prefix

    def test_rgb(self):
        assert rgba_to_fairygui('rgb(255, 255, 255)') == '#FFFFFF'

    def test_hex_passthrough_lower(self):
        assert rgba_to_fairygui('#ff730a') == '#FF730A'

    def test_hex_passthrough_upper(self):
        assert rgba_to_fairygui('#FF730A') == '#FF730A'

    def test_hex8_passthrough(self):
        assert rgba_to_fairygui('#80FF730A') == '#80FF730A'

    def test_empty_returns_none(self):
        assert rgba_to_fairygui('') is None

    def test_none_returns_none(self):
        assert rgba_to_fairygui(None) is None  # type: ignore

    def test_invalid_string_returns_none(self):
        assert rgba_to_fairygui('not-a-color') is None

    def test_alpha_clamp_above_1(self):
        # Some schemas may emit alpha > 1 erroneously
        r = rgba_to_fairygui('rgba(255, 0, 0, 1.5)')
        assert r == '#FF0000'  # clamped to 1

    def test_white(self):
        assert rgba_to_fairygui('rgba(255,255,255,1)') == '#FFFFFF'

    def test_black_half_opacity(self):
        r = rgba_to_fairygui('rgba(0,0,0,0.502)')
        # 0.502 * 255 ≈ 128 = 0x80
        assert r.startswith('#80')


# ─────────────────────────────────────────────────────────────────────────────
# NodeIdGenerator
# ─────────────────────────────────────────────────────────────────────────────

class TestNodeIdGenerator:
    def test_sequential_ids(self):
        gen = NodeIdGenerator()
        assert gen.next() == 'n1'
        assert gen.next() == 'n2'
        assert gen.next() == 'n3'

    def test_independent_instances(self):
        gen1 = NodeIdGenerator()
        gen2 = NodeIdGenerator()
        assert gen1.next() == 'n1'
        assert gen2.next() == 'n1'

    def test_100_iterations(self):
        gen = NodeIdGenerator()
        ids = [gen.next() for _ in range(100)]
        assert ids[0] == 'n1'
        assert ids[99] == 'n100'
        assert len(set(ids)) == 100  # all unique


# ─────────────────────────────────────────────────────────────────────────────
# _parse_numeric
# ─────────────────────────────────────────────────────────────────────────────

class TestParseNumeric:
    def test_px_string(self):
        assert _parse_numeric('24px') == 24.0

    def test_float_string(self):
        assert _parse_numeric('1.5') == 1.5

    def test_int_value(self):
        assert _parse_numeric(24) == 24.0

    def test_float_value(self):
        assert _parse_numeric(1.5) == 1.5

    def test_none_default(self):
        assert _parse_numeric(None, 0.0) == 0.0

    def test_zero_string(self):
        assert _parse_numeric('0') == 0.0

    def test_em_stripped(self):
        assert _parse_numeric('2em') == 2.0

    def test_invalid_fallback(self):
        assert _parse_numeric('abc', 99.0) == 99.0


# ─────────────────────────────────────────────────────────────────────────────
# _merge_style
# ─────────────────────────────────────────────────────────────────────────────

class TestMergeStyle:
    def test_props_style_overrides_top_level(self):
        node = {
            'style': {'color': 'red'},
            'props': {'style': {'color': 'blue'}},
        }
        assert _merge_style(node)['color'] == 'blue'

    def test_alignjustify_merged_into_style(self):
        node = {
            'style': {},
            'props': {'style': {}},
            'alignJustify': {'justifyContent': 'center', 'alignItems': 'flex-start'},
        }
        s = _merge_style(node)
        assert s['justifyContent'] == 'center'
        assert s['alignItems'] == 'flex-start'

    def test_alignjustify_does_not_override_existing(self):
        node = {
            'style': {},
            'props': {'style': {'justifyContent': 'flex-end'}},
            'alignJustify': {'justifyContent': 'center'},
        }
        assert _merge_style(node)['justifyContent'] == 'flex-end'


# ─────────────────────────────────────────────────────────────────────────────
# _xml_escape
# ─────────────────────────────────────────────────────────────────────────────

class TestXmlEscape:
    def test_ampersand(self):
        assert _xml_escape('a & b') == 'a &amp; b'

    def test_double_quote(self):
        assert _xml_escape('"hello"') == '&quot;hello&quot;'

    def test_lt_gt(self):
        assert _xml_escape('<tag>') == '&lt;tag&gt;'

    def test_empty(self):
        assert _xml_escape('') == ''

    def test_plain_text_unchanged(self):
        assert _xml_escape('Hello World') == 'Hello World'


# ─────────────────────────────────────────────────────────────────────────────
# _sanitize_name
# ─────────────────────────────────────────────────────────────────────────────

class TestSanitizeName:
    def test_loop_suffix_removed(self):
        assert _sanitize_name('item_name-3') == 'item_name'

    def test_special_chars_replaced(self):
        assert _sanitize_name('btn confirm') == 'btn_confirm'

    def test_already_clean(self):
        assert _sanitize_name('myButton') == 'myButton'

    def test_empty_fallback(self):
        assert _sanitize_name('') == 'item'


# ─────────────────────────────────────────────────────────────────────────────
# _guess_ext
# ─────────────────────────────────────────────────────────────────────────────

class TestGuessExt:
    def test_png(self):
        assert _guess_ext('https://cdn.example.com/img.png?v=1') == '.png'

    def test_svg(self):
        assert _guess_ext('https://cdn.example.com/icon.svg') == '.svg'

    def test_unknown_defaults_to_png(self):
        assert _guess_ext('https://cdn.example.com/resource') == '.png'

    def test_jpg(self):
        assert _guess_ext('https://cdn.example.com/photo.jpg') == '.jpg'


# ─────────────────────────────────────────────────────────────────────────────
# _build_items_from_lanhu
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildItemsFromLanhu:

    def _text_node(self, text='Hello', w=100, h=20, bold=False):
        return {
            'type': 'lanhutext',
            'props': {
                'className': 'title_1',
                'text': text,
                'style': {
                    'width': f'{w}px', 'height': f'{h}px',
                    'fontSize': '16px',
                    'color': 'rgba(51,51,51,1)',
                    'fontWeight': 'bold' if bold else 'normal',
                },
            },
        }

    def _image_node(self, src='https://cdn.example.com/avatar.png'):
        return {
            'type': 'lanhuimage',
            'props': {
                'className': 'avatar',
                'src': src,
                'style': {'width': '80px', 'height': '80px'},
            },
        }

    def _button_node(self, title='确认'):
        return {
            'type': 'lanhubutton',
            'props': {
                'className': 'btn_confirm',
                'style': {'width': '175px', 'height': '44px'},
            },
            'children': [self._text_node(title)],
        }

    def _flex_container(self, direction='row', justify='space-between', align='center'):
        return {
            'type': 'div',
            'props': {
                'className': 'row_container',
                'style': {
                    'display': 'flex', 'flexDirection': direction,
                    'width': '375px', 'height': '50px',
                    'justifyContent': justify, 'alignItems': align,
                },
            },
            'children': [self._text_node()],
        }

    # ─── text ───

    def test_text_element_generated(self):
        gen = NodeIdGenerator()
        xml = _build_items_from_lanhu(self._text_node(), gen, [])
        assert '<text ' in xml
        assert 'text="Hello"' in xml
        assert 'fontSize="16"' in xml
        assert 'color="#333333"' in xml
        assert 'autoSize="none"' in xml

    def test_text_bold(self):
        gen = NodeIdGenerator()
        xml = _build_items_from_lanhu(self._text_node(bold=True), gen, [])
        assert 'bold="true"' in xml

    def test_text_normal_no_bold_attr(self):
        gen = NodeIdGenerator()
        xml = _build_items_from_lanhu(self._text_node(bold=False), gen, [])
        assert 'bold="true"' not in xml

    def test_text_align_center(self):
        node = self._text_node()
        node['props']['style']['textAlign'] = 'center'
        gen = NodeIdGenerator()
        xml = _build_items_from_lanhu(node, gen, [])
        assert 'align="center"' in xml

    # ─── image ───

    def test_image_element_generated(self):
        gen = NodeIdGenerator()
        res = []
        xml = _build_items_from_lanhu(self._image_node(), gen, res)
        assert '<image ' in xml
        assert 'fileName="res/avatar.png"' in xml
        assert len(res) == 1
        assert res[0]['remote_url'] == 'https://cdn.example.com/avatar.png'

    def test_image_no_src_no_filename_attr(self):
        node = {
            'type': 'lanhuimage',
            'props': {'className': 'bg', 'style': {'width': '375px', 'height': '200px'}},
        }
        gen = NodeIdGenerator()
        res = []
        xml = _build_items_from_lanhu(node, gen, res)
        assert '<image ' in xml
        assert 'fileName' not in xml
        assert len(res) == 0

    # ─── button ───

    def test_button_element_generated(self):
        gen = NodeIdGenerator()
        xml = _build_items_from_lanhu(self._button_node(), gen, [])
        assert '<button ' in xml
        assert 'title="确认"' in xml

    def test_button_special_chars_escaped(self):
        gen = NodeIdGenerator()
        xml = _build_items_from_lanhu(self._button_node('A & B'), gen, [])
        assert 'title="A &amp; B"' in xml

    # ─── flex container → Flow Controller ───

    def test_flex_row_generates_flow_controller(self):
        gen = NodeIdGenerator()
        xml = _build_items_from_lanhu(self._flex_container('row'), gen, [])
        assert '<component ' in xml
        assert 'controller name="layout" type="flow"' in xml
        assert '<axis value="x"/>' in xml

    def test_flex_col_uses_y_axis(self):
        gen = NodeIdGenerator()
        xml = _build_items_from_lanhu(self._flex_container('column'), gen, [])
        assert '<axis value="y"/>' in xml

    def test_flex_justify_space_between(self):
        gen = NodeIdGenerator()
        xml = _build_items_from_lanhu(self._flex_container(justify='space-between'), gen, [])
        assert 'space-between' in xml

    def test_flex_justify_center(self):
        gen = NodeIdGenerator()
        xml = _build_items_from_lanhu(self._flex_container(justify='center'), gen, [])
        assert 'alignH value="center"' in xml

    # ─── loop expansion ───

    def test_loop_expansion_three_items(self):
        node = {
            'type': 'div',
            'loopType': 'array',
            'loop': [{'label': 'A'}, {'label': 'B'}, {'label': 'C'}],
            'props': {'className': 'item', 'style': {'width': '100px', 'height': '30px'}},
            'children': [{
                'type': 'lanhutext',
                'props': {'className': 'item_label', 'text': 'this.item.label', 'style': {}},
            }],
        }
        gen = NodeIdGenerator()
        xml = _build_items_from_lanhu(node, gen, [])
        assert 'text="A"' in xml
        assert 'text="B"' in xml
        assert 'text="C"' in xml

    def test_loop_placeholder_unknown_key_empty(self):
        node = {
            'type': 'div',
            'loopType': 'array',
            'loop': [{'name': 'X'}],
            'props': {'className': 'item', 'style': {'width': '50px', 'height': '20px'}},
            'children': [{
                'type': 'lanhutext',
                'props': {'className': 'unknown', 'text': 'this.item.MISSING_KEY', 'style': {}},
            }],
        }
        gen = NodeIdGenerator()
        xml = _build_items_from_lanhu(node, gen, [])
        assert 'text=""' in xml  # missing key → empty string

    # ─── opacity ───

    def test_opacity_alpha_attribute(self):
        node = {
            'type': 'div',
            'props': {
                'className': 'faded',
                'style': {'width': '100px', 'height': '100px', 'opacity': '0.5'},
            },
            'children': [],
        }
        gen = NodeIdGenerator()
        xml = _build_items_from_lanhu(node, gen, [])
        assert 'alpha="0.5"' in xml

    def test_opacity_1_no_alpha_attribute(self):
        node = {
            'type': 'div',
            'props': {
                'className': 'full',
                'style': {'width': '100px', 'height': '100px', 'opacity': 1},
            },
            'children': [],
        }
        gen = NodeIdGenerator()
        xml = _build_items_from_lanhu(node, gen, [])
        assert 'alpha' not in xml

    # ─── background color ───

    def test_background_color_opaque(self):
        node = {
            'type': 'div',
            'props': {
                'className': 'colored_box',
                'style': {
                    'width': '100px', 'height': '100px',
                    'backgroundColor': 'rgba(255,0,0,1)',
                },
            },
            'children': [],
        }
        gen = NodeIdGenerator()
        xml = _build_items_from_lanhu(node, gen, [])
        assert 'opaque="true"' in xml
        assert 'color="#FF0000"' in xml


# ─────────────────────────────────────────────────────────────────────────────
# _build_items_from_sketch
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildItemsFromSketch:

    def _text_layer(self, text='World', x=10, y=20, w=200, h=40):
        return {
            'type': 'text',
            'visible': True,
            'name': 'my_title',
            'frame': {'x': x * 2, 'y': y * 2, 'width': w * 2, 'height': h * 2},
            'text': {
                'value': text,
                'style': {
                    'font': {'size': 32, 'name': 'PingFangSC'},  # @2x → 16px
                    'color': {'value': 'rgba(51,51,51,1)'},
                },
            },
        }

    def _image_layer(self, url='https://cdn.example.com/img.png'):
        return {
            'type': 'image',
            'visible': True,
            'name': 'hero_img',
            'frame': {'x': 0, 'y': 0, 'width': 750, 'height': 400},
            'images': {'png_xxxhd': url},
        }

    def _group_layer(self, children):
        return {
            'type': 'group',
            'visible': True,
            'name': 'card_group',
            'frame': {'x': 0, 'y': 0, 'width': 750, 'height': 200},
            'layers': children,
        }

    def test_text_layer_generates_text_element(self):
        gen = NodeIdGenerator()
        xml = _build_items_from_sketch(self._text_layer(), gen, [], scale=2.0)
        assert '<text ' in xml
        assert 'text="World"' in xml
        assert 'fontSize="16"' in xml  # 32/2=16
        assert 'color="#333333"' in xml

    def test_image_layer_generates_image_element(self):
        gen = NodeIdGenerator()
        res = []
        xml = _build_items_from_sketch(self._image_layer(), gen, res, scale=2.0)
        assert '<image ' in xml
        assert 'fileName="res/hero_img.png"' in xml
        assert len(res) == 1

    def test_group_generates_component_with_children(self):
        gen = NodeIdGenerator()
        res = []
        group = self._group_layer([self._text_layer()])
        xml = _build_items_from_sketch(group, gen, res, scale=2.0)
        assert '<component ' in xml
        assert '<text ' in xml

    def test_invisible_layer_skipped(self):
        layer = {
            'type': 'text',
            'visible': False,
            'name': 'hidden',
            'frame': {'x': 0, 'y': 0, 'width': 100, 'height': 30},
            'text': {'value': 'Hidden'},
        }
        gen = NodeIdGenerator()
        xml = _build_items_from_sketch(layer, gen, [], scale=2.0)
        assert xml == ''

    def test_scale_3x(self):
        layer = {
            'type': 'text',
            'visible': True,
            'name': 'big_title',
            'frame': {'x': 0, 'y': 0, 'width': 600, 'height': 90},
            'text': {'value': 'Hi', 'style': {'font': {'size': 60}}},
        }
        gen = NodeIdGenerator()
        xml = _build_items_from_sketch(layer, gen, [], scale=3.0)
        # 600/3 = 200, 90/3 = 30
        assert 'size="200,30"' in xml

    def test_opacity_from_blend_options(self):
        layer = {
            'type': 'image',
            'visible': True,
            'name': 'semi',
            'frame': {'x': 0, 'y': 0, 'width': 100, 'height': 100},
            'images': {'png_xxxhd': 'https://cdn.example.com/semi.png'},
            'blendOptions': {'opacity': {'value': 50}},
        }
        gen = NodeIdGenerator()
        xml = _build_items_from_sketch(layer, gen, [], scale=1.0)
        assert 'alpha="0.5"' in xml


# ─────────────────────────────────────────────────────────────────────────────
# build_component_xml
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildComponentXml:
    def test_basic_structure(self):
        xml = build_component_xml('<text id="n1"/>', 375, 812)
        assert '<?xml version="1.0"' in xml
        assert 'size="375,812"' in xml
        assert '<displayList>' in xml
        assert '</displayList>' in xml
        assert '</component>' in xml
        assert '<text id="n1"/>' in xml


# ─────────────────────────────────────────────────────────────────────────────
# build_package_xml
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildPackageXml:
    def test_basic_structure(self):
        resources = [
            {'type': 'image', 'id': 'n1', 'name': 'bg', 'local_path': 'res/bg.png', 'size': '375,812'},
            {'type': 'component', 'id': 'n2', 'name': 'HomePage', 'local_path': 'HomePage'},
        ]
        xml = build_package_xml('abc12345', resources)
        assert 'packageDescription id="abc12345"' in xml
        assert '<image id="n1"' in xml
        assert 'res/bg.png' in xml
        assert 'size="375,812"' in xml
        assert '<component id="n2"' in xml
        assert 'name="HomePage"' in xml

    def test_image_no_size(self):
        resources = [
            {'type': 'image', 'id': 'n1', 'name': 'icon', 'local_path': 'res/icon.png', 'size': ''},
        ]
        xml = build_package_xml('abc12345', resources)
        # size="" should not appear as attribute
        assert 'size=""' not in xml


# ─────────────────────────────────────────────────────────────────────────────
# build_fairy_project_file
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildFairyProjectFile:
    def test_laya3_type(self):
        xml = build_fairy_project_file('MyProject')
        assert 'type="laya3"' in xml
        assert '<item name="UI" path="UI/"' in xml
        assert '<?xml version="1.0"' in xml


# ─────────────────────────────────────────────────────────────────────────────
# build_targets_xml
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildTargetsXml:
    def test_laya3_platform(self):
        xml = build_targets_xml()
        assert 'platform value="laya3"' in xml
        assert 'outputCodeType value="ts"' in xml
        assert 'binderClass value="UIPackage_binder"' in xml

    def test_target_name_laya3(self):
        xml = build_targets_xml()
        assert 'target name="Laya3"' in xml


# ─────────────────────────────────────────────────────────────────────────────
# build_global_relations_xml
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildGlobalRelationsXml:
    def test_empty_relations(self):
        xml = build_global_relations_xml()
        assert '<relations/>' in xml
        assert '<?xml version="1.0"' in xml


# ─────────────────────────────────────────────────────────────────────────────
# convert_lanhu_to_fairygui_project (integration)
# ─────────────────────────────────────────────────────────────────────────────

class TestConvertLanhuToFairyguiProject:

    def _minimal_lanhu_schema(self):
        return {
            'type': 'div',
            'props': {
                'className': 'root',
                'style': {
                    'width': '375px', 'height': '812px',
                    'display': 'flex', 'flexDirection': 'column',
                },
            },
            'children': [
                {
                    'type': 'lanhutext',
                    'props': {
                        'className': 'welcome',
                        'text': '欢迎',
                        'style': {
                            'width': '200px', 'height': '30px',
                            'fontSize': '24px', 'color': 'rgba(0,0,0,1)',
                        },
                    },
                },
                {
                    'type': 'lanhuimage',
                    'props': {
                        'className': 'hero',
                        'src': 'https://cdn.example.com/hero.png',
                        'style': {'width': '375px', 'height': '200px'},
                    },
                },
            ],
        }

    def test_success_creates_five_files(self, tmp_path):
        result = convert_lanhu_to_fairygui_project(
            self._minimal_lanhu_schema(), 'HomePage', tmp_path
        )
        assert result['status'] == 'success'
        assert len(result['files_created']) == 5

    def test_fairy_file_created_with_laya3(self, tmp_path):
        convert_lanhu_to_fairygui_project(self._minimal_lanhu_schema(), 'HomePage', tmp_path)
        fairy = tmp_path / 'HomePage.fairy'
        assert fairy.exists()
        assert 'type="laya3"' in fairy.read_text(encoding='utf-8')

    def test_package_xml_contains_image_and_component(self, tmp_path):
        convert_lanhu_to_fairygui_project(self._minimal_lanhu_schema(), 'HomePage', tmp_path)
        pkg = (tmp_path / 'UI' / 'package.xml').read_text(encoding='utf-8')
        assert '<image ' in pkg
        assert 'HomePage' in pkg

    def test_component_xml_size_matches_schema(self, tmp_path):
        convert_lanhu_to_fairygui_project(self._minimal_lanhu_schema(), 'HomePage', tmp_path)
        comp = (tmp_path / 'UI' / 'HomePage.xml').read_text(encoding='utf-8')
        assert 'size="375,812"' in comp

    def test_component_xml_has_text_element(self, tmp_path):
        convert_lanhu_to_fairygui_project(self._minimal_lanhu_schema(), 'HomePage', tmp_path)
        comp = (tmp_path / 'UI' / 'HomePage.xml').read_text(encoding='utf-8')
        assert 'text="欢迎"' in comp

    def test_component_xml_has_image_element(self, tmp_path):
        convert_lanhu_to_fairygui_project(self._minimal_lanhu_schema(), 'HomePage', tmp_path)
        comp = (tmp_path / 'UI' / 'HomePage.xml').read_text(encoding='utf-8')
        assert 'fileName="res/hero.png"' in comp

    def test_build_targets_xml_laya3(self, tmp_path):
        convert_lanhu_to_fairygui_project(self._minimal_lanhu_schema(), 'HomePage', tmp_path)
        bt = (tmp_path / 'settings' / 'BuildTargets.xml').read_text(encoding='utf-8')
        assert 'laya3' in bt

    def test_res_directory_created(self, tmp_path):
        convert_lanhu_to_fairygui_project(self._minimal_lanhu_schema(), 'HomePage', tmp_path)
        assert (tmp_path / 'UI' / 'res').is_dir()

    def test_res_download_map_has_image(self, tmp_path):
        result = convert_lanhu_to_fairygui_project(self._minimal_lanhu_schema(), 'HomePage', tmp_path)
        assert len(result['res_download_map']) == 1
        assert 'https://cdn.example.com/hero.png' in result['res_download_map'].values()

    def test_image_count(self, tmp_path):
        result = convert_lanhu_to_fairygui_project(self._minimal_lanhu_schema(), 'HomePage', tmp_path)
        assert result['image_count'] == 1

    def test_design_name_with_slash_sanitized(self, tmp_path):
        schema = {
            'type': 'div',
            'props': {'className': 'root', 'style': {'width': '375px', 'height': '100px'}},
            'children': [],
        }
        result = convert_lanhu_to_fairygui_project(schema, '首页/弹窗', tmp_path)
        assert result['status'] == 'success'
        # slash sanitized to underscore
        assert (tmp_path / '首页_弹窗.fairy').exists()

    def test_image_url_mapping_merged(self, tmp_path):
        schema = {
            'type': 'div',
            'props': {'className': 'root', 'style': {'width': '375px', 'height': '100px'}},
            'children': [],
        }
        mapping = {'./assets/slices/extra.png': 'https://cdn.example.com/extra.png'}
        result = convert_lanhu_to_fairygui_project(schema, 'Test', tmp_path, image_url_mapping=mapping)
        assert result['image_count'] == 1
        assert 'https://cdn.example.com/extra.png' in result['res_download_map'].values()

    def test_flex_controller_in_component_xml(self, tmp_path):
        # flex 容器必须是根节点的 **子元素** 才能被渲染为带 Flow Controller 的 component；
        # 根节点本身会被展开为 displayList，不会额外生成 component 元素。
        schema = {
            'type': 'div',
            'props': {
                'className': 'page_root',
                'style': {'width': '375px', 'height': '812px'},
            },
            'children': [{
                'type': 'div',
                'props': {
                    'className': 'flex_row',
                    'style': {
                        'width': '375px', 'height': '100px',
                        'display': 'flex', 'flexDirection': 'row',
                        'justifyContent': 'center', 'alignItems': 'center',
                    },
                },
                'children': [{
                    'type': 'lanhutext',
                    'props': {
                        'className': 'label',
                        'text': 'Hi',
                        'style': {'width': '50px', 'height': '20px'},
                    },
                }],
            }],
        }
        result = convert_lanhu_to_fairygui_project(schema, 'FlexPage', tmp_path)
        comp = (tmp_path / 'UI' / 'FlexPage.xml').read_text(encoding='utf-8')
        assert 'controller name="layout" type="flow"' in comp
        assert '<axis value="x"/>' in comp


# ─────────────────────────────────────────────────────────────────────────────
# convert_sketch_to_fairygui_project (integration)
# ─────────────────────────────────────────────────────────────────────────────

class TestConvertSketchToFairyguiProject:

    def _artboard_sketch(self):
        return {
            'device': '@2x',
            'artboard': {
                'frame': {'width': 750, 'height': 1334, 'x': 0, 'y': 0},
                'layers': [
                    {
                        'type': 'text',
                        'visible': True,
                        'name': 'page_title',
                        'frame': {'x': 40, 'y': 200, 'width': 400, 'height': 60},
                        'text': {
                            'value': 'Hello Sketch',
                            'style': {
                                'font': {'size': 48, 'name': 'PingFangSC-Medium'},
                                'color': {'value': 'rgba(51,51,51,1)'},
                            },
                        },
                    }
                ],
            },
        }

    def test_success_status(self, tmp_path):
        result = convert_sketch_to_fairygui_project(self._artboard_sketch(), 'HomeSketch', tmp_path)
        assert result['status'] == 'success'

    def test_root_size_2x(self, tmp_path):
        convert_sketch_to_fairygui_project(self._artboard_sketch(), 'HomeSketch', tmp_path)
        comp = (tmp_path / 'UI' / 'HomeSketch.xml').read_text(encoding='utf-8')
        # 750/2=375, 1334/2=667
        assert 'size="375,667"' in comp

    def test_text_content_in_component(self, tmp_path):
        convert_sketch_to_fairygui_project(self._artboard_sketch(), 'HomeSketch', tmp_path)
        comp = (tmp_path / 'UI' / 'HomeSketch.xml').read_text(encoding='utf-8')
        assert 'text="Hello Sketch"' in comp

    def test_design_bg_added_when_url_provided(self, tmp_path):
        result = convert_sketch_to_fairygui_project(
            self._artboard_sketch(), 'BgTest', tmp_path,
            design_img_url='https://cdn.example.com/design.png?key=xyz',
        )
        assert result['status'] == 'success'
        comp = (tmp_path / 'UI' / 'BgTest.xml').read_text(encoding='utf-8')
        assert 'design_bg' in comp
        # query string stripped
        map_vals = list(result['res_download_map'].values())
        assert 'https://cdn.example.com/design.png' in map_vals

    def test_board_format_supported(self, tmp_path):
        sketch_data = {
            'device': '@2x',
            'board': {
                'width': 750, 'height': 1334,
                'layers': [],
            },
        }
        result = convert_sketch_to_fairygui_project(sketch_data, 'BoardTest', tmp_path)
        assert result['status'] == 'success'
        comp = (tmp_path / 'UI' / 'BoardTest.xml').read_text(encoding='utf-8')
        assert 'size="375,667"' in comp

    def test_scale_3x(self, tmp_path):
        sketch_data = {
            'device': '@3x',
            'artboard': {
                'frame': {'width': 1125, 'height': 2436},
                'layers': [],
            },
        }
        result = convert_sketch_to_fairygui_project(sketch_data, 'ThreeX', tmp_path)
        comp = (tmp_path / 'UI' / 'ThreeX.xml').read_text(encoding='utf-8')
        # 1125/3=375, 2436/3=812
        assert 'size="375,812"' in comp

    def test_five_files_created(self, tmp_path):
        result = convert_sketch_to_fairygui_project(self._artboard_sketch(), 'HomeSketch', tmp_path)
        assert len(result['files_created']) == 5

    def test_image_layer_generates_image(self, tmp_path):
        sketch_data = {
            'device': '@2x',
            'artboard': {
                'frame': {'width': 750, 'height': 1334},
                'layers': [{
                    'type': 'image',
                    'visible': True,
                    'name': 'banner',
                    'frame': {'x': 0, 'y': 0, 'width': 750, 'height': 400},
                    'images': {'png_xxxhd': 'https://cdn.example.com/banner.png'},
                }],
            },
        }
        result = convert_sketch_to_fairygui_project(sketch_data, 'WithImage', tmp_path)
        assert result['image_count'] >= 1
        comp = (tmp_path / 'UI' / 'WithImage.xml').read_text(encoding='utf-8')
        assert 'fileName="res/banner.png"' in comp
