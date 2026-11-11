def gen_small(rng, sub):
    n_max = sub.get("n_max", 20)
    m_max = sub.get("m_max", 20)
    n = rng.randint(1, n_max)
    m = rng.randint(1, m_max)
    c = [rng.randint(1, m) for _ in range(n)]
    v = [rng.randint(1, 1000) for _ in range(n)]
    edges = []
    for i in range(2, n + 1):
        fa = rng.randint(1, i - 1)
        edges.append((fa, i))
    rng.shuffle(edges)
    res = [f"{n} {m}"]
    for ci, vi in zip(c, v):
        res.append(f"{ci} {vi}")
    for u, w in edges:
        res.append(f"{u} {w}")
    return '\n'.join(res) + '\n'

def gen_chain(rng, sub):
    n_max = sub.get("n_max", 200)
    m_max = sub.get("m_max", 200)
    n = rng.randint(1, n_max)
    m = rng.randint(1, m_max)
    c = [rng.randint(1, m) for _ in range(n)]
    v = [rng.randint(1, 1000) for _ in range(n)]
    edges = []
    for i in range(1, n):
        edges.append((i, i + 1))
    rng.shuffle(edges)
    res = [f"{n} {m}"]
    for ci, vi in zip(c, v):
        res.append(f"{ci} {vi}")
    for u, w in edges:
        res.append(f"{u} {w}")
    return '\n'.join(res) + '\n'

def gen_normal(rng, sub):
    n_max = sub.get("n_max", 1000)
    m_max = sub.get("m_max", 1000)
    n = rng.randint(1, n_max)
    m = rng.randint(1, m_max)
    c = [rng.randint(1, m) for _ in range(n)]
    v = [rng.randint(1, 1000) for _ in range(n)]
    edges = []
    for i in range(2, n + 1):
        fa = rng.randint(1, i - 1)
        edges.append((fa, i))
    rng.shuffle(edges)
    res = [f"{n} {m}"]
    for ci, vi in zip(c, v):
        res.append(f"{ci} {vi}")
    for u, w in edges:
        res.append(f"{u} {w}")
    return '\n'.join(res) + '\n'

TEMPLATES = {
    "small": gen_small,
    "chain": gen_chain,
    "normal": gen_normal
}

FUZZ = ["small"]
FUZZ_MID = ["chain", "normal"]
