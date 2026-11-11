// A. 配对（pair）标准程序
// 排序后相邻两两配对，答案是 max(a[i+1] - a[i])（i 取偶数）。
#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    if (scanf("%d", &n) != 1) return 0;
    vector<long long> a(n);
    for (int i = 0; i < n; ++i) scanf("%lld", &a[i]);
    sort(a.begin(), a.end());
    long long ans = 0;
    for (int i = 0; i + 1 < n; i += 2) ans = max(ans, a[i + 1] - a[i]);
    printf("%lld\n", ans);
    return 0;
}
