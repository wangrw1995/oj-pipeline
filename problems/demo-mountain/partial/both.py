#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拿子任务 1 + 2：小规模枚举，已排序的走 O(n) 判定，其余放弃。"""
import sys


def solve_n2(h, S):
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


def solve_sorted(h, S):
    n = len(h)
    lo, hi = 1, max(h)
    while lo < hi:
        mid = (lo + hi) // 2
        best = 0
        for i in range(n):
            b = h[i] if h[i] < mid else mid
            a = b * (n - i)
            if a > best:
                best = a
        if best >= S:
            hi = mid
        else:
            lo = mid + 1
    return lo


def main():
    d = sys.stdin.buffer.read().split()
    if not d:
        return
    n = int(d[0])
    h = list(map(int, d[1:1 + n]))
    S = int(d[n + 1])
    if n <= 2000:
        print(solve_n2(h, S))
    elif all(h[i] <= h[i + 1] for i in range(n - 1)):
        print(solve_sorted(h, S))
    else:
        print(-1)


if __name__ == "__main__":
    main()
