#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
oj —— 自动出题工作流命令行。

    oj new <id> [--title 标题]      从 _template 建一题
    oj solve <id>                   编译 + 小数据对拍 + 中数据对拍
    oj gen <id>                     按 spec 生成数据并归一化
    oj attack <id>                  错解攻击，必须全部 0 分
    oj calib <id>                   部分分曲线定标
    oj build <id>                   题面渲染 + 打包 + 报告
    oj run <id>                     从头跑到 build
    oj batch                        所有题目断点续跑
    oj status                       各题闸门状态

退出码：0 全部通过，1 有失败，2 用法错误。
"""
import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from framework.problem import Problem, discover          # noqa: E402
from framework.stages import STAGES                      # noqa: E402
from framework.utils import (now, read_json, setup_stdio,  # noqa: E402
                             write_json)

PROBLEMS = os.path.join(HERE, "problems")
TEMPLATE = os.path.join(PROBLEMS, "_template")

STAGE_NAMES = [s[0] for s in STAGES]
STAGE_FUNC = {s[0]: s[2] for s in STAGES}
STAGE_LABEL = {s[0]: s[1] for s in STAGES}


# ---------------------------------------------------------------- 基础
def get_problem(pid):
    d = os.path.join(PROBLEMS, pid)
    if not os.path.isdir(d):
        sys.exit(f"没有这个题目目录：problems/{pid}")
    return Problem(d)


def print_issues(issues):
    for i in issues:
        print(f"  ! {i}")


def save(prob, name, detail):
    detail.setdefault("stage", name)
    detail.setdefault("at", now())
    detail["hash"] = prob.input_hash()
    write_json(prob.stage_path(name), detail)


def should_skip(prob, name, force):
    if force:
        return False
    d = read_json(prob.stage_path(name))
    if not d or not d.get("ok"):
        return False
    return d.get("hash") == prob.input_hash()


def run_stage(prob, name, args):
    print(f"[{prob.id}] {STAGE_LABEL[name]} …")
    detail = STAGE_FUNC[name](prob, args)
    save(prob, name, detail)
    ok = bool(detail.get("ok"))
    if detail.get("msg"):
        print(f"  → {'OK' if ok else '失败'}：{detail['msg']}")
    elif ok:
        print(f"  → OK")
    return ok


# ---------------------------------------------------------------- 子命令
def cmd_new(args):
    pid = args.id
    dst = os.path.join(PROBLEMS, pid)
    if os.path.isdir(dst):
        sys.exit(f"已存在：problems/{pid}")
    if not os.path.isdir(TEMPLATE):
        sys.exit("缺少 problems/_template")
    import shutil
    shutil.copytree(TEMPLATE, dst)
    title = args.title or pid
    # 替换占位符
    for base, _, names in os.walk(dst):
        for n in names:
            p = os.path.join(base, n)
            try:
                with open(p, "r", encoding="utf-8") as f:
                    t = f.read()
            except UnicodeDecodeError:
                continue
            if "__ID__" in t or "__TITLE__" in t:
                with open(p, "w", encoding="utf-8", newline="\n") as f:
                    f.write(t.replace("__ID__", pid).replace("__TITLE__", title))
    print(f"已创建 problems/{pid}")
    print("下一步：改 spec.py 的 SUBTASKS / TESTS / GLOBAL，写 gen.py 的模板，")
    print("       补 sol / brute / ref，放 2 个 sample，然后 `oj run " + pid + "`。")
    return 0


def cmd_list(args):
    probs = discover(PROBLEMS)
    if not probs:
        print("problems/ 下还没有题目")
        return 0
    rows = []
    for p in probs:
        try:
            p.load()
        except Exception as e:
            rows.append((p.id, "", p.id, "", "", str(e), "!"))
            continue
        gates = []
        for n in STAGE_NAMES:
            d = read_json(p.stage_path(n))
            gates.append("✓" if d and d.get("ok") else ("✗" if d else "·"))
        rows.append((p.id, p.code, p.title, f"{p.limit:g}s", f"{p.mem}MB",
                     "、".join(p.tags) or "—", "".join(gates)))
    w = [max(len(r[i]) for r in rows) for i in range(7)]
    w[2] = max(w[2], 2)
    print(f"{'id':<{w[0]}}  {'code':<{w[1]}}  {'标题':<{w[2]}}  "
          f"{'时限':<{w[3]}}  {'内存':<{w[4]}}  {'考点':<{w[5]}}  闸门")
    print("-" * (sum(w) + 20))
    for r in rows:
        print(f"{r[0]:<{w[0]}}  {r[1]:<{w[1]}}  {r[2]:<{w[2]}}  "
              f"{r[3]:<{w[3]}}  {r[4]:<{w[4]}}  {r[5]:<{w[5]}}  {r[6]}")
    print("\n闸门顺序：" + " ".join(STAGE_NAMES))
    return 0


def cmd_status(args):
    probs = discover(PROBLEMS)
    if not probs:
        print("problems/ 下还没有题目")
        return 0
    w = max(len(p.id) for p in probs) + 2
    head = "题目".ljust(w) + "".join(n.ljust(9) for n in STAGE_NAMES)
    print(head)
    print("-" * len(head))
    for p in probs:
        cells = []
        for n in STAGE_NAMES:
            d = read_json(p.stage_path(n))
            if not d:
                cells.append("·".ljust(9))
            elif d.get("ok"):
                fresh = d.get("hash") == p.input_hash()
                cells.append(("✓" if fresh else "✓*").ljust(9))
            else:
                cells.append("✗".ljust(9))
        print(p.id.ljust(w) + "".join(cells))
    print("\n· 未跑   ✓ 通过   ✓* 通过但输入已改动（需重跑）   ✗ 失败")
    return 0


def cmd_check(args):
    prob = get_problem(args.id)
    issues = prob.validate(spec_only=getattr(args, "spec_only", False))
    if issues:
        print(f"[{prob.id}] 契约不完整：")
        print_issues(issues)
        return 1
    if getattr(args, "spec_only", False):
        print(f"[{prob.id}] spec 通过：{len(prob.tests)} 个测试点，"
              f"{len(prob.subtasks)} 个子任务，满分 {prob.total_points()}")
        return 0
    print(f"[{prob.id}] 契约完整：{len(prob.tests)} 个测试点，"
          f"{len(prob.subtasks)} 个子任务，满分 {prob.total_points()}")
    solvers = {"sol": prob.sol_path(), "brute": prob.brute_path(), "ref": prob.ref_path()}
    for k, v in solvers.items():
        print(f"  {k:<6} {'—' if not v else os.path.basename(v)}")
    print(f"  wrong   {len(prob.wrong_paths())} 个")
    print(f"  partial {len(prob.partial_paths())} 个")
    return 0


def cmd_one(args):
    prob = get_problem(args.id)
    issues = prob.validate()
    if issues:
        print(f"[{prob.id}] 契约不完整，不能开跑：")
        print_issues(issues)
        return 1
    ok = run_stage(prob, args.stage, args)
    return 0 if ok else 1


def cmd_run(args):
    prob = get_problem(args.id)
    issues = prob.validate()
    if issues:
        print(f"[{prob.id}] 契约不完整，不能开跑：")
        print_issues(issues)
        return 1
    return _run_pipeline(prob, args)


def _run_pipeline(prob, args):
    for name in STAGE_NAMES:
        if should_skip(prob, name, args.force):
            print(f"[{prob.id}] {STAGE_LABEL[name]} … 跳过（输入未变且已通过）")
            continue
        if not run_stage(prob, name, args):
            print(f"[{prob.id}] 停在 {name}")
            return 1
    print(f"[{prob.id}] 全部通过")
    return 0


def cmd_batch(args):
    probs = discover(PROBLEMS)
    if not probs:
        print("problems/ 下还没有题目")
        return 0
    if args.only:
        probs = [p for p in probs if p.id in args.only]
    bad = []
    for p in probs:
        print(f"\n=== {p.id} ===")
        issues = p.validate()
        if issues:
            print("  契约不完整：")
            print_issues(issues)
            bad.append(p.id)
            continue
        if _run_pipeline(p, args) != 0:
            bad.append(p.id)
    print("\n" + "=" * 40)
    if bad:
        print(f"{len(probs) - len(bad)} 题通过，{len(bad)} 题卡住：{', '.join(bad)}")
        return 1
    print(f"{len(probs)} 题全部通过")
    return 0


# ---------------------------------------------------------------- 入口
def _failed_root():
    return os.path.join(PROBLEMS, "_failed")


def cmd_revive(args):
    """把 problems/_failed 里的题挪回 problems/，方便继续用命令行折腾。"""
    src = os.path.join(_failed_root(), args.id)
    dst = os.path.join(PROBLEMS, args.id)
    if not os.path.isdir(src):
        names = sorted(os.listdir(_failed_root())) if os.path.isdir(_failed_root()) else []
        print(f"problems/_failed 里没有 {args.id}。")
        if names:
            print("  现有：" + "、".join(names))
        return 1
    if os.path.isdir(dst):
        print(f"problems/{args.id} 已经存在，先删掉或改名再试。")
        return 1
    shutil.move(src, dst)
    print(f"已移回 problems/{args.id}")
    return 0


def cmd_failed(args):
    """列出被挪走的失败题，顺便标出它死在哪个阶段。"""
    root = _failed_root()
    if not os.path.isdir(root):
        print("还没有失败产物")
        return 0
    names = sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)))
    if not names:
        print("还没有失败产物")
        return 0
    print(f"失败产物 {len(names)} 道（problems/_failed/）：")
    for n in names:
        note = ""
        bj = os.path.join(root, n, "build", "build.json")
        if os.path.exists(bj):
            note = "  （已打包）"
        print(f"  {n}{note}")
    print("\n用 python oj.py revive <题号> 移回 problems/ 继续处理")
    return 0


def main(argv=None):
    setup_stdio()
    ap = argparse.ArgumentParser(prog="oj", description="自动出题工作流")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("new", help="从模板建一题")
    p.add_argument("id")
    p.add_argument("--title", default=None)
    p.set_defaults(func=cmd_new)

    for name, label in [("check", "只校验契约"), ("run", "整条流水线"),
                        ("solve", "编译+对拍"), ("gen", "生成数据"),
                        ("attack", "错解攻击"), ("calib", "部分分定标"),
                        ("build", "组装打包")]:
        p = sub.add_parser(name, help=label)
        p.add_argument("id")
        p.add_argument("--force", action="store_true", help="忽略缓存重跑")
        p.add_argument("--fuzz", type=int, default=300, help="对拍轮数")
        if name == "check":
            p.add_argument("--spec", dest="spec_only", action="store_true",
                           help="只校验 spec（解法和数据还没写时用）")
            p.set_defaults(func=cmd_check)
        elif name == "run":
            p.set_defaults(func=cmd_run, stage=None)
        else:
            p.set_defaults(func=cmd_one, stage=name)

    p = sub.add_parser("batch", help="所有题目断点续跑")
    p.add_argument("--only", nargs="*", default=None)
    p.add_argument("--force", action="store_true")
    p.add_argument("--fuzz", type=int, default=300)
    p.set_defaults(func=cmd_batch)

    p = sub.add_parser("revive", help="把失败题从 _failed 移回 problems")
    p.add_argument("id")
    p.set_defaults(func=cmd_revive)

    p = sub.add_parser("failed", help="列出失败产物")
    p.set_defaults(func=cmd_failed)

    p = sub.add_parser("status", help="闸门状态")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("list", help="题目一览（组卷用）")
    p.set_defaults(func=cmd_list)

    args = ap.parse_args(argv)
    if not hasattr(args, "fuzz"):
        args.fuzz = 300
    if not hasattr(args, "force"):
        args.force = False
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
