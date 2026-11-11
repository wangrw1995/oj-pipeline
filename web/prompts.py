# -*- coding: utf-8 -*-
"""各槽位的提示词。

三条设计约束：
1. 每个提示词都要求 `===FILE: name===` 分块输出 —— 文件名在分隔符里，便于机器解析。
2. 每个提示词末尾带 [SLOT:xxx] 标记 —— mock 提供方按它回放，真实模型会忽略。
3. 审查类任务要求输出**结构化结论**（冲突列表），而不是"我觉得没问题"。
"""

OUT_FMT = """\
输出格式（严格遵守，不要输出任何多余解释）：
===FILE: 文件名===
文件内容
===FILE: 另一个文件名===
文件内容
"""

CONTRACT = """\
本工作流的机器契约（写文件时必须满足，否则闸门会红）：
- spec.py 必须定义：ID, CODE, TITLE, LIMIT, MEM, TAGS, SUBTASKS, TESTS, GLOBAL, check(text, sub)
- SUBTASKS 形如 {1: dict(score=30, desc="..."), ...}，score 之和必须正好 100
- TESTS 形如 [(子任务号, "模板名"), ...]，第 i 个元素就是第 i 个测试点
- 每个子任务的 score 必须能被它的测试点数整除
- check(text, sub) 负责断言一份输入是否满足该子任务的约束。
  **sub 传进来的是该子任务的 dict**（例如 {{"score": 30, "desc": "...", "sorted": True}}），
  要用 sub.get("键") 取约束，禁止写成 `if sub == 1:` 这种拿 dict 和整数比的形式——
  那样永远不会成立，等于没校验
- statement.md 用占位符 {{SUBTASK_TABLE}} {{GLOBAL}} {{SAMPLES}} {{CODE}} {{TITLE}} {{LIMIT}} {{MEM}}，
  禁止手写子任务表格和样例
"""


def _feedback(prev):
    if not prev:
        return ""
    return f"\n你上一轮的尝试没能通过闸门，失败原因如下，必须针对性修掉：\n{prev}\n"


# ---------------------------------------------------------------- 1 号
SUBTYPE_HINTS = {
    "树形dp": ["换根DP（二次扫描）", "树上背包 / 树形依赖背包", "树的最小支配集",
               "树的最大独立集", "树的直径 / 中心", "树上差分", "树上路径统计",
               "树形DP + 单调队列优化"],
    "状压dp": ["轮廓线 DP（插头 DP）", "枚举子集的子集（3^n）", "集合覆盖 DP",
               "TSP 类路径 DP", "状压 DP + 矩阵快速幂"],
    "二分答案": ["二分 + 贪心判定", "二分 + 并查集", "二分 + 最短路", "二分 + 网络流",
                 "二分 + 树状数组"],
    "贪心": ["交换论证", "相邻交换排序", "反悔贪心（堆）", "区间调度"],
    "最短路": ["分层图最短路", "差分约束", "最短路计数", "次短路", "最短路 + 状压"],
    "线段树": ["区间加区间和", "区间最值 + 二分", "线段树合并", "扫描线", "标记永久化"],
}


def subtype_list(topic):
    """按考点返回可用的子方向列表；没有对应菜单的返回空列表。"""
    key = str(topic or "").strip().lower()
    for k, v in SUBTYPE_HINTS.items():
        if k in key or key in k:
            return list(v)
    return []


def _subtype_menu(topic):
    key = str(topic or "").strip().lower()
    for k, v in SUBTYPE_HINTS.items():
        if k in key or key in k:
            picked = "、".join(v)
            return (f"""
这次的题目**必须从下面这些子方向里挑一个**，不要用最常见的那个
（比如树形DP 的"树上加权独立集/支配集"已经被反复出过了）：
{picked}
请把你选的那个子方向写进 TITLE 和 TAGS 里，方便以后查重。
""")
    return ""


def _subtype_line(seed):
    st = str(seed.get("subtype") or "").strip()
    if not st:
        return ""
    return (f"""
**本次指定的子方向：{st}**
请严格围绕这个子方向出题，不要换成别的（这是批量出题时用来错开考法的）。
""")


def p_spec(seed, prev=None, avoid=None):
    avoid_txt = ""
    if avoid:
        lines = "\n".join(f"- {a['title']}（{'、'.join(a['tags'][:4])}）" for a in avoid)
        avoid_txt = (f"""
**题库里已经有这些题，不要出成同类型**（考点组合、约束结构、场景都换一换）：
{lines}
""")
    return [
        {"role": "system", "content": "你是信息学奥赛命题流水线里的 1 号「作者」。"
                                      "你负责产出可被机器校验的命题文件。"},
        {"role": "user", "content": f"""\
根据下面的命题种子设计一道题。

考点：{seed['topic']}
期望难度：{seed['difficulty']}
分档设想：{seed.get('ladder') or '（自行设计三档）'}{_subtype_line(seed)}
{_subtype_menu(seed.get('topic'))}{avoid_txt}
要求：
1. 至少 3 个子任务，形成三档：小规模暴力可过 / 特殊性质可过 / 只有正解可过
2. 每个子任务至少 2 个测试点
3. 题面必须把输出定义写死（唯一整数？多关键字？取模？），不允许留歧义
4. 同时给出 2 组样例（sample/s1.in、sample/s1.ans、sample/s2.in、sample/s2.ans），
   样例答案必须是你手算的、确定的
{CONTRACT}
{_feedback(prev)}
请输出 3 类文件：spec.py、statement.md、sample/s1.in、sample/s1.ans、sample/s2.in、sample/s2.ans
{OUT_FMT}
[SLOT:spec]"""},
    ]


def p_brute_gen(statement, spec, required=None):
    need = ""
    if required:
        need = ("\n`gen.py` 的模板名必须和 spec.TESTS 里写的一字不差：\n"
                + "、".join(f"`{n}`" for n in required) + "\n")
    return [
        {"role": "system", "content": "你是 1 号「作者」。现在写两样东西：暴力，和数据生成器。"},
        {"role": "user", "content": f"""\
题面：
```markdown
{statement}
```

约束：
```python
{spec}
```
{need}
请写两个文件：

**① brute.cpp** —— 暴力，只要求能在子任务 1 的规模上跑得动，写得越笨越好，
结果必须精确，标准输入输出，C++17。

**② gen.py** —— 数据模板注册表。**现在还没有标程，你只需要产出输入，不用管答案。**
- 暴露 `TEMPLATES = {{模板名: 函数}}`，函数签名 `(rng, sub) -> 完整输入字符串`
- 提供 `FUZZ` 和 `FUZZ_MID` 两个列表（对拍用的小、中规模模板）
- 每个模板生成的输入都必须满足 check() 的全部 assert
- 读 sub 一律用 `sub.get("键", 默认值)`，不要用 `sub["键"]`

{code_rule("brute.cpp", "gen.py")}
{OUT_FMT}
[SLOT:brute_gen]"""},
    ]


def p_brute(statement, spec, role, feedback=""):
    fb = f"\n上一版没通过，问题在这里：\n{feedback}\n" if feedback else ""
    return [
        {"role": "system", "content": f"你是{role}。现在只写暴力，不写正解、不写解释。"},
        {"role": "user", "content": f"""\
题面：
```markdown
{statement}
```

约束：
```python
{spec}
```

请写 brute.cpp：**只要求能在子任务 1 的规模上跑得动**，写得越笨越好
（枚举所有方案 / 深搜 / 全排列都行）。

**不要试图想明白题目最优解是什么**——你要写的恰恰是"最笨的、把所有可能都试一遍"的做法。
想得越多越容易错，直接照题面的定义暴力模拟即可。

要求：
1. 完全按题面理解的题意实现，不要猜"出题人可能想要什么"
2. 结果必须精确，不能近似、不能剪枝到影响正确性
3. 标准输入输出，C++17
4. **题面规定的所有输出约定都必须照做**——包括无解时输出什么、并列怎么处理。
   题面没说清的地方，不要自己发明哨兵值（INT_MAX 之类），
   而是在文件顶部写一行 `// UNCLEAR: 这里题面没定义`，然后按最自然的理解实现

{fb}
{code_rule("brute.cpp")}
{OUT_FMT}
[SLOT:brute]"""},
    ]


def p_std(statement, spec, brutes):
    return [
        {"role": "system", "content": "你是 1 号「作者」。现在写正解，并把算法思路写清楚。"},
        {"role": "user", "content": f"""\
题面：
```markdown
{statement}
```

约束：
```python
{spec}
```

已有两份互相验证过的暴力（结果一致），你的正解必须和它们一致：
```cpp
{brutes}
```

请写两个文件：
1. `sol.cpp` —— 正解，必须能在最大数据上跑进时限的 30%
2. `approach.md` —— 十行以内，写清：用什么算法、关键那一步为什么成立、复杂度、
   你自己最没把握的一步

{code_rule("sol.cpp", "approach.md")}
{OUT_FMT}
[SLOT:sol]"""},
    ]


def p_statement_fix(spec, statement, missing):
    return [
        {"role": "system", "content": "你是 1 号「作者」。只修题面，不要动 spec。"},
        {"role": "user", "content": f"""\
你的 spec.py 已经通过校验，内容**不要再改**：
```python
{spec}
```

但你上一版 statement.md 缺少这些渲染占位符：{"、".join(missing)}
（缺 {{GLOBAL}} 通常意味着你压根没写"数据范围"这一节）

上一版题面：
```markdown
{statement}
```

请只输出**修正后的 statement.md**：把缺的章节补齐，并确保这三个占位符都原样出现在
对应的位置：
- `{{GLOBAL}}` 放在 `## 数据范围` 一节里
- `{{SUBTASK_TABLE}}` 放在 `## 子任务` 一节里
- `{{SAMPLES}}` 放在 `## 样例` 一节里

不要手写数据范围的具体数字——那些由 spec 渲染。

{OUT_FMT}
[SLOT:statement_fix]"""},
    ]


def p_adjudicate(statement, code_a, code_b, inp, out_a, out_b):
    return [
        {"role": "system", "content": "你是 3 号「审查者」。两份暴力算出了不同答案，你来定是谁错了。"},
        {"role": "user", "content": f"""\
题面：
```markdown
{statement}
```

第一份暴力（A）：
```cpp
{code_a}
```

第二份暴力（B）：
```cpp
{code_b}
```

同一组输入，两者答案不同。

输入：
```
{inp}
```

A 输出：{out_a}
B 输出：{out_b}

请判断到底是哪一种：

- `A错`：题面其实是清楚的，A 的实现有 bug（越界、初始值、边界条件……）
- `B错`：题面其实是清楚的，B 的实现有 bug
- `题面不清`：题面确实没交代某种情况（无解、并列、边界），两份代码都是"合理的理解"

注意：不要因为"我想不到哪种理解对"就选"题面不清"。
只有当你**指得出题面里缺了哪一句**时才选它。

{OUT_FMT}
===FILE: verdict.json===
{{"判定": "A错 或 B错 或 题面不清", "理由": "一句话说清分歧点"}}
[SLOT:adjudicate]"""},
    ]


def p_review_code(statement, approach, sol):
    return [
        {"role": "system", "content": "你是 3 号「审查者」。你不写实现，你只找漏洞。"
                                      "只说“看起来对”不算回答。"},
        {"role": "user", "content": f"""\
请审查这道题的**算法思路**和**代码实现**。

题面：
```markdown
{statement}
```

作者的算法思路 approach.md：
```markdown
{approach}
```

作者的标准程序 sol.cpp：
```cpp
{sol}
```

两件事分开查：

**A. 思路**：approach.md 里那条关键论证真的成立吗？
   - 如果某一步推不出来，指出是哪一步、为什么
   - 特别留意"小规模成立、大规模不成立"的贪心
**B. 代码**：sol.cpp 有没有溢出、越界、初始值、边界特判的问题？

输出一个文件：
===FILE: review.json===
{{"结论": "ok 或 problem",
  "分析": "用两三句话说明你验证了哪一步、为什么成立，或者为什么不成立",
  "问题": ["只有确实需要修改时才写进来，一条一行；没有就空数组"],
  "反例": "如果能构造出让 sol 出错的输入，把它原样写在这里（n ≤ 10，格式与题目一致）；构造不出来就留空字符串"}}

规矩：
- **"问题"只放真的需要改的**。你验证后认为没问题，就写"结论": "ok"、"问题": []，
  分析过程写进"分析"字段，不要塞进"问题"里——那会被当成真的有 bug。
- 反例必须是一个完整合法的输入，我们会直接拿它跑 sol 和暴力对拍。宁可不给，也别给没把握的。
[SLOT:review_code]"""},
    ]


def p_impl_plan(statement, spec):
    return [
        {"role": "system", "content": "你是 4 号「实现者」。第一步只出思路，不写代码。"},
        {"role": "user", "content": f"""\
题面：
```markdown
{statement}
```

约束：
```python
{spec}
```

请给出你的实现方案，**十行以内**：
1. 用什么算法
2. 复杂度，以及为什么能在 n ≤ 200 上跑得动
3. 打算怎么处理边界

不要写代码。想不出正解就直接写"用暴力枚举"，那也是合法答案——**能跑通的笨办法，胜过跑不通的聪明办法**。

{OUT_FMT}
[SLOT:impl_plan]"""},
    ]


def p_impl_code(statement, spec, plan):
    return [
        {"role": "system", "content": "你是 4 号「实现者」。按你上一步定的方案写代码，不要改方案。"},
        {"role": "user", "content": f"""\
题面：
```markdown
{statement}
```

约束：
```python
{spec}
```

你在上一步定下的方案：
```markdown
{plan}
```

请按这个方案写 ref.cpp，只需要在 n ≤ 200 上跑得动。

{code_rule("ref.cpp")}
{OUT_FMT}
[SLOT:impl_code]"""},
    ]


def p_gen(spec, sol, required=None, prev=None):
    need = ""
    if required:
        need = ("\n**模板名必须和 spec.TESTS 里写的一字不差**，需要提供的键就是这些：\n"
                + "、".join(f"`{n}`" for n in required)
                + "\n少一个都会导致闸门失败。\n")
    if prev:
        need += ("\n**这次是修 bug，不是重写文件。**\n"
                 "- 只改出问题的那几个模板，其它模板原样保留\n"
                 "- 改完每个模板生成的每一行数据，都必须满足 check() 里的所有 assert\n"
                 "- 特别检查：数值范围要落在题面约束内（比如 t_i 的上界），行数要等于 n 相关表达式\n")
    return [
        {"role": "system", "content": "你是 1 号「作者」，现在负责数据生成器。"},
        {"role": "user", "content": f"""\
请写 gen.py：按 spec.TESTS 的顺序，为每个测试点提供数据模板。

spec.py：
```python
{spec}
```

sol.cpp（标程，答案由它产出）：
```cpp
{sol}
```
{need}
要求：
1. 暴露 TEMPLATES 字典：{{模板名: 函数}}，函数签名 (rng, sub) -> 完整的输入字符串
2. 模板名前缀决定层次：fixed_ 卡边界 / struct_ 结构（链、星、全等、双峰、尖峰）/
   rand_ 随机 / fuzz_ 只用于对拍
3. 必须提供 FUZZ 和 FUZZ_MID 两个列表，元素是**模板名字符串**，供小数据/中数据对拍使用。
   正确写法：FUZZ = ["small_1", "small_2"]
   **不要**写成 [("small_1", {"max_n": 20})] 这种带参数的元组。
   **FUZZ 模板里读 sub 必须用 `sub.get("键", 默认值)`，不能用 `sub["键"]`**——
   对拍时传进去的是合并后的约束字典，缺键会直接抛 KeyError 把整关打挂
4. 生成器的每个参数都要自己算，不许写死常数，也不许产生违反 check() 的数据
5. 每个模板的 docstring 写清楚"这个点打的是什么错解"
{_feedback(prev)}
{OUT_FMT}
[SLOT:gen]"""},
    ]


def p_editorial(spec, statement, gen, calib):
    return [
        {"role": "system", "content": "你是 1 号「作者」，现在负责写题解。"},
        {"role": "user", "content": f"""\
请为这道题写题解 editorial.md。

spec.py：
```python
{spec}
```

statement.md：
```markdown
{statement}
```

数据模板 gen.py：
```python
{gen}
```

部分分实测结果（必须与题解里写的完全一致，不许夸大）：
```json
{calib}
```

要求：
1. 结构：思路 → 正确性证明 → 复杂度 → 部分分设计 → 易错点
2. "部分分设计"一节里，每个子任务的得分必须和上面的实测结果一字不差
3. 复杂度分析要具体到每一步，不要只写一个大 O
4. 易错点要写你在数据里真正针对过的那些

{OUT_FMT}
[SLOT:editorial]"""},
    ]


# ---------------------------------------------------------------- 2 号
def p_review(statement, spec):
    return [
        {"role": "system", "content": "你是 2 号「审题者」。你的任务是从做题人的角度找题面的坑。"},
        {"role": "user", "content": f"""\
下面是一道题的**题面**和它的 **spec.py**（spec 是机器契约：子任务、测试点、check()）。

题面：
```markdown
{statement}
```

spec.py：
```python
{spec}
```

请检查：**一个没看过 spec 的选手，只读题面，能不能唯一确定正确答案？**

重点核对这四件事，缺一件就是一个冲突：
1. 输入格式：每行几个数、顺序、可能跨行吗
2. 输出定义：输出什么（一个整数？一行三个数？）、怎么分隔、要不要取模
3. 边界行为：最小值/空集/无解/并列最优 时输出什么
4. 子任务：spec 里每个子任务的约束，题面的数据范围表里有没有对应上

判断标准很严：**只有"选手读完后仍然无法唯一确定答案"才算冲突**。
下面这些不算冲突，不要写进列表：
- spec.py 里的实现细节（check() 怎么写的、内部变量怎么命名）
- 题面用词不够优雅、语气不够好
- 你觉得"可能有人会误解"但题面其实说清楚了的情况

输出一个文件：
===FILE: review.json===
{{"理解": "用你自己的话复述这题的输入和输出", "冲突": [], "结论": "ok"}}

如果确实有冲突，"冲突"数组里每条写清楚：哪句话、缺什么、选手可能怎么误读。"结论"写 "ambiguous"。
[SLOT:review]"""},
    ]


def code_rule(*names):
    """代码类任务的输出格式规则。

    文件名必须逐个列出来——只在示例里写死一个名字，模型会照抄那个名字，
    然后因为"文件名不对"被判成没产出。
    """
    if not names:
        names = ("<上面要求的文件名>",)
    lines = "\n".join(f"  - `===FILE: {n}===` 后面紧跟文件内容" for n in names)
    return f"""\
输出必须是**纯文件**，不允许任何解释文字。你要输出的文件恰好是这些，名字一字不差：
{lines}
- 第一个字符必须是 `=`
- 不要先写"好的，我来写…"，不要用 ``` 把整个文件包起来
- 文件写完后直接结束，不要追加 ===END=== 之类的收尾标记
"""


CODE_RULE = code_rule()


def p_ref(statement, spec, prev=None):
    return [
        {"role": "system", "content": "你是 3 号「第三方」。你负责独立实现交叉验证。"
                                      "你只输出代码文件，不解释。"},
        {"role": "user", "content": f"""\
请根据题面写一份参考实现 ref.cpp。

题面：
```markdown
{statement}
```

约束（spec.py）：
```python
{spec}
```

要求：
1. 用你**自己**判断最自然正确的算法，不要假设出题人用了什么做法
2. 只需要在中等规模（n ≤ 2000）上跑得动，不需要最优复杂度
3. 如果题面某处有歧义，按你的理解实现，并在注释里写明你的假设

{CODE_RULE}
{_feedback(prev)}
{OUT_FMT}
[SLOT:ref]"""},
    ]


def p_wrong(spec, sol, gen, prev=None):
    return [
        {"role": "system", "content": "你是 4 号「对抗者」。你的任务不是帮忙，是找茬。"},
        {"role": "user", "content": f"""\
请写一批"必须被数据杀掉"的错解，以及一批"只应该拿部分分"的程序。

spec.py：
```python
{spec}
```

sol.cpp（标程）：
```cpp
{sol}
```

gen.py（数据模板）：
```python
{gen}
```

要写：
1. wrong/ 下 3 个错解（.cpp 或 .py 都行），从标程派生，覆盖：
   边界特判写错、把某个概念理解错、复杂度退化
2. partial/ 下 2~3 个只拿部分分的程序，每个子任务一个
3. partial/expected.json：{{"程序名": 期望得分}}，必须和子任务分值对得上

注意：wrong/ 里的程序会被要求在**所有**测试点上拿 0 分。
如果某个错解在数学上无法被某个测试点区分（例如答案为 0 时"最大值"和"求和"必然相等），
把它写进 wrong/allow.json 并注明原因，而不是假装它被杀了。
{_feedback(prev)}
{OUT_FMT}
[SLOT:wrong]"""},
    ]


# ---------------------------------------------------------------- 3 号
def p_ref_alt(statement, sol, prev=None):
    return [
        {"role": "system", "content": "你是 4 号「对抗者」。你负责用另一种算法交叉验证。"
                                      "你只输出代码文件，不解释。"},
        {"role": "user", "content": f"""\
题面：
```markdown
{statement}
```

出题人写的标程（**不要照抄它的做法**）：
```cpp
{sol}
```

要求：
1. 写一份 ref.cpp，算法必须和上面的标程**实质不同**
   （标程用二分你就用枚举，标程用单调栈你就用朴素扫描，标程用 DP 你就用搜索）
2. 允许更慢，只要在中等规模（n ≤ 2000）跑得动
3. 不要为了让结果和标程一致而妥协——你写你认为对的

{CODE_RULE}
{_feedback(prev)}
{OUT_FMT}
[SLOT:ref_alt]"""},
    ]
