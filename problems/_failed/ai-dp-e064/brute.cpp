#include <iostream>
#include <vector>
#include <climits>
#include <algorithm>
using namespace std;

typedef long long ll;
const ll INF = 1e18;

int main()
{
    int n; ll K;
    cin >> n >> K;
    vector<ll> c(n);
    for (int i = 0; i < n; i++) cin >> c[i];
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < n - 1; i++)
    {
        int u, v; cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    ll ans = INF;
    for (int u = 1; u <= n; u++)
    {
        vector<bool> cov(n + 1, false);
        cov[u] = true;
        for (int v : adj[u]) cov[v] = true;
        for (int mask = 0; mask < (1 << n); mask++)
        {
            ll cost = K;
            for (int i = 0; i < n; i++) if (mask >> i & 1) cost += c[i];
            bool ok = true;
            for (int i = 1; i <= n; i++)
            {
                if (cov[i]) continue;
                bool covered = false;
                if (mask >> (i - 1) & 1) covered = true;
                else for (int v : adj[i]) if (mask >> (v - 1) & 1) { covered = true; break; }
                if (!covered) { ok = false; break; }
            }
            if (ok) ans = min(ans, cost);
        }
    }
    cout << ans << endl;
    return 0;
}
