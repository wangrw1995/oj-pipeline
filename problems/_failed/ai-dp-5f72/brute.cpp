#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int n, k;
    cin >> n >> k;
    vector<long long> a(n + 1);
    for (int i = 1; i <= n; i++) {
        cin >> a[i];
    }
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < n - 1; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    long long max_ans = 0;
    for (int u = 1; u <= n; u++) {
        vector<int> dist(n + 1, -1);
        queue<int> q;
        dist[u] = 0;
        q.push(u);
        long long sum = 0;
        while (!q.empty()) {
            int v = q.front();
            q.pop();
            if (dist[v] > k) continue;
            sum += a[v];
            for (int w : adj[v]) {
                if (dist[w] == -1) {
                    dist[w] = dist[v] + 1;
                    q.push(w);
                }
            }
        }
        max_ans = max(max_ans, sum);
    }
    cout << max_ans << endl;
    return 0;
}
