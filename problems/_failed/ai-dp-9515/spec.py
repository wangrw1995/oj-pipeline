ID = "TP001"
CODE = "tree_knapsack_monitor"
TITLE = "树上背包：自然保护区监测站建设"
LIMIT = 1
MEM = 256
TAGS = ["动态规划", "树形DP", "树上背包", "NOIP"]

SUBTASKS = {
    1: {"score": 30, "desc": "n ≤ 20，m ≤ 20，无特殊性质", "n_max": 20, "m_max": 20},
    2: {"score": 30, "desc": "树为一条链，n ≤ 1000，m ≤ 100", "is_chain": True, "n_max": 1000, "m_max": 100},
    3: {"score": 40, "desc": "无特殊性质，n ≤ 200，m ≤ 200", "n_max": 200, "m_max": 200},
}

TESTS = [
    (1, "small_random_1"),
    (1, "small_random_2"),
    (2, "chain_1"),
    (2, "chain_2"),
    (3, "normal_1"),
    (3, "normal_2"),
]

GLOBAL = {
    "n_min": 1,
    "cost_min": 1,
    "cost_max": 100,
    "val_min": 1,
    "val_max": 100,
}

def check(text, sub):
    data = list(map(int, text.strip().split()))
    ptr = 0
    n = data[ptr]
    ptr += 1
    m = data[ptr]
    ptr += 1
    cost = data[ptr:ptr + n]
    ptr += n
    val = data[ptr:ptr + n]
    ptr += n
    adj = [[] for _ in range(n + 1)]
    for _ in range(n - 1):
        u = data[ptr]
        v = data[ptr + 1]
        adj[u].append(v)
        adj[v].append(u)
        ptr += 2
    # 校验基本范围
    assert n >= GLOBAL["n_min"], "n too small"
    assert n <= sub.get("n_max"), f"n exceed subtask limit {sub.get('n_max')}"
    assert m <= sub.get("m_max"), f"m exceed subtask limit {sub.get('m_max')}"
    for c in cost:
        assert GLOBAL["cost_min"] <= c <= GLOBAL["cost_max"], "cost out of range"
    for vv in val:
        assert GLOBAL["val_min"] <= vv <= GLOBAL["val_max"], "val out of range"
    # 校验链约束
    if sub.get("is_chain", False):
        deg = [len(lst) for lst in adj]
        for d in deg[1:]:
            assert d <= 2, "chain subtask node degree cannot exceed 2"
        if n >= 2:
            assert deg[1] == 1, "chain subtask root degree must be 1"
    return True
