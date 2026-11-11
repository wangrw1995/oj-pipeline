#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B. 削山 —— 独立实现。

和 sol 换了个方向：区间枚举时按**右端点从右往左**扩展，同样 O(n^2)，
但和 sol 的"二分 + 单调栈"是两条完全不同的路。中等规模上对拍用。
"""
import sys


def solve(h, S):
    n = len(h)
    best = None
    for r in range(n):
        m = h[r]
        for l in range(r, -1, -1):
            if h[l] < m:
                m = h[l]
            L = r - l + 1
            need = -(-S // L)
            if need <= m and (best is None or need < best):
                best = need
                if best == 1:
                    return 1
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
