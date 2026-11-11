ID = 1001
CODE = "TREEDP_REROOT_001"
TITLE = "「换根DP」便民核心站选址"
LIMIT = 1000
MEM = 256
TAGS = ["换根DP", "树形DP", "NOIP提高组"]

SUBTASKS = {
    1: {"score": 30, "desc": "n ≤ 1000，无特殊约束", "max_n": 1000},
    2: {"score": 30, "desc": "树为链，n ≤ 1e5", "is_chain": True, "max_n": 100000},
    3: {"score": 40, "desc": "无特殊约束，n ≤ 1e5", "max_n": 100000}
}

TESTS = [
    (1, "t1"), (1, "t2"), (1, "t3"),
    (2, "t4"), (2, "t5"), (2, "t6"),
    (3, "t7"), (3, "t8"), (3, "t9"), (3, "t10")
]

GLOBAL = """
1 ≤ n ≤ 100000
0 ≤ k ≤ n
1 ≤ a_i ≤ 1000
输入保证给出的图是一棵合法的无向树。
"""

def check(text, sub):
    lines = text.strip().split('\n')
    ptr = 0
    n, k = map(int, lines[ptr].split())
    ptr += 1
    a = list(map(int, lines[ptr].split()))
    ptr += 1
    deg = [0] * (n + 1)
    for _ in range(n - 1):
        u, v = map(int, lines[ptr].split())
        ptr += 1
        deg[u] += 1
        deg[v] += 1
    # 全局校验
    assert 1 <= n <= 100000
    assert 0 <= k <= n
    assert len(a) == n
    for num in a:
        assert num >= 1
    # 子任务校验
    if sub.get("max_n"):
        assert n <= sub["max_n"]
    if sub.get("is_chain"):
        cnt_deg1 = 0
        valid = True
        for i in range(1, n+1):
            if deg[i] == 1:
                cnt_deg1 += 1
            elif deg[i] != 2:
                valid = False
        assert cnt_deg1 == 2 and valid
