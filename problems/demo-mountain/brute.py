#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B. 削山 —— 暴力：枚举所有区间，直接算出每个区间需要的 H。O(n^2)。

原理：对区间 [l,r]，长度 L、最小值 m。要建成面积 >= S 的平台，
需要 ceil(S/L) 的高度；只要 ceil(S/L) <= m 这个区间就是可行的，
它要求的 H 就是 ceil(S/L)。答案 = 所有可行区间里的最小值。
"""
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
    sys.stdout.write(str(solve(h, S)) + "\n")


if __name__ == "__main__":
    main()
