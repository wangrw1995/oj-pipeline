import heapq

def gen_random_tree(rng, n):
    if n == 1:
        return []
    prufer = [rng.randint(1, n) for _ in range(n-2)]
    degree = [0] * (n + 1)
    for u in prufer:
        degree[u] += 1
    for i in range(1, n+1):
        degree[i] += 1
    leaves = []
    for i in range(1, n+1):
        if degree[i] == 1:
            heapq.heappush(leaves, i)
    edges = []
    for u in prufer:
        v = heapq.heappop(leaves)
        edges.append((u, v))
        degree[u] -= 1
        if degree[u] == 1:
            heapq.heappush(leaves, u)
    u = heapq.heappop(leaves)
    v = heapq.heappop(leaves)
    edges.append((u, v))
    return edges

def gen_chain(rng, n):
    edges = []
    for i in range(1, n):
        edges.append((i, i+1))
    return edges

def t1(rng, sub):
    return """5 1
1 2 3 4 5
1 2
1 3
2 4
2 5
"""

def t2(rng, sub):
    return """6 2
1 1 1 1 1 1
1 2
2 3
3 4
4 5
5 6
"""

def t3(rng, sub):
    max_n = sub.get("max_n", 1000)
    n = rng.randint(500, max_n)
    k = rng.randint(0, n)
    a = [str(rng.randint(1, 1000)) for _ in range(n)]
    edges = gen_random_tree(rng, n)
    lines = []
    lines.append(f"{n} {k}")
    lines.append(" ".join(a))
    for u, v in edges:
        lines.append(f"{u} {v}")
    return "\n".join(lines) + "\n"

def t4(rng, sub):
    max_n = sub.get("max_n", 100000)
    n = max_n
    k = 0
    a = [str(rng.randint(1, 1000)) for _ in range(n)]
    edges = gen_chain(rng, n)
    lines = []
    lines.append(f"{n} {k}")
    lines.append(" ".join(a))
    for u, v in edges:
        lines.append(f"{u} {v}")
    return "\n".join(lines) + "\n"

def t5(rng, sub):
    max_n = sub.get("max_n", 100000)
    n = max_n
    k = rng.randint(100, 10000)
    a = [str(rng.randint(1, 1000)) for _ in range(n)]
    edges = gen_chain(rng, n)
    lines = []
    lines.append(f"{n} {k}")
    lines.append(" ".join(a))
    for u, v in edges:
        lines.append(f"{u} {v}")
    return "\n".join(lines) + "\n"

def t6(rng, sub):
    max_n = sub.get("max_n", 100000)
    n = max_n
    k = rng.randint(50000, n)
    a = [str(rng.randint(1, 1000)) for _ in range(n)]
    edges = gen_chain(rng, n)
    lines = []
    lines.append(f"{n} {k}")
    lines.append(" ".join(a))
    for u, v in edges:
        lines.append(f"{u} {v}")
    return "\n".join(lines) + "\n"

def t7(rng, sub):
    max_n = sub.get("max_n", 100000)
    n = max_n
    k = 0
    a = [str(rng.randint(1, 1000)) for _ in range(n)]
    edges = gen_random_tree(rng, n)
    lines = []
    lines.append(f"{n} {k}")
    lines.append(" ".join(a))
    for u, v in edges:
        lines.append(f"{u} {v}")
    return "\n".join(lines) + "\n"

def t8(rng, sub):
    max_n = sub.get("max_n", 100000)
    n = max_n
    k = 10
    a = [str(rng.randint(1, 1000)) for _ in range(n)]
    edges = gen_random_tree(rng, n)
    lines = []
    lines.append(f"{n} {k}")
    lines.append(" ".join(a))
    for u, v in edges:
        lines.append(f"{u} {v}")
    return "\n".join(lines) + "\n"

def t9(rng, sub):
    max_n = sub.get("max_n", 100000)
    n = max_n
    k = rng.randint(100, 10000)
    a = [str(rng.randint(1, 1000)) for _ in range(n)]
    edges = gen_random_tree(rng, n)
    lines = []
    lines.append(f"{n} {k}")
    lines.append(" ".join(a))
    for u, v in edges:
        lines.append(f"{u} {v}")
    return "\n".join(lines) + "\n"

def t10(rng, sub):
    max_n = sub.get("max_n", 100000)
    n = max_n
    k = rng.randint(50000, n)
    a = [str(rng.randint(1, 1000)) for _ in range(n)]
    edges = gen_random_tree(rng, n)
    lines = []
    lines.append(f"{n} {k}")
    lines.append(" ".join(a))
    for u, v in edges:
        lines.append(f"{u} {v}")
    return "\n".join(lines) + "\n"

def fuzz_small(rng, sub):
    n = rng.randint(10, 200)
    k = rng.randint(0, n)
    a = [str(rng.randint(1, 1000)) for _ in range(n)]
    edges = gen_random_tree(rng, n) if rng.random() > 0.5 else gen_chain(rng, n)
    lines = [f"{n} {k}", " ".join(a)] + [f"{u} {v}" for u, v in edges]
    return "\n".join(lines) + "\n"

def fuzz_mid_chain(rng, sub):
    n = rng.randint(1000, 10000)
    k = rng.randint(0, n)
    a = [str(rng.randint(1, 1000)) for _ in range(n)]
    edges = gen_chain(rng, n)
    lines = [f"{n} {k}", " ".join(a)] + [f"{u} {v}" for u, v in edges]
    return "\n".join(lines) + "\n"

def fuzz_mid_tree(rng, sub):
    n = rng.randint(1000, 10000)
    k = rng.randint(0, n)
    a = [str(rng.randint(1, 1000)) for _ in range(n)]
    edges = gen_random_tree(rng, n)
    lines = [f"{n} {k}", " ".join(a)] + [f"{u} {v}" for u, v in edges]
    return "\n".join(lines) + "\n"

TEMPLATES = {
    "t1": t1,
    "t2": t2,
    "t3": t3,
    "t4": t4,
    "t5": t5,
    "t6": t6,
    "t7": t7,
    "t8": t8,
    "t9": t9,
    "t10": t10,
    "fuzz_small": fuzz_small,
    "fuzz_mid_chain": fuzz_mid_chain,
    "fuzz_mid_tree": fuzz_mid_tree
}

FUZZ = ["t1", "t2", "fuzz_small"]
FUZZ_MID = ["fuzz_mid_chain", "fuzz_mid_tree"]
