# -*- coding: utf-8 -*-
"""通用工具：文本归一化、令牌比较、文件哈希、时间戳。"""
import hashlib
import os
import sys
from datetime import datetime


def setup_stdio():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            try:
                s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def now():
    return datetime.now().isoformat(timespec="seconds")


def normalize(text: str) -> str:
    """CRLF/CR -> LF；删行末空格；去掉文件末尾多余空行；保证恰好一个结尾换行。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip(" \t") for ln in text.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def tokens(text: str):
    return text.split()


def same_answer(got: str, expected: str) -> bool:
    return tokens(got) == tokens(expected)


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def write_text(path, text):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def write_bytes(path, data: bytes):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def read_json(path, default=None):
    import json
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json(path, obj):
    import json
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=False)
        f.write("\n")


IGNORE_DIRS = {"build", "__pycache__", ".git", "midfail"}


def dir_hash(paths):
    """对一个题目目录里除 build/ 外的所有文件求哈希，用于判断是否需要重跑。"""
    h = hashlib.sha256()
    files = []
    for base, dirs, names in os.walk(paths):
        dirs[:] = sorted(d for d in dirs if d not in IGNORE_DIRS)
        for n in sorted(names):
            if n.endswith((".pyc", ".o", ".exe")):
                continue
            files.append(os.path.join(base, n))
    for p in files:
        rel = os.path.relpath(p, paths).replace("\\", "/")
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        with open(p, "rb") as f:
            h.update(f.read())
        h.update(b"\0")
    return h.hexdigest()[:16]


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f}{unit}" if unit != "B" else f"{n}B"
        n /= 1024.0


def fmt_ms(ms):
    return f"{ms:.0f}ms" if ms < 1000 else f"{ms / 1000:.2f}s"
