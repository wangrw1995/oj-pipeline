# -*- coding: utf-8 -*-
"""数据模板注册表。

每个模板签名是 (rng, sub) -> 完整输入字符串，sub 是该测试点所属子任务的 dict。
模板名决定它在覆盖矩阵里的类别：
    fixed_   定点：正好卡在某个约束的边界上
    struct_  结构：链、星、菊花、等权、全等、平行边……
    rand_    随机：多种分布
    fuzz_    只给对拍用，不进正式数据
"""
import random


def fixed_small(rng, sub):
    n = 10
    a = [rng.randint(1, 20) for _ in range(n)]
    return f"{n}\n" + " ".join(map(str, a)) + "\n"


def rand_small(rng, sub):
    n = rng.randint(2, 10)
    a = [rng.randint(1, 10 ** 9) for _ in range(n)]
    return f"{n}\n" + " ".join(map(str, a)) + "\n"


def rand_big(rng, sub):
    n = 200000
    a = [rng.randint(1, 10 ** 9) for _ in range(n)]
    return f"{n}\n" + " ".join(map(str, a)) + "\n"


def struct_chain(rng, sub):
    n = 200000
    a = [i * 5000 for i in range(1, n + 1)]
    rng.shuffle(a)
    return f"{n}\n" + " ".join(map(str, a)) + "\n"


def fuzz_small(rng, sub):
    n = rng.choice([2, 4, 6, 8, 10])
    a = [rng.randint(1, 20) for _ in range(n)]
    return f"{n}\n" + " ".join(map(str, a)) + "\n"


def fuzz_mid(rng, sub):
    n = rng.choice([20, 60, 200, 1000])
    a = [rng.randint(1, 10 ** 9) for _ in range(n)]
    return f"{n}\n" + " ".join(map(str, a)) + "\n"


TEMPLATES = {
    "fixed_small": fixed_small,
    "rand_small": rand_small,
    "rand_big": rand_big,
    "struct_chain": struct_chain,
    "fuzz_small": fuzz_small,
    "fuzz_mid": fuzz_mid,
}

FUZZ = ["fuzz_small"]
FUZZ_MID = ["fuzz_mid"]
