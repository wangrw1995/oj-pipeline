#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""错解：把"最大矩形面积"错算成"可用格子总数"（所有高度之和）。"""
import sys


def main():
    d = sys.stdin.buffer.read().split()
    if not d:
        return
    n = int(d[0])
    h = list(map(int, d[1:1 + n]))
    S = int(d[n + 1])
    lo, hi = 1, max(h)
    while lo < hi:
        mid = (lo + hi) // 2
        if sum(x if x < mid else mid for x in h) >= S:
            hi = mid
        else:
            lo = mid + 1
    print(lo)


if __name__ == "__main__":
    main()
