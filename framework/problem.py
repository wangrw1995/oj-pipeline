# -*- coding: utf-8 -*-
"""题目加载与契约校验。

一道题 = problems/<id>/ 一个目录，契约如下（缺一项就报错，不允许"差不多能跑"）：

    spec.py     ID / TITLE / LIMIT / MEM / SUBTASKS / TESTS / GLOBAL / check()
    gen.py      TEMPLATES 注册表，可选 FUZZ / FUZZ_MID
    statement.md  题面模板，含 {{...}} 占位符
    sol.*      标程        brute.*  暴力        ref.*  独立实现
    wrong/     必须被杀的错解      partial/  只拿部分分的程序
"""
import importlib.util
import os
import re
import sys

from .utils import dir_hash

SOLVER_EXTS = (".cpp", ".py")


def _load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载 {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class ProblemError(Exception):
    pass


class _EmptyGen:
    TEMPLATES = {}


def _divisors(n):
    return [d for d in range(2, n + 1) if n % d == 0]


def _as_number(v, default):
    """宽容解析：模型常把 LIMIT 写成 '1s'、'1.5 秒'、'256MB' 这种带单位的值。"""
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"\d+(?:\.\d+)?", str(v))
    return float(m.group()) if m else float(default)


class Problem:
    def __init__(self, path):
        self.dir = os.path.abspath(path)
        self.id = os.path.basename(self.dir)
        self.build = os.path.join(self.dir, "build")
        self.data = os.path.join(self.build, "data")
        self._hash = None
        self._spec = None
        self._gen = None
        self.gen_missing = False
        self.problems = []          # 契约问题列表，非空即不可用

    # ---------------------------------------------------------------- 加载
    def load(self):
        if self._spec is not None:
            return self
        spec_path = os.path.join(self.dir, "spec.py")
        gen_path = os.path.join(self.dir, "gen.py")
        if not os.path.exists(spec_path):
            raise ProblemError(f"{self.id}: 缺少 spec.py")
        self._spec = _load_module(spec_path, f"oj_spec_{self.id.replace('-', '_')}")
        if os.path.exists(gen_path):
            self._gen = _load_module(gen_path, f"oj_gen_{self.id.replace('-', '_')}")
        else:
            # 流水线早期（题面和 spec 刚写出来）还没有 gen.py，
            # 允许加载，由 validate 决定这算不算问题
            self._gen = _EmptyGen()
            self.gen_missing = True
        return self

    # ---------------------------------------------------------------- 元信息
    @property
    def spec(self):
        self.load()
        return self._spec

    @property
    def gen(self):
        self.load()
        return self._gen

    @property
    def title(self):
        return getattr(self.spec, "TITLE", self.id)

    @property
    def code(self):
        """提交文件名（题面表格用），例如 pair。默认等于目录名。"""
        return getattr(self.spec, "CODE", self.id)

    @property
    def limit(self):
        return _as_number(getattr(self.spec, "LIMIT", 1.0), 1.0)

    @property
    def mem(self):
        return int(_as_number(getattr(self.spec, "MEM", 256), 256))

    @property
    def tags(self):
        return list(getattr(self.spec, "TAGS", []))

    @property
    def subtasks(self):
        return dict(getattr(self.spec, "SUBTASKS", {}))

    @property
    def tests(self):
        return list(getattr(self.spec, "TESTS", []))

    @property
    def templates(self):
        return dict(getattr(self.gen, "TEMPLATES", {}))

    @staticmethod
    def _norm_fuzz(entries):
        """把 FUZZ / FUZZ_MID 归一成 [(模板名, 覆盖参数)]。

        约定是模板名字符串列表，但模型有时会写成 ("名字", {"max_n": 20}) 这种
        带参数的元组。两种都接受，否则一个格式问题会被误判成"题面缺约定"。
        """
        out = []
        for e in entries or ():
            if isinstance(e, str):
                out.append((e, {}))
            elif isinstance(e, (list, tuple)) and e and isinstance(e[0], str):
                extra = e[1] if len(e) > 1 and isinstance(e[1], dict) else {}
                out.append((e[0], dict(extra)))
        return out

    def fuzz_small(self):
        return self._norm_fuzz(getattr(self.gen, "FUZZ", []))

    def fuzz_mid(self):
        return self._norm_fuzz(getattr(self.gen, "FUZZ_MID", []))

    # ---------------------------------------------------------------- 评分
    def sub_count(self, sub):
        return sum(1 for s, _ in self.tests if s == sub)

    def points(self, idx):
        """第 idx 个测试点（1-based）的分值：子任务总分在其测试点间均分。"""
        sub = self.tests[idx - 1][0]
        cnt = self.sub_count(sub)
        if cnt == 0:
            return 0
        return self.subtasks[sub]["score"] // cnt

    def total_points(self):
        return sum(self.points(i + 1) for i in range(len(self.tests)))

    # ---------------------------------------------------------------- 解法
    def _pick(self, stem):
        for ext in SOLVER_EXTS:
            p = os.path.join(self.dir, stem + ext)
            if os.path.exists(p):
                return p
        return None

    def sol_path(self):
        return self._pick("sol")

    def brute_path(self):
        return self._pick("brute")

    def ref_path(self):
        return self._pick("ref")

    def wrong_paths(self):
        d = os.path.join(self.dir, "wrong")
        if not os.path.isdir(d):
            return []
        return [os.path.join(d, n) for n in sorted(os.listdir(d))
                if n.endswith(SOLVER_EXTS)]

    def partial_paths(self):
        d = os.path.join(self.dir, "partial")
        if not os.path.isdir(d):
            return []
        return [os.path.join(d, n) for n in sorted(os.listdir(d))
                if n.endswith(SOLVER_EXTS)]

    def partial_expected(self):
        import json
        p = os.path.join(self.dir, "partial", "expected.json")
        if not os.path.exists(p):
            return {}
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    def wrong_allow(self):
        """wrong/allow.json：某些错解在数学上无法被某类测试点区分，
        可以显式声明"允许拿多少分"。默认全部 0 分。"""
        import json
        p = os.path.join(self.dir, "wrong", "allow.json")
        if not os.path.exists(p):
            return {}
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    def statement_path(self):
        for name in ("statement.md", "statement.md.j2"):
            p = os.path.join(self.dir, name)
            if os.path.exists(p):
                return p
        return None

    def sample_dir(self):
        d = os.path.join(self.dir, "sample")
        return d if os.path.isdir(d) else None

    # ---------------------------------------------------------------- 契约
    def validate(self, spec_only=False):
        """返回问题列表；空列表表示契约完整。

        spec_only=True 只校验 spec 本身（子任务/测试点/分值），
        用于流水线早期：题面和 spec 刚写出来、解法和数据还没有的时候。
        """
        out = []
        try:
            self.load()
        except ProblemError as e:
            return [str(e)]
        for attr in ("ID", "TITLE", "LIMIT", "MEM", "SUBTASKS", "TESTS"):
            if not hasattr(self.spec, attr):
                out.append(f"spec.py 缺少 {attr}")
        if out:
            return out
        if not hasattr(self.spec, "check"):
            out.append("spec.py 缺少 check(text, sub) 约束校验函数")
        if not hasattr(self.spec, "GLOBAL"):
            out.append("spec.py 缺少 GLOBAL（题面数据范围文字）")

        subs = self.subtasks
        if not subs:
            out.append("SUBTASKS 为空")
        for sid, s in subs.items():
            if "score" not in s:
                out.append(f"子任务 {sid} 缺少 score")
            if not s.get("desc"):
                out.append(f"子任务 {sid} 缺少 desc（题面表格要用）")

        tests = self.tests
        if not tests:
            out.append("TESTS 为空")
        tmpl = self.templates
        for i, item in enumerate(tests, 1):
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                out.append(f"TESTS 第 {i} 项应为 (子任务, 模板名)")
                continue
            sub, name = item
            if sub not in subs:
                out.append(f"TESTS 第 {i} 项引用了不存在的子任务 {sub}")
            if not spec_only and name not in tmpl:
                out.append(f"TESTS 第 {i} 项引用了不存在的模板 {name!r}")
        for sid in subs:
            if self.sub_count(sid) == 0:
                out.append(f"子任务 {sid} 没有任何测试点")
        # 分值必须能被测试点数整除，否则均分时会丢分
        for sid, s in subs.items():
            cnt = self.sub_count(sid)
            if cnt and s.get("score") and s["score"] % cnt != 0:
                per = s["score"] // cnt
                out.append(
                    f"子任务 {sid} 的 {s['score']} 分无法被它的 {cnt} 个测试点整除"
                    f"（每点 {per} 分，只覆盖 {per * cnt} 分）。"
                    f"请把该子任务的测试点改成 {s['score']} 的约数"
                    f"（如 {', '.join(str(d) for d in _divisors(s['score']) if d <= 10)} 个），"
                    f"或把分值调成能被 {cnt} 整除的数"
                )
        used_total = self.total_points()
        if subs and used_total != 100:
            out.append(f"测试点分值合计 {used_total}，应为 100")

        # 时限/内存的合理区间。模型偶尔会写出 LIMIT = 1000 这种值，
        # 那会让后面所有超时判断按 1000 秒算，等于没有超时，整个流程会磨到天荒地老。
        try:
            lim = float(self.limit)
        except Exception:
            lim = -1.0
        if not (0.1 <= lim <= 20):
            out.append(f"LIMIT = {self.limit} 不合理：应写 0.5~10 之间（例如 LIMIT = 1）")
        try:
            mem = float(self.mem)
        except Exception:
            mem = -1.0
        if not (16 <= mem <= 2048):
            out.append(f"MEM = {self.mem} 不合理：应写 64~1024 MB")

        for name, _over in self.fuzz_small() + self.fuzz_mid():
            if not spec_only and name not in tmpl:
                out.append(f"FUZZ 引用了不存在的模板 {name!r}")

        if spec_only:
            return out

        if self.gen_missing:
            out.append("缺少 gen.py")
        if not self.sol_path():
            out.append("缺少 sol.cpp / sol.py（标程）")
        if not self.brute_path():
            out.append("缺少 brute.cpp / brute.py（暴力）")
        if self.statement_path() is None:
            out.append("缺少 statement.md（题面模板）")
        return out

    # ---------------------------------------------------------------- 其他
    def input_hash(self):
        if self._hash is None:
            self._hash = dir_hash(self.dir)
        return self._hash

    def stage_path(self, stage):
        return os.path.join(self.build, f"{stage}.json")


def discover(root):
    """列出 problems/ 下的所有题目目录（跳过 _template）。"""
    out = []
    if not os.path.isdir(root):
        return out
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        if not os.path.isdir(d) or name.startswith("_"):
            continue
        if os.path.exists(os.path.join(d, "spec.py")):
            out.append(Problem(d))
    return out
