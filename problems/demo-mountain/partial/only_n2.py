#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只拿子任务 1（n <= 2000）：O(n^2) 枚举区间。更大的规模直接放弃。"""
import sys


def solve(h, S):
    n = len(h)
    best = None
    for l in range(n):
        m = h[l]
        for r in range(l, n):
            if h[r] < m:
                m = h[r]
            L = r - l + 1
            need = (S + L - 1) // L
            if need <= m and (best is None or need < best):
                best = need
    return best if best is not None else -1


def main():
    d = sys.stdin.buffer.read().split()
    if not d:
        return
    n = int(d[0])
    h = list(map(int, d[1:1 + n]))
    S = int(d[n + 1])
    print(solve(h, S) if n <= 2000 else -1)


if __name__ == "__main__":
    main()
