#pragma comment(linker, "/STACK:1024000000,1024000000")
#include <bits/stdc++.h>
using namespace std;
typedef long long ll;
const int MAXN = 1e5 + 10;

vector<pair<int, int>> adj[MAXN];
ll a[MAXN], dp[MAXN], sum_a[MAXN], ans[MAXN], total_a;
int n;

void dfs1(int u, int fa) {
    sum_a[u] = a[u];
    dp[u] = 0;
    for (auto &e : adj[u]) {
        int v = e.first, w = e.second;
        if (v == fa) continue;
        dfs1(v, u);
        sum_a[u] += sum_a[v];
        dp[u] += dp[v] + sum_a[v] * w;
    }
}

void dfs2(int u, int fa) {
    for (auto &e : adj[u]) {
        int v = e.first, w = e.second;
        if (v == fa) continue;
        ans[v] = ans[u] + w * (total_a - 2 * sum_a[v]);
        dfs2(v, u);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cin >> n;
    for (int i = 1; i <= n; i++) {
        cin >> a[i];
    }
    for (int i = 0; i < n-1; i++) {
        int u, v, w;
        cin >> u >> v >> w;
        adj[u].emplace_back(v, w);
        adj[v].emplace_back(u, w);
    }
    dfs1(1, 0);
    total_a = sum_a[1];
    ans[1] = dp[1];
    dfs2(1, 0);
    ll min_ans = LLONG_MAX;
    for (int i = 1; i <= n; i++) {
        min_ans = min(min_ans, ans[i]);
    }
    cout << min_ans << '\n';
    return 0;
}
