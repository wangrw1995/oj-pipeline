ID = 1001
CODE = "WATER_STATION"
TITLE = "最优供水站选址【换根DP】"
LIMIT = 1
MEM = 128
TAGS = ["换根DP", "树形DP", "NOIP提高组"]
GLOBAL = """
- $1 \\leq n \\leq 10^5$
- $1 \\leq K, c_i \\leq 10^9$
- 保证输入是一棵树。
"""
SUBTASKS = {
    1: {
        "score": 30,
        "desc": "$n \\leq 20$，暴力枚举每个核心站位置，暴力树形DP即可通过",
        "n_max": 20
    },
    2: {
        "score": 30,
        "desc": "输入的树是一条链，每个节点度数不超过2，$n \\leq 1000$",
        "chain": True,
        "n_max": 1000
    },
    3: {
        "score": 40,
        "desc": "无特殊限制，$n \\leq 10^5$",
        "n_max": 100000
    }
}
TESTS = [
    (1, "small1"),
    (1, "small2"),
    (2, "chain1"),
    (2, "chain2"),
    (3, "large1"),
    (3, "large2")
]

def check(text, sub):
    lines = text.strip().split('\n')
    ptr = 0
    n, K = map(int, lines[ptr].split())
    ptr += 1
    c = list(map(int, lines[ptr].split()))
    ptr += 1
    deg = [0] * (n + 1)
    for _ in range(n - 1):
        u, v = map(int, lines[ptr].split())
        deg[u] += 1
        deg[v] += 1
        ptr += 1
    assert n <= sub.get("n_max"), f"n={n} exceeds limit {sub.get('n_max')}"
    if sub.get("chain", False):
        for d in deg:
            assert d <= 2, "node degree exceeds 2 for chain subtask"
    assert 1 <= K <= 10**9
    for ci in c:
        assert 1 <= ci <= 10**9
