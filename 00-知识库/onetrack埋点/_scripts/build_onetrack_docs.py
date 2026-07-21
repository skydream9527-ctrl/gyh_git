#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将解析后的 OneTrack JSON 生成可索引查询的 Markdown + JSON 知识库。"""
import json, os, re, html

ROOT = '/Users/mi/Desktop/trae-cn/data-product/00-知识库/onetrack埋点'
CC_JSON = '/tmp/onetrack_content_center.json'
BR_JSON = '/tmp/onetrack_browser.json'

# ---------- 业务配置 ----------
# 每个业务: 预置属性 sheet 名列表, 说明 sheet 名列表, 事件模块 sheet 名(有序)
BUSINESS = {
    'content_center': {
        'name': '内容中心',
        'name_en': 'content_center',
        'dir': '内容中心业务',
        'json': CC_JSON,
        'source_file': '内容中心onetrack埋点(三期)  带沉浸式.xlsx',
        'preset_sheets': ['common key 预置&公共属性', 'content key 内容通用属性 '],
        'note_sheets': ['打点规则', '说明！！！', '【先不打】hot热榜', '小说'],
        # 事件模块按业务顺序
        'modules': [
            'app通用', 'content内容相关', '抖音&穿山甲直播间', '短剧',
            '桌面上划入口拉新拉活', 'operating运营位', 'me我的页面', 'ad商业化',
            'search搜索', '异常事件捕获', 'tab标签', '【8.0】激励体系',
        ],
        'preset_display': {
            'common key 预置&公共属性': 'common key 预置 & 公共属性',
            'content key 内容通用属性 ': 'content key 内容通用属性',
        },
    },
    'browser': {
        'name': '浏览器',
        'name_en': 'browser',
        'dir': '浏览器业务',
        'json': BR_JSON,
        'source_file': '浏览器新版OneTrack埋点汇总（可用于神策、数鲸）.xlsx',
        'preset_sheets': ['OneTrack SDK系统属性', 'commen key公共属性', 'content key信息流通用属性'],
        'note_sheets': ['说明', 'Sheet30', '附：接入tips', 'bugfix', '细节记录', '附1：页面定义', '附2：安全网址请求过滤规则'],
        'modules': [
            'app浏览器全局事件', 'content信息流事件', 'search搜索事件', 'livestream直播事件',
            'ad商业化事件', 'personal个人中心事件', 'icon_slots站点事件', 'general常规事件',
            'setting设置事件', '信息流热榜内容事件', '工程埋点', 'novel小说事件',
            '热榜事件', 'button_bar底部工具栏事件', 'download下载事件', '下载拦截事件',
            '搜索_安全网址事件(服务端)', '浏览器Push事件', 'AI搜索', 'AI浏览器',
        ],
        'preset_display': {
            'OneTrack SDK系统属性': 'OneTrack SDK 系统属性',
            'commen key公共属性': 'common key 公共属性',
            'content key信息流通用属性': 'content key 信息流通用属性',
        },
    },
}

# ---------- 工具 ----------
def slug(s):
    """安全文件名"""
    s = re.sub(r'[【】\(\)（）&＆\s]+', '-', s).strip('-')
    s = re.sub(r'-+', '-', s)
    return s or 'unnamed'

def md_cell(v):
    if v is None: return ''
    s = str(v).replace('|', '\\|').replace('\n', '<br>')
    return s

def short(s, n=80):
    s = str(s or '').replace('\n', ' ').strip()
    return s[:n] + '…' if len(s) > n else s

# ---------- 加载数据 ----------
def load(biz):
    with open(BUSINESS[biz]['json'], encoding='utf-8') as f:
        data = json.load(f)
    sheets = {s['sheet']: s for s in data['sheets']}
    return data, sheets

# ---------- 预置属性文档 ----------
def gen_preset_doc(biz, sheets):
    cfg = BUSINESS[biz]
    lines = []
    lines.append('# %s - 预置与公共属性\n' % cfg['name'])
    lines.append('> 本文档汇总所有事件共用的预置属性。每个事件实际上报时自动携带其引用的公共属性集(见各事件 `公共属性` 列)。\n')
    total = 0
    for sn in cfg['preset_sheets']:
        s = sheets.get(sn.rstrip(), sheets.get(sn)) if False else sheets.get(sn)
        # 兼容尾随空格
        if s is None:
            for k in sheets:
                if k.rstrip() == sn.rstrip():
                    s = sheets[k]; break
        if s is None:
            continue
        display = cfg['preset_display'].get(sn, sn)
        preset = s['preset']
        total += len(preset)
        lines.append('\n---\n')
        lines.append('## %s\n' % display)
        lines.append('> 来源 sheet: `%s` | 属性数: %d\n' % (s['sheet'], len(preset)))
        if not preset:
            lines.append('_(空)_\n')
            continue
        lines.append('\n| # | 属性名(英文) | 属性名(中文) | 值类型 | 值说明 | 备注 | 进版版本 |')
        lines.append('|---|---|---|---|---|---|---|')
        for i, p in enumerate(preset, 1):
            cat = p.get('category', '')
            name_en = p['param_en']
            # category 前缀(降级 sheet)
            if cat and cat != name_en:
                name_en = '**[%s]** %s' % (cat, name_en) if False else name_en
            lines.append('| %d | `%s` | %s | %s | %s | %s | %s |' % (
                i, md_cell(p['param_en']), md_cell(p['param_cn']), md_cell(p['value_type']),
                md_cell(short(p['value_desc'], 200)), md_cell(short(p['remark'], 80)),
                md_cell(p.get('version', ''))))
        # 详情
        lines.append('\n### 属性详情\n')
        for p in preset:
            if not p['param_en']:
                continue
            lines.append('#### `%s` — %s' % (p['param_en'], p['param_cn'] or ''))
            meta = []
            if p.get('category'): meta.append('分类: %s' % p['category'])
            if p['value_type']: meta.append('类型: %s' % p['value_type'])
            if p.get('version'): meta.append('进版: %s' % p['version'])
            if meta:
                lines.append('- ' + ' | '.join(meta))
            if p['value_desc']:
                lines.append('- **值说明**:\n  %s' % p['value_desc'].replace('\n', '\n  '))
            if p['remark']:
                lines.append('- **备注**: %s' % p['remark'])
            lines.append('')
    lines.append('\n---\n\n**预置属性合计**: %d\n' % total)
    return '\n'.join(lines)

# ---------- 事件模块文档 ----------
def gen_module_doc(biz, sheet_obj):
    s = sheet_obj
    lines = []
    lines.append('# %s - %s\n' % (BUSINESS[biz]['name'], s['sheet']))
    n_ev = len(s['events'])
    n_pa = sum(len(e['params']) for e in s['events'])
    n_ref = sum(len(e['preset_refs']) for e in s['events'])
    lines.append('> 来源 sheet: `%s` | 事件数: %d | 参数数: %d\n' % (s['sheet'], n_ev, n_pa))
    if not s['events']:
        lines.append('\n_(无事件)_\n')
        return '\n'.join(lines)
    # 总览表
    lines.append('\n## 事件总览\n')
    has_cat = any(e.get('category') for e in s['events'])
    header = '| # |'
    if has_cat: header += ' 分类 |'
    header += ' 事件名(英文) | 事件名(中文) | 上报时机 | 参数数 | 公共属性 | 进版 |'
    lines.append(header)
    lines.append('|' + '---|' * (6 + (1 if has_cat else 0)))
    for i, e in enumerate(s['events'], 1):
        row = '| %d |' % i
        if has_cat: row += ' %s |' % md_cell(short(e.get('category', ''), 20))
        row += ' `%s` | %s | %s | %d | %s | %s |' % (
            md_cell(e['event_en']), md_cell(e['event_cn']), md_cell(short(e['report'], 60)),
            len(e['params']), md_cell(', '.join(e['preset_refs']) or '-'),
            md_cell(e.get('version', '')))
        lines.append(row)
    # 详情
    lines.append('\n---\n\n## 事件详情\n')
    for e in s['events']:
        lines.append('### `%s` — %s\n' % (e['event_en'], e['event_cn'] or ''))
        meta = []
        if e.get('category'): meta.append('分类: %s' % e['category'])
        if e.get('version'): meta.append('进版版本: %s' % e['version'])
        if e.get('incognito'): meta.append('无痕模式上报: %s' % e['incognito'])
        if e['preset_refs']: meta.append('公共属性: %s' % ', '.join('`%s`' % r for r in e['preset_refs']))
        if meta:
            for m in meta:
                lines.append('- ' + m)
            lines.append('')
        if e['report']:
            lines.append('**上报时机/逻辑**:\n\n%s\n' % e['report'])
        if e['params']:
            lines.append('\n**参数列表** (%d):\n' % len(e['params']))
            lines.append('| 参数名(英文) | 参数名(中文) | 值类型 | 值说明 | 备注 |')
            lines.append('|---|---|---|---|---|')
            for p in e['params']:
                tag = ''
                if p.get('color_tag'):
                    tag = ' '.join('`%s`' % t for t in p['color_tag'])
                desc = p['value_desc']
                if tag:
                    desc = ('%s %s' % (tag, desc)).strip()
                lines.append('| `%s` | %s | %s | %s | %s |' % (
                    md_cell(p['param_en']), md_cell(p['param_cn']), md_cell(p['value_type']),
                    md_cell(short(desc, 300)), md_cell(short(p['remark'], 80))))
            # 参数详情(值说明长的)
            long_params = [p for p in e['params'] if p['value_desc'] and len(p['value_desc']) > 60]
            if long_params:
                lines.append('\n<details><summary>参数取值详情</summary>\n')
                for p in long_params:
                    if not p['param_en']:
                        continue
                    lines.append('\n**`%s`** (%s)' % (p['param_en'], p['param_cn'] or ''))
                    if p['value_type']:
                        lines.append('- 类型: %s' % p['value_type'])
                    lines.append('- 取值:\n  %s' % p['value_desc'].replace('\n', '\n  '))
                    if p['remark']:
                        lines.append('- 备注: %s' % p['remark'])
                lines.append('\n</details>\n')
        else:
            lines.append('\n_(无独立参数,仅携带公共属性)_\n')
        if e['remark']:
            lines.append('\n> **事件备注**: %s\n' % e['remark'])
        lines.append('')
    return '\n'.join(lines)

# ---------- 说明/附录文档 ----------
def gen_note_doc(biz, sheet_obj, title=None):
    s = sheet_obj
    lines = []
    lines.append('# %s - %s\n' % (BUSINESS[biz]['name'], title or s['sheet']))
    lines.append('> 来源 sheet: `%s`\n' % s['sheet'])
    raw = s.get('raw_lines') or s.get('lines') or []
    if raw:
        lines.append('\n```\n')
        for l in raw:
            lines.append(l)
        lines.append('\n```\n')
    else:
        lines.append('\n_(空)_\n')
    return '\n'.join(lines)

def gen_combined_note_doc(biz, sheets, sheet_names, title, intro=None):
    """合并多个说明 sheet 为一个文档"""
    lines = []
    lines.append('# %s - %s\n' % (BUSINESS[biz]['name'], title))
    if intro:
        lines.append(intro + '\n')
    for sn in sheet_names:
        s = sheets.get(sn)
        if not s:
            continue
        raw = s.get('raw_lines') or s.get('lines') or []
        if not raw:
            continue
        lines.append('\n---\n')
        lines.append('## %s\n' % sn)
        lines.append('\n```\n')
        for l in raw:
            lines.append(l)
        lines.append('\n```\n')
    return '\n'.join(lines)

# ---------- 业务 README ----------
def gen_biz_readme(biz, sheets):
    cfg = BUSINESS[biz]
    lines = []
    lines.append('# %s业务 - OneTrack 埋点现状\n' % cfg['name'])
    lines.append('> 数据来源: `%s`\n' % cfg['source_file'])
    # 元信息(浏览器的"说明"sheet 有 appid/hive 等)
    if biz == 'browser':
        note = sheets.get('说明')
        if note and note.get('lines'):
            lines.append('## 业务元信息\n')
            lines.append('| 项 | 值 |')
            lines.append('|---|---|')
            for l in note['lines']:
                parts = l.split(' | ', 1)
                if len(parts) == 2 and parts[0].strip():
                    lines.append('| %s | %s |' % (md_cell(parts[0]), md_cell(parts[1])))
            lines.append('')
    # 统计
    n_ev = sum(len(sheets[sn]['events']) for sn in cfg['modules'] if sn in sheets)
    n_pa = sum(sum(len(e['params']) for e in sheets[sn]['events']) for sn in cfg['modules'] if sn in sheets)
    n_pre = sum(len(sheets[sn]['preset']) for sn in cfg['preset_sheets'] if sn.rstrip() in {k.rstrip():k for k in sheets})
    # 说明文档导航
    if biz == 'content_center':
        lines.append('> 📄 命名规则与版本图例见 [00-说明与规则.md](00-说明与规则.md)\n')
    elif biz == 'browser':
        lines.append('> 📄 appid/hive表/数鲸/神策地址等元信息见 [00-业务说明.md](00-业务说明.md)\n')
    lines.append('## 现状概览\n')
    lines.append('| 维度 | 数量 |')
    lines.append('|---|---|')
    lines.append('| 事件模块 | %d |' % len(cfg['modules']))
    lines.append('| 事件总数 | %d |' % n_ev)
    lines.append('| 事件参数总数 | %d |' % n_pa)
    lines.append('| 预置/公共属性 | %d |' % n_pre)
    lines.append('')
    # 模块导航
    lines.append('## 事件模块\n')
    lines.append('| # | 模块 | 事件数 | 参数数 | 文档 |')
    lines.append('|---|---|---|---|---|')
    for i, sn in enumerate(cfg['modules'], 1):
        s = sheets.get(sn)
        if not s:
            continue
        ne = len(s['events'])
        npa = sum(len(e['params']) for e in s['events'])
        fname = '%02d-%s.md' % (i, slug(sn))
        lines.append('| %d | %s | %d | %d | [%s](%s) |' % (i, sn, ne, npa, fname, fname))
    lines.append('')
    # 预置属性导航
    lines.append('## 预置与公共属性\n')
    lines.append('| # | 属性集 | 属性数 | 文档 |')
    lines.append('|---|---|---|---|')
    for i, sn in enumerate(cfg['preset_sheets'], 1):
        s = sheets.get(sn)
        if not s:
            for k in sheets:
                if k.rstrip() == sn.rstrip():
                    s = sheets[k]; break
        if not s:
            continue
        display = cfg['preset_display'].get(sn, sn)
        fname = '预置属性-%s.md' % slug(display)
        lines.append('| %d | %s | %d | [%s](%s) |' % (i, display, len(s['preset']), fname, fname))
    lines.append('')
    # 附录
    note_files = []
    if biz == 'browser':
        note_files = [('附：接入tips', '接入tips'), ('bugfix', 'bugfix 修复记录'), ('细节记录', '打点细节记录'), ('附1：页面定义', '页面定义(page/module 枚举)'), ('附2：安全网址请求过滤规则', '安全网址过滤规则')]
    if note_files:
        lines.append('## 附录\n')
        for sn, title in note_files:
            s = sheets.get(sn)
            if s:
                fname = '附录/%s.md' % slug(title)
                lines.append('- [%s](%s) (%d 行)' % (title, fname, len(s.get('lines', []))))
        lines.append('')
    lines.append('## 查询方式\n')
    lines.append('- 按事件名查询: 见顶层 [索引/按事件名检索.md](../索引/按事件名检索.md) 或 [索引/全局事件索引.json](../索引/全局事件索引.json)')
    lines.append('- 按参数名查询: 见 [索引/全局参数索引.json](../索引/全局参数索引.json)')
    lines.append('- 程序化查询: `jq \'.["app_open"]\' 索引/全局事件索引.json`')
    lines.append('')
    return '\n'.join(lines)

# ---------- 全局索引 ----------
def build_global_index(all_biz_data):
    """event_en -> {business: {module, file, report, params}}; param_en -> [{business,module,event}]"""
    event_idx = {}
    param_idx = {}
    module_idx = {}
    for biz, (data, sheets) in all_biz_data.items():
        cfg = BUSINESS[biz]
        module_idx[biz] = {'name': cfg['name'], 'modules': []}
        for i, sn in enumerate(cfg['modules'], 1):
            s = sheets.get(sn)
            if not s:
                continue
            fname = '%s/%02d-%s.md' % (cfg['dir'], i, slug(sn))
            module_idx[biz]['modules'].append({
                'module': sn, 'file': fname, 'events': len(s['events']),
                'params': sum(len(e['params']) for e in s['events']),
            })
            for e in s['events']:
                key = e['event_en']
                if not key:
                    continue
                event_idx.setdefault(key, {})[biz] = {
                    'business': cfg['name'],
                    'module': sn,
                    'event_cn': e['event_cn'],
                    'file': fname,
                    'report': short(e['report'], 200),
                    'preset_refs': e['preset_refs'],
                    'param_count': len(e['params']),
                    'params': [{'param_en': p['param_en'], 'param_cn': p['param_cn'],
                                'value_type': p['value_type']} for p in e['params']],
                }
                for p in e['params']:
                    pk = p['param_en']
                    if not pk or pk.lower() in {'common key', 'content key', 'commen key', 'commey_key'}:
                        continue
                    param_idx.setdefault(pk, []).append({
                        'business': cfg['name'], 'business_key': biz,
                        'module': sn, 'event_en': e['event_en'], 'event_cn': e['event_cn'],
                    })
        # 预置属性也进参数索引
        for sn in cfg['preset_sheets']:
            s = sheets.get(sn)
            if not s:
                for k in sheets:
                    if k.rstrip() == sn.rstrip():
                        s = sheets[k]; break
            if not s:
                continue
            for p in s['preset']:
                pk = p['param_en']
                if not pk:
                    continue
                param_idx.setdefault(pk, []).append({
                    'business': cfg['name'], 'business_key': biz,
                    'module': '[预置] %s' % cfg['preset_display'].get(sn, sn),
                    'event_en': '-', 'event_cn': p['param_cn'],
                })
    return event_idx, param_idx, module_idx

# ---------- 索引文档 ----------
def gen_event_index_md(event_idx):
    lines = []
    lines.append('# 全局事件索引(按事件名检索)\n')
    lines.append('> 覆盖内容中心 + 浏览器两个业务。同名事件跨业务时,列出所有命中。\n')
    lines.append('| 事件名(英文) | 中文 | 内容中心 | 浏览器 |')
    lines.append('|---|---|---|---|')
    # 排序: 字母序
    for key in sorted(event_idx.keys()):
        info = event_idx[key]
        cc = info.get('content_center')
        br = info.get('browser')
        cn = (cc or br)['event_cn']
        def link(x):
            if not x: return '—'
            return '[%s](%s)' % (x['module'], x['file'])
        lines.append('| `%s` | %s | %s | %s |' % (key, md_cell(cn), link(cc), link(br)))
    lines.append('\n**事件去重数**: %d\n' % len(event_idx))
    return '\n'.join(lines)

def gen_param_index_md(param_idx):
    lines = []
    lines.append('# 全局参数索引(按参数名检索)\n')
    lines.append('> 参数名 -> 使用该参数的事件/预置属性。仅列出在事件中出现的参数及公共属性。\n')
    # 仅展示出现>=1次的,排序
    items = sorted(param_idx.items())
    lines.append('| 参数名(英文) | 使用处数 | 使用位置(业务/模块/事件) |')
    lines.append('|---|---|---|')
    for pk, uses in items:
        locs = '; '.join('%s/%s/%s' % (u['business'], u['module'], u['event_en']) for u in uses[:5])
        more = '' if len(uses) <= 5 else ' …(+%d)' % (len(uses) - 5)
        lines.append('| `%s` | %d | %s%s |' % (pk, len(uses), md_cell(locs), more))
    lines.append('\n**参数去重数**: %d\n' % len(param_idx))
    return '\n'.join(lines)

def gen_module_index_md(module_idx, all_biz_data):
    lines = []
    lines.append('# 按模块索引\n')
    for biz, info in module_idx.items():
        cfg = BUSINESS[biz]
        lines.append('## %s\n' % info['name'])
        lines.append('| # | 模块 | 事件数 | 参数数 | 文档 |')
        lines.append('|---|---|---|---|---|')
        for m in info['modules']:
            lines.append('| - | %s | %d | %d | [%s](%s) |' % (
                m['module'], m['events'], m['params'], m['module'], m['file']))
        lines.append('')
    return '\n'.join(lines)

# ---------- 顶层 README ----------
def gen_top_readme(all_biz_data, event_idx, param_idx, module_idx):
    cfg_cc = BUSINESS['content_center']
    cfg_br = BUSINESS['browser']
    cc = all_biz_data['content_center'][1]
    br = all_biz_data['browser'][1]
    cc_ev = sum(len(cc[sn]['events']) for sn in cfg_cc['modules'] if sn in cc)
    cc_pa = sum(sum(len(e['params']) for e in cc[sn]['events']) for sn in cfg_cc['modules'] if sn in cc)
    cc_pre = sum(len(cc[sn]['preset']) for sn in cfg_cc['preset_sheets'] if sn.rstrip() in {k.rstrip():k for k in cc})
    br_ev = sum(len(br[sn]['events']) for sn in cfg_br['modules'] if sn in br)
    br_pa = sum(sum(len(e['params']) for e in br[sn]['events']) for sn in cfg_br['modules'] if sn in br)
    br_pre = sum(len(br[sn]['preset']) for sn in cfg_br['preset_sheets'] if sn in br)
    # 同名事件跨业务
    both = [k for k, v in event_idx.items() if 'content_center' in v and 'browser' in v]

    lines = []
    lines.append('# OneTrack 埋点现状知识库\n')
    lines.append('> 本知识库从两份 OneTrack 埋点 Excel 提炼,按 **两个业务** 组织,完整记录每个业务的 **埋点模块、事件、参数** 现状,并提供可索引查询结构。\n')
    lines.append('## 数据来源\n')
    lines.append('| 业务 | 源文件 | 模块数 | 事件数 | 参数数 | 预置属性 |')
    lines.append('|---|---|---|---|---|---|')
    lines.append('| 内容中心 | `%s` | %d | %d | %d | %d |' % (cfg_cc['source_file'], len(cfg_cc['modules']), cc_ev, cc_pa, cc_pre))
    lines.append('| 浏览器 | `%s` | %d | %d | %d | %d |' % (cfg_br['source_file'], len(cfg_br['modules']), br_ev, br_pa, br_pre))
    lines.append('')
    lines.append('## 目录结构\n')
    lines.append('```')
    lines.append('onetrack埋点/')
    lines.append('├── README.md                     ← 本文件(总入口)')
    lines.append('├── 内容中心业务/')
    lines.append('│   ├── README.md                 ← 业务总览 + 模块导航')
    lines.append('│   ├── 预置属性-*.md             ← common key / content key')
    lines.append('│   ├── 01-app通用.md …           ← 各事件模块')
    lines.append('│   └── _data.json                ← 完整结构化数据')
    lines.append('├── 浏览器业务/')
    lines.append('│   ├── README.md')
    lines.append('│   ├── 预置属性-*.md             ← SDK系统属性 / common key / content key')
    lines.append('│   ├── 01-app浏览器全局事件.md …')
    lines.append('│   ├── 附录/                     ← 接入tips / bugfix / 页面定义 / 细节记录')
    lines.append('│   └── _data.json')
    lines.append('└── 索引/')
    lines.append('    ├── 全局事件索引.json          ← event_en -> {业务: 事件+参数}')
    lines.append('    ├── 全局参数索引.json          ← param_en -> 使用位置列表')
    lines.append('    ├── 按事件名检索.md            ← 事件名平铺表(跨业务对比)')
    lines.append('    ├── 按参数名检索.md            ← 参数名平铺表')
    lines.append('    └── 按模块索引.md              ← 业务->模块->文档')
    lines.append('```\n')
    lines.append('## 检索指南\n')
    lines.append('| 我想… | 去哪查 |')
    lines.append('|---|---|')
    lines.append('| 看某业务全貌 | [内容中心业务/README.md](内容中心业务/README.md) / [浏览器业务/README.md](浏览器业务/README.md) |')
    lines.append('| 查某事件名的定义和参数 | [索引/按事件名检索.md](索引/按事件名检索.md) 或 `索引/全局事件索引.json` |')
    lines.append('| 查某参数名被哪些事件使用 | [索引/按参数名检索.md](索引/按参数名检索.md) 或 `索引/全局参数索引.json` |')
    lines.append('| 按模块浏览 | [索引/按模块索引.md](索引/按模块索引.md) |')
    lines.append('| 看公共属性定义 | 各业务下 `预置属性-*.md` |')
    lines.append('| 看 page/module 取值字典 | [浏览器业务/附录/页面定义.md](浏览器业务/附录/页面定义.md) |')
    lines.append('')
    lines.append('### 程序化查询示例\n')
    lines.append('```bash')
    lines.append('# 查 app_open 事件在两个业务里的定义')
    lines.append('jq \'.["app_open"]\' "索引/全局事件索引.json"')
    lines.append('')
    lines.append('# 查 page 参数被哪些事件使用')
    lines.append('jq \'.["page"]\' "索引/全局参数索引.json"')
    lines.append('')
    lines.append('# 列出浏览器业务所有事件名')
    lines.append('jq \'to_entries[] | select(.value.browser) | .key\' "索引/全局事件索引.json"')
    lines.append('```\n')
    lines.append('## 跨业务同名事件\n')
    lines.append('以下 %d 个事件名在 **内容中心** 和 **浏览器** 两个业务中均有定义(口径可能不同,使用前请对照):\n' % len(both))
    if both:
        lines.append('| 事件名 | 内容中心模块 | 浏览器模块 |')
        lines.append('|---|---|---|')
        for k in sorted(both):
            lines.append('| `%s` | %s | %s |' % (k, event_idx[k]['content_center']['module'], event_idx[k]['browser']['module']))
    lines.append('')
    lines.append('## 埋点层级说明\n')
    lines.append('- **埋点(模块)**: 一组相关事件的集合,对应 Excel 的一个 sheet,如「app通用」「content信息流事件」「ad商业化」。\n- **事件**: 一次完整的用户行为或系统行为上报,有唯一英文事件名(如 `content_item_expose`)和中文描述。\n- **参数**: 事件携带的属性,分为①公共属性(引用 common key / content key,所有事件自动携带)②事件专属参数(仅该事件上报)。\n')
    return '\n'.join(lines)

# ---------- 主流程 ----------
def main():
    os.makedirs(ROOT, exist_ok=True)
    all_biz_data = {}
    for biz in ['content_center', 'browser']:
        cfg = BUSINESS[biz]
        data, sheets = load(biz)
        all_biz_data[biz] = (data, sheets)
        biz_dir = os.path.join(ROOT, cfg['dir'])
        os.makedirs(biz_dir, exist_ok=True)
        # 业务 README
        with open(os.path.join(biz_dir, 'README.md'), 'w', encoding='utf-8') as f:
            f.write(gen_biz_readme(biz, sheets))
        # 预置属性文档
        for sn in cfg['preset_sheets']:
            s = sheets.get(sn)
            if s is None:
                for k in sheets:
                    if k.rstrip() == sn.rstrip():
                        s = sheets[k]; break
            if s is None:
                continue
            display = cfg['preset_display'].get(sn, sn)
            fname = '预置属性-%s.md' % slug(display)
            with open(os.path.join(biz_dir, fname), 'w', encoding='utf-8') as f:
                f.write(gen_preset_doc(biz, sheets))
        # 事件模块文档
        for i, sn in enumerate(cfg['modules'], 1):
            s = sheets.get(sn)
            if s is None:
                print('  [WARN] %s 缺失 sheet: %s' % (biz, sn))
                continue
            fname = '%02d-%s.md' % (i, slug(sn))
            with open(os.path.join(biz_dir, fname), 'w', encoding='utf-8') as f:
                f.write(gen_module_doc(biz, s))
        # 说明文档
        if biz == 'content_center':
            cc_notes = ['打点规则', '说明！！！', '【先不打】hot热榜', '小说']
            with open(os.path.join(biz_dir, '00-说明与规则.md'), 'w', encoding='utf-8') as f:
                f.write(gen_combined_note_doc(biz, sheets, cc_notes, '说明与打点规则',
                    '本文件汇总打点命名规则、版本颜色图例及未启用模块说明,便于回溯原始文档。'))
        elif biz == 'browser':
            s_note = sheets.get('说明')
            if s_note:
                with open(os.path.join(biz_dir, '00-业务说明.md'), 'w', encoding='utf-8') as f:
                    f.write(gen_note_doc(biz, s_note, '业务说明与元信息'))
        # 附录(浏览器)
        if biz == 'browser':
            appx_dir = os.path.join(biz_dir, '附录')
            os.makedirs(appx_dir, exist_ok=True)
            note_map = [('附：接入tips', '接入tips'), ('bugfix', 'bugfix 修复记录'),
                        ('细节记录', '打点细节记录'), ('附1：页面定义', '页面定义'),
                        ('附2：安全网址请求过滤规则', '安全网址过滤规则')]
            for sn, title in note_map:
                s = sheets.get(sn)
                if s:
                    fname = '%s.md' % slug(title)
                    with open(os.path.join(appx_dir, fname), 'w', encoding='utf-8') as f:
                        f.write(gen_note_doc(biz, s, title))
        # _data.json
        with open(os.path.join(biz_dir, '_data.json'), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print('[%s] docs generated in %s' % (biz, biz_dir))

    # 索引
    idx_dir = os.path.join(ROOT, '索引')
    os.makedirs(idx_dir, exist_ok=True)
    event_idx, param_idx, module_idx = build_global_index(all_biz_data)
    with open(os.path.join(idx_dir, '全局事件索引.json'), 'w', encoding='utf-8') as f:
        json.dump(event_idx, f, ensure_ascii=False, indent=2)
    with open(os.path.join(idx_dir, '全局参数索引.json'), 'w', encoding='utf-8') as f:
        json.dump(param_idx, f, ensure_ascii=False, indent=2)
    with open(os.path.join(idx_dir, '按事件名检索.md'), 'w', encoding='utf-8') as f:
        f.write(gen_event_index_md(event_idx))
    with open(os.path.join(idx_dir, '按参数名检索.md'), 'w', encoding='utf-8') as f:
        f.write(gen_param_index_md(param_idx))
    with open(os.path.join(idx_dir, '按模块索引.md'), 'w', encoding='utf-8') as f:
        f.write(gen_module_index_md(module_idx, all_biz_data))
    print('[index] %d events, %d params -> %s' % (len(event_idx), len(param_idx), idx_dir))

    # 顶层 README
    with open(os.path.join(ROOT, 'README.md'), 'w', encoding='utf-8') as f:
        f.write(gen_top_readme(all_biz_data, event_idx, param_idx, module_idx))
    print('[top] README.md')

    # 复制解析/生成脚本到知识库
    import shutil
    sdir = os.path.join(ROOT, '_scripts')
    os.makedirs(sdir, exist_ok=True)
    shutil.copy('/tmp/parse_onetrack.py', os.path.join(sdir, 'parse_onetrack.py'))
    shutil.copy('/tmp/build_onetrack_docs.py', os.path.join(sdir, 'build_onetrack_docs.py'))
    print('[scripts] copied to _scripts/')

if __name__ == '__main__':
    main()
