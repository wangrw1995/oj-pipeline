#include <bits/stdc++.h>
using namespace std;
typedef long long ll;
const int MAXN = 1e5 + 5;
vector<int> adj[MAXN];
ll a[MAXN], ans[MAXN];
int n, k;
bool vis[MAXN];
int sz[MAXN], maxp[MAXN], sum, root;

void get_root(int u, int fa) {
    sz[u] = 1; maxp[u] = 0;
    for (int v : adj[u]) {
        if (v == fa || vis[v]) continue;
        get_root(v, u);
        sz[u] += sz[v];
        maxp[u] = max(maxp[u], sz[v]);
    }
    maxp[u] = max(maxp[u], sum - sz[u]);
    if (maxp[u] < maxp[root]) root = u;
}

void get_dist(int u, int fa, int d, vector<pair<int, int>>& vec) {
    if (d > k) return;
    vec.emplace_back(d, u);
    for (int v : adj[u]) {
        if (v == fa || vis[v]) continue;
        get_dist(v, u, d + 1, vec);
    }
}

void calc(int u) {
    vector<pair<int, int>> total;
    total.emplace_back(0, u);
    vector<vector<pair<int, int>>> subs;
    for (int v : adj[u]) {
        if (vis[v]) continue;
        vector<pair<int, int>> sub;
        get_dist(v, u, 1, sub);
        subs.push_back(sub);
        for (auto& p : sub) total.push_back(p);
    }
    int maxd = 0;
    for (auto& p : total) maxd = max(maxd, p.first);
    int lim = min(maxd, k);
    vector<ll> cnt_total(lim + 2, 0);
    for (auto& p : total) {
        int d = p.first;
        if (d <= lim) cnt_total[d] += a[p.second];
    }
    vector<ll> sum_total(lim + 2, 0);
    sum_total[0] = cnt_total[0];
    for (int i = 1; i <= lim; i++) sum_total[i] = sum_total[i-1] + cnt_total[i];
    ans[u] += sum_total[min(k, lim)];
    for (auto& sub : subs) {
        int sub_maxd = 0;
        for (auto& p : sub) sub_maxd = max(sub_maxd, p.first);
        int sub_lim = min(sub_maxd, k);
        vector<ll> cnt_sub(sub_lim + 2, 0);
        for (auto& p : sub) {
            int d = p.first;
            if (d <= sub_lim) cnt_sub[d] += a[p.second];
        }
        vector<ll> sum_sub(sub_lim + 2, 0);
        for (int i = 1; i <= sub_lim; i++) sum_sub[i] = sum_sub[i-1] + cnt_sub[i];
        for (auto& p : sub) {
            int d = p.first, node = p.second;
            if (d > k) continue;
            int t = min(k - d, lim);
            if (t < 0) continue;
            ll add = sum_total[t];
            int st = min(t, sub_lim);
            add -= sum_sub[st];
            ans[node] += add;
        }
    }
}

void solve(int u) {
    vis[u] = true;
    calc(u);
    for (int v : adj[u]) {
        if (vis[v]) continue;
        sum = sz[v];
        root = 0;
        maxp[root] = 1e9;
        get_root(v, u);
        solve(root);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cin >> n >> k;
    ll total_sum = 0;
    for (int i = 1; i <= n; i++) {
        cin >> a[i];
        total_sum += a[i];
    }
    if (k >= n - 1) {
        cout << total_sum << '\n';
        return 0;
    }
    for (int i = 0; i < n - 1; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    sum = n;
    root = 0;
    maxp[root] = 1e9;
    get_root(1, 0);
    solve(root);
    ll max_ans = 0;
    for (int i = 1; i <= n; i++) {
        max_ans = max(max_ans, ans[i]);
    }
    cout << max_ans << '\n';
    return 0;
}
