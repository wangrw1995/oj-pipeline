#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

const int MAXN = 205;
vector<pair<int, int>> adj[MAXN];
long long a[MAXN], dp[MAXN], sum_a[MAXN], total_a;

void dfs1(int u, int fa) {
    sum_a[u] = a[u];
    dp[u] = 0;
    for (auto &edge : adj[u]) {
        int v = edge.first;
        int w = edge.second;
        if (v == fa) continue;
        dfs1(v, u);
        sum_a[u] += sum_a[v];
        dp[u] += dp[v] + sum_a[v] * w;
    }
}

void dfs2(int u, int fa) {
    for (auto &edge : adj[u]) {
        int v = edge.first;
        int w = edge.second;
        if (v == fa) continue;
        dp[v] = dp[u] - sum_a[v] * w + (total_a - sum_a[v]) * w;
        dfs2(v, u);
    }
}

int main() {
    int n;
    cin >> n;
    if (n == 1) {
        cout << 0 << endl;
        return 0;
    }
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
    }
    for (int i = 0; i < n-1; ++i) {
        int u, v, w;
        cin >> u >> v >> w;
        adj[u].emplace_back(v, w);
        adj[v].emplace_back(u, w);
    }
    dfs1(1, -1);
    total_a = sum_a[1];
    dfs2(1, -1);
    long long ans = 1e18;
    for (int i = 1; i <= n; ++i) {
        ans = min(ans, dp[i]);
    }
    cout << ans << endl;
    return 0;
}
