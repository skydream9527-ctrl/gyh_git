import sys
import numpy as np

def solve():
    MOD = 1000000007
    data = sys.stdin.buffer.read().split()
    idx = 0
    out = []

    while idx < len(data):
        n = int(data[idx]); m = int(data[idx+1]); d = int(data[idx+2])
        idx += 3
        grid = []
        for _ in range(n):
            grid.append(data[idx].decode()); idx += 1

        j_arr = np.arange(m, dtype=np.int64)
        hi1 = np.minimum(j_arr + d, m)
        lo1 = np.maximum(j_arr - d + 1, 0)
        hi2 = np.minimum(j_arr + d + 1, m)
        lo2 = np.maximum(j_arr - d, 0)

        blocked = np.frombuffer(b''.join(c.encode() for c in grid), dtype=np.uint8).reshape(n, m) == 35

        sg = np.zeros(m + 1, dtype=np.int64)

        for i in range(n):
            mask = ~blocked[i]
            if i == 0:
                f = mask.astype(np.int64)
            else:
                f = np.where(mask, (sg[hi1] - sg[lo1]) % MOD, 0)

            sf = np.empty(m + 1, dtype=np.int64)
            sf[0] = 0
            np.cumsum(f, out=sf[1:])

            h = np.where(mask, (sf[hi2] - sf[lo2]) % MOD, 0)

            sg[0] = 0
            np.cumsum(h, out=sg[1:])

        out.append(str(int(sg[m] % MOD)))

    sys.stdout.write('\n'.join(out))

solve()
