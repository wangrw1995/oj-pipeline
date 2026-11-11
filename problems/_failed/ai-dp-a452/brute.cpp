#include <bits/stdc++.h>
using namespace std;
typedef long long ll;
const int MAXN = 2005;
vector<pair<int, int>> adj[MAXN];
int a[MAXN];

ll dfs(int u, int fa, ll dist) {
    ll res = 1LL * a[u] * dist;
    for (auto &e : adj[u]) {
        int v = e.first, w = e.second;
        if (v != fa) {
            res += dfs(v, u, dist + w);
        }
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int n;
    cin >> n;
    for (int i = 1; i <= n; i++) {
        cin >> a[i];
    }
    for (int i = 0; i < n - 1; i++) {
        int u, v, w;
        cin >> u >> v >> w;
        adj[u].emplace_back(v, w);
        adj[v].emplace_back(u, w);
    }
    ll ans = LLONG_MAX;
    for (int i = 1; i <= n; i++) {
        ans = min(ans, dfs(i, 0, 0));
    }
    cout << ans << '\n';
    return 0;
}
