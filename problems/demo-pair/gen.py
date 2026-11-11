# -*- coding: utf-8 -*-
"""A. 配对 —— 数据模板。

覆盖矩阵：定点（fixed_）、结构（struct_）、随机（rand_）、对拍（fuzz_）。
"""
N_BIG = 200000


def _emit(a):
    return f"{len(a)}\n" + " ".join(map(str, a)) + "\n"


# ---------------------------------------------------------------- 定点
def fixed_small(rng, sub):
    """刻意用锯齿顺序：原始相邻差最大是 9，排序后相邻差全是 1。

    这样"不排序直接相邻"必错，不会因为排列碰巧对上而白送分。
    小数据最容易被运气分污染，所以这里不用随机。
    """
    a = [1, 10, 2, 9, 3, 8, 4, 7, 5, 6]
    return _emit(a)


def fixed_edges(rng, sub):
    """三段值域，且两段计数为奇数 —— 制造两个非平凡配对，答案非 0。

    这样"把答案当成难度之和"的错解才藏不住：和 = 3e8-1 + 7e8 > 最大值 7e8。
    """
    n = N_BIG
    a = [1] * 100001 + [3 * 10 ** 8] * 50000 + [10 ** 9] * 49999
    assert len(a) == n
    rng.shuffle(a)
    return _emit(a)


# ---------------------------------------------------------------- 结构
def struct_sorted(rng, sub):
    n = N_BIG
    a = sorted(rng.randint(1, 10 ** 9) for _ in range(n))
    return _emit(a)


def struct_two_val(rng, sub):
    """两种值，各一半 —— 正确答案固定为 0，任何"不排序"的实现都会翻车。"""
    n = N_BIG
    a = [1] * (n // 2) + [10 ** 9] * (n // 2)
    rng.shuffle(a)
    return _emit(a)


def struct_arith(rng, sub):
    n = N_BIG
    a = [i * 5000 for i in range(1, n + 1)]
    rng.shuffle(a)
    return _emit(a)


# ---------------------------------------------------------------- 随机
def rand_small(rng, sub):
    """严格递减的小数据。

    递减顺序下"不排序直接相邻配对"算出的差全是负数，答案必然退化成 0，
    而真实答案是那个特大的间隔 —— 两者在构造上就不可能撞上。
    最后一个间隔取得很大，保证答案严格大于 (max-min)/2，顺手把 half 也堵死。
    """
    gaps = [rng.randint(1, 50) for _ in range(9)]
    gaps[rng.randrange(9)] = rng.randint(1000, 5000)
    a = [rng.randint(1, 100)]
    for g in gaps:
        a.append(a[-1] + g)
    a.sort(reverse=True)
    return _emit(a)


def rand_sorted(rng, sub):
    n = N_BIG
    a = sorted(rng.randint(1, 10 ** 9) for _ in range(n))
    return _emit(a)


def rand_big(rng, sub):
    n = N_BIG
    a = [rng.randint(1, 10 ** 9) for _ in range(n)]
    return _emit(a)


def rand_dup(rng, sub):
    """大量重复（1..1000），末尾再塞两对极端值。

    那两对保证至少有两个非平凡配对，于是"难度之和"一定严格大于"最大难度"，
    这题才能卡住 sum_diff 那类错解。
    """
    n = N_BIG
    a = [rng.randint(1, 1000) for _ in range(n - 4)]
    a += [5 * 10 ** 8 - 7, 5 * 10 ** 8, 10 ** 9 - 3, 10 ** 9]
    assert len(a) == n
    rng.shuffle(a)
    return _emit(a)


def rand_gap(rng, sub):
    """双峰分布：一堆小值 + 一堆大值。"""
    n = N_BIG
    a = []
    for _ in range(n):
        if rng.random() < 0.5:
            a.append(rng.randint(1, 100))
        else:
            a.append(rng.randint(10 ** 9 - 100, 10 ** 9))
    return _emit(a)


# ---------------------------------------------------------------- 对拍专用
def fuzz_small(rng, sub):
    n = rng.choice([2, 4, 6, 8, 10])
    a = [rng.randint(1, 20) for _ in range(n)]
    return _emit(a)


def fuzz_mid(rng, sub):
    n = rng.choice([20, 60, 200, 1000])
    a = [rng.randint(1, 10 ** 9) for _ in range(n)]
    return _emit(a)


TEMPLATES = {
    "fixed_small": fixed_small,
    "fixed_edges": fixed_edges,
    "struct_sorted": struct_sorted,
    "struct_two_val": struct_two_val,
    "struct_arith": struct_arith,
    "rand_small": rand_small,
    "rand_sorted": rand_sorted,
    "rand_big": rand_big,
    "rand_dup": rand_dup,
    "rand_gap": rand_gap,
    "fuzz_small": fuzz_small,
    "fuzz_mid": fuzz_mid,
}

FUZZ = ["fuzz_small"]
FUZZ_MID = ["fuzz_mid"]
