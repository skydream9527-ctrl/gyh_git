import sys
input = sys.stdin.readline

def solve():
    MOD = 1000000007
    first_line = list(map(int, input().split()))
    if len(first_line) == 3:
        n, m, d = first_line
    else:
        n, d = first_line
    grid = []
    for _ in range(n):
        grid.append(input().strip())
    m = len(grid[0])

    sf = [0] * (m + 1)
    sg = [0] * (m + 1)

    for i in range(n):
        for j in range(m):
            if grid[i][j] == '#':
                sf[j + 1] = sf[j]
            elif i == 0:
                sf[j + 1] = sf[j] + 1
            else:
                hi = j + d if j + d < m else m
                lo = j - d + 1 if j - d + 1 > 0 else 0
                sf[j + 1] = (sf[j] + sg[hi] - sg[lo]) % MOD

        for j in range(m):
            if grid[i][j] == '#':
                sg[j + 1] = sg[j]
            else:
                hi = j + d + 1 if j + d + 1 < m else m
                lo = j - d if j - d > 0 else 0
                sg[j + 1] = (sg[j] + sf[hi] - sf[lo]) % MOD

    print(sg[m] % MOD)

solve()
