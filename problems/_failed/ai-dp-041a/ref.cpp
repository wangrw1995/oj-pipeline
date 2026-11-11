#include <iostream>
#include <vector>
#include <algorithm>
#include <cstring>
using namespace std;

typedef long long ll;
const ll INF = 1e18;
const int MAXN = 205;
const int MAXK = 25;

vector<pair<int, int>> adj[MAXN];
ll a[MAXN];
ll dp1[MAXN][MAXK]; // 子树u内选t条边的最小代价
ll dp2[MAXN][MAXK]; // 换根用，父亲方向的贡献
ll tmp[MAXK];
ll total_a;
ll size_a[MAXN];
int n, k;

void dfs1(int u, int fa) {
    size_a[u] = a[u];
    for (int t = 0; t <= k; ++t) dp1[u][t] = 0;
    for (auto &e : adj[u]) {
        int v = e.first, w = e.second;
        if (v == fa) continue;
        dfs1(v, u);
        size_a[u] += size_a[v];
        memset(tmp, 0x3f, sizeof(tmp));
        for (int t1 = 0; t1 <= k; ++t1) {
            if (dp1[u][t1] >= INF) continue;
            for (int t2 = 0; t2 <= k - t1; ++t2) {
                if (dp1[v][t2] >= INF) continue;
                // 不升级u-v边
                tmp[t1 + t2] = min(tmp[t1 + t2], dp1[u][t1] + dp1[v][t2] + size_a[v] * w);
                // 升级u-v边
                if (t1 + t2 + 1 <= k) {
                    tmp[t1 + t2 + 1] = min(tmp[t1 + t2 + 1], dp1[u][t1] + dp1[v][t2]);
                }
            }
        }
        memcpy(dp1[u], tmp, sizeof(tmp));
    }
}

void dfs2(int u, int fa) {
    for (auto &e : adj[u]) {
        int v = e.first, w = e.second;
        if (v == fa) continue;
        memset(tmp, 0x3f, sizeof(tmp));
        // 把u的dp1（除了v的子树）和dp2合并，得到上半部分的贡献
        // 先初始化tmp为dp2[u]的状态
        for (int t = 0; t <= k; ++t) tmp[t] = dp2[u][t];
        // 现在需要把dp1[u]中减去v的贡献加回来？不，我们重新计算u的"其他部分"
        // 由于n小，我们可以用另一种方式：对于换根后的v来说，父亲部分的size是total_a - size_a[v]
        // 我们重新计算tmp，表示把u作为v的儿子时，处理u的情况
        memset(tmp, 0x3f, sizeof(tmp));
        // 初始状态：空
        tmp[0] = 0;
        // 先加入父亲方向的dp2
        for (int t1 = k; t1 >= 0; --t1) {
            if (tmp[t1] >= INF) continue;
            for (int t2 = 1; t2 <= k - t1; ++t2) {
                if (dp2[u][t2] >= INF) continue;
                tmp[t1 + t2] = min(tmp[t1 + t2], tmp[t1] + dp2[u][t2]);
            }
        }
        // 再加入其他子树（除了v）的dp1
        for (auto &e2 : adj[u]) {
            int v2 = e2.first, w2 = e2.second;
            if (v2 == fa || v2 == v) continue;
            memset(tmp, 0x3f, sizeof(tmp));
            // 哦，不对，应该用类似背包的方式合并
            // 重新来，用一个cur数组
            static ll cur[MAXK];
            memcpy(cur, tmp, sizeof(tmp));
            memset(tmp, 0x3f, sizeof(tmp));
            for (int t1 = 0; t1 <= k; ++t1) {
                if (cur[t1] >= INF) continue;
                for (int t2 = 0; t2 <= k - t1; ++t2) {
                    if (dp1[v2][t2] >= INF) continue;
                    // 不升级u-v2边
                    tmp[t1 + t2] = min(tmp[t1 + t2], cur[t1] + dp1[v2][t2] + size_a[v2] * w2);
                    // 升级u-v2边
                    if (t1 + t2 + 1 <= k) {
                        tmp[t1 + t2 + 1] = min(tmp[t1 + t2 + 1], cur[t1] + dp1[v2][t2]);
                    }
                }
            }
        }
        // 现在tmp是u除了v之外的部分的最优值，接下来要处理u-v边，作为v的父亲边
        memset(dp2[v], 0x3f, sizeof(dp2[v]));
        ll father_size = total_a - size_a[v];
        for (int t = 0; t <= k; ++t) {
            if (tmp[t] >= INF) continue;
            // 不升级u-v边
            dp2[v][t] = min(dp2[v][t], tmp[t] + father_size * w);
            // 升级u-v边
            if (t + 1 <= k) {
                dp2[v][t + 1] = min(dp2[v][t + 1], tmp[t]);
            }
        }
        dfs2(v, u);
    }
}

int main() {
    cin >> n >> k;
    for (int i = 0; i < n-1; ++i) {
        int u, v, w;
        cin >> u >> v >> w;
        adj[u].emplace_back(v, w);
        adj[v].emplace_back(u, w);
    }
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
        total_a += a[i];
    }
    ll ans = INF;
    // 枚举每个根
    for (int root = 1; root <= n; ++root) {
        for (int i = 1; i <= n; ++i) {
            for (int t = 0; t <= k; ++t) {
                dp1[i][t] = INF;
                dp2[i][t] = INF;
            }
        }
        dfs1(root, -1);
        // 对于root来说，dp2都是0，因为没有父亲
        for (int t = 0; t <= k; ++t) {
            ans = min(ans, dp1[root][t]);
        }
    }
    cout << ans << endl;
    return 0;
}
