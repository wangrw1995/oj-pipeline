#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    vector<int> c(n + 1), v(n + 1);
    for (int i = 1; i <= n; ++i) {
        cin >> c[i] >> v[i];
    }
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < n - 1; ++i) {
        int u, w;
        cin >> u >> w;
        adj[u].push_back(w);
        adj[w].push_back(u);
    }
    vector<int> fa(n + 1, 0);
    queue<int> q;
    q.push(1);
    fa[1] = 0;
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        for (int w : adj[u]) {
            if (w != fa[u]) {
                fa[w] = u;
                q.push(w);
            }
        }
    }
    int ans = 0;
    for (int mask = 0; mask < (1 << n); ++mask) {
        bool valid = true;
        int sumc = 0, sumv = 0;
        for (int i = 1; i <= n; ++i) {
            if (mask & (1 << (i - 1))) {
                sumc += c[i];
                sumv += v[i];
                if (i != 1 && !(mask & (1 << (fa[i] - 1)))) {
                    valid = false;
                    break;
                }
            }
        }
        if (valid && sumc <= m) {
            ans = max(ans, sumv);
        }
    }
    cout << ans << endl;
    return 0;
}
