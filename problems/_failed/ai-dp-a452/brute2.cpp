#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>

using namespace std;

struct Edge {
    int to;
    int w;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<long long> a(n + 1);
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
    }

    vector<vector<Edge>> adj(n + 1);
    for (int i = 0; i < n - 1; ++i) {
        int u, v, w;
        cin >> u >> v >> w;
        adj[u].push_back({v, w});
        adj[v].push_back({u, w});
    }

    long long min_total_cost = -1;

    for (int station = 1; station <= n; ++station) {
        vector<int> dist(n + 1, -1);
        queue<int> q;

        dist[station] = 0;
        q.push(station);

        while (!q.empty()) {
            int u = q.front();
            q.pop();
            for (const auto& e : adj[u]) {
                if (dist[e.to] == -1) {
                    dist[e.to] = dist[u] + e.w;
                    q.push(e.to);
                }
            }
        }

        long long current_cost = 0;
        for (int i = 1; i <= n; ++i) {
            current_cost += a[i] * dist[i];
        }

        if (min_total_cost == -1 || current_cost < min_total_cost) {
            min_total_cost = current_cost;
        }
    }

    cout << min_total_cost << "\n";
    return 0;
}
