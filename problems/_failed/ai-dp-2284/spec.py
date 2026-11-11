ID = 1001
CODE = "colony"
TITLE = "[树上背包] 星际殖民计划"
LIMIT = 1
MEM = 256
TAGS = ["动态规划", "树形DP", "树上背包", "NOIP提高组"]

SUBTASKS = {
    1: {"score": 30, "desc": "n ≤ 20，m ≤ 20，暴力可过", "n_max": 20, "m_max": 20},
    2: {"score": 30, "desc": "树为一条链，n ≤ 200，m ≤ 200，线性DP可过", "is_chain": True, "n_max": 200, "m_max": 200},
    3: {"score": 40, "desc": "无特殊性质，n ≤ 1000，m ≤ 1000，需正解树上背包", "n_max": 1000, "m_max": 1000}
}

TESTS = [
    (1, "small"), (1, "small"), (1, "small"),
    (2, "chain"), (2, "chain"), (2, "chain"),
    (3, "normal"), (3, "normal"), (3, "normal"), (3, "normal")
]

GLOBAL = """
输入格式：
第一行两个正整数n, m，表示空间站总数和总资源量。
接下来n行，每行两个正整数c_i, v_i，分别表示第i个空间站建立殖民点的资源消耗和收益。
接下来n-1行，每行两个正整数u, v，表示两个空间站之间有空间桥连接。
输出格式：
输出一个整数，表示在总资源不超过m的情况下能获得的最大收益。
数据范围：
1 ≤ n ≤ 1000，1 ≤ m ≤ 1000，1 ≤ c_i ≤ m，1 ≤ v_i ≤ 1000。
树的根为1号空间站。
"""

def check(text, sub):
    tokens = list(map(int, text.strip().split()))
    ptr = 0
    n = tokens[ptr]
    ptr += 1
    m = tokens[ptr]
    ptr += 1
    ptr += 2 * n  # 跳过c_i和v_i
    deg = [0] * (n + 1)
    for _ in range(n - 1):
        u = tokens[ptr]
        v = tokens[ptr + 1]
        ptr += 2
        deg[u] += 1
        deg[v] += 1
    # 校验基础范围
    assert n <= sub.get("n_max"), f"n={n}超过子任务限制{sub.get('n_max')}"
    assert m <= sub.get("m_max"), f"m={m}超过子任务限制{sub.get('m_max')}"
    # 校验是否是链
    if sub.get("is_chain", False):
        cnt1 = 0
        valid = True
        for i in range(1, n+1):
            if deg[i] == 1:
                cnt1 += 1
            elif deg[i] != 2:
                valid = False
        assert cnt1 == 2 and valid, "子任务要求树为链，但输入不符合"
