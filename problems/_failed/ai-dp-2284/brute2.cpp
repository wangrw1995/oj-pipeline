#include <bits/stdc++.h>
using namespace std;

int n, m;
int c[25], v[25];
vector<int> adj[25];
int parent_node[25];
bool visited[25];

void dfs(int u, int p) {
    parent_node[u] = p;
    visited[u] = true;
    for (int to : adj[u]) {
        if (!visited[to]) {
            dfs(to, u);
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n >> m)) return 0;

    for (int i = 1; i <= n; ++i) {
        cin >> c[i] >> v[i];
    }

    for (int i = 0; i < n - 1; ++i) {
        int u, w;
        cin >> u >> w;
        adj[u].push_back(w);
        adj[w].push_back(u);
    }

    memset(visited, 0, sizeof(visited));
    dfs(1, 0);

    int ans = 0;
    int total_masks = 1 << n;

    for (int mask = 1; mask < total_masks; ++mask) {
        // 根节点必须被选中
        if (!((mask >> 0) & 1)) continue;

        int cur_cost = 0;
        int cur_val = 0;
        bool valid = true;

        for (int i = 1; i <= n; ++i) {
            if ((mask >> (i - 1)) & 1) {
                cur_cost += c[i];
                cur_val += v[i];
                if (cur_cost > m) {
                    valid = false;
                    break;
                }
                // 依赖检查：非根节点被选，则其父节点必须被选
                if (i != 1 && !((mask >> (parent_node[i] - 1)) & 1)) {
                    valid = false;
                    break;
                }
            }
        }

        if (valid && cur_cost <= m) {
            ans = max(ans, cur_val);
        }
    }

    cout << ans << "\n";
    return 0;
}
