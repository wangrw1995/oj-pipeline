#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""__ID__ 的独立实现。

这份文件存在的唯一目的，是在**中等规模**上和 sol 对拍，把"标程错了"挡在数据之前。
所以必须换算法、换语言、换思路写——把 sol 翻译一遍没有任何价值。
"""
import sys


def main():
    data = sys.stdin.buffer.read().split()
    if not data:
        return
    n = int(data[0])
    # TODO：用和 sol 不同的算法
    print(0)


if __name__ == "__main__":
    main()
