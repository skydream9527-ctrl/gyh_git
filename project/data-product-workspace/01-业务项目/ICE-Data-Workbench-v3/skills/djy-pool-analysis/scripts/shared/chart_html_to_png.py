#!/usr/bin/env python3
"""v7 图表 HTML → PNG 截图 · 每个 card 单独一张

用法：
  python3 chart_html_to_png.py <html_path> <out_dir>

输出：
  <out_dir>/chart_c1.png   4 CP 每日入库内容数
  <out_dir>/chart_c2.png   4 CP 内容池异常存量趋势
  <out_dir>/chart_c3.png   guoying 全字段存量
  <out_dir>/chart_c4.png   dihui 全字段存量
  <out_dir>/chart_c5.png   beike 全字段存量
  <out_dir>/chart_c6.png   meilaoban 全字段存量

实现：注入 JS 只保留目标 canvas 的 card，隐藏所有 section-title / h1 / 其他 card；
     把目标 card 从 grid 里拎出来撑满 body 宽度
"""
import os
import subprocess
import sys
import tempfile

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


CARD_INDEX = {"c0": 0, "c1": 1, "c2": 2, "c3": 3, "c4": 4, "c5": 5, "c6": 6}


def make_variant(full_html: str, target_id: str) -> str:
    """Python 直接修改 HTML：给非目标 card / section-title / h1 加 inline style=display:none
    不依赖 Chrome 的 JS/CSS 时序（Chrome headless --screenshot 会在 JS 执行前截图）
    """
    target_idx = CARD_INDEX[target_id]

    # 1. 把 h1 替换成 display:none
    out = full_html.replace("<h1>", '<h1 style="display:none !important">', 1)

    # 2. section-title 全部 display:none
    import re as _re
    out = _re.sub(
        r'<div class="section-title[^"]*"[^>]*>',
        lambda m: m.group(0).replace('style="', 'style="display:none !important;') if 'style="' in m.group(0) else m.group(0).rstrip(">") + ' style="display:none !important">',
        out,
    )

    # 3. 非目标 card 加 display:none（按出现顺序编号）
    card_count = [0]

    def card_replace(m):
        idx = card_count[0]
        card_count[0] += 1
        if idx == target_idx:
            return m.group(0)  # 保留目标 card
        tag = m.group(0)
        if 'style="' in tag:
            return tag.replace('style="', 'style="display:none !important;')
        return tag.rstrip(">") + ' style="display:none !important">'

    out = _re.sub(r'<div class="card"[^>]*>', card_replace, out)

    # 4. 布局 override（让目标 card 撑满，减少留白）
    #    新版样式引入的 .header / .insight / .footer / .container 在单卡截图中必须隐藏，
    #    否则飞书卡片单图会在顶部多出蓝青渐变横幅、底部多出黄色洞察框。
    style_override = """
<style>
body { padding: 4px 12px !important; margin: 0 !important; background: white !important; }
.container { max-width: none !important; padding: 0 !important; margin: 0 !important; }
.header, .insight, .footer, .health-overview, .biz-card { display: none !important; }
.section { margin: 0 !important; max-width: none !important; padding: 0 !important; }
.grid2 { display: block !important; }
.card { max-width: none !important; margin: 0 !important; padding: 12px 18px !important; box-shadow: none !important; }
.card h3 { margin: 0 0 4px 0 !important; }
.card .hint { margin-bottom: 4px !important; }
canvas { max-height: 380px !important; }
</style>
"""
    out = out.replace("</head>", style_override + "</head>")
    return out


def shoot(html_path: str, png_path: str, width: int, height: int):
    url = "file://" + os.path.abspath(html_path)
    cmd = [
        CHROME,
        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-sandbox",
        "--virtual-time-budget=8000",
        f"--window-size={width},{height}",
        f"--screenshot={png_path}",
        url,
    ]
    subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if not os.path.exists(png_path):
        raise RuntimeError(f"截图失败: {png_path}")


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    html_path, out_dir = sys.argv[1], sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    full = open(html_path, encoding="utf-8").read()

    tmp_dir = tempfile.mkdtemp(prefix="chart_")

    import re as _re
    has_c0 = len(_re.findall(r'<div class="card"', full)) > 6
    cards_to_shoot = (["c0"] if has_c0 else []) + ["c1", "c2", "c3", "c4", "c5", "c6"]

    for cid in cards_to_shoot:
        variant = make_variant(full, cid)
        tmp = os.path.join(tmp_dir, f"v7_{cid}.html")
        open(tmp, "w", encoding="utf-8").write(variant)
        png = os.path.join(out_dir, f"chart_{cid}.png")
        height = 450 if cid == "c0" else 560
        shoot(tmp, png, 1500, height)
        print(f"✅ {cid}: {png}")


if __name__ == "__main__":
    main()
