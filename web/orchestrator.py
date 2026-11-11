# -*- coding: utf-8 -*-
"""流水线编排：把人 → 三个 AI → 机器闸门串成一个可以自我纠错的循环。

核心原则（和纯 AI 评审的区别）：
- AI 只负责**产出文件**，不负责判断对错
- 每一关的裁决权交给 oj 的机器闸门（编译、对拍、攻击、定标）
- 闸门的失败信息被格式化成反馈，回灌给下一轮的同一个角色
- 同一关连续 N 轮不过 → 整道题作废，并给出作废原因分类
"""
import ast
import json
import os
import random
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from collections import Counter

import prompts
from llm import LLMError, chat, chat_stream, extract_json, parse_files

HERE = os.path.dirname(os.path.abspath(__file__))
OJ_ROOT = os.path.dirname(HERE)
OJ_PY = os.path.join(OJ_ROOT, "oj.py")
PROBLEMS = os.path.join(OJ_ROOT, "problems")
RUNS = os.path.join(HERE, "runs")

MAX_ROUNDS = 3
# 一直在思考、迟迟不写正文的容忍时长。超过它就判定为打转，中止本次调用。
REASON_ONLY_SECONDS = 12 * 60
# 单次调用的总时长上限，防止"一直在缓慢吐字"把整个运行拖死。
CALL_MAX_SECONDS = 25 * 60


def _same_answer(a, b):
    """借 framework 里的判定：两个都用大数表示无解时视为一致。"""
    sys.path.insert(0, OJ_ROOT)
    from framework.stages import same_answer
    return same_answer(a, b)

class StageFailed(Exception):
    def __init__(self, stage, reason):
        super().__init__(f"{stage}: {reason}")
        self.stage = stage
        self.reason = reason


class Degenerate(Exception):
    """模型陷入重复输出，必须立刻中止，不能等它烧完整个预算。"""


class StatementProblem(Exception):
    """两份暴力对不上 = 题意有分歧 = 题面缺了约定，必须回退重写题面。"""


def _degenerate(text):
    """检测重复：同一段 200/300 字符出现 8 次以上，且这段内容本身不平凡。

    要求"不平凡"（至少 40 个不同字符）是为了避开 'abcabc...' 这种周期性文本，
    真实的代码和中文段落不会这么单调。
    """
    n = len(text)
    if n < 1600:
        return ""
    for size in (200, 300):
        blocks = [text[i:i + size] for i in range(0, n - size + 1, size)]
        if len(blocks) < 8:
            continue
        blk, cnt = Counter(blocks).most_common(1)[0]
        if cnt >= 8 and len(set(blk)) >= 40:
            return f"{size} 字符的片段重复了 {cnt} 次"
    return ""


def _read(path, default=""):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        return f.read()


def _write(path, text):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


class Run:
    def __init__(self, run_id, seed, slots):
        self.run_id = run_id
        self.seed = seed
        self.slots = slots                 # [cfg1, cfg2, cfg3]
        self.dir = os.path.join(RUNS, run_id)
        self.status = "pending"
        self.phase = ""
        self.error = ""
        self.logs = []
        self.live = {"state": "idle", "text": "", "reasoning": "", "label": "",
                     "model": "", "slot": 0, "tick": 0}
        self.live_seq = 0
        self.started = time.time()
        self.problem_id = seed.get("problem_id") or self._mk_id(seed["topic"])
        self.prob_dir = os.path.join(PROBLEMS, self.problem_id)
        os.makedirs(self.dir, exist_ok=True)

    # ---------------------------------------------------------------- 基础
    @staticmethod
    def _mk_id(topic):
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", topic).strip("-").lower()[:24]
        return f"ai-{slug or 'problem'}-{uuid.uuid4().hex[:4]}"

    def log(self, msg, level="info"):
        entry = {"t": round(time.time() - self.started, 1), "level": level, "msg": msg}
        self.logs.append(entry)
        with open(os.path.join(self.dir, "log.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.save()

    def save(self):
        state = {
            "run_id": self.run_id,
            "problem_id": self.problem_id,
            "seed": self.seed,
            "status": self.status,
            "phase": self.phase,
            "error": self.error,
            "elapsed": round(time.time() - self.started, 1),
            "logs": self.logs[-400:],
        }
        _write(os.path.join(self.dir, "run.json"),
               json.dumps(state, ensure_ascii=False, indent=2))

    # ---------------------------------------------------------------- 模型
    def call(self, slot, messages, label):
        cfg = self.slots[slot - 1]
        self.log(f"{label} → {slot} 号（{cfg.get('model') or '未配置'}）")
        self.live = {"state": "streaming", "text": "", "reasoning": "", "label": label,
                     "model": cfg.get("model") or "", "slot": slot, "tick": time.time()}
        self.live_seq += 1
        buf = []
        think = []
        t0 = time.time()

        def on_chunk(s):
            buf.append(s)
            txt = "".join(buf)
            # 只保留尾部，避免长题面把内存撑爆
            self.live["text"] = txt[-60000:]
            self.live["tick"] = time.time()
            d = _degenerate(txt[-8000:])
            if d:
                raise Degenerate(d)
            if time.time() - t0 > CALL_MAX_SECONDS:
                raise Degenerate(f"单次调用超过 {CALL_MAX_SECONDS // 60} 分钟仍未写完")

        def on_reasoning(s):
            think.append(s)
            txt = "".join(think)
            self.live["reasoning"] = txt[-60000:]
            self.live["tick"] = time.time()
            # 只抓"原地打转"和"想了太久一个字没写"，不按字符数一刀切。
            # 字符数是粗糙的代理指标：一道难题合理想几万字符很正常。
            d = _degenerate(txt[-8000:])
            if d:
                raise Degenerate(f"思考过程{d}")
            if not buf and time.time() - t0 > REASON_ONLY_SECONDS:
                raise Degenerate(f"思考超过 {REASON_ONLY_SECONDS // 60} 分钟仍没开始写正文")

        try:
            text = chat_stream(cfg, messages, on_chunk, on_reasoning=on_reasoning)
        except Degenerate as e:
            self.live["state"] = "error"
            self.live["error"] = f"输出退化：{e}"
            self.log(f"{label} 输出退化（{e}），中止本次调用", "bad")
            raise RuntimeError(f"{slot} 号输出退化：{e}")
        except LLMError as e:
            # 流式挂了（常见：推理模型长时间不吐字、连接卡死）不要直接放弃，
            # 换普通请求再要一次，通常能拿到完整答案。
            self.log(f"{label} 流式失败（{e}），改用非流式", "warn")
            # 界面上必须能看出"已经换模式了"，否则看起来就是死机
            self.live["state"] = "fallback"
            self.live["reasoning"] = ""
            self.live["tick"] = time.time()
            text = ""
        dt = time.time() - t0
        text = text or ""
        if not text.strip():
            try:
                # 非流式要给足时间：这类"整段算完才返回"的模型一次能跑 8 分钟，
                # 300 秒会把明明能成功的调用判死。
                text = chat(cfg, messages, timeout=900)
            except LLMError as e:
                self.live["state"] = "error"
                self.live["error"] = str(e)
                raise RuntimeError(f"{slot} 号调用失败：{e}")
            on_chunk(text)
        if not text.strip():
            self.live["state"] = "error"
            raise RuntimeError(f"{slot} 号返回了空内容")
        self.live["state"] = "done"
        self.live["text"] = text[-60000:]
        self.log(f"{label} ← {len(text)} 字符，{dt:.1f}s", "ok")
        _write(os.path.join(self.dir, f"{label}-{uuid.uuid4().hex[:4]}.txt"), text)
        return text

    # ---------------------------------------------------------------- 文件
    def write_files(self, files, allowed_dirs=()):
        written = []
        for name, body in files.items():
            name = name.strip().lstrip("/").replace("\\", "/")
            if ".." in name or name.startswith("/"):
                self.log(f"忽略可疑文件名 {name}", "warn")
                continue
            target = os.path.join(self.prob_dir, name)
            _write(target, body)
            written.append(name)
        if written:
            self.log("写入：" + "、".join(written))
        return written

    def files_of(self, *names):
        return {n: _read(os.path.join(self.prob_dir, n)) for n in names}

    # ---------------------------------------------------------------- 闸门
    def oj(self, stage, extra=None, timeout=1800):
        """跑一个 oj 子命令，并把它的输出逐行实时写进日志。

        对拍要跑几百组、期间 og 不产出文件，不流式输出的话界面就是一片死寂。
        """
        cmd = [sys.executable, OJ_PY, stage, self.problem_id] + (extra or [])
        proc = subprocess.Popen(cmd, cwd=OJ_ROOT, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True,
                                encoding="utf-8", errors="replace", bufsize=1)
        killer = threading.Timer(timeout, proc.kill)
        killer.start()
        buf = []
        skip_next = False
        try:
            for line in proc.stdout:
                line = line.rstrip("\n")
                if not line.strip():
                    continue
                # spec.py 里的反斜杠会触发 SyntaxWarning，纯噪音，滤掉
                if skip_next:
                    skip_next = False
                    continue
                if "SyntaxWarning" in line:
                    skip_next = True
                    continue
                buf.append(line)
                s = line.strip()
                if len(s) > 180:
                    s = s[:180] + "…"
                self.log("  " + s, "info")
        finally:
            killer.cancel()
        rc = proc.wait()
        return rc, "\n".join(buf), \
            _read(os.path.join(self.prob_dir, "build", f"{stage}.json"))

    def _detail(self, stage, raw):
        try:
            d = json.loads(raw) if raw.strip().startswith("{") else {}
        except Exception:
            d = {}
        bits = []
        if d.get("msg"):
            bits.append(d["msg"])
        for k in ("issues",):
            if d.get(k):
                bits.append("；".join(d[k]))
        if d.get("tests"):
            bad = [t for t in d["tests"] if not t.get("ok")]
            if bad:
                bits.append("；".join(f"#{t['test']} {t.get('why', '失败')}" for t in bad[:4]))
        for key, tag in (("small", "小数据"), ("mid", "中数据")):
            sub = d.get(key) or {}
            if sub.get("fail"):
                f = sub["fail"][0]
                bits.append(f"{tag}对拍不一致：输入 {f.get('input', '')[:120]!r} "
                            f"std={f.get('std')} 对照={f.get('brute') or f.get('ref')}")
        if d.get("programs"):
            alive = [p for p in d["programs"] if (p.get("score") or 0) > (p.get("allow") or 0)]
            if alive:
                bits.append("错解存活：" + "、".join(
                    f"{p['name']}（{p['score']} 分）" for p in alive))
        if d.get("rows"):
            bad = [r for r in d["rows"] if not r.get("ok")]
            if bad:
                bits.append("部分分不符：" + "、".join(
                    f"{r['name']} 得 {r.get('score')} 分（期望 {r.get('expect')}）" for r in bad))
        return "；".join(b for b in bits if b)

    def gate(self, stage, label, extra=None):
        rc, out, raw = self.oj(stage, extra)
        if rc == 0:
            self.log(f"闸门 {stage} 通过", "ok")
            return True, ""
        detail = self._detail(stage, raw)
        if not detail:
            # check 这类阶段不写 build/*.json，从 stdout 里把问题行都捡出来，
            # 只取最后一行会丢掉最关键的具体原因（比如"40 分不能被 6 整除"）。
            issues = [ln.strip().lstrip("! ").strip()
                      for ln in out.splitlines() if ln.strip().startswith("!")]
            detail = "；".join(issues) or ((out.strip().splitlines() or ["未知错误"])[-1])
        self.log(f"闸门 {stage} 失败：{detail}", "bad")
        return False, detail

    # ---------------------------------------------------------------- 重试
    def step(self, key, label, fn, attempts=MAX_ROUNDS):
        self.phase = f"{key} {label}"
        self.log(f"—— {label} ——", "phase")
        last = ""
        for i in range(attempts):
            if i:
                self.log(f"{label} 第 {i + 1}/{attempts} 轮", "warn")
            try:
                ok, fb = fn(last, i)
            except StageFailed:
                raise
            except Exception as e:
                ok, fb = False, f"{type(e).__name__}: {e}"
                # 一定要把原因写进日志，否则界面上只有"第 2/3 轮"，看不出为什么
                self.log(f"{label} 出错，重试：{fb}", "bad")
            if ok:
                return
            last = fb
        raise StageFailed(key, f"连续 {attempts} 轮未通过。最后一次原因：{last}")

    # ---------------------------------------------------------------- 各阶段
    # ---------------------------------------------------------------- 查重
    _TAG_ALIAS = {
        "状态压缩动态规划": "状压DP", "状态压缩dp": "状压DP", "状压动态规划": "状压DP",
        "状压dp": "状压DP", "状态压缩": "状压DP", "状压": "状压DP",
        "动态规划": "DP", "dp": "DP",
        "二分答案": "二分", "二分查找": "二分",
        "贪心算法": "贪心", "搜索": "DFS", "深度优先搜索": "DFS",
    }
    _TAG_NOISE = ("noip", "noi", "csp", "t1", "t2", "t3", "t4",
                  "提高组", "普及组", "入门组", "省选", "待填")

    @classmethod
    def _norm_tags(cls, tags):
        out = set()
        for t in tags or ():
            s = str(t).strip().lower()
            if not s:
                continue
            if any(n in s for n in cls._TAG_NOISE):
                continue
            out.add(cls._TAG_ALIAS.get(s, str(t).strip()))
        return out

    def library(self):
        """题库：只收录**成功出完**的题（跑通全部闸门、打包成功的）。

        失败的尝试不算数——那些题本身是废品，不该占着题型不让再出。
        来源两处：problems/ 下还在的，以及 web/runs/ 里成功运行的 spec 原文
        （目录被删了也能追溯）。
        """
        runs = os.path.join(OJ_ROOT, "web", "runs")
        done_ids = set()
        if os.path.isdir(runs):
            for d in os.listdir(runs):
                f = os.path.join(runs, d, "run.json")
                if not os.path.exists(f):
                    continue
                try:
                    meta = json.loads(_read(f) or "{}")
                except Exception:
                    continue
                if meta.get("status") == "done" and meta.get("problem_id"):
                    done_ids.add(meta["problem_id"])

        lib = []
        seen = set()
        root = os.path.join(OJ_ROOT, "problems")
        if os.path.isdir(root):
            for name in sorted(os.listdir(root)):
                spec = os.path.join(root, name, "spec.py")
                if name == self.problem_id or not os.path.exists(spec):
                    continue
                if name not in done_ids and not name.startswith("demo-"):
                    continue
                try:
                    text = _read(spec)
                except Exception:
                    continue
                item = self._parse_spec_meta(text, name)
                if item and item["title"] not in seen:
                    seen.add(item["title"])
                    lib.append(item)
        if os.path.isdir(runs):
            for d in sorted(os.listdir(runs)):
                f = os.path.join(runs, d, "run.json")
                if not os.path.exists(f):
                    continue
                try:
                    meta = json.loads(_read(f) or "{}")
                except Exception:
                    continue
                if meta.get("status") != "done":
                    continue
                rd = os.path.join(runs, d)
                for fn in os.listdir(rd):
                    if not fn.startswith("S1-spec-") or not fn.endswith(".txt"):
                        continue
                    try:
                        raw = _read(os.path.join(rd, fn))
                    except Exception:
                        continue
                    body = parse_files(raw).get("spec.py")
                    if not body:
                        i = raw.find("===FILE: spec.py===")
                        if i < 0:
                            continue
                        body = raw[i + 19:]
                    item = self._parse_spec_meta(body, d)
                    if item and item["title"] not in seen:
                        seen.add(item["title"])
                        lib.append(item)
        return lib

    @staticmethod
    def _parse_spec_meta(text, fallback_id):
        mt = re.search(r"TITLE\s*=\s*[\"'](.+?)[\"']", text)
        mg = re.search(r"TAGS\s*=\s*\[(.*?)\]", text, re.DOTALL)
        tags = re.findall(r"[\"']([^\"']+)[\"']", mg.group(1)) if mg else []
        if not tags:
            return None
        return {"id": fallback_id, "title": (mt.group(1) if mt else fallback_id),
                "tags": tags}

    def dup_check(self, title, tags):
        """返回和一个已有题目撞车的描述；不撞返回空串。

        判据：去掉难度标签后，考点集合的 Jaccard 相似度 >= 0.75。
        """
        mine = self._norm_tags(tags)
        if not mine:
            return ""
        best = None
        for item in self.library():
            theirs = self._norm_tags(item["tags"])
            if not theirs:
                continue
            inter = len(mine & theirs)
            union = len(mine | theirs)
            if not union:
                continue
            sim = inter / union
            if best is None or sim > best[1]:
                best = (item, sim)
        if not best:
            return ""
        item, sim = best
        if sim >= 0.75:
            return (f"你这道题的考点（{'、'.join(sorted(mine))}）和已有的"
                    f"「{item['title']}」（{'、'.join(item['tags'])}）重合度 {sim:.0%}，"
                    f"基本是同一类题。请换一个考点组合，或者换一种完全不同的约束结构。")
        return ""

    def do_spec(self, feedback, i):
        avoid = sorted(self.library(), key=lambda x: x["id"])[-12:]
        text = self.call(1, prompts.p_spec(self.seed, feedback, avoid), "S1-spec")
        files = parse_files(text)
        if "spec.py" not in files or "statement.md" not in files:
            return False, "输出里缺少 spec.py 或 statement.md"
        self.write_files(files)
        ok, fb = self.gate("check", "spec", ["--spec"])
        if not ok:
            return ok, fb
        # 题面里必须留出由 spec 渲染的位置，否则数据范围表和样例是手写的，会漂移
        stmt = _read(os.path.join(self.prob_dir, "statement.md"))
        missing = [p for p in ("{{SUBTASK_TABLE}}", "{{GLOBAL}}", "{{SAMPLES}}")
                   if p not in stmt]
        if missing:
            # 只补题面，不动 spec —— spec 一改，契约和下游产物全变，代价太大
            self.log(f"题面缺少占位符 {missing}，只重写题面", "warn")
            spec = _read(os.path.join(self.prob_dir, "spec.py"))
            try:
                text = self.call(1, prompts.p_statement_fix(spec, stmt, missing),
                                 "S1-statement-fix")
            except RuntimeError as e:
                return False, f"补题面失败：{e}"
            files = parse_files(text)
            if "statement.md" not in files:
                return False, f"statement.md 缺少占位符 {missing}，而且补写也没产出题面"
            _write(os.path.join(self.prob_dir, "statement.md"), files["statement.md"])
            stmt = _read(os.path.join(self.prob_dir, "statement.md"))
            missing = [p for p in ("{{SUBTASK_TABLE}}", "{{GLOBAL}}", "{{SAMPLES}}")
                       if p not in stmt]
            if missing:
                return False, (f"补完之后 statement.md 仍然缺少 {missing}。"
                               "数据范围表必须用 {{SUBTASK_TABLE}}、范围文字用 {{GLOBAL}}、"
                               "样例用 {{SAMPLES}}，不能手写")
            self.log("题面占位符补齐了", "ok")

        # 模型有时会写成 {{GLOBAL.mod}} 这种"变量访问"形式，渲染器不认，
        # 会让 2 号审到原始模板。这里把多余的 .xxx 后缀去掉。
        stmt = _read(os.path.join(self.prob_dir, "statement.md"))
        cleaned = re.sub(r"\{\{\s*([A-Z_]+)\.[A-Za-z0-9_]+\s*\}\}", r"{{\1}}", stmt)
        if cleaned != stmt:
            _write(os.path.join(self.prob_dir, "statement.md"), cleaned)
            self.log("题面里的 {{XXX.yyy}} 多余后缀已去掉", "warn")
            stmt = cleaned
        unknown = sorted(set(re.findall(r"\{\{([^{}]+)\}\}", stmt)) -
                         {"TITLE", "LIMIT", "MEM", "CODE", "GLOBAL",
                          "SUBTASK_TABLE", "SAMPLES"})
        if unknown:
            return False, ("题面里出现了渲染器不认识的占位符："
                           + "、".join(f"{{{{{u}}}}}" for u in unknown)
                           + "。只允许 {{TITLE}} {{LIMIT}} {{MEM}} {{CODE}} "
                             "{{GLOBAL}} {{SUBTASK_TABLE}} {{SAMPLES}}，其它内容请直接写死。")

        # 查重：和题库里已有的题撞了就打回重出
        # mock 模式只能回放同一道题，查重必然撞车，自检时跳过
        if str((self.slots[0] or {}).get("base_url", "")).startswith("mock"):
            self.log("mock 模式，跳过查重（回放素材只有一套）", "info")
            return True, ""
        spec_text = _read(os.path.join(self.prob_dir, "spec.py"))
        mt = re.search(r"TITLE\s*=\s*[\"'](.+?)[\"']", spec_text)
        mg = re.search(r"TAGS\s*=\s*\[(.*?)\]", spec_text, re.DOTALL)
        tags = re.findall(r"[\"']([^\"']+)[\"']", mg.group(1)) if mg else []
        dupe = self.dup_check(mt.group(1) if mt else "", tags)
        if dupe:
            self.log("撞题了：" + dupe[:150], "warn")
            return False, dupe
        self.log(f"查重通过（{len(tags)} 个标签，题库 {len(self.library())} 道）", "ok")
        return True, ""

    def check_code(self):
        """S3 阶段还没有 gen.py / ref，用编译代替完整的契约检查。"""
        sys.path.insert(0, OJ_ROOT)
        from framework.runner import Runner
        runner = Runner(os.path.join(self.prob_dir, "build"))
        for stem in ("sol", "brute"):
            src = None
            for ext in (".cpp", ".py"):
                p = os.path.join(self.prob_dir, stem + ext)
                if os.path.exists(p):
                    src = p
                    break
            if src is None:
                return False, f"缺少 {stem}.cpp / {stem}.py"
            if runner.compile(src, stem) is None:
                return False, f"{stem} 编译失败：" + "；".join(runner.errors)
        if not os.path.exists(os.path.join(self.prob_dir, "statement.md")):
            return False, "缺少 statement.md"
        if not os.path.exists(os.path.join(self.prob_dir, "spec.py")):
            return False, "缺少 spec.py"
        self.log("sol / brute 编译通过", "ok")
        return True, ""

    def verify_counterexample(self):
        """之前记下的反例如果还在，修完代码必须能过它。"""
        p = os.path.join(self.prob_dir, "build", "counterexample.in")
        if not os.path.exists(p):
            return True, ""
        sys.path.insert(0, OJ_ROOT)
        from framework.runner import Runner
        r = Runner(os.path.join(self.prob_dir, "build"))
        sol = r.compile(os.path.join(self.prob_dir, "sol.cpp"), "sol")
        bru = r.compile(os.path.join(self.prob_dir, "brute.cpp"), "brute")
        if sol is None or bru is None:
            return True, ""
        data = open(p, "rb").read()
        a, _, sa = r.run(sol, data, 30)
        b, _, sb = r.run(bru, data, 30)
        if sa == "OK" and sb == "OK" and not _same_answer(a, b):
            return False, (f"之前那个反例还没修好：标程 {a.strip()[:40]}，"
                           f"暴力 {b.strip()[:40]}，输入见 build/counterexample.in")
        self.log("已有的反例已经修复", "ok")
        return True, ""

    def do_sol(self, feedback, i):
        f = self.files_of("spec.py", "statement.md")
        text = self.call(1, prompts.p_sol(self.seed, f["spec.py"], f["statement.md"], feedback),
                         "S3-sol")
        files = parse_files(text)
        if not any(n.endswith(("sol.cpp", "sol.py")) for n in files):
            return False, "没有产出 sol.cpp"
        if "approach.md" not in files:
            return False, "没有产出 approach.md（3 号要靠它审思路）"
        self.write_files(files)
        ok, fb = self.check_code()
        if not ok:
            return ok, fb
        ok2, fb2 = self.check_samples()
        if not ok2:
            return ok2, fb2
        return self.verify_counterexample()

    def check_samples(self):
        """样例必须能被标程复算出来——AI 手写的样例答案经常是错的。

        但"标程和样例答案不一致"有两种可能：样例答案写错，或者标程写错。
        这时候不能默认标程对，先用两份已经互验过的暴力裁决。
        """
        sdir = os.path.join(self.prob_dir, "sample")
        if not os.path.isdir(sdir):
            return True, ""
        sys.path.insert(0, OJ_ROOT)
        from framework.runner import Runner
        runner = Runner(os.path.join(self.prob_dir, "build"))
        prog = runner.compile(os.path.join(self.prob_dir, "sol.cpp"), "sol")
        if prog is None:
            return False, "标程编译失败：" + "；".join(runner.errors)
        def _compile_brute(stem):
            for ext in (".cpp", ".py"):
                p = os.path.join(self.prob_dir, stem + ext)
                if os.path.exists(p):
                    return runner.compile(p, stem)
            return None
        judge = _compile_brute("brute")
        judge2 = _compile_brute("brute2")

        fixed, bad = [], []
        for name in sorted(os.listdir(sdir)):
            if not name.endswith(".in"):
                continue
            stem = name[:-3]
            inp = open(os.path.join(sdir, name), "rb").read()
            got, _, st = runner.run(prog, inp, 60)
            ans_path = os.path.join(sdir, stem + ".ans")
            want = _read(ans_path).split()
            if st == "OK" and got.split() == want:
                continue

            # 用暴力裁决：暴力跟谁一致，就以谁为准
            votes = []
            for prober in (judge, judge2):
                if prober is None:
                    continue
                v, _, vs = runner.run(prober, inp, 60)
                if vs == "OK":
                    votes.append(v.split())
            if votes and all(v == got.split() for v in votes):
                # 两份暴力都站在标程这边 → 是样例答案写错了，直接按标程改
                _write(ans_path, got if got.endswith("\n") else got + "\n")
                fixed.append(stem)
                self.log(f"样例 {stem} 的答案原来是错的（写的是 {want[:3]}，"
                         f"标程和暴力都是 {got.split()[:3]}），已按标程改正", "warn")
                continue
            if votes and all(v == want for v in votes):
                bad.append(f"{stem}: 标程输出 {got.split()[:3]}，但样例答案和暴力都是 {want[:3]}"
                           f"——是你标程写错了")
                continue
            bad.append(f"{stem}: 标程 {got.split()[:3]}、样例答案 {want[:3]}、"
                       f"暴力 {[v[:3] for v in votes]}，三方对不上")
        if fixed:
            self.log(f"改正了 {len(fixed)} 个样例答案：{fixed}", "warn")
        if bad:
            return False, "样例复算失败：" + "；".join(bad)
        return True, ""

    def run_counterexample(self, text):
        """3 号给了反例，直接拿去跑：sol 和暴力结果不一致才算站住。"""
        sys.path.insert(0, OJ_ROOT)
        from framework.runner import Runner
        r = Runner(os.path.join(self.prob_dir, "build"))
        sol = r.compile(os.path.join(self.prob_dir, "sol.cpp"), "sol")
        bru = r.compile(os.path.join(self.prob_dir, "brute.cpp"), "brute")
        if sol is None or bru is None:
            return False, "反例无法验证（编译失败）"
        data = text.encode("utf-8")
        a, _, sa = r.run(sol, data, 30)
        b, _, sb = r.run(bru, data, 30)
        if sa != "OK" or sb != "OK":
            self.log(f"3 号的反例跑不起来（{sa}/{sb}），忽略", "warn")
            return False, ""
        if a.split() == b.split():
            self.log("3 号给的反例没站住：标程和暴力输出一致", "warn")
            return False, ""
        return True, (f"输入 {text[:200]!r}，标程输出 {a.strip()[:60]!r}，"
                      f"暴力输出 {b.strip()[:60]!r}")

    def do_review_code(self, feedback, i):
        """3 号审思路 + 审代码。它不写实现，所以不会卡在长输出上。

        通过与否只看「结论」和「反例」：
        分析过程写进「分析」字段，不能被当成问题——否则模型夸你一句都算失败。
        """
        f = self.files_of("approach.md", "sol.cpp")
        text = self.call(3, prompts.p_review_code(self.rendered_statement(),
                                                  f["approach.md"], f["sol.cpp"]),
                         "S4-review-code")
        try:
            data = extract_json(text)
        except Exception:
            self.log("3 号的 review.json 无法解析，跳过这次审查", "warn")
            return True, ""
        files = parse_files(text)
        if "review.json" in files:
            self.write_files(files)

        verdict = str(data.get("结论") or "").strip().lower()
        notes = data.get("问题") or []
        analysis = str(data.get("分析") or "")[:200]
        if analysis:
            self.log(f"3 号的分析：{analysis}")
        if notes:
            self.log("3 号列出的问题：" + "；".join(map(str, notes))[:300],
                     "warn" if verdict.startswith("problem") else "info")

        problems = []
        ce = (data.get("反例") or "").strip()
        if ce:
            stands, detail = self.run_counterexample(ce)
            if stands:
                problems.append("反例站住了：" + detail)
                _write(os.path.join(self.prob_dir, "build", "counterexample.in"), ce + "\n")

        says_problem = verdict.startswith(("problem", "有问题", "fail", "not ok"))
        if says_problem and not problems:
            # 3 号说有问题，但一次反例都拿不出来（或给的反例被机器否掉）。
            # "我没想到证明"不等于"证明不成立"——只记录为疑虑，不阻塞流水线。
            self.log("3 号判定有问题，但没能给出站得住的反例；只记为疑虑，不阻塞流程", "warn")
            _write(os.path.join(self.prob_dir, "build", "review_code_concerns.json"),
                   json.dumps({"结论": verdict, "分析": data.get("分析"),
                               "问题": notes, "反例": ce}, ensure_ascii=False, indent=2))
            return True, ""
        if problems:
            return False, "；".join(problems) + ("；3 号指出的问题：" + "；".join(map(str, notes))
                                                if notes else "")
        self.log("3 号检查通过", "ok")
        return True, ""

    def do_impl(self, feedback, i):
        """4 号：先出思路，再写代码。拆两步是为了失败得更快。"""
        f = self.files_of("spec.py")
        statement = self.rendered_statement()
        plan_text = self.call(4, prompts.p_impl_plan(statement, f["spec.py"]), "S5-impl-plan")
        plan_files = parse_files(plan_text)
        plan = next(iter(plan_files.values()), plan_text)[:4000]
        _write(os.path.join(self.prob_dir, "impl_plan.md"), plan)

        ref_name, ref_body = None, None
        for attempt in range(2):
            text = self.call(4, prompts.p_impl_code(statement, f["spec.py"], plan),
                             "S5-impl-code" if attempt == 0 else "S5-impl-code-retry")
            for n, body in parse_files(text).items():
                if os.path.basename(n).startswith("ref") and len(body.strip()) > 80:
                    ref_name, ref_body = os.path.basename(n), body
                    break
            if ref_name:
                break
            self.log(f"4 号第 {attempt + 1} 次没写出可用代码", "warn")
        if ref_name is None:
            return False, "4 号按方案也没写出 ref.cpp"

        for old in ("ref.cpp", "ref.py"):
            p = os.path.join(self.prob_dir, old)
            if os.path.exists(p):
                os.remove(p)
        _write(os.path.join(self.prob_dir, ref_name), ref_body)
        ok, fb = self.gate("solve", "4 号独立实现对拍", ["--force"])

        # 小数据对拍只比 sol 和 brute，跟 4 号的 ref 无关——那是 1 号自己的两个程序打架
        if not ok and "小数据对拍不一致" in fb:
            self.log("标程和暴力在小数据上就不一致，这是 1 号的锅，回退让他修", "bad")
            sok, sfb = self.do_sol("你写的标程和暴力在小规模随机数据上结果不一致，"
                                   "必须先把它们修到一致：\n" + fb[:1500], i)
            if not sok:
                return False, sfb
            ok, fb = self.gate("solve", "4 号独立实现对拍", ["--force"])

        if not ok and re.search(r"\b(KeyError|TypeError|NameError|IndexError|ValueError)\b", fb):
            # 这类错不是实现的问题，是 gen.py 自己的代码炸了——让 1 号修，别让 4 号背锅
            self.log("对拍时生成器抛异常，问题在 gen.py，让 1 号修完再重试", "warn")
            gok, gfb = self.do_gen(fb, i)
            if not gok:
                return False, gfb
            ok, fb = self.gate("solve", "4 号独立实现对拍", ["--force"])
        return ok, fb

    def do_gen(self, feedback, i):
        f = self.files_of("spec.py", "sol.cpp")
        sys.path.insert(0, OJ_ROOT)
        from framework.problem import Problem
        names = []
        try:
            p = Problem(self.prob_dir).load()
            names = [n for _, n in p.tests]
        except Exception:
            pass
        text = self.call(1, prompts.p_gen(f["spec.py"], f["sol.cpp"], names, feedback), "S5-gen")
        files = parse_files(text)
        if "gen.py" not in files:
            return False, "没有产出 gen.py"
        # 先做语法检查：import 失败的报错没有行号，模型改不动
        try:
            ast.parse(files["gen.py"])
        except SyntaxError as e:
            snippet = (e.text or "").strip()
            return False, (f"gen.py 第 {e.lineno} 行语法错误：{e.msg}\n"
                           f"出错的那一行是：{snippet}")
        self.write_files(files)
        ok, fb = self.gate("check", "契约")
        if not ok:
            return ok, fb
        return self.gate("gen", "生成数据")

    def classify_wrongs(self, rounds=120):
        """把"其实是对的错解"踢出去，给真错的错解找出具体反例。

        返回 {错解名: (输入, 标程输出, 它的输出)}，供补强时当反馈。
        """
        wdir = os.path.join(self.prob_dir, "wrong")
        if not os.path.isdir(wdir):
            return {}
        srcs = sorted(f for f in os.listdir(wdir) if f.endswith((".cpp", ".py")))
        if not srcs:
            return {}
        sys.path.insert(0, OJ_ROOT)
        from framework.problem import Problem
        from framework import stages as oj_stages
        try:
            p = Problem(self.prob_dir).load()
        except Exception:
            return {}
        tmpl_names = p.fuzz_small()
        if not tmpl_names:
            return {}
        ctx = oj_stages._fuzz_ctx(p)
        r = self._runner()
        sol = r.compile(os.path.join(self.prob_dir, "sol.cpp"), "sol")
        if sol is None:
            return {}

        witnesses = {}
        dropped = []
        for src in srcs:
            stem = os.path.splitext(src)[0]
            prog = r.compile(os.path.join(wdir, src), "w_" + stem)
            if prog is None:
                continue
            found = None
            for it in range(rounds):
                nm, over = tmpl_names[it % len(tmpl_names)]
                c3 = dict(ctx); c3.update(over)
                try:
                    inp = p.templates[nm](random.Random(it * 7 + 1), c3).encode()
                except Exception:
                    continue
                # 反例必须是**合法输入**，否则让 1 号照着加测试点就是害他
                try:
                    p.spec.check(inp.decode("utf-8", "replace"),
                                 p.subtasks.get(1, {}))
                except AssertionError:
                    continue
                except Exception:
                    continue
                a, _, sa = r.run(sol, inp, 20)
                b, _, sb = r.run(prog, inp, 20)
                if sa != "OK" or sb != "OK" or not _same_answer(a, b):
                    found = (inp.decode("utf-8", "replace"), a.strip()[:40], b.strip()[:40])
                    break
            if found:
                witnesses[stem] = found
            else:
                # 和标程在随机小数据上完全一致，又没有已知反例 —— 它不是错解
                dst = os.path.join(self.prob_dir, "build", "discarded")
                os.makedirs(dst, exist_ok=True)
                shutil.move(os.path.join(wdir, src), os.path.join(dst, src))
                dropped.append(stem)
        if dropped:
            self.log("这些「错解」和标程在随机数据上完全一致，其实是对的，"
                     "已移出攻击列表：" + "、".join(dropped), "warn")
        return witnesses

    def do_wrong(self, feedback, i):
        f = self.files_of("spec.py", "sol.cpp", "gen.py")
        text = self.call(4, prompts.p_wrong(f["spec.py"], f["sol.cpp"], f["gen.py"], feedback),
                         "S6-wrong")
        files = parse_files(text)
        if not files:
            return False, "没有产出任何错解文件"
        # 先清掉上一轮留下的程序文件：补强时 4 号会重写一批，
        # 旧的留在目录里会被当成"又一个错解/部分分"继续参与评分。
        for sub in ("wrong", "partial"):
            d = os.path.join(self.prob_dir, sub)
            if not os.path.isdir(d):
                continue
            for f in os.listdir(d):
                if f.endswith((".cpp", ".py", ".cc", ".cxx")):
                    try:
                        os.remove(os.path.join(d, f))
                    except OSError:
                        pass
        self.write_files(files)
        # 先甄别：把"其实和标程一致"的假错解踢出去，顺便抓真错解的反例
        self.last_witnesses = self.classify_wrongs()
        ok, fb = self.gate("attack", "错解攻击")
        if not ok:
            return ok, fb
        return self.gate("calib", "部分分定标")

    def do_editorial(self, feedback, i):
        f = self.files_of("spec.py", "statement.md", "gen.py")
        calib = _read(os.path.join(self.prob_dir, "build", "calib.json"), "{}")
        text = self.call(1, prompts.p_editorial(f["spec.py"], f["statement.md"],
                                                f["gen.py"], calib), "S7-editorial")
        files = parse_files(text)
        if "editorial.md" not in files:
            return False, "没有产出 editorial.md"
        self.write_files(files)
        return self.check_editorial(files["editorial.md"])

    def check_editorial(self, md):
        """题解必须和实测分数、spec 里的子任务分值双向对齐。"""
        spec = _read(os.path.join(self.prob_dir, "spec.py"))
        declared = set(re.findall(r"score\s*=\s*(\d+)", spec))
        calib = json.loads(_read(os.path.join(self.prob_dir, "build", "calib.json"), "{}"))
        measured = {str(r.get("score")) for r in calib.get("rows", [])
                    if r.get("score") is not None}
        missing = [s for s in (declared | measured) if s not in md]
        if missing:
            self.log(f"题解里没有提到这些分数 {sorted(missing)}"
                     f"（spec 声明 {sorted(declared)}，实测 {sorted(measured)}）", "warn")
        for need in ("复杂度", "部分分"):
            if need not in md:
                self.log(f"题解缺少「{need}」一节，建议补上", "warn")
        self.log("题解已生成（分数对齐情况见上面的警告）", "ok")
        return True, ""

    def attack_block(self):
        """错解存活 = 数据不够强 → 反馈给 1 号补模板，而不是改错解。"""
        fb = ""
        for i in range(MAX_ROUNDS):
            if i:
                self.phase = "S6 补强数据"
                self.log(f"—— 数据补强第 {i + 1}/{MAX_ROUNDS} 轮 ——", "phase")
                try:
                    ok, fb2 = self.do_gen(fb, i)
                except RuntimeError as e:
                    self.log(f"1 号这次没能补完数据（{e}）", "warn")
                    fb = str(e)
                    continue
                if not ok:
                    fb = fb2
                    continue
            try:
                ok, fb2 = self.do_wrong("", i)
            except RuntimeError as e:
                # 4 号超长思考/调用失败，不该让整道题异常终止
                self.log(f"4 号这次没能写完错解（{e}）", "warn")
                fb = (f"4 号在写错解时失败了：{e}。如果反复出现，说明这个模型"
                      f"不适合写错解，换一个不做长推理的模型。")
                continue
            if ok:
                return
            fb = ("上一轮错解存活了：" + fb2 +
                  "\n请针对这些错解补充数据模板（例如让某个测试点能区分它），"
                  "不要修改错解本身，也不要放宽 check()。")
            wit = getattr(self, "last_witnesses", None) or {}
            if wit:
                picked = list(wit.items())[:3]
                fb += "\n下面是我实测到的、这些错解真的会出错的输入，请把它们或同类的加进测试点：\n"
                for name, (inp, a, b) in picked:
                    fb += f"- 错解 {name}：输入 `{inp[:180]!r}` 时标程给 {a}，它给 {b}\n"
            self.log("数据不够强，回退重写 gen.py：" + fb2, "warn")
        raise StageFailed("attack", f"连续 {MAX_ROUNDS} 轮补强仍未杀掉错解。最后原因：{fb[:300]}")

    def rendered_statement(self):
        """把题面按 spec 渲染好再给审题者看。

        直接给模板会让 2 号误判"数据范围没写"——因为 {{SUBTASK_TABLE}} 之类
        要到打包时才展开。审题必须看选手最终看到的东西。
        """
        sys.path.insert(0, OJ_ROOT)
        from framework.problem import Problem
        from framework import statement as stmt
        try:
            return stmt.render(Problem(self.prob_dir))
        except Exception as e:
            self.log(f"题面渲染失败，审题退回原始模板：{e}", "warn")
            return _read(os.path.join(self.prob_dir, "statement.md"))

    def review_once(self):
        """2 号审题。返回 (是否通过, 冲突描述)。

        模型偶尔会返回空内容或不可解析的 JSON —— 那是审题器故障，
        不是题面有问题，所以原地重试审题，而不是回退去改题面。
        """
        f = self.files_of("spec.py")
        statement = self.rendered_statement()
        for attempt in range(2):
            tag = "S2-review" if attempt == 0 else "S2-review-retry"
            text = self.call(2, prompts.p_review(statement, f["spec.py"]), tag)
            try:
                data = extract_json(text)
            except Exception:
                self.log("2 号的 review.json 无法解析，重试审题", "warn")
                continue
            files = parse_files(text)
            if "review.json" in files:
                self.write_files(files)
            conflicts = data.get("冲突") or []
            verdict = str(data.get("结论") or "").strip().lower()
            if conflicts or verdict in ("ambiguous", "歧义"):
                return False, "；".join(map(str, conflicts)) or "2 号判定题面有歧义"
            self.log("2 号认为题面完整：" + str(data.get("理解", ""))[:160], "ok")
            return True, ""
        self.log("2 号连续两次没给出可解析的 review，跳过审题闸门（已记录，请人工看题面）", "warn")
        return True, ""

    def plan_loop(self, seed_feedback=""):
        """S1 写题面 → S2 审题；审出歧义就带着冲突回退给 1 号重写。

        注意：审题失败不能原地重试——什么都没改，必然一直失败。
        """
        fb = seed_feedback
        for i in range(MAX_ROUNDS):
            self.phase = "S1 写 spec + 题面"
            self.log(f"—— 1 号：写 spec + 题面 + 样例（第 {i + 1}/{MAX_ROUNDS} 轮）——", "phase")
            try:
                ok, fb2 = self.do_spec(fb, i)
            except RuntimeError as e:
                self.log(f"1 号这次没能正常写完（{e}）", "warn")
                fb = str(e)
                continue
            if not ok:
                fb = "spec 校验没过，先修这个：\n" + fb2
                continue
            try:
                ok, conflicts = self.review_once()
            except RuntimeError as e:
                # 审题器自己崩了（思考死循环、调用失败）不该拖累整道题
                self.log(f"2 号这次没能正常审题（{e}），跳过审题继续往下走", "warn")
                return
            if ok:
                return
            self.log("2 号认为题面有歧义，回退让 1 号重写：" + conflicts[:300], "warn")
            fb = ("2 号审题时发现题面没把下面这些说清楚，请同时修题面和 spec，"
                  "不要只改措辞而不补信息：\n" + conflicts)
        raise StageFailed("review", f"连续 {MAX_ROUNDS} 轮题面都没审过。最后问题：{fb}")

    # ---------------------------------------------------------------- S3 暴力
    def _runner(self):
        sys.path.insert(0, OJ_ROOT)
        from framework.runner import Runner
        return Runner(os.path.join(self.prob_dir, "build"))

    def compile_one(self, name, label):
        src = os.path.join(self.prob_dir, name)
        if not os.path.exists(src):
            return False, f"缺少 {name}"
        r = self._runner()
        p = r.compile(src, label)
        return (p is not None), ("" if p else "；".join(r.errors))

    def fuzz_pair(self, file_a, file_b, label_a, label_b, rounds=200):
        """拿 gen.py 的 FUZZ 模板跑两个程序，逐组比对。"""
        sys.path.insert(0, OJ_ROOT)
        from framework.problem import Problem
        from framework import stages as oj_stages
        try:
            p = Problem(self.prob_dir).load()
        except Exception as e:
            return False, f"题目文件加载失败：{e}"
        names = p.fuzz_small()
        if not names:
            return False, "gen.py 没有声明 FUZZ，没法对拍"
        ctx = oj_stages._fuzz_ctx(p)
        r = self._runner()
        pa = r.compile(os.path.join(self.prob_dir, file_a), label_a)
        pb = r.compile(os.path.join(self.prob_dir, file_b), label_b)
        if pa is None or pb is None:
            return False, "编译失败：" + "；".join(r.errors)
        for it in range(rounds):
            name, over = names[it % len(names)]
            c2 = dict(ctx); c2.update(over)
            try:
                inp = p.templates[name](random.Random(f"fz/{it}"), c2).encode()
            except Exception as e:
                return False, f"模板 {name} 生成失败：{e}"
            x, _, sx = r.run(pa, inp, 20)
            y, _, sy = r.run(pb, inp, 20)
            if sx != "OK" or sy != "OK" or not _same_answer(x, y):
                snip = inp.decode("utf-8", "replace")[:260].replace("\n", " ⏎ ")
                self.last_mismatch = {"input": inp.decode("utf-8", "replace"),
                                      "a": x.strip(), "b": y.strip(),
                                      "label_a": label_a, "label_b": label_b}
                return False, (f"第 {it + 1} 组就不一致（模板 {name}）："
                               f"{label_a} = {x.strip()[:40]}，{label_b} = {y.strip()[:40]}。"
                               f"输入是：{snip}")
        return True, ""

    def do_brute_gen(self, feedback, i):
        f = self.files_of("spec.py")
        names = []
        try:
            sys.path.insert(0, OJ_ROOT)
            from framework.problem import Problem
            names = [n for _, n in Problem(self.prob_dir).load().tests]
        except Exception:
            pass
        text = self.call(1, prompts.p_brute_gen(self.rendered_statement(),
                                                f["spec.py"], names), "S3-brute-gen")
        files = parse_files(text)
        for need in ("brute.cpp", "gen.py"):
            if need not in files:
                return False, f"没有产出 {need}"
        try:
            ast.parse(files["gen.py"])
        except SyntaxError as e:
            return False, f"gen.py 第 {e.lineno} 行语法错误：{e.msg}"
        self.write_files(files)
        ok, m = self.compile_one("brute.cpp", "brute")
        if not ok:
            return False, "brute.cpp 编译失败：" + m
        self.log("1 号的暴力编译通过", "ok")
        return True, ""

    def adjudicate(self):
        """两份暴力不一致时，让 3 号判是谁错了。

        这一步很重要：不分青红皂白就"回退重写题面"，等于用最贵的动作
        去处理一个可能只是实现 bug 的问题。
        """
        mm = getattr(self, "last_mismatch", None)
        if not mm:
            return "题面不清", "没有拿到冲突输入"
        fa = _read(os.path.join(self.prob_dir, "brute.cpp"))
        fb2 = _read(os.path.join(self.prob_dir, "brute2.cpp"))
        try:
            text = self.call(3, prompts.p_adjudicate(
                self.rendered_statement(), fa[:3500], fb2[:3500],
                mm["input"][:800], mm["a"], mm["b"]), "S3-adjudicate")
            data = extract_json(text)
        except Exception as e:
            self.log(f"仲裁失败（{e}），按题面不清处理", "warn")
            return "题面不清", ""
        verdict = str(data.get("判定") or "")
        reason = str(data.get("理由") or "")[:200]
        if "A错" in verdict or "a错" in verdict.lower():
            v = "1号错"
        elif "B错" in verdict or "b错" in verdict.lower():
            v = "2号错"
        else:
            v = "题面不清"
        self.log(f"3 号仲裁：{v}（{reason}）", "warn" if v != "2号错" else "info")
        return v, reason

    def do_brute2(self, feedback, i):
        f = self.files_of("spec.py")
        text = self.call(2, prompts.p_brute(self.rendered_statement(), f["spec.py"],
                                            " 2 号「审题者」", feedback), "S3-brute2")
        body = None
        for n, b in parse_files(text).items():
            base = os.path.basename(n)
            looks_cpp = base.endswith((".cpp", ".cc", ".cxx")) or \
                b.lstrip().startswith(("#include", "//", "/*"))
            if looks_cpp and len(b.strip()) > 80:
                body = b
                if base != "brute.cpp":
                    self.log(f"2 号把文件写成了 {base}，内容看着是 C++，按暴力处理", "warn")
                break
        if body is None:
            return False, f"2 号只返回了 {len(text.strip())} 字符，没写出可用暴力"
        _write(os.path.join(self.prob_dir, "brute2.cpp"), body)
        ok, m = self.compile_one("brute2.cpp", "brute2")
        if not ok:
            return False, "2 号的暴力编译失败：" + m
        ok, m = self.fuzz_pair("brute.cpp", "brute2.cpp", "1号暴力", "2号暴力")
        if not ok:
            verdict, reason = self.adjudicate()
            if verdict == "1号错":
                return False, "1号错：" + m
            if verdict == "2号错":
                return False, "2号错：" + m
            return False, "题面不清：" + m
        self.log("两份暴力在 200 组小数据上完全一致", "ok")
        return True, ""

    def brute_loop(self):
        """1 号写暴力+生成器 → 2 号独立写一份暴力 → 两份对拍。

        先把"真值"钉死：后面的正解、数据、错解全都拿暴力当裁判。
        """
        fb = ""
        need_a = True
        for i in range(MAX_ROUNDS):
            if need_a:
                self.phase = "S3 写暴力 + 生成器"
                self.log(f"—— 1 号：写暴力 + 数据生成器（第 {i + 1}/{MAX_ROUNDS} 轮）——", "phase")
                try:
                    ok, f = self.do_brute_gen(fb, i)
                except RuntimeError as e:
                    self.log(f"1 号这次没能写完暴力（{e}）", "warn")
                    ok, f = False, str(e)
                if not ok:
                    self.log("暴力/生成器没过：" + f[:200], "warn")
                    fb = f
                    continue
            self.phase = "S3 第二份暴力"
            self.log("—— 2 号：独立写一份暴力 ——", "phase")
            try:
                ok, f = self.do_brute2(fb if not need_a else "", i)
            except RuntimeError as e:
                self.log(f"2 号这次没能写完暴力（{e}）", "warn")
                ok, f = False, f"2 号这次没能写完暴力：{e}"
            if ok:
                return
            if f.startswith("题面不清"):
                # 这才是真的"题面缺约定"，回退重写题面
                raise StatementProblem(f)
            if f.startswith("2号错"):
                # 只有 2 号的暴力有问题，1 号的不用重写
                self.log("仲裁判定 2 号 的暴力算错了，只重做它", "warn")
                fb = f"你上一版的暴力算错了：{f[4:600]}"
                need_a = False
            else:
                self.log("仲裁判定 1 号 的暴力算错了，只重做它", "warn")
                fb = f"你的暴力算错了：{f[4:600]}"
                need_a = True
        raise StageFailed("brute", f"连续 {MAX_ROUNDS} 轮暴力没通过。最后：{fb[:300]}")

    def do_std(self, feedback, i):
        f = self.files_of("spec.py", "brute.cpp")
        brute2 = _read(os.path.join(self.prob_dir, "brute2.cpp"))
        text = self.call(1, prompts.p_std(self.rendered_statement(), f["spec.py"],
                                          f["brute.cpp"][:1800] + "\n/* 第二份暴力 */\n" + brute2[:1800]),
                         "S4-std")
        files = parse_files(text)
        for need in ("sol.cpp", "approach.md"):
            if need not in files:
                return False, f"没有产出 {need}"
        self.write_files(files)
        ok, m = self.check_code()
        if not ok:
            return ok, m
        ok, m = self.check_samples()
        if not ok:
            return ok, m
        ok, m = self.gate("gen", "生成数据 + 小数据对拍")
        if not ok:
            return ok, m
        ok, m = self.fuzz_pair("sol.cpp", "brute2.cpp", "标程", "2号暴力")
        if not ok:
            return False, "标程和 2 号暴力不一致：" + m
        return self.verify_counterexample()

    def std_loop(self):
        fb = ""
        for i in range(MAX_ROUNDS):
            self.phase = "S4 写正解"
            self.log(f"—— 1 号：写正解 + 思路（第 {i + 1}/{MAX_ROUNDS} 轮）——", "phase")
            try:
                ok, f = self.do_std(fb, i)
            except RuntimeError as e:
                self.log(f"1 号这次没能写完（{e}）", "warn")
                ok, f = False, str(e)
            if not ok:
                self.log("正解没过：" + f[:240], "warn")
                fb = "正解没过：\n" + f
                continue
            try:
                ok, f2 = self.do_review_code("", i)
            except RuntimeError as e:
                self.log(f"3 号这次没能正常审查（{e}），跳过审查继续", "warn")
                return
            if ok:
                return
            self.log("3 号发现真问题，回退让 1 号修正解：" + f2[:200], "warn")
            fb = ("3 号审查时发现了真问题（反例已被机器验证）。请修 sol.cpp：\n" + f2)
        raise StageFailed("std", f"连续 {MAX_ROUNDS} 轮正解没通过。最后：{fb[:300]}")

    def run(self):
        self.status = "running"
        self.save()
        try:
            if os.path.isdir(self.prob_dir):
                shutil.rmtree(self.prob_dir)
            os.makedirs(self.prob_dir, exist_ok=True)
            self.log(f"题目目录：problems/{self.problem_id}")
            self.plan_loop()
            for _outer in range(2):
                try:
                    self.brute_loop()
                    break
                except StatementProblem as e:
                    self.log("两份暴力对不上，说明题面缺了约定；回退重写题面", "bad")
                    self.plan_loop(seed_feedback=(
                        "两份独立写的暴力在同一组输入上给出了不同的答案。"
                        "这通常不是暴力写错了，而是题面缺了某个约定"
                        "（比如无解时输出什么、并列最优怎么处理）。"
                        "请补上题面里缺的约定，同时让 spec 的 check 也校验对应前提：\n"
                        + str(e)[:1200]))
            else:
                raise StageFailed("brute", "两份暴力始终对不上，题面改了两轮还是没统一")
            self.std_loop()
            self.step("impl", "4 号：先出思路，再写实现", self.do_impl)
            self.attack_block()
            self.step("editorial", "1 号：写题解", self.do_editorial)
            ok, fb = self.gate("build", "组装打包")
            if not ok:
                raise StageFailed("build", fb)
            self.status = "done"
            self.phase = "完成"
            self.log("全部闸门通过，可以出厂了", "ok")
        except StageFailed as e:
            self.status = "failed"
            self.error = e.reason
            self.phase = e.stage
            self.log(f"作废：{e.reason}", "bad")
        except Exception as e:
            self.status = "failed"
            self.error = f"{type(e).__name__}: {e}"
            self.log(f"异常终止：{self.error}", "bad")
        finally:
            # 成功和失败的题分开放：成功的留在 problems/，失败的挪到 problems/_failed/
            # 这样 problems/ 里只看得到真正出完的题，查重库也不会被半成品污染。
            if self.status != "done":
                try:
                    if os.path.isdir(self.prob_dir):
                        dest_root = os.path.join(OJ_ROOT, "problems", "_failed")
                        os.makedirs(dest_root, exist_ok=True)
                        dest = os.path.join(dest_root, self.problem_id)
                        if os.path.isdir(dest):
                            shutil.rmtree(dest, ignore_errors=True)
                        shutil.move(self.prob_dir, dest)
                        self.log(f"失败产物已挪到 problems/_failed/{self.problem_id}")
                except Exception as e:
                    self.log(f"挪动失败产物时出错：{e}", "warn")
            self.save()
        return self.status


def start(seed, slots):
    rid = time.strftime("run-%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    run = Run(rid, seed, slots)
    run.save()          # 先落盘，前端立刻就能轮询到
    return run
