#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""错解：把"最大磨合难度"错当成"磨合难度之和"。必须被数据杀到 0 分。"""
import sys


def main():
    d = sys.stdin.buffer.read().split()
    if not d:
        return
    n = int(d[0])
    a = sorted(int(x) for x in d[1:1 + n])
    s = 0
    for i in range(0, n - 1, 2):
        s += a[i + 1] - a[i]
    sys.stdout.write(str(s) + "\n")


if __name__ == "__main__":
    main()
