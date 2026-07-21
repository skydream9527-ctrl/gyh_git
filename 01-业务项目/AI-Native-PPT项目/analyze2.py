import json, os

bfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'blocks.json')
with open(bfile) as f:
    data = json.load(f)

blocks = data.get('blocks', [])

for i in range(505, 555):
    if i >= len(blocks):
        break
    b = blocks[i]
    bid = b.get('block_id', '')
    btype = b.get('block_type', '')
    parent = b.get('parent_id', '')
    children = len(b.get('children', []))
    cp = []
    if 'text' in b and 'elements' in b.get('text', {}):
        for el in b['text']['elements']:
            if 'text_run' in el:
                cp.append(el['text_run'].get('content', ''))
    sn = ''.join(cp)[:60] if cp else ''
    if 'table' in b:
        sn = f"[TABLE rows={b['table'].get('rows','')} cols={b['table'].get('columns','')}]"
    print(f"{i:3d} {bid} t={str(btype):>2s} p={str(parent)[:12]}... ch={children} | {sn}")
