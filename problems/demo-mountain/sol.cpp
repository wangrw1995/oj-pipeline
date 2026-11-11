// B. 削山（mountain）标准程序
// 二分 H，判定：把每个高度削到 min(h_i, H)，用单调栈求柱状图最大矩形，看是否 >= S。
#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

int n;
vector<ll> h;
ll S;

bool ok(ll H) {
    vector<ll> b(n);
    for (int i = 0; i < n; ++i) b[i] = (h[i] < H) ? h[i] : H;
    vector<int> st;
    st.reserve(n);
    for (int i = 0; i <= n; ++i) {
        ll cur = (i < n) ? b[i] : 0;
        while (!st.empty() && b[st.back()] > cur) {
            int j = st.back();
            st.pop_back();
            int left = st.empty() ? 0 : st.back() + 1;
            ll area = b[j] * (ll)(i - left);
            if (area >= S) return true;
        }
        if (i < n) st.push_back(i);
    }
    return false;
}

int main() {
    if (scanf("%d", &n) != 1) return 0;
    h.resize(n);
    for (int i = 0; i < n; ++i) scanf("%lld", &h[i]);
    if (scanf("%lld", &S) != 1) return 0;
    ll lo = 1, hi = *max_element(h.begin(), h.end());
    while (lo < hi) {
        ll mid = (lo + hi) / 2;
        if (ok(mid)) hi = mid;
        else lo = mid + 1;
    }
    printf("%lld\n", lo);
    return 0;
}
