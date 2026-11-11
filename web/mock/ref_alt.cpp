// mock 用的"第三方实现"：从后往前扫一遍，和标程的迭代方向相反
#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    if (scanf("%d", &n) != 1) return 0;
    vector<long long> a(n);
    for (int i = 0; i < n; ++i) scanf("%lld", &a[i]);
    sort(a.begin(), a.end());
    long long r = 0;
    for (int i = n / 2 - 1; i >= 0; --i)
        r = max(r, a[2 * i + 1] - a[2 * i]);
    printf("%lld\n", r);
    return 0;
}
