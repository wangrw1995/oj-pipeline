#include <iostream>
#include <vector>
#include <cstring>
#include <algorithm>
using namespace std;

typedef long long ll;
const ll INF = 1e18;
const int MAXN = 205;

vector<int> G[MAXN];
ll c[MAXN];
int n, K;
ll dp[MAXN][3]; // 0: u被自己覆盖 1: u被父亲覆盖 2: u被儿子覆盖
ll dp_root[MAXN];
ll up[MAXN];
ll best[MAXN];

void dfs1(int u, int fa) {
    dp[u][0] = c[u];
    dp[u][1] = 0;
    dp[u][2] = INF;
    for (int v : G[u]) {
        if (v == fa) continue;
        dfs1(v, u);
        dp[u][0] += min({dp[v][0], dp[v][1], dp[v][2]});
        dp[u][1] += min(dp[v][0], dp[v][2]);
        ll min_v = min(dp[v][0], dp[v][2]);
        best[v] = dp[v][0] - min_v;
    }
    // 计算dp[u][2]
    ll sum_min = 0;
    ll min_diff = INF;
    bool has_child = false;
    for (int v : G[u]) {
        if (v == fa) continue;
        has_child = true;
        ll min_v = min(dp[v][0], dp[v][2]);
        sum_min += min_v;
        min_diff = min(min_diff, dp[v][0] - min_v);
    }
    if (has_child) {
        dp[u][2] = sum_min + min_diff;
    }
}

ll dfs2(int u, int fa) {
    ll res = dp_root[u];
    for (int v : G[u]) {
        if (v == fa) continue;
        // 计算dp_root[v]
        ll old_u0 = dp[u][0];
        ll old_u1 = dp[u][1];
        ll old_u2 = dp[u][2];
        
        ll min_v012 = min({dp[v][0], dp[v][1], dp[v][2]});
        ll min_v02 = min(dp[v][0], dp[v][2]);
        
        dp[u][0] -= min_v012;
        dp[u][1] -= min_v02;
        
        // 重新计算dp[u][2]
        ll sum_min = 0;
        ll min_diff = INF;
        bool has_child = false;
        for (int w : G[u]) {
            if (w == fa || w == v) continue;
            has_child = true;
            ll min_w = min(dp[w][0], dp[w][2]);
            sum_min += min_w;
            min_diff = min(min_diff, dp[w][0] - min_w);
        }
        if (has_child) {
            dp[u][2] = sum_min + min_diff;
        } else {
            dp[u][2] = INF;
        }
        
        // 现在计算v的新dp
        ll old_v0 = dp[v][0];
        ll old_v1 = dp[v][1];
        ll old_v2 = dp[v][2];
        
        dp[v][0] += min({dp[u][0], dp[u][1], dp[u][2]});
        dp[v][1] += min(dp[u][0], dp[u][2]);
        
        sum_min = 0;
        min_diff = INF;
        has_child = false;
        for (int w : G[v]) {
            has_child = true;
            ll min_w = min(dp[w][0], dp[w][2]);
            sum_min += min_w;
            min_diff = min(min_diff, dp[w][0] - min_w);
        }
        if (has_child) {
            dp[v][2] = sum_min + min_diff;
        } else {
            dp[v][2] = INF;
        }
        
        dp_root[v] = (K - c[v]) + dp[v][0];
        res = min(res, dfs2(v, u));
        
        // 恢复
        dp[u][0] = old_u0;
        dp[u][1] = old_u1;
        dp[u][2] = old_u2;
        dp[v][0] = old_v0;
        dp[v][1] = old_v1;
        dp[v][2] = old_v2;
    }
    return res;
}

int main() {
    cin >> n >> K;
    for (int i = 1; i <= n; i++) {
        cin >> c[i];
    }
    for (int i = 0; i < n-1; i++) {
        int u, v;
        cin >> u >> v;
        G[u].push_back(v);
        G[v].push_back(u);
    }
    if (n == 1) {
        cout << min(K, (int)c[1]) << endl;
        return 0;
    }
    dfs1(1, -1);
    dp_root[1] = (K - c[1]) + dp[1][0];
    ll ans = dfs2(1, -1);
    cout << ans << endl;
    return 0;
}
