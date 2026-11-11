ID = "NOIP2024_TREE_DP_003"
CODE = "VILLAGE_MARKET"
TITLE = "【换根DP】村庄集市选址"
LIMIT = 1000
MEM = 262144
TAGS = ["换根DP", "树形DP", "NOIP提高组"]

SUBTASKS = {
    1: {"score": 30, "desc": "n ≤ 2000，暴力枚举每个点计算可过", "max_n": 2000},
    2: {"score": 30, "desc": "树是一条链，可通过前缀和特殊处理通过", "is_chain": True, "max_n": 100000},
    3: {"score": 40, "desc": "无特殊限制，满数据", "max_n": 100000}
}

TESTS = [
    (1, "small"), (1, "small"),
    (2, "chain"), (2, "chain"), (2, "chain"),
    (3, "large"), (3, "large"), (3, "large"), (3, "large")
]

GLOBAL = """
1. 第一行一个正整数 $n$，表示村庄的数量。
2. 第二行 $n$ 个正整数 $w_1, w_2, \dots, w_n$，其中 $w_i$ 表示第 $i$ 个村庄的人数。
3. 第三行 $n$ 个非负整数 $c_1, c_2, \dots, c_n$，其中 $c_i$ 表示在第 $i$ 个村庄举办集市的固定成本。
4. 接下来 $n-1$ 行，每行三个正整数 $u, v, k$，表示村庄 $u$ 和 $v$ 之间有一条长度为 $k$ 的双向道路。
保证输入的道路构成一棵树，$1 \le n \le 10^5, 1 \le w_i \le 10^3, 0 \le c_i \le 10^9, 1 \le k \le 10^3$。
"""

def check(text, sub):
    lines = text.strip().split('\n')
    ptr = 0
    n = int(lines[ptr])
    ptr += 1
    max_n = sub.get("max_n", 100000)
    assert 1 <= n <= max_n
    w = list(map(int, lines[ptr].split()))
    ptr += 1
    assert len(w) == n
    for num in w:
        assert 1 <= num <= 1000
    c = list(map(int, lines[ptr].split()))
    ptr += 1
    assert len(c) == n
    for num in c:
        assert 0 <= num <= 10**9
    adj = [[] for _ in range(n+1)]
    for _ in range(n-1):
        u, v, k = map(int, lines[ptr].split())
        ptr += 1
        assert 1 <= u <= n and 1 <= v <= n and u != v
        assert 1 <= k <= 1000
        adj[u].append(v)
        adj[v].append(u)
    if sub.get("is_chain", False):
        deg = [len(lst) for lst in adj[1:]]
        cnt_end = 0
        for d in deg:
            assert d in (1, 2)
            if d == 1:
                cnt_end += 1
        assert cnt_end == 2
    visited = [False]*(n+1)
    q = [1]
    visited[1] = True
    cnt = 1
    while q:
        u = q.pop(0)
        for v in adj[u]:
            if not visited[v]:
                visited[v] = True
                cnt += 1
                q.append(v)
    assert cnt == n
