#include <iostream>
#include <vector>
#include <queue>
using namespace std;
typedef long long ll;
const ll INF = 1e18;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int n, d, w;
    cin >> n >> d >> w;
    vector<int> c(n + 1), cost(n + 1);
    for (int i = 1; i <= n; ++i) {
        cin >> c[i] >> cost[i];
    }
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    ll min_total = INF;
    for (int u = 1; u <= n; ++u) {
        vector<int> dist(n + 1, -1);
        queue<int> q;
        q.push(u);
        dist[u] = 0;
        while (!q.empty()) {
            int cur = q.front();
            q.pop();
            for (int v : adj[cur]) {
                if (dist[v] == -1) {
                    dist[v] = dist[cur] + 1;
                    q.push(v);
                }
            }
        }
        ll total = cost[u];
        for (int v = 1; v <= n; ++v) {
            if (dist[v] > d) {
                total += 1LL * c[v] * w;
            }
        }
        if (total < min_total) {
            min_total = total;
        }
    }
    cout << min_total << endl;
    return 0;
}
