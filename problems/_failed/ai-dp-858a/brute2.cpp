#include <bits/stdc++.h>
using namespace std;

const int MAXN = 100005;
vector<int> adj[MAXN];
long long c[MAXN], station_cost[MAXN];
int n, d, w;

long long calc(int root) {
    vector<int> dist(n + 1, -1);
    queue<int> q;
    q.push(root);
    dist[root] = 0;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (int v : adj[u]) {
            if (dist[v] == -1) {
                dist[v] = dist[u] + 1;
                q.push(v);
            }
        }
    }
    long long penalty = 0;
    for (int i = 1; i <= n; ++i) {
        if (dist[i] > d) {
            penalty += c[i] * w;
        }
    }
    return station_cost[root] + penalty;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if (!(cin >> n >> d >> w)) return 0;
    for (int i = 1; i <= n; ++i) {
        cin >> c[i] >> station_cost[i];
    }
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    long long ans = -1;
    for (int i = 1; i <= n; ++i) {
        long long cur = calc(i);
        if (ans == -1 || cur < ans) {
            ans = cur;
        }
    }
    cout << ans << "\n";
    return 0;
}
