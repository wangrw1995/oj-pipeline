#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拿子任务 1 + 2：小数据枚举，已升序的直接相邻，其余放弃。"""
import sys


def brute(a):
    n = len(a)

    def rec(used, i, cur):
        while i < n and used[i]:
            i += 1
        if i == n:
            return cur
        used[i] = True
        best = None
        for j in range(i + 1, n):
            if used[j]:
                continue
            used[j] = True
            v = rec(used, i, max(cur, abs(a[i] - a[j])))
            used[j] = False
            if best is None or v < best:
                best = v
        used[i] = False
        return best

    return rec([False] * n, 0, 0)


def main():
    d = sys.stdin.buffer.read().split()
    if not d:
        return
    n = int(d[0])
    a = [int(x) for x in d[1:1 + n]]
    if n <= 10:
        print(brute(a))
        return
    if all(a[i] <= a[i + 1] for i in range(n - 1)):
        ans = 0
        for i in range(0, n - 1, 2):
            ans = max(ans, a[i + 1] - a[i])
        print(ans)
        return
    print(-1)


if __name__ == "__main__":
    main()
