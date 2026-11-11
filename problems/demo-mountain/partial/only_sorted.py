#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只拿子任务 2（h_i 单调不降）：单调时最大矩形是 max_i b_i * (n-i)，O(n) 判定。"""
import sys


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
    if all(h[i] <= h[i + 1] for i in range(n - 1)):
        print(solve_sorted(h, S))
    else:
        print(-1)


if __name__ == "__main__":
    main()
