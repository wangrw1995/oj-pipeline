#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A. 配对 —— 暴力：枚举所有两两配对方案，取最小总难度。只用于 n <= 10。"""
import sys

BEST = [None]


def rec(a, used, cur_max, best):
    n = len(a)
    i = 0
    while i < n and used[i]:
        i += 1
    if i == n:
        if best[0] is None or cur_max < best[0]:
            best[0] = cur_max
        return
    used[i] = True
    for j in range(i + 1, n):
        if used[j]:
            continue
        used[j] = True
        rec(a, used, max(cur_max, abs(a[i] - a[j])), best)
        used[j] = False
    used[i] = False


def main():
    d = sys.stdin.buffer.read().split()
    if not d:
        return
    n = int(d[0])
    a = [int(x) for x in d[1:1 + n]]
    best = [None]
    rec(a, [False] * n, 0, best)
    sys.stdout.write(str(best[0]) + "\n")


if __name__ == "__main__":
    main()
