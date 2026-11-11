# -*- coding: utf-8 -*-
"""B. 削山（mountain）—— 二分答案 + 单调栈最大矩形。

考点：
  1. 看到"最小的 H 使得……"要想到二分（判定单调）
  2. 判定里是"柱状图最大矩形"，单调栈 O(n)
  3. 两者相乘 O(n log V)，n=1e5 时约 30 次栈扫描
"""

ID = "demo-mountain"
CODE = "mountain"
TITLE = "B. 削山"
LIMIT = 2.0
MEM = 256
TAGS = ["二分答案", "单调栈", "最大矩形"]

SUBTASKS = {
    1: dict(score=30, desc="$n\\le 2000$"),
    2: dict(score=30, desc="$h_i$ 单调不降", sorted=True),
    3: dict(score=40, desc="无特殊限制"),
}

TESTS = [
    (1, "fixed_small"),
    (1, "rand_small"),
    (1, "struct_small_wall"),
    (2, "struct_sorted"),
    (2, "struct_plateau"),
    (3, "rand_big"),
    (3, "struct_mountain"),
    (3, "fixed_exact"),
    (3, "struct_zigzag"),
    (3, "rand_spikes"),
]

GLOBAL = ("对于全部数据：$1\\le n\\le 10^5$，$1\\le h_i\\le 10^9$，"
          "$1\\le S\\le 10^{18}$。保证 $S\\le$ 不削山时的最大矩形面积。")

NMAX = 100000


def check(text, sub):
    d = text.split()
    n = int(d[0])
    assert 1 <= n <= NMAX, f"n={n} 越界"
    assert len(d) == 1 + n + 1, f"数据个数 {len(d)} 与 n={n} 不符"
    h = [int(x) for x in d[1:1 + n]]
    assert all(1 <= x <= 10 ** 9 for x in h), "h_i 越界"
    S = int(d[n + 1])
    assert 1 <= S <= 10 ** 18, f"S={S} 越界"
    if sub.get("sorted"):
        assert all(h[i] <= h[i + 1] for i in range(n - 1)), "子任务要求 h_i 单调不降"
