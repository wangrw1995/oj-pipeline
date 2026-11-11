#include <iostream>
#include <vector>
#include <queue>
#include <climits>

using namespace std;

int countSetBits(int n) {
    int c = 0;
    while (n > 0) {
        n &= (n - 1);
        c++;
    }
    return c;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, k;
    if (!(cin >> n >> k)) return 0;

    struct Edge { int u, v, w; };
    vector<Edge> edges;
    vector<vector<pair<int, int>>> adj(n + 1);

    for (int i = 0; i < n - 1; ++i) {
        int u, v, w;
        cin >> u >> v >> w;
        edges.push_back({u, v, w});
        adj[u].push_back({v, (int)edges.size() - 1});
        adj[v].push_back({u, (int)edges.size() - 1});
    }

    vector<int> a(n + 1);
    for (int i = 1; i <= n; ++i) cin >> a[i];

    long long ans = LLONG_MAX;
    int m = n - 1;
    int limit = (m == 0) ? 1 : (1 << m);

    for (int root = 1; root <= n; ++root) {
        for (int mask = 0; mask < limit; ++mask) {
            if (countSetBits(mask) > k) continue;

            vector<long long> dist(n + 1, -1);
            queue<int> q;
            dist[root] = 0;
            q.push(root);

            while (!q.empty()) {
                int u = q.front(); q.pop();
                for (auto& p : adj[u]) {
                    int v = p.first;
                    int idx = p.second;
                    if (dist[v] != -1) continue;
                    long long w = edges[idx].w;
                    if ((mask >> idx) & 1) w = 0;
                    dist[v] = dist[u] + w;
                    q.push(v);
                }
            }

            long long cur_cost = 0;
            bool ok = true;
            for (int i = 1; i <= n; ++i) {
                if (dist[i] == -1) { ok = false; break; }
                cur_cost += (long long)a[i] * dist[i];
            }

            if (ok && cur_cost < ans) ans = cur_cost;
        }
    }

    cout << ans << "\n";
    return 0;
}
