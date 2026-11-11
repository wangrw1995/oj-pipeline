#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只拿子任务 2（a_i 已升序）：不排序，直接相邻配对。"""
import sys


def main():
    d = sys.stdin.buffer.read().split()
    if not d:
        return
    n = int(d[0])
    a = [int(x) for x in d[1:1 + n]]
    ans = 0
    for i in range(0, n - 1, 2):
        ans = max(ans, a[i + 1] - a[i])
    sys.stdout.write(str(ans) + "\n")


if __name__ == "__main__":
    main()
