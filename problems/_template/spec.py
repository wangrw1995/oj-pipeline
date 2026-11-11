# -*- coding: utf-8 -*-
"""题目事实源：子任务、测试点、约束、题面数据范围。

改这道题只需要改这个文件 + gen.py + 三个解法，其余全部由 oj 推导。
"""

ID = "__ID__"
TITLE = "__TITLE__"
LIMIT = 1.0          # 秒
MEM = 256            # MB
TAGS = ["待填"]       # 考点标签，用于查重和分类

# 子任务：score 必须加起来 100；desc 会直接渲染进题面表格
SUBTASKS = {
    1: dict(score=30, desc="n ≤ 10"),
    2: dict(score=70, desc="无特殊限制"),
}

# 第 i 个测试点 = (所属子任务, gen.py 里的模板名)
# 命名约定：fixed_ 定点边界 / struct_ 特殊结构 / rand_ 随机 / fuzz_ 对拍专用
TESTS = [
    (1, "fixed_small"),
    (1, "rand_small"),
    (2, "rand_big"),
    (2, "struct_chain"),
]

# 题面里"对于全部数据"那一段，原样渲染
GLOBAL = "对于全部数据：$2\\le n\\le 2\\times 10^5$。$1\\le a_i\\le 10^9$。"


def check(text, sub):
    """按子任务校验一份输入是否合法，不合法就 assert 失败。"""
    d = text.split()
    n = int(d[0])
    assert 2 <= n <= 200000, f"n={n} 越界"
    assert len(d) == 1 + n, "元素个数与 n 不符"
    assert all(1 <= int(x) <= 10 ** 9 for x in d[1:]), "a_i 越界"
