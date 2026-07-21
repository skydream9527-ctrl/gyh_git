import json, sys

import os
bfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'blocks.json')
with open(bfile) as f:
    data = json.load(f)

blocks = data.get('blocks', [])

keywords = ['预期对比', '准确性', '可解释性', '可修正性', '可复用性', '稳定可预期']

for i, b in enumerate(blocks):
    text = json.dumps(b, ensure_ascii=False)
    for kw in keywords:
        if kw in text:
            bid = b.get('block_id', 'N/A')
            btype = b.get('block_type', 'N/A')
            content_parts = []
            if 'text' in b and 'elements' in b['text']:
                for el in b['text']['elements']:
                    if 'text_run' in el:
                        content_parts.append(el['text_run'].get('content', ''))
            snippet = ''.join(content_parts)[:100] if content_parts else ''
            parent = b.get('parent_id', 'N/A')
            children = b.get('children', [])
            print(f"idx={i} id={bid} type={btype} parent={parent} children={len(children)} | {snippet or kw}")
            break
