ID = 1001
CODE = "TREE_REROOT_MAX_SUM"
TITLE = "Maximum Root Function Sum (Rerooting DP)"
LIMIT = 1
MEM = 256
TAGS = ["Rerooting DP", "树形DP", "动态规划", "NOIP"]
GLOBAL = {
    "mod": 998244353,
    "max_n_global": 200000
}
SUBTASKS = {
    1: {"score": 30, "desc": "n ≤ 20，暴力可过", "max_n": 20},
    2: {"score": 30, "desc": "给定的树是一条链", "max_n": 200000, "is_chain": True},
    3: {"score": 40, "desc": "无特殊约束，n ≤ 2e5", "max_n": 200000}
}
TESTS = [
    (1, "small_1"),
    (1, "small_2"),
    (2, "chain_1"),
    (2, "chain_2"),
    (3, "general_1"),
    (3, "general_2")
]

def check(text, sub):
    lines = text.strip().split('\n')
    assert len(lines) >= 1
    n = int(lines[0])
    assert 1 <= n <= sub.get("max_n")
    assert len(lines) == n
    edges = []
    degree = [0]*(n+1)
    for line in lines[1:]:
        u, v = map(int, line.split())
        assert 1 <= u <= n and 1 <= v <= n
        assert u != v
        edges.append((min(u,v), max(u,v)))
        degree[u] += 1
        degree[v] += 1
    assert len(set(edges)) == n-1
    if sub.get("is_chain", False):
        if n == 1:
            return True
        cnt_deg1 = sum(1 for i in range(1, n+1) if degree[i] == 1)
        cnt_deg2 = sum(1 for i in range(1, n+1) if degree[i] == 2)
        assert cnt_deg1 == 2 and cnt_deg1 + cnt_deg2 == n
    return True
