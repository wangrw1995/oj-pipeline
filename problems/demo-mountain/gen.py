# -*- coding: utf-8 -*-
"""B. 削山 —— 数据模板。

S 不是随便取的：先用最大矩形算出"不削山时的面积上界" M，再取 S<=M，
这样每个测试点都有解，不会出现"整份数据都是 -1"导致部分分程序白拿分。
"""
N_BIG = 100000


def _max_rect(h):
    st = []
    best = 0
    n = len(h)
    for i in range(n + 1):
        cur = h[i] if i < n else 0
        while st and h[st[-1]] > cur:
            j = st.pop()
            left = st[-1] + 1 if st else 0
            a = h[j] * (i - left)
            if a > best:
                best = a
        st.append(i)
    return best


def _emit(h, S):
    return f"{len(h)}\n" + " ".join(map(str, h)) + f"\n{S}\n"


def _pick_S(rng, h, lo=0.15, hi=0.95):
    """挑 S。

    下界里那个 n*min(h)+1 是故意的：只要 S 超过 n*min(h)，
    "铺满整行"就办不到，于是 ceil(S/n) 这类错解不可能蒙对。
    """
    n = len(h)
    M = _max_rect(h)
    lb = max(1, int(M * lo), n * min(h) + 1)
    ub = max(lb, min(M, int(M * hi)))
    if lb > M:                      # 这个模板本身杀不掉"整行"类错解，只能取上界附近
        lb = max(1, min(M, int(M * lo)))
        ub = max(lb, min(M, int(M * hi)))
    return rng.randint(lb, ub)


# ---------------------------------------------------------------- 定点
def fixed_small(rng, sub):
    """小数据但带一根尖峰：答案由那根尖峰决定，整行/求和两种错解都会偏。"""
    h = [rng.randint(1, 3) for _ in range(10)]
    h[rng.randrange(10)] = 10 ** 9
    return _emit(h, _pick_S(rng, h, 0.4, 0.9))


def fixed_exact(rng, sub):
    """S 正好等于不削山时的最大面积 M —— 答案由"哪个矩形达到 M"决定。

    专门测二分的等号与上界：稍微把 H 写小一点就达不到 M。
    """
    h = [rng.randint(1, 10 ** 9) for _ in range(N_BIG)]
    return _emit(h, _max_rect(h))


# ---------------------------------------------------------------- 结构
def struct_sorted(rng, sub):
    h = sorted(rng.randint(1, 10 ** 9) for _ in range(N_BIG))
    return _emit(h, _pick_S(rng, h))


def struct_plateau(rng, sub):
    """非降 + 大量平台。"""
    h = []
    v = rng.randint(1, 10)
    while len(h) < N_BIG:
        v = min(10 ** 9, v + rng.randint(0, 5))
        h.extend([v] * rng.randint(1, 40))
    h = h[:N_BIG]
    h.sort()
    return _emit(h, _pick_S(rng, h))


def struct_mountain(rng, sub):
    """先升后降的山峰：非降也不是非增，专测"只处理单调"的部分分。"""
    half = N_BIG // 2
    left = sorted(rng.randint(1, 10 ** 9) for _ in range(half))
    right = sorted((rng.randint(1, 10 ** 9) for _ in range(N_BIG - half)), reverse=True)
    h = left + right
    return _emit(h, _pick_S(rng, h))


def struct_zigzag(rng, sub):
    """高-低交替：最大矩形往往被"低柱"截断，单调栈最吃这种形状。"""
    hi = rng.randint(5 * 10 ** 8, 10 ** 9)
    lo = rng.randint(1, 1000)
    h = [(hi if i % 2 == 0 else lo) for i in range(N_BIG)]
    return _emit(h, _pick_S(rng, h, 0.3, 0.9))


def struct_small_wall(rng, sub):
    """n 刚好卡在子任务 1 的上界，S 取到接近上界，逼二分往上找。"""
    h = [rng.randint(1, 10 ** 9) for _ in range(2000)]
    return _emit(h, _pick_S(rng, h, 0.9, 1.0))


# ---------------------------------------------------------------- 随机
def rand_small(rng, sub):
    n = rng.randint(1, 2000)
    h = [rng.randint(1, 10 ** 9) for _ in range(n)]
    return _emit(h, _pick_S(rng, h))


def rand_big(rng, sub):
    h = [rng.randint(1, 10 ** 9) for _ in range(N_BIG)]
    return _emit(h, _pick_S(rng, h))


def rand_spikes(rng, sub):
    """低矮山体 + 少量尖峰：最大矩形由尖峰决定，宽度只有 1。

    这种形状下"铺满整行"和"按面积求和"都会严重低估答案。
    """
    h = [rng.randint(1, 100) for _ in range(N_BIG)]
    for _ in range(rng.randint(100, 300)):
        h[rng.randrange(N_BIG)] = 10 ** 9
    return _emit(h, _pick_S(rng, h, 0.3, 0.9))


# ---------------------------------------------------------------- 对拍
def fuzz_small(rng, sub):
    n = rng.choice([1, 2, 3, 5, 8])
    h = [rng.randint(1, 12) for _ in range(n)]
    return _emit(h, _pick_S(rng, h, 0.05, 1.0))


def fuzz_mid(rng, sub):
    n = rng.choice([20, 60, 200, 400])
    h = [rng.randint(1, 10 ** 6) for _ in range(n)]
    return _emit(h, _pick_S(rng, h, 0.05, 1.0))


TEMPLATES = {
    "fixed_small": fixed_small,
    "fixed_exact": fixed_exact,
    "struct_sorted": struct_sorted,
    "struct_plateau": struct_plateau,
    "struct_mountain": struct_mountain,
    "struct_zigzag": struct_zigzag,
    "struct_small_wall": struct_small_wall,
    "rand_small": rand_small,
    "rand_big": rand_big,
    "rand_spikes": rand_spikes,
    "fuzz_small": fuzz_small,
    "fuzz_mid": fuzz_mid,
}

FUZZ = ["fuzz_small"]
FUZZ_MID = ["fuzz_mid"]
