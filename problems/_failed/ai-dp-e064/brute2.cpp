#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

int n;
ll K;
ll c[25];
vector<int> adj[25];
int cnt[25];
ll ans = LLONG_MAX;

void dfs(int idx, ll cur_cost) {
    if (idx > n) {
        bool ok = true;
        for (int i = 1; i <= n; ++i) {
            if (cnt[i] == 0) {
                ok = false;
                break;
            }
        }
        if (ok) {
            ans = min(ans, cur_cost);
        }
        return;
    }
    // 分支1：不在当前节点建辅助蓄水池
    dfs(idx + 1, cur_cost);
    
    // 分支2：在当前节点建辅助蓄水池
    cnt[idx]++;
    for (int v : adj[idx]) cnt[v]++;
    dfs(idx + 1, cur_cost + c[idx]);
    
    // 回溯恢复状态
    cnt[idx]--;
    for (int v : adj[idx]) cnt[v]--;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    cin >> n >> K;
    for (int i = 1; i <= n; ++i) cin >> c[i];
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    // 暴力枚举每一个可能的核心供水站位置
    for (int root = 1; root <= n; ++root) {
        memset(cnt, 0, sizeof(cnt));
        // 核心站覆盖自身及邻居
        cnt[root]++;
        for (int v : adj[root]) cnt[v]++;
        
        // 暴力枚举所有辅助蓄水池的放置方案（全排列/子集枚举）
        dfs(1, K);
    }
    
    cout << ans << "\n";
    return 0;
}
