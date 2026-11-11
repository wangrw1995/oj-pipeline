import heapq
from random import Random
from typing import Callable, Dict, List

def random_tree(rng: Random, n: int) -> List[tuple]:
    if n == 1:
        return []
    prufer = [rng.randint(1, n) for _ in range(n - 2)]
    degree = [1] * (n + 1)
    for x in prufer:
        degree[x] += 1
    leaves = []
    for i in range(1, n + 1):
        if degree[i] == 1:
            heapq.heappush(leaves, i)
    edges = []
    for x in prufer:
        u = heapq.heappop(leaves)
        edges.append((u, x))
        degree[u] -= 1
        degree[x] -= 1
        if degree[x] == 1:
            heapq.heappush(leaves, x)
    u = heapq.heappop(leaves)
    v = heapq.heappop(leaves)
    edges.append((u, v))
    return edges

def chain_tree(rng: Random, n: int) -> List[tuple]:
    edges = []
    for i in range(1, n):
        edges.append((i, i + 1))
    perm = list(range(1, n + 1))
    rng.shuffle(perm)
    new_edges = []
    for u, v in edges:
        new_edges.append((perm[u - 1], perm[v - 1]))
    return new_edges

def gen_small1(rng: Random, sub: dict) -> str:
    n_max = sub.get("n_max", 20)
    n = rng.randint(2, n_max)
    K = rng.randint(1, 10**9)
    c = [rng.randint(1, 10**9) for _ in range(n)]
    edges = random_tree(rng, n)
    lines = [f"{n} {K}", ' '.join(map(str, c))]
    for u, v in edges:
        lines.append(f"{u} {v}")
    return '\n'.join(lines) + '\n'

def gen_small2(rng: Random, sub: dict) -> str:
    n_max = sub.get("n_max", 20)
    n = rng.randint(3, n_max)
    if rng.random() < 0.5:
        K = rng.randint(1, 100)
    else:
        K = rng.randint(1, 10**9)
    c = []
    for _ in range(n):
        if rng.random() < 0.3:
            c.append(rng.randint(1, 100))
        else:
            c.append(rng.randint(1, 10**9))
    edges = random_tree(rng, n)
    lines = [f"{n} {K}", ' '.join(map(str, c))]
    for u, v in edges:
        lines.append(f"{u} {v}")
    return '\n'.join(lines) + '\n'

def gen_chain1(rng: Random, sub: dict) -> str:
    n_max = sub.get("n_max", 1000)
    n = rng.randint(2, n_max)
    K = rng.randint(1, 10**9)
    c = [rng.randint(1, 10**9) for _ in range(n)]
    edges = chain_tree(rng, n)
    lines = [f"{n} {K}", ' '.join(map(str, c))]
    for u, v in edges:
        lines.append(f"{u} {v}")
    return '\n'.join(lines) + '\n'

def gen_chain2(rng: Random, sub: dict) -> str:
    n_max = sub.get("n_max", 1000)
    n = rng.randint(5, n_max)
    K = rng.randint(1, 10**5)
    c = [rng.randint(1, 10**5) for _ in range(n)]
    edges = chain_tree(rng, n)
    lines = [f"{n} {K}", ' '.join(map(str, c))]
    for u, v in edges:
        lines.append(f"{u} {v}")
    return '\n'.join(lines) + '\n'

def gen_large1(rng: Random, sub: dict) -> str:
    n_max = sub.get("n_max", 100000)
    n = n_max
    K = rng.randint(1, 10**9)
    c = [rng.randint(1, 10**9) for _ in range(n)]
    edges = random_tree(rng, n)
    lines = [f"{n} {K}", ' '.join(map(str, c))]
    for u, v in edges:
        lines.append(f"{u} {v}")
    return '\n'.join(lines) + '\n'

def gen_large2(rng: Random, sub: dict) -> str:
    n_max = sub.get("n_max", 100000)
    n = n_max
    K = rng.randint(1, 10**9)
    c = [rng.randint(1, 10**9) for _ in range(n)]
    root = rng.randint(1, n)
    edges = []
    for i in range(1, n + 1):
        if i != root:
            edges.append((root, i))
    lines = [f"{n} {K}", ' '.join(map(str, c))]
    for u, v in edges:
        lines.append(f"{u} {v}")
    return '\n'.join(lines) + '\n'

TEMPLATES: Dict[str, Callable] = {
    "small1": gen_small1,
    "small2": gen_small2,
    "chain1": gen_chain1,
    "chain2": gen_chain2,
    "large1": gen_large1,
    "large2": gen_large2
}

FUZZ: List[str] = ["small1", "small2"]
FUZZ_MID: List[str] = ["chain1", "chain2"]
