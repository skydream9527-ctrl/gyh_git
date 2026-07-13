"""
LeetCode-3762: 使数组元素相等的最小操作次数
- 每次操作可让 nums 中某个元素 +k 或 -k。
- 对每个查询 [l, r]，求把子区间内所有元素变相等所需最少操作数；不可行返回 -1。

解法（O(n log V) 预处理 + O(log V) 查询）：
1. 区间可行 ⇔ 区间内所有 nums[i] % k 相等；用前缀计数 O(1) 检测。
2. 同余前提下，令 b[i] = nums[i] // k，最少操作 = sum |b[i] - m|，m 取区间中位数。
3. 在 b 的值域上建 **可持久化线段树**，节点维护 (count, sum)。
4. 单次查询沿版本差下降找第 k 小，并同时累计严格小于中位数的 (cnt_lt, sum_lt)。
   ops = 2 * cnt_lt * m - 2 * sum_lt + total_sum - length * m
   其中 total_sum = SM[root_{r+1}] - SM[root_l]。

输入（多组用例直到 EOF）：
  第 1 行: n q k
  第 2 行: n 个整数 nums
  随后 q 行: l r
输出：每组一行，q 个整数空格分隔。
"""

from __future__ import annotations

import sys
from array import array
from typing import List, Tuple


def solve_case(nums: List[int], k: int, queries: List[Tuple[int, int]]) -> List[int]:
    n = len(nums)
    if n == 0:
        return [0 if l == r else -1 for l, r in queries]

    # 同余检测的前缀和：bad_prefix[i+1] - bad_prefix[l+1] = (l, r] 内余数变化次数
    bad_prefix = [0] * (n + 1)
    prev_mod = nums[0] % k
    for i in range(1, n):
        cur_mod = nums[i] % k
        bad_prefix[i + 1] = bad_prefix[i] + (1 if cur_mod != prev_mod else 0)
        prev_mod = cur_mod

    # b 值与值域压缩
    b = [x // k for x in nums]
    sorted_unique = sorted(set(b))
    val_to_idx = {v: i for i, v in enumerate(sorted_unique)}
    V = len(sorted_unique)
    Vm1 = V - 1

    # 可持久化线段树：4 个并行数组 + null 节点(0)
    # 每次插入新建 depth+1 ≈ log2(V)+2 个节点；放宽到 25 倍足够
    max_nodes = n * 25 + 32
    LC = array('q', bytes(8 * max_nodes))
    RC = array('q', bytes(8 * max_nodes))
    CNT = array('q', bytes(8 * max_nodes))
    SM = array('q', bytes(8 * max_nodes))
    cnt_nodes = 1  # 0 号是 null

    roots = array('q', bytes(8 * (n + 1)))

    # 局部别名，减少属性查找
    LC_l = LC
    RC_l = RC
    CNT_l = CNT
    SM_l = SM

    for i in range(n):
        prev_root = roots[i]
        pos = val_to_idx[b[i]]
        val = b[i]

        # 沿原版本下降，记录路径
        path_old: List[int] = []
        path_mid: List[int] = []
        cur = prev_root
        lo, hi = 0, Vm1
        while lo < hi:
            mid = (lo + hi) >> 1
            path_old.append(cur)
            path_mid.append(mid)
            if pos <= mid:
                cur = LC_l[cur]
                hi = mid
            else:
                cur = RC_l[cur]
                lo = mid + 1

        # 新建叶子
        new_leaf = cnt_nodes
        LC_l[new_leaf] = 0
        RC_l[new_leaf] = 0
        CNT_l[new_leaf] = CNT_l[cur] + 1
        SM_l[new_leaf] = SM_l[cur] + val
        cnt_nodes += 1

        # 自底向上新建内部节点
        cur_new = new_leaf
        for j in range(len(path_old) - 1, -1, -1):
            old_node = path_old[j]
            mid_p = path_mid[j]
            new_node = cnt_nodes
            if pos <= mid_p:
                LC_l[new_node] = cur_new
                RC_l[new_node] = RC_l[old_node]
            else:
                LC_l[new_node] = LC_l[old_node]
                RC_l[new_node] = cur_new
            CNT_l[new_node] = CNT_l[old_node] + 1
            SM_l[new_node] = SM_l[old_node] + val
            cur_new = new_node
            cnt_nodes += 1

        roots[i + 1] = cur_new

    ans: List[int] = []
    ans_append = ans.append

    for l, r in queries:
        if l == r:
            ans_append(0)
            continue
        if bad_prefix[r + 1] - bad_prefix[l + 1] > 0:
            ans_append(-1)
            continue

        length = r - l + 1
        u = roots[l]
        v = roots[r + 1]
        total_sum = SM_l[v] - SM_l[u]

        # 一次下降：找下中位数 (kth = (len+1)//2)，同时累计 cnt_lt / sum_lt
        kth = (length + 1) >> 1
        cnt_lt = 0
        sum_lt = 0
        lo, hi = 0, Vm1
        while lo < hi:
            mid = (lo + hi) >> 1
            lcv = LC_l[v]
            lcu = LC_l[u]
            left_cnt = CNT_l[lcv] - CNT_l[lcu]
            if kth <= left_cnt:
                u = lcu
                v = lcv
                hi = mid
            else:
                kth -= left_cnt
                cnt_lt += left_cnt
                sum_lt += SM_l[lcv] - SM_l[lcu]
                u = RC_l[u]
                v = RC_l[v]
                lo = mid + 1

        median = sorted_unique[lo]
        # ops = sum_{<m}(m - b) + sum_{>m}(b - m)
        #     = 2 * cnt_lt * m - 2 * sum_lt + total_sum - length * m
        ops = (cnt_lt << 1) * median - (sum_lt << 1) + total_sum - length * median
        ans_append(ops)

    return ans


def main() -> None:
    data = sys.stdin.buffer.read().split()
    idx = 0
    out: List[str] = []
    L = len(data)

    while idx < L:
        if idx + 3 > L:
            break
        n = int(data[idx]); q = int(data[idx + 1]); k = int(data[idx + 2])
        idx += 3
        nums = list(map(int, data[idx:idx + n]))
        idx += n
        queries: List[Tuple[int, int]] = []
        q_append = queries.append
        for _ in range(q):
            q_append((int(data[idx]), int(data[idx + 1])))
            idx += 2
        ans = solve_case(nums, k, queries)
        out.append(' '.join(map(str, ans)))

    sys.stdout.write('\n'.join(out))
    if out:
        sys.stdout.write('\n')


if __name__ == "__main__":
    main()
