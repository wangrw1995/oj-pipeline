# -*- coding: utf-8 -*-
"""题面渲染：把 spec 里的子任务/测试点/分值渲染成 markdown 表格。

题面里凡是能由 spec 推导的内容，一律不许手写——这是"题面永不漂移"的唯一实现方式。
"""
import os

from .utils import read_text


def _range_text(indices):
    """[1,2] -> '1~2'，[7] -> '7'，[1,2,3,5,6] -> '1~3, 5~6'"""
    if not indices:
        return "—"
    parts = []
    start = prev = indices[0]
    for x in indices[1:]:
        if x == prev + 1:
            prev = x
            continue
        parts.append(f"{start}~{prev}" if prev > start else f"{start}")
        start = prev = x
    parts.append(f"{start}~{prev}" if prev > start else f"{start}")
    return "、".join(parts)


def subtask_table(prob):
    subs = prob.subtasks
    tests = prob.tests
    lines = ["| 测试点 | 特殊限制 | 分值 |", "| :---: | :--- | :---: |"]
    for sid in sorted(subs):
        idxs = [i + 1 for i, (s, _) in enumerate(tests) if s == sid]
        desc = subs[sid]["desc"].replace("|", "\\|")
        cnt = len(idxs)
        score = subs[sid]["score"]
        per = score // cnt if cnt else 0
        extra = f"（每点 {per} 分）" if cnt > 1 else ""
        lines.append(f"| {_range_text(idxs)} | {desc}{extra} | {score} |")
    lines.append(f"| **合计** |  | **{prob.total_points()}** |")
    return "\n".join(lines)


def samples_block(prob):
    d = prob.sample_dir()
    if not d:
        return "（无样例文件）"
    names = sorted(n[:-3] for n in os.listdir(d) if n.endswith(".in"))
    if not names:
        return "（无样例文件）"
    out = []
    for n in names:
        in_path = os.path.join(d, n + ".in")
        ans_path = os.path.join(d, n + ".ans")
        if not os.path.exists(ans_path):
            continue
        out.append(f"### 样例 `{n}`\n")
        out.append("输入：\n\n```\n" + read_text(in_path).rstrip("\n") + "\n```\n")
        out.append("输出：\n\n```\n" + read_text(ans_path).rstrip("\n") + "\n```")
    return "\n\n".join(out) if out else "（无样例文件）"


def render(prob, extra=None):
    path = prob.statement_path()
    if path is None:
        raise FileNotFoundError(f"{prob.id}: 缺少 statement.md")
    text = read_text(path)
    mapping = {
        "ID": prob.id,
        "CODE": prob.code,
        "TITLE": prob.title,
        "LIMIT": f"{prob.limit:g}",
        "MEM": str(prob.mem),
        "TAGS": "、".join(prob.tags) if prob.tags else "—",
        "GLOBAL": getattr(prob.spec, "GLOBAL", ""),
        "SUBTASK_TABLE": subtask_table(prob),
        "SAMPLES": samples_block(prob),
    }
    if extra:
        mapping.update(extra)
    for k, v in mapping.items():
        text = text.replace("{{" + k + "}}", str(v))
    left = _find_placeholders(text)
    if left:
        raise ValueError(f"{prob.id}: 题面里有未替换的占位符 {sorted(set(left))}")
    return text


def _find_placeholders(text):
    out = []
    i = 0
    while True:
        i = text.find("{{", i)
        if i < 0:
            return out
        j = text.find("}}", i)
        if j < 0:
            return out
        out.append(text[i + 2:j])
        i = j + 2
