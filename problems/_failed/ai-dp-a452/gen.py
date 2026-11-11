def generate_random_tree(rng, n):
    if n == 1:
        return []
    prufer = [rng.randint(1, n) for _ in range(n - 2)]
    count = [0] * (n + 1)
    for u in prufer:
        count[u] += 1
    leaves = []
    for i in range(1, n + 1):
        if count[i] == 0:
            leaves.append(i)
    edges = []
    for u in prufer:
        v = leaves.pop(0)
        edges.append((u, v, rng.randint(1, 1000)))
        count[u] -= 1
        if count[u] == 0:
            leaves.append(u)
    u = leaves.pop(0)
    v = leaves.pop(0)
    edges.append((u, v, rng.randint(1, 1000)))
    return edges

def gen_small(rng, sub):
    max_n = sub.get('max_n', 2000)
    n = rng.randint(1, max_n)
    a = [rng.randint(0, 1000) for _ in range(n)]
    edges = generate_random_tree(rng, n)
    lines = [str(n), ' '.join(map(str, a))]
    for u, v, w in edges:
        lines.append(f"{u} {v} {w}")
    return '\n'.join(lines) + '\n'

def gen_chain(rng, sub):
    max_n = sub.get('max_n', 100000)
    n = rng.randint(1, max_n)
    a = [rng.randint(0, 1000) for _ in range(n)]
    edges = []
    for i in range(1, n):
        edges.append((i, i + 1, rng.randint(1, 1000)))
    lines = [str(n), ' '.join(map(str, a))]
    for u, v, w in edges:
        lines.append(f"{u} {v} {w}")
    return '\n'.join(lines) + '\n'

def gen_normal(rng, sub):
    max_n = sub.get('max_n', 100000)
    n = rng.randint(1, max_n)
    a = [rng.randint(0, 1000) for _ in range(n)]
    edges = generate_random_tree(rng, n)
    lines = [str(n), ' '.join(map(str, a))]
    for u, v, w in edges:
        lines.append(f"{u} {v} {w}")
    return '\n'.join(lines) + '\n'

TEMPLATES = {
    "small": gen_small,
    "chain": gen_chain,
    "normal": gen_normal
}

FUZZ = ["small"]
FUZZ_MID = ["small", "chain", "normal"]
