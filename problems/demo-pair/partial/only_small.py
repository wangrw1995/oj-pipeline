#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只拿子任务 1（n <= 10）：枚举所有配对。其余规模输出 -1。"""
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
    print(brute(a) if n <= 10 else -1)


if __name__ == "__main__":
    main()
