#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""错解：首尾配对（sort 后 a[i] 和 a[n-1-i] 配）。必须被数据杀到 0 分。"""
import sys


def main():
    d = sys.stdin.buffer.read().split()
    if not d:
        return
    n = int(d[0])
    a = sorted(int(x) for x in d[1:1 + n])
    ans = 0
    for i in range(n // 2):
        ans = max(ans, a[n - 1 - i] - a[i])
    sys.stdout.write(str(ans) + "\n")


if __name__ == "__main__":
    main()
