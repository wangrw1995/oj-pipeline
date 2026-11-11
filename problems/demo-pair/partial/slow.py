#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""答案正确但复杂度退化：用选择排序代替排序。用来验证数据能卡掉 O(n^2)。"""
import sys


def main():
    d = sys.stdin.buffer.read().split()
    if not d:
        return
    n = int(d[0])
    a = [int(x) for x in d[1:1 + n]]
    for i in range(n):
        m = i
        for j in range(i + 1, n):
            if a[j] < a[m]:
                m = j
        a[i], a[m] = a[m], a[i]
    ans = 0
    for i in range(0, n - 1, 2):
        ans = max(ans, a[i + 1] - a[i])
    sys.stdout.write(str(ans) + "\n")


if __name__ == "__main__":
    main()
