#include <bits/stdc++.h>
using namespace std;
typedef long long ll;
const int MAXN = 1e5 + 5;
const ll INF = 1e18;

vector<pair<int, int>> adj[MAXN];
ll a[MAXN], sum_a[MAXN], f[MAXN];
ll total_sum;
int n, k;
multiset<ll, greater<ll>> st;
ll ans = INF;

ll get_gain() {
    ll res = 0;
    int cnt = 0;
    for (auto it = st.begin(); it != st.end() && cnt < k; ++it, ++cnt) {
        res += *it;
    }
    return res;
}

void dfs1(int u, int fa) {
    sum_a[u] = a[u];
    for (auto &e : adj[u]) {
        int v = e.first, w = e.second;
        if (v == fa) continue;
        dfs1(v, u);
        sum_a[u] += sum_a[v];
        f[1] += sum_a[v] * w;
        st.insert(1LL * w * sum_a[v]);
    }
}

void dfs2(int u, int fa) {
    ll gain = get_gain();
    ans = min(ans, f[u] - gain);
    for (auto &e : adj[u]) {
        int v = e.first, w = e.second;
        if (v == fa) continue;
        ll old_val = 1LL * w * sum_a[v];
        ll new_val = 1LL * w * (total_sum - sum_a[v]);
        st.erase(st.find(old_val));
        st.insert(new_val);
        f[v] = f[u] + 1LL * w * (total_sum - 2 * sum_a[v]);
        dfs2(v, u);
        st.erase(st.find(new_val));
        st.insert(old_val);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cin >> n >> k;
    for (int i = 0; i < n-1; ++i) {
        int u, v, w;
        cin >> u >> v >> w;
        adj[u].emplace_back(v, w);
        adj[v].emplace_back(u, w);
    }
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
        total_sum += a[i];
    }
    if (n == 1) {
        cout << 0 << endl;
        return 0;
    }
    dfs1(1, 0);
    dfs2(1, 0);
    cout << ans << endl;
    return 0;
}
