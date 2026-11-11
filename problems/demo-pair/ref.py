#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A. 配对 —— 独立实现。

和 sol 不同的思路：不直接套"相邻配对"的结论，而是**二分答案 + 可行性判定**。
判定用的是"排序后第一个未配对的元素必须和它后面最近的元素配"这一性质，
走的是二分而不是公式，能抓住 sol 在边界上的错误。
"""
import sys


def solve(a):
    a.sort()
    n = len(a)
    lo, hi = 0, a[-1] - a[0]
    while lo < hi:
        mid = (lo + hi) // 2
        ok = True
        for i in range(0, n, 2):
            if a[i + 1] - a[i] > mid:
                ok = False
                break
        if ok:
            hi = mid
        else:
            lo = mid + 1
    return lo


def main():
    d = sys.stdin.buffer.read().split()
    if not d:
        return
    n = int(d[0])
    a = [int(x) for x in d[1:1 + n]]
    sys.stdout.write(str(solve(a)) + "\n")


if __name__ == "__main__":
    main()
