#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""错解：以为平台总能铺满整个宽度，直接答 ceil(S/n)。"""
import sys


def main():
    d = sys.stdin.buffer.read().split()
    if not d:
        return
    n = int(d[0])
    h = list(map(int, d[1:1 + n]))
    S = int(d[n + 1])
    print((S + n - 1) // n)


if __name__ == "__main__":
    main()
