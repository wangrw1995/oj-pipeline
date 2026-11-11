// mock 用的暴力：枚举所有配对方案
#include <bits/stdc++.h>
using namespace std;
int n;
vector<long long> a;
long long best = LLONG_MAX;

void rec(int used, long long cur, int cnt) {
    if (cnt == n / 2) { best = min(best, cur); return; }
    int i = 0;
    while (used >> i & 1) ++i;
    for (int j = i + 1; j < n; ++j) {
        if (used >> j & 1) continue;
        rec(used | (1 << i) | (1 << j), max(cur, llabs(a[i] - a[j])), cnt + 1);
    }
}

int main() {
    if (scanf("%d", &n) != 1) return 0;
    a.resize(n);
    for (int i = 0; i < n; ++i) scanf("%lld", &a[i]);
    rec(0, 0, 0);
    printf("%lld\n", best);
    return 0;
}
