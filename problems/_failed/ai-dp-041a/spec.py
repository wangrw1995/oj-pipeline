ID = 1001
CODE = "TREE_CHARGE"
TITLE = "换根DP：城市充电桩选址"
LIMIT = 1
MEM = 256
TAGS = ["换根DP", "动态规划", "二次扫描", "NOIP提高组"]
GLOBAL = """
- 对于所有测试数据，满足 $1 \\leq n \\leq 10^5$，$0 \\leq k \\leq 20$，$1 \\leq w_i \\leq 10^3$，$1 \\leq a_i \\leq 10^3$。
- 输入保证给出的是一棵合法的无根树。
"""
SUBTASKS = {
    1: {"score": 30, "desc": "n ≤ 20，k ≤ 10，暴力枚举可过", "max_n":20, "max_k":10},
    2: {"score": 30, "desc": "特殊性质：树为链或k=0，可使用针对性算法通过", "special": True},
    3: {"score": 40, "desc": "无特殊限制，仅正解可通过", "max_n":100000, "max_k":20}
}
TESTS = [
    (1, "small_1"), (1, "small_2"), (1, "small_3"),
    (2, "chain_1"), (2, "k0_1"), (2, "chain_2"),
    (3, "normal_1"), (3, "normal_2"), (3, "normal_3"), (3, "normal_4")
]

def check(text, sub):
    lines = text.strip().split('\n')
    ptr = 0
    n, k = map(int, lines[ptr].split())
    ptr +=1
    edges = []
    deg = [0]*(n+1)
    for _ in range(n-1):
        u, v, w = map(int, lines[ptr].split())
        edges.append((u,v,w))
        deg[u] +=1
        deg[v] +=1
        ptr +=1
    a = list(map(int, lines[ptr].split()))
    # 通用校验
    assert 1<=n<=10**5
    assert 0<=k<=20
    for u,v,w in edges:
        assert 1<=u<=n and 1<=v<=n and u!=v
        assert w>=1
    for num in a:
        assert num>=1
    # 子任务校验
    if sub.get("max_n"):
        assert n <= sub["max_n"]
    if sub.get("max_k"):
        assert k <= sub["max_k"]
    if sub.get("special"):
        is_chain = (deg.count(1) == 2) and all(x<=2 for x in deg[1:])
        assert k==0 or is_chain
