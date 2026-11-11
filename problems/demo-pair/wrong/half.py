#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""错解：把答案当成"最大能力差的一半"。必须被数据杀到 0 分。"""
import sys


def main():
    d = sys.stdin.buffer.read().split()
    if not d:
        return
    n = int(d[0])
    a = [int(x) for x in d[1:1 + n]]
    sys.stdout.write(str((max(a) - min(a)) // 2) + "\n")


if __name__ == "__main__":
    main()
