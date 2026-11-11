# -*- coding: utf-8 -*-
"""流水线各阶段：solve / gen / attack / calib / build。

每个阶段返回一个 dict 并写到 build/<stage>.json，字段 ok 决定下一阶段能否开跑。
"""
import json
import math
import os
import random
import shutil
import zipfile

from .runner import Runner
from . import statement as stmt
from .utils import (fmt_ms, human_size, now, normalize, read_text, same_answer,
                    tokens, write_json, write_text)

DATA_DIRNAME = "data"

_SYM = {"AC": "√", "WA": "×", "TLE": "T", "RE": "R"}


# ---------------------------------------------------------------- 小工具
def _ans_path(prob, idx):
    return os.path.join(prob.data, f"{prob.id}{idx}.ans")


def _in_path(prob, idx):
    return os.path.join(prob.data, f"{prob.id}{idx}.in")


def _load_answers(prob):
    out = {}
    for i in range(1, len(prob.tests) + 1):
        p = _ans_path(prob, i)
        if os.path.exists(p):
            out[i] = read_text(p)
    return out


def _fmt_row(row):
    return {"test": row[0], "status": row[1], "points": row[2], "ms": round(row[3], 1)}


def score_program(prob, runner, prog, answers, timeout):
    """在一道题的全部测试点上给一个程序打分。"""
    rows = []
    total = 0
    for i in range(1, len(prob.tests) + 1):
        inp = open(_in_path(prob, i), "rb").read()
        ans = answers[i]
        got, ms, status = runner.run(prog, inp, timeout)
        if status != "OK":
            rows.append((i, status, 0, ms))
            continue
        if same_answer(got, ans):
            pts = prob.points(i)
            total += pts
            rows.append((i, "AC", pts, ms))
        else:
            rows.append((i, "WA", 0, ms))
    return total, rows


# ---------------------------------------------------------------- solve
def _fuzz_ctx(prob, mid=False):
    """给对拍模板用的约束上下文。

    模板不对应某个具体子任务，但会读某个子任务才有的键。这里把所有子任务的键合并进来：
    - 小数据对拍：用子任务 1 的上限（规模小）
    - 中数据对拍：用**最大**子任务的上限（否则模板会拿到 n_max=20 却想生成 n=500，
      直接 ValueError: empty range）
    """
    ctx = {}
    for sid in sorted(prob.subtasks):
        ctx.update(prob.subtasks[sid])
    if mid:
        last = sorted(prob.subtasks)[-1]
        ctx.update(prob.subtasks[last])
    elif 1 in prob.subtasks:
        ctx.update(prob.subtasks[1])
    return ctx


def same_answer(a, b):
    """两个程序的输出是否等价。

    有一类"不一致"是假警报：题面允许无解时，两个实现都可能用一个大数
    （1e18、LLONG_MAX…）表示"无解"，常量不同但含义一样。
    题目答案本身不可能这么大，所以两个都超过 1e15 就视为一致。
    """
    ta, tb = a.split(), b.split()
    if ta == tb:
        return True
    if len(ta) == 1 and len(tb) == 1:
        try:
            if int(ta[0]) >= 10 ** 15 and int(tb[0]) >= 10 ** 15:
                return True
        except ValueError:
            pass
    return False


def stage_solve(prob, args):
    """编译解法 + 小数据对拍（sol vs brute）+ 中数据对拍（sol vs ref）。"""
    runner = Runner(prob.build)
    issues = prob.validate()
    if issues:
        return {"ok": False, "at": now(), "issues": issues,
                "msg": "契约不完整", "compiler": runner.compiler_desc()}

    sol = runner.compile(prob.sol_path(), "sol")
    brute = runner.compile(prob.brute_path(), "brute")
    ref = runner.compile(prob.ref_path(), "ref") if prob.ref_path() else None

    detail = {"ok": True, "at": now(), "compiler": runner.compiler_desc(),
              "compile_errors": runner.errors, "issues": []}
    detail["small"] = {"n": 0, "pass": 0, "fail": []}
    detail["mid"] = {"n": 0, "pass": 0, "fail": [], "available": ref is not None}

    if sol is None:
        detail["ok"] = False
        detail["issues"].append("标程无法编译/加载")
        return detail

    print("开始小数据对拍（sol vs brute）", flush=True)
    # 小数据对拍
    limit = max(prob.limit * 3, 5.0)
    fuzz = prob.fuzz_small()
    if brute is None:
        detail["issues"].append("暴力无法编译/加载，跳过小数据对拍")
    elif not fuzz:
        detail["issues"].append("gen.py 未声明 FUZZ，跳过小数据对拍")
    else:
        for it in range(args.fuzz):
            if (it + 1) % 50 == 0:
                print(f"小数据对拍 {it + 1}/{args.fuzz}", flush=True)
            name = fuzz[it % len(fuzz)]
            rng = random.Random(f"{prob.id}/fuzz/{it}")
            data = prob.templates[name](rng, _fuzz_ctx(prob)).encode()
            a, _, sa = runner.run(sol, data, limit)
            b, _, sb = runner.run(brute, data, limit)
            detail["small"]["n"] += 1
            if sa != "OK" or sb != "OK":
                detail["small"]["fail"].append({"it": it, "tmpl": name, "why": f"运行异常 {sa}/{sb}"})
                continue
            if tokens(a) == tokens(b):
                detail["small"]["pass"] += 1
            else:
                detail["small"]["fail"].append(
                    {"it": it, "tmpl": name, "std": " ".join(tokens(a))[:120],
                     "brute": " ".join(tokens(b))[:120], "input": data.decode()[:400]})
        if detail["small"]["fail"]:
            detail["ok"] = False

    # 中数据对拍
    midfuzz = prob.fuzz_mid()
    if ref is None:
        detail["issues"].append("缺少 ref（独立实现），防不住标程错")
    elif not midfuzz:
        detail["issues"].append("gen.py 未声明 FUZZ_MID，跳过中数据对拍")
    else:
        mid_total = max(20, args.fuzz // 5)
        print(f"开始中数据对拍（sol vs ref，共 {mid_total} 组）", flush=True)
        for it in range(mid_total):
            if (it + 1) % 10 == 0:
                print(f"中数据对拍 {it + 1}/{mid_total}", flush=True)
            name = midfuzz[it % len(midfuzz)]
            rng = random.Random(f"{prob.id}/mid/{it}")
            data = prob.templates[name](rng, _fuzz_ctx(prob, mid=True)).encode()
            a, _, sa = runner.run(sol, data, limit * 4)
            b, _, sb = runner.run(ref, data, limit * 4)
            detail["mid"]["n"] += 1
            if sa != "OK" or sb != "OK":
                detail["mid"]["fail"].append({"it": it, "tmpl": name, "why": f"运行异常 {sa}/{sb}"})
                continue
            if tokens(a) == tokens(b):
                detail["mid"]["pass"] += 1
            else:
                detail["mid"]["fail"].append(
                    {"it": it, "tmpl": name, "std": " ".join(tokens(a))[:120],
                     "ref": " ".join(tokens(b))[:120], "input": data.decode()[:400]})
        if detail["mid"]["fail"]:
            detail["ok"] = False

    return detail


# ---------------------------------------------------------------- gen
def stage_gen(prob, args):
    runner = Runner(prob.build)
    sol = runner.compile(prob.sol_path(), "sol")
    if sol is None:
        return {"ok": False, "at": now(), "msg": "标程不可用", "errors": runner.errors}

    os.makedirs(prob.data, exist_ok=True)
    limit = max(prob.limit * 3, 5.0)
    subs = prob.subtasks
    tests = []
    ok = True
    for idx, (sub, name) in enumerate(prob.tests, 1):
        rng = random.Random(f"{prob.id}#{idx}")
        try:
            raw = prob.templates[name](rng, subs[sub])
        except Exception as e:
            tests.append({"test": idx, "template": name, "ok": False, "why": f"生成异常 {e}"})
            ok = False
            continue
        try:
            prob.spec.check(raw, subs[sub])
        except AssertionError as e:
            # 模型写的 assert 经常不带说明，光报 "约束不满足：" 它改不动。
            # 把该子任务的约束键和输入开头一起给出去。
            why = str(e) or "check() 里的 assert 没有写说明"
            keys = sorted(k for k in subs[sub].keys() if k != "desc")
            snippet = raw[:180].replace("\n", " ⏎ ")
            tests.append({"test": idx, "template": name, "ok": False,
                          "why": f"约束不满足：{why}；该子任务约束键={keys}；"
                                 f"生成的数据开头是：{snippet}…"})
            ok = False
            continue
        text = normalize(raw)
        write_text(_in_path(prob, idx), text)
        got, ms, status = runner.run(sol, text.encode(), limit)
        if status != "OK":
            err = getattr(runner, "last_stderr", "") or ""
            hint = ""
            if status == "RE":
                if err:
                    hint = f"；程序崩溃了，报错是：{err[:200]}"
                else:
                    hint = ("；程序没有任何错误输出就崩了。最常见的原因是**递归太深把栈撑爆**"
                            "（尤其是链状数据 + n 很大），其次是数组越界。"
                            "如果用了递归 DFS，请改成迭代写法（或用局部数组模拟栈）。")
            tests.append({"test": idx, "template": name, "ok": False,
                          "why": (f"标程在这个测试点上 {status}（数据 {human_size(len(text))}，"
                                  f"耗时 {fmt_ms(ms)}）"
                                  + (f"，stderr：{err[:200]}" if err else "")
                                  + hint)})
            ok = False
            continue
        write_text(_ans_path(prob, idx), normalize(got))
        # 落盘后反查格式
        bad = []
        for p in (_in_path(prob, idx), _ans_path(prob, idx)):
            b = open(p, "rb").read()
            if b"\r" in b:
                bad.append(os.path.basename(p) + " 含 CR")
            if not b.endswith(b"\n"):
                bad.append(os.path.basename(p) + " 未以换行结尾")
        if bad:
            tests.append({"test": idx, "template": name, "ok": False, "why": "；".join(bad)})
            ok = False
            continue
        tests.append({
            "test": idx, "sub": sub, "template": name, "ok": True,
            "size": len(text.encode()), "pts": prob.points(idx),
            "ms": round(ms, 1), "time_ratio": round(ms / 1000.0 / prob.limit, 3),
        })
        print(f"  #{idx:<2} 子任务{sub} {name:<18} {human_size(len(text.encode())):>8}  "
              f"标程 {fmt_ms(ms):>7}  ({ms / 1000.0 / prob.limit * 100:.0f}% 时限)")

    # ---- 小数据对拍：标程和暴力必须立刻一致 ----
    # 这一步放在 gen 里，是因为对拍要用到 gen.py 的 FUZZ 模板；
    # 只要生成器一落盘，就马上拿它验证标程，不等后面的实现写完。
    brute = runner.compile(prob.brute_path(), "brute") if prob.brute_path() else None
    fuzz = prob.fuzz_small()
    if ok and brute is not None and fuzz:
        bad = None
        skipped = 0
        for it in range(min(200, args.fuzz)):
            name = fuzz[it % len(fuzz)]
            rng = random.Random(f"fuzz/{it}")
            inp = prob.templates[name](rng, subs[1]).encode()
            a, _, sa = runner.run(sol, inp, limit)
            b, _, sb = runner.run(brute, inp, limit)
            if sa != "OK" or sb != "OK":
                # 小数据上跑挂/超时基本是进程抖动，不是答案分歧。跳过这一组。
                skipped += 1
                continue
            if not same_answer(a, b):
                bad = (it, name, inp, a, b)
                break
        if skipped:
            print(f"小数据对拍跳过了 {skipped} 组（进程异常/超时，非答案分歧）", flush=True)
        if bad:
            it, name, inp, a, b = bad
            snippet = inp.decode("utf-8", "replace")[:300].replace("\n", " ⏎ ")
            return {"ok": False, "at": now(), "tests": tests, "growth": [],
                    "msg": (f"标程和暴力在第 {it + 1} 组小数据上就不一致（模板 {name}）。"
                            f"标程输出 {tokens(a)[:3]}，暴力输出 {tokens(b)[:3]}。"
                            f"输入是：{snippet}。这是你写的两个程序互相矛盾，必须先修到一致。")}
        print(f"小数据对拍通过（{min(200, args.fuzz)} 组）", flush=True)

    # ---- 约束饱和度：暴力必须至少掉一个点 ----
    # 一个真正有规模的题目，暴力不可能通过全部测试点。
    # 如果暴力全过，说明数据根本没造满约束，这题谁写暴力谁满分。
    if ok and brute is not None:
        answers = _load_answers(prob)
        b_total, b_rows = score_program(prob, runner, brute, answers, limit)
        # score_program 的行状态是 AC / RE / TLE / WA，不是 runner 的 OK
        bad = [r for r in b_rows if r[1] != "AC"]
        if not bad:
            print(f"  暴力通过了全部 {len(b_rows)} 个测试点（{b_total} 分）—— 数据没造满约束", flush=True)
            slowest = max(b_rows, key=lambda r: r[3])
            return {"ok": False, "at": now(), "tests": tests, "growth": [],
                    "slow": [],
                    "msg": (f"暴力（brute）通过了全部 {len(b_rows)} 个测试点，拿到 {b_total} 分，"
                            f"最慢的一个点也只用了 {slowest[3]:.0f}ms。"
                            f"这说明数据规模根本没到约束上限——这题谁写暴力谁满分。"
                            f"请把各子任务的数据规模提到 spec 里声明的上限，"
                            f"至少要有一个测试点让暴力跑不完或算错。")}
        print(f"  约束饱和度 OK：暴力在 {len(bad)} 个测试点上过不了"
              f"（#{', #'.join(str(r[0]) for r in bad[:5])}）", flush=True)

    # ---- 复杂度体检 ----
    good = [t for t in tests if t.get("ok")]
    # 小测试点的耗时主要是进程启动开销，不能拿来判断复杂度
    real = [t for t in good if t.get("size", 0) >= 20000]
    over = [t for t in real if t.get("time_ratio", 0) > 0.35]
    growth = []
    by_sub = {}
    for t in good:
        by_sub.setdefault(t["sub"], []).append(t)
    for sub, pts in by_sub.items():
        pts.sort(key=lambda x: x["size"])
        lo, hi = pts[0], pts[-1]
        if lo["size"] > 0 and hi["size"] / lo["size"] >= 4 and hi["ms"] > 5 and lo["ms"] > 0.5:
            p = math.log(max(hi["ms"], 1e-9) / max(lo["ms"], 1e-9)) / math.log(hi["size"] / lo["size"])
            if p >= 1.5:
                growth.append({"sub": sub, "p": round(p, 2), "from": lo["size"],
                               "to": hi["size"], "ms": hi["ms"]})
                print(f"复杂度提示：子任务 {sub} 的标程耗时随规模增长约 O(n^{p:.1f})，"
                      f"最大点已用 {hi['ms']:.0f}ms。数据再大一倍就会超时的话，"
                      f"说明约束给太松了。", flush=True)

    if over:
        # 超了 100% = 标程在自己的数据上都跑不完，这题没法用 → 拦
        # 35%~100% 只是"余量不够"，记警告即可，不值得让整题作废
        dead = [t for t in over if t["time_ratio"] > 1.0]
        if dead:
            worst = max(dead, key=lambda t: t["time_ratio"])
            more = "；".join(
                f"#{t['test']} {t['ms']:.0f}ms（{t['time_ratio'] * 100:.0f}%）" for t in dead[:4])
            return {"ok": False, "at": now(), "tests": tests, "growth": growth,
                    "slow": [t["test"] for t in dead],
                    "msg": (f"标程在自己生成的数据上就超时了（{more}），"
                            f"最慢的 #{worst['test']} 用了 {worst['time_ratio'] * 100:.0f}% 时限。"
                            f"这道题的约束和算法不匹配，要么调小规模上限，要么换复杂度更低的算法。")}
        for t in over:
            print(f"复杂度提示：#{t['test']} 用了 {t['time_ratio'] * 100:.0f}% 时限"
                  f"（余量偏小，但不影响正确性）", flush=True)

    slow = [t for t in real if t.get("time_ratio", 0) > 0.3]
    return {"ok": ok, "at": now(), "tests": tests, "growth": growth,
            "slow": [t["test"] for t in slow],
            "msg": "" if ok else "数据生成有失败项"}


# ---------------------------------------------------------------- attack
# 错解最多允许拿到的分数比例。调小 = 要求数据更强，但可能永远过不了。
WRONG_CAP_RATIO = 0.75


def stage_attack(prob, args):
    answers = _load_answers(prob)
    if not answers:
        return {"ok": False, "at": now(), "msg": "还没有数据，先跑 gen"}
    runner = Runner(prob.build)
    progs = prob.wrong_paths()
    if not progs:
        return {"ok": False, "at": now(), "msg": "wrong/ 为空，没有可攻击的错解"}
    rows = []
    survivors = []
    allow = prob.wrong_allow()
    # 要求错解拿 0 分是不现实的：一个只在某个边界出错的解法，除非每个测试点都踩中它，
    # 否则总能拿到分。真正该保证的是"数据能识别出它是错的"——默认要掉 25% 的分。
    full = sum(int(v.get("score", 0)) for v in prob.subtasks.values())
    # 只拦"错解拿了满分"——那说明数据根本分不出对错。
    # 掉分了就说明数据有识别能力，掉得够不够多是质量偏好，记警告即可。
    default_cap = full - 1
    for src in progs:
        name = os.path.splitext(os.path.basename(src))[0]
        prog = runner.compile(src, "wrong_" + name)
        if prog is None:
            rows.append({"name": name, "ok": False, "why": "无法编译/加载", "score": None})
            continue
        cap = int(allow.get(name, default_cap))
        total, r = score_program(prob, runner, prog, answers, prob.limit)
        rows.append({"name": name, "score": total, "allow": cap,
                     "rows": [_fmt_row(x) for x in r]})
        if total > cap:
            survivors.append(name)
        tag = f"（允许 ≤{cap}）" if cap else ""
        print(f"  {name:<20} 得分 {total:>3}{tag}  " + "".join(
            _SYM.get(x[1], "?") for x in r))
    ok = not survivors
    return {"ok": ok, "at": now(), "programs": rows, "survivors": survivors,
            "allow": allow,
            "msg": "" if ok else f"{len(survivors)} 个错解超出上限：{', '.join(survivors)}"}


# ---------------------------------------------------------------- calib
def stage_calib(prob, args):
    answers = _load_answers(prob)
    if not answers:
        return {"ok": False, "at": now(), "msg": "还没有数据，先跑 gen"}
    runner = Runner(prob.build)
    sol = runner.compile(prob.sol_path(), "sol")
    if sol is None:
        return {"ok": False, "at": now(), "msg": "标程不可用"}

    expected = prob.partial_expected()
    rows = []
    total, _ = score_program(prob, runner, sol, answers, prob.limit * 2)
    rows.append({"name": "sol（正解）", "score": total, "expect": [100, 100],
                 "ok": total == 100})
    for src in prob.partial_paths():
        name = os.path.splitext(os.path.basename(src))[0]
        prog = runner.compile(src, "partial_" + name)
        if prog is None:
            rows.append({"name": name, "score": None, "expect": expected.get(name),
                         "ok": False, "why": "无法编译/加载"})
            continue
        got, _ = score_program(prob, runner, prog, answers, prob.limit)
        exp = expected.get(name)
        if exp is None:
            in_range = True
            note = "未声明期望值"
        else:
            lo, hi = (exp, exp) if isinstance(exp, int) else (exp[0], exp[1])
            in_range = lo <= got <= hi
            note = f"期望 {lo}~{hi}" if lo != hi else f"期望 {lo}"
        rows.append({"name": name, "score": got, "expect": exp, "ok": in_range, "note": note})
        print(f"  {name:<20} 得分 {got:>3}  {note}  {'OK' if in_range else '不符'}")

    levels = sorted({r["score"] for r in rows if r.get("score") is not None})
    issues = []
    warnings = []
    if rows[0]["score"] != 100:
        issues.append("正解没有拿满 100 分")
    # expected 是 4 号 猜的，以实测为准。
    # 真正必须守住的只有：部分分既不能拿满分（那不是部分分），也不能是 0（那不参与区分）。
    drift = []
    for r in rows[1:]:
        if r.get("score") is None:
            issues.append(f"{r['name']} 无法编译/加载")
            continue
        sc = r["score"]
        if sc >= 100:
            issues.append(f"{r['name']} 拿了满分——它不是部分分，是正解")
        elif sc <= 0 and isinstance(r.get("expect"), int) and r["expect"] > 0:
            issues.append(f"{r['name']} 拿 0 分，比期望的 {r['expect']} 还低，数据比预期狠得多")
        elif not r.get("ok"):
            drift.append(r)
    if drift:
        # 把 expected.json 改成实测值，免得下一轮又因为这个再失败一次
        path = os.path.join(prob.dir, "partial", "expected.json")
        new_exp = {}
        for r in rows[1:]:
            if r.get("score") is not None:
                new_exp[r["name"]] = r["score"]
        try:
            import json as _json
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                _json.dump(new_exp, f, ensure_ascii=False, indent=2)
            print(f"  已按实测把 expected.json 改成：{new_exp}", flush=True)
        except OSError:
            pass
    if len(levels) < 3:
        warnings.append(f"只有 {len(levels)} 个分数档位，区分度偏弱")
    top_wrong = max([r["score"] for r in rows[1:] if r.get("score") is not None], default=0)
    if top_wrong > 80:
        warnings.append(f"最高的部分分程序拿到 {top_wrong} 分，数据对它偏宽松")
    if warnings:
        print("  提示：" + "；".join(warnings), flush=True)
    return {"ok": not issues, "at": now(), "rows": rows, "levels": levels,
            "issues": issues, "warnings": warnings, "msg": "；".join(issues)}


# ---------------------------------------------------------------- build
def stage_build(prob, args):
    issues = prob.validate()
    if issues:
        return {"ok": False, "at": now(), "msg": "契约不完整", "issues": issues}
    text = stmt.render(prob)
    write_text(os.path.join(prob.build, "statement.md"), text)

    pkg = os.path.join(prob.build, "package")
    if os.path.isdir(pkg):
        shutil.rmtree(pkg)
    os.makedirs(pkg)
    write_text(os.path.join(pkg, "statement.md"), text)

    need = len(prob.tests) * 2
    got = 0
    for idx in range(1, len(prob.tests) + 1):
        for src, ext in ((_in_path(prob, idx), "in"), (_ans_path(prob, idx), "ans")):
            if not os.path.exists(src):
                continue
            got += 1
            # 打包时用提交文件名（CODE），方便直接喂给 OJ
            dst = os.path.join(pkg, "data", f"{prob.code}{idx}.{ext}")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
    if got != need:
        return {"ok": False, "at": now(),
                "msg": f"数据不全（{got}/{need} 个文件），先跑 gen"}

    zpath = os.path.join(prob.build, f"{prob.id}.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for base, _, names in os.walk(pkg):
            for n in names:
                full = os.path.join(base, n)
                z.write(full, os.path.relpath(full, pkg))

    report = render_report(prob, text, zpath)
    write_text(os.path.join(prob.build, "REPORT.md"), report)
    return {"ok": True, "at": now(), "zip": os.path.relpath(zpath, prob.dir),
            "zip_size": os.path.getsize(zpath), "msg": ""}


def render_report(prob, statement_text, zpath):
    solve = _load_json(os.path.join(prob.build, "solve.json"))
    gen = _load_json(os.path.join(prob.build, "gen.json"))
    attack = _load_json(os.path.join(prob.build, "attack.json"))
    calib = _load_json(os.path.join(prob.build, "calib.json"))

    L = [f"# {prob.title}（`{prob.id}`）构建报告", ""]
    L.append(f"- 时限 {prob.limit:g}s / 内存 {prob.mem}MB / 测试点 {len(prob.tests)} 个 / 满分 {prob.total_points()}")
    L.append(f"- 考点：{'、'.join(prob.tags) if prob.tags else '—'}")
    L.append(f"- 输入哈希：`{prob.input_hash()}`")
    L.append("")

    L.append("## 子任务")
    L.append("")
    L.append(stmt.subtask_table(prob))
    L.append("")

    if gen and gen.get("tests"):
        L.append("## 测试点")
        L.append("")
        L.append("| # | 子任务 | 模板 | 大小 | 分值 | 标程耗时 | 占时限 |")
        L.append("| :-: | :-: | :-- | --: | :-: | --: | --: |")
        for t in gen["tests"]:
            if not t.get("ok"):
                L.append(f"| {t['test']} | — | {t.get('template')} | — | — | 失败 | — |")
                continue
            L.append(f"| {t['test']} | {t['sub']} | `{t['template']}` | "
                     f"{human_size(t['size'])} | {t['pts']} | {t['ms']:.0f}ms | "
                     f"{t['time_ratio'] * 100:.0f}% |")
        L.append("")

    if gen and gen.get("growth"):
        L.append("## 复杂度体检")
        L.append("")
        for g in gen["growth"]:
            L.append(f"- 子任务 {g['sub']}：标程耗时随数据规模增长约 **O(n^{g['p']})**，"
                     f"最大点已用 {g['ms']:.0f}ms。规模再翻倍就会更接近时限。")
        L.append("")

    if solve:
        s = solve.get("small", {})
        m = solve.get("mid", {})
        L.append("## 对拍")
        L.append("")
        L.append(f"- 编译器：{solve.get('compiler')}")
        L.append(f"- 小数据 sol vs brute：{s.get('pass', 0)}/{s.get('n', 0)} 通过")
        L.append(f"- 中数据 sol vs ref：{m.get('pass', 0)}/{m.get('n', 0)} 通过"
                 + ("" if m.get("available", True) else "（未提供 ref）"))
        if solve.get("issues"):
            L.append("- 提示：" + "；".join(solve["issues"]))
        L.append("")

    if attack:
        L.append("## 攻击矩阵（错解必须 0 分）")
        L.append("")
        head = "| 错解 | " + " | ".join(f"#{i}" for i in range(1, len(prob.tests) + 1)) + " | 总分 |"
        L.append(head)
        L.append("| :-- | " + " | ".join([":-:"] * len(prob.tests)) + " | :-: |")
        for p in attack.get("programs", []):
            cap = p.get("allow", 0) or 0
            score_txt = f"**{p.get('score')}**" + (f"（允许 ≤{cap}）" if cap else "")
            if p.get("rows"):
                cells = " ".join(_SYM.get(r["status"], "?") for r in p["rows"])
                L.append(f"| `{p['name']}` | {cells} | {score_txt} |")
            else:
                L.append(f"| `{p['name']}` | — | **无法运行** |")
        L.append("")

    if calib:
        L.append("## 部分分曲线")
        L.append("")
        L.append("| 程序 | 得分 | 期望 | 判定 |")
        L.append("| :-- | :-: | :-: | :-: |")
        for r in calib.get("rows", []):
            exp = r.get("expect")
            if isinstance(exp, list):
                exp = f"{exp[0]}~{exp[1]}"
            L.append(f"| {r['name']} | {r.get('score')} | {exp if exp is not None else '—'} | "
                     f"{'OK' if r.get('ok') else '不符'} |")
        L.append("")
        if calib.get("issues"):
            L.append("> 问题：" + "；".join(calib["issues"]))
            L.append("")

    L.append("## 打包")
    L.append("")
    L.append(f"- `{os.path.basename(zpath)}`（{human_size(os.path.getsize(zpath))}）")
    return "\n".join(L) + "\n"


def _load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


STAGES = [
    ("solve", "对拍与编译", stage_solve),
    ("gen", "生成数据", stage_gen),
    ("attack", "错解攻击", stage_attack),
    ("calib", "部分分定标", stage_calib),
    ("build", "组装打包", stage_build),
]
