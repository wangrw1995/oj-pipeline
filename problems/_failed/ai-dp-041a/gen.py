def gen_random_tree(n, rng):
    edges = []
    for i in range(2, n+1):
        u = rng.randint(1, i-1)
        v = i
        w = rng.randint(1, 1000)
        edges.append((u, v, w))
    rng.shuffle(edges)
    return edges

def gen_chain(n, rng):
    edges = []
    for i in range(1, n):
        u = i
        v = i+1
        w = rng.randint(1, 1000)
        edges.append((u, v, w))
    rng.shuffle(edges)
    return edges

def gen_a(n, rng):
    return [rng.randint(1, 1000) for _ in range(n)]

def small(rng, sub):
    max_n = sub.get("max_n", 20)
    n = rng.randint(2, max_n)
    max_k = sub.get("max_k", 10)
    k = rng.randint(0, min(max_k, n-1))
    edges = gen_random_tree(n, rng)
    a = gen_a(n, rng)
    lines = [f"{n} {k}"]
    for u, v, w in edges:
        lines.append(f"{u} {v} {w}")
    lines.append(" ".join(map(str, a)))
    return "\n".join(lines)

def chain(rng, sub):
    max_n = sub.get("max_n", 100000)
    n = rng.randint(2, max_n)
    k = rng.randint(0, min(20, n-1))
    edges = gen_chain(n, rng)
    a = gen_a(n, rng)
    lines = [f"{n} {k}"]
    for u, v, w in edges:
        lines.append(f"{u} {v} {w}")
    lines.append(" ".join(map(str, a)))
    return "\n".join(lines)

def k0(rng, sub):
    max_n = sub.get("max_n", 100000)
    n = rng.randint(2, max_n)
    k = 0
    edges = gen_random_tree(n, rng)
    a = gen_a(n, rng)
    lines = [f"{n} {k}"]
    for u, v, w in edges:
        lines.append(f"{u} {v} {w}")
    lines.append(" ".join(map(str, a)))
    return "\n".join(lines)

def normal(rng, sub):
    max_n = sub.get("max_n", 100000)
    n = rng.randint(2, max_n)
    k = rng.randint(0, min(20, n-1))
    edges = gen_random_tree(n, rng)
    a = gen_a(n, rng)
    lines = [f"{n} {k}"]
    for u, v, w in edges:
        lines.append(f"{u} {v} {w}")
    lines.append(" ".join(map(str, a)))
    return "\n".join(lines)

TEMPLATES = {
    "small_1": small,
    "small_2": small,
    "small_3": small,
    "chain_1": chain,
    "k0_1": k0,
    "chain_2": chain,
    "normal_1": normal,
    "normal_2": normal,
    "normal_3": normal,
    "normal_4": normal,
}

FUZZ = ["small_1", "small_2", "small_3"]
FUZZ_MID = ["chain_1", "k0_1", "normal_1"]
