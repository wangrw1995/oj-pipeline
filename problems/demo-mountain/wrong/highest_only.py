#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""错解：认为"必须削到最高峰"才能拿到最大面积，直接输出 max(h)。"""
import sys


def main():
    d = sys.stdin.buffer.read().split()
    if not d:
        return
    n = int(d[0])
    h = list(map(int, d[1:1 + n]))
    print(max(h))


if __name__ == "__main__":
    main()
