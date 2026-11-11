# -*- coding: utf-8 -*-
"""程序运行器：统一处理 .cpp（编译后执行）与 .py（解释执行）。

设计要点：流水线的其余部分不关心题目用什么语言实现。
题目目录里同名不同扩展名的文件，优先用 .cpp；没有编译器时自动降级到 .py。
"""
import os
import shutil
import subprocess
import sys
import time

from .utils import fmt_ms

CXX_CANDIDATES = ["g++", "clang++", "c++"]

# PATH 里没找到时，再探一遍常见安装位置（新装的编译器往往要重开终端才进 PATH）
CXX_COMMON_PATHS = [
    r"C:\w64devkit\bin\g++.exe",
    r"C:\mingw64\bin\g++.exe",
    r"C:\msys64\mingw64\bin\g++.exe",
    r"C:\MinGW\bin\g++.exe",
    r"C:\TDM-GCC-64\bin\g++.exe",
    r"C:\Program Files\mingw-w64\bin\g++.exe",
    r"C:\Program Files\LLVM\bin\clang++.exe",
]


def find_cxx():
    env = os.environ.get("OJ_CXX")
    if env:
        return shutil.which(env) or (env if os.path.exists(env) else None)
    for name in CXX_CANDIDATES:
        p = shutil.which(name)
        if p:
            return p
    for p in CXX_COMMON_PATHS:
        if os.path.exists(p):
            return p
    return None


class Program:
    """一个可运行的程序。kind 为 'exe' 或 'py'。"""

    def __init__(self, kind, path, src, label):
        self.kind = kind
        self.path = path
        self.src = src
        self.label = label

    def __repr__(self):
        return f"<{self.kind} {self.label}>"


class Runner:
    def __init__(self, builddir):
        self.builddir = builddir
        self.bindir = os.path.join(builddir, "bin")
        self.cxx = find_cxx()
        self.compiled = {}      # src -> Program
        self.errors = []
        os.makedirs(self.bindir, exist_ok=True)

    # ---------------------------------------------------------------- 编译
    def compile(self, src, label=None):
        if src in self.compiled:
            return self.compiled[src]
        label = label or os.path.splitext(os.path.basename(src))[0]
        if src.endswith(".py"):
            prog = Program("py", src, src, label)
            self.compiled[src] = prog
            return prog
        if not self.cxx:
            self.errors.append(f"{label}: 没有找到 C++ 编译器（g++/clang++），跳过")
            return None
        out = os.path.join(self.bindir, label + ".exe")
        # 真实 OJ 的栈普遍是 8MB 起（Linux 默认 ulimit -s 8192，有的开到 256MB），
        # 而 Windows 下 mingw 链接出来的 exe 默认只有约 2MB。
        # 不显式放大，n=1e5 的递归 DFS 会在本地崩、在 OJ 上却能过 —— 那是假阴性。
        cmd = [self.cxx, "-O2", "-std=c++17", "-Wl,--stack,67108864", "-o", out, src]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        except Exception as e:
            self.errors.append(f"{label}: 编译异常 {e}")
            return None
        if r.returncode != 0:
            self.errors.append(f"{label}: 编译失败\n{r.stderr.strip()[:800]}")
            return None
        prog = Program("exe", out, src, label)
        self.compiled[src] = prog
        return prog

    # ---------------------------------------------------------------- 运行
    def run(self, prog, data: bytes, timeout: float):
        """返回 (stdout_text, elapsed_ms, status)，status ∈ OK / TLE / RE"""
        cmd = [prog.path] if prog.kind == "exe" else [sys.executable, prog.path]
        env = dict(os.environ)
        env.setdefault("PYTHONIOENCODING", "utf-8")
        t0 = time.perf_counter()
        try:
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, env=env)
        except Exception as e:
            return "", 0.0, f"RE({e})"
        try:
            out, err = p.communicate(data, timeout=timeout)
            ms = (time.perf_counter() - t0) * 1000
        except subprocess.TimeoutExpired:
            ms = (time.perf_counter() - t0) * 1000
            # 有些程序（越界写坏了内存/死循环）在 Windows 上 p.kill() 一次杀不掉，
            # 而 communicate() 会一直等管道关闭 —— 整条流水线就卡在这里。
            # 所以：杀一次 → 限时等 → 还不死就放弃，绝不再无限等。
            for _ in range(2):
                try:
                    p.kill()
                except Exception:
                    pass
                try:
                    p.communicate(timeout=2)
                    break
                except Exception:
                    continue
            else:
                self.last_stderr = "（超时后进程无法终止，已放弃等待）"
                return "", ms, "TLE"
            self.last_stderr = "（超时）"
            return "", ms, "TLE"
        self.last_stderr = "" if p.returncode == 0 else err.decode("utf-8", "replace")[:500]
        if p.returncode != 0:
            return out.decode("utf-8", "replace"), ms, "RE"
        return out.decode("utf-8", "replace"), ms, "OK"

    def compiler_desc(self):
        return self.cxx or "（未安装）"
