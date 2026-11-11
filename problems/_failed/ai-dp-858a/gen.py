def small_random(rng, sub):
    max_n = sub.get("max_n", 1000)
    n = rng.randint(1, max_n)
    d = rng.randint(0, n)
    w = rng.randint(1, 1000)
    lines = [f"{n} {d} {w}"]
    for _ in range(n):
        c = rng.randint(1, 1000)
        cost = rng.randint(1, 10**9)
        lines.append(f"{c} {cost}")
    if n > 1:
        for i in range(2, n + 1):
            parent = rng.randint(1, i - 1)
            lines.append(f"{i} {parent}")
    return "\n".join(lines) + "\n"

def chain_case(rng, sub):
    max_n = sub.get("max_n", 100000)
    n = rng.randint(1, max_n)
    d = rng.randint(0, n)
    w = rng.randint(1, 1000)
    lines = [f"{n} {d} {w}"]
    for _ in range(n):
        c = rng.randint(1, 1000)
        cost = rng.randint(1, 10**9)
        lines.append(f"{c} {cost}")
    for i in range(1, n):
        lines.append(f"{i} {i+1}")
    return "\n".join(lines) + "\n"

TEMPLATES = {
    "small_random": small_random,
    "chain_case": chain_case,
    "large_random": small_random
}

FUZZ = [
    ("small_random", {"max_n": 20}),
    ("chain_case", {"max_n": 20})
]

FUZZ_MID = [
    ("small_random", {"max_n": 200}),
    ("chain_case", {"max_n": 500})
]
