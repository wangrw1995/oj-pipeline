ID = "TP001"
CODE = "firestation"
TITLE = "村庄消防站选址（换根DP）"
LIMIT = 1000
MEM = 256
TAGS = ["换根DP", "二次扫描", "树形DP", "NOIP提高组"]
GLOBAL = """- 对于所有测试数据：$1 \\le n \\le 10^5$，$0 \\le a_i \\le 10^3$，$1 \\le w \\le 10^3$，输入保证为合法无根树。"""

SUBTASKS = {
    1: {"score": 30, "desc": "$n \\le 2000$，无特殊限制", "max_n": 2000},
    2: {"score": 30, "desc": "$n \\le 10^5$，树为链结构", "max_n": 100000, "is_chain": True},
    3: {"score": 40, "desc": "无特殊限制，$n \\le 10^5$", "max_n": 100000}
}

TESTS = [
    (1, "small"),
    (1, "small"),
    (2, "chain"),
    (2, "chain"),
    (3, "normal"),
    (3, "normal")
]

def check(text, sub):
    tokens = text.strip().split()
    ptr = 0
    n = int(tokens[ptr])
    ptr += 1
    assert 1 <= n <= sub.get("max_n"), f"n={n}超出范围"
    a = list(map(int, tokens[ptr:ptr+n]))
    ptr += n
    for num in a:
        assert num >= 0, "a[i]不能为负数"
    deg = [0]*(n+1)
    for _ in range(n-1):
        u = int(tokens[ptr])
        v = int(tokens[ptr+1])
        w = int(tokens[ptr+2])
        ptr += 3
        assert 1 <= u <= n and 1 <= v <= n, "节点编号非法"
        assert w >= 1, "边权不能小于1"
        deg[u] += 1
        deg[v] += 1
    if sub.get("is_chain", False):
        if n == 1:
            return
        cnt1 = sum(1 for i in range(1, n+1) if deg[i] == 1)
        cnt2 = sum(1 for i in range(1, n+1) if deg[i] == 2)
        assert cnt1 == 2 and cnt1 + cnt2 == n, "不是链结构"
