# -*- coding: utf-8 -*-
"""参考题：A. 配对（pair）。

用它来演示契约：spec 是事实源，gen 只出输入，答案由标程产出。
"""

ID = "demo-pair"
CODE = "pair"
TITLE = "A. 配对"
LIMIT = 1.0
MEM = 256
TAGS = ["排序", "交换论证", "贪心"]

SUBTASKS = {
    1: dict(score=20, desc="$n\\le 10$"),
    2: dict(score=20, desc="$a_i$ 单调不降", sorted=True),
    3: dict(score=60, desc="无特殊限制"),
}

TESTS = [
    (1, "fixed_small"),
    (1, "rand_small"),
    (2, "struct_sorted"),
    (2, "rand_sorted"),
    (3, "rand_big"),
    (3, "rand_dup"),
    (3, "struct_two_val"),
    (3, "struct_arith"),
    (3, "fixed_edges"),
    (3, "rand_gap"),
]

GLOBAL = ("对于全部数据：$2\\le n\\le 2\\times 10^5$，$n$ 为偶数，"
          "$1\\le a_i\\le 10^9$。")


def check(text, sub):
    d = text.split()
    n = int(d[0])
    assert 2 <= n <= 200000, f"n={n} 越界"
    assert n % 2 == 0, f"n={n} 不是偶数"
    assert len(d) == 1 + n, f"元素个数 {len(d) - 1} 与 n={n} 不符"
    a = [int(x) for x in d[1:]]
    assert all(1 <= x <= 10 ** 9 for x in a), "a_i 越界"
    if sub.get("sorted"):
        assert all(a[i] <= a[i + 1] for i in range(n - 1)), "子任务要求 a_i 单调不降"
