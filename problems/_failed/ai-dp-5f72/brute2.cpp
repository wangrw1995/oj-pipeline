#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>

using namespace std;

const int MAXN = 1005;
int n, k;
int a[MAXN];
vector<int> adj[MAXN];
bool vis[MAXN];

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n >> k)) return 0;
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
    }
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    long long max_served = 0;

    for (int root = 1; root <= n; ++root) {
        fill(vis, vis + n + 1, false);
        queue<pair<int, int>> q;
        q.push({root, 0});
        vis[root] = true;
        
        long long current_sum = 0;
        
        while (!q.empty()) {
            pair<int, int> cur = q.front();
            q.pop();
            int u = cur.first;
            int d = cur.second;
            
            if (d > k) continue;
            
            current_sum += a[u];
            
            if (d < k) {
                for (int v : adj[u]) {
                    if (!vis[v]) {
                        vis[v] = true;
                        q.push({v, d + 1});
                    }
                }
            }
        }
        
        if (current_sum > max_served) {
            max_served = current_sum;
        }
    }

    cout << max_served << "\n";
    return 0;
}
