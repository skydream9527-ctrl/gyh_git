import json, os

bfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'blocks.json')
with open(bfile) as f:
    data = json.load(f)

blocks = data.get('blocks', [])
doc_id = 'JZImdNlTZohPMNxFNCucEuqGnpb'

empty_count = 0
for i, b in enumerate(blocks):
    btype = b.get('block_type', 0)
    parent = str(b.get('parent_id', ''))
    bid = b.get('block_id', '')
    if parent == doc_id and btype == 2:
        cp = []
        if 'text' in b and 'elements' in b.get('text', {}):
            for el in b['text']['elements']:
                if 'text_run' in el:
                    cp.append(el['text_run'].get('content', ''))
        text = ''.join(cp).strip()
        if not text:
            empty_count += 1
            if empty_count <= 10:
                print(f"EMPTY: idx={i} id={bid}")

print(f"\nTotal empty top-level text blocks: {empty_count}")
print(f"Total blocks: {len(blocks)}")
