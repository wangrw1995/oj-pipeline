#pragma comment(linker, "/STACK:1024000000,1024000000")
#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;
typedef long long ll;
const ll INF = 1000000000000000000LL;
const int MAXN = 1e5 + 5;
vector<int> adj[MAXN];
ll c[MAXN];
ll down[MAXN][3];
ll up[MAXN][3];
int parent[MAXN];
ll sum_min3_child[MAXN];
ll sum_min_child[MAXN];
ll sum_dp1_child[MAXN];
int count_inf_min3_child[MAXN];
int count_inf_min_child[MAXN];
int count_inf_dp1_child[MAXN];
ll min1_delta[MAXN];
ll min2_delta[MAXN];
int cnt1[MAXN];
void dfs_post(int u, int p) {
    parent[u] = p;
    sum_min3_child[u] = 0;
    sum_min_child[u] = 0;
    sum_dp1_child[u] = 0;
    count_inf_min3_child[u] = 0;
    count_inf_min_child[u] = 0;
    count_inf_dp1_child[u] = 0;
    min1_delta[u] = INF;
    min2_delta[u] = INF;
    cnt1[u] = 0;
    for (int v : adj[u]) {
        if (v == p) continue;
        dfs_post(v, u);
        ll m3 = min(down[v][0], min(down[v][1], down[v][2]));
        if (m3 < INF) sum_min3_child[u] += m3;
        else count_inf_min3_child[u]++;
        ll mv = min(down[v][0], down[v][1]);
        if (mv < INF) sum_min_child[u] += mv;
        else count_inf_min_child[u]++;
        if (down[v][1] < INF) sum_dp1_child[u] += down[v][1];
        else count_inf_dp1_child[u]++;
        ll delta;
        if (down[v][1] >= INF) delta = -INF;
        else delta = down[v][0] - down[v][1];
        if (delta < min1_delta[u]) {
            min2_delta[u] = min1_delta[u];
            min1_delta[u] = delta;
            cnt1[u] = 1;
        } else if (delta == min1_delta[u]) {
            cnt1[u]++;
        } else if (delta < min2_delta[u]) {
            min2_delta[u] = delta;
        }
    }
    if (count_inf_min3_child[u] > 0) down[u][0] = INF;
    else down[u][0] = c[u] + sum_min3_child[u];
    if (count_inf_min_child[u] > 0 || min1_delta[u] >= INF) down[u][1] = INF;
    else down[u][1] = sum_min_child[u] + max(0LL, min1_delta[u]);
    if (count_inf_dp1_child[u] > 0) down[u][2] = INF;
    else down[u][2] = sum_dp1_child[u];
}
void dfs_pre(int u, int p) {
    for (int v : adj[u]) {
        if (v == p) continue;
        ll m3_v = min(down[v][0], min(down[v][1], down[v][2]));
        int cnt_inf3 = count_inf_min3_child[u] - (m3_v >= INF? 1 : 0);
        ll sum3 = INF;
        if (cnt_inf3 == 0) {
            sum3 = sum_min3_child[u];
            if (m3_v < INF) sum3 -= m3_v;
        }
        if (p!= -1) {
            ll up_m3 = min(up[u][0], min(up[u][1], up[u][2]));
            if (up_m3 >= INF) sum3 = INF;
            else if (sum3 < INF) sum3 += up_m3;
        }
        up[v][0] = (sum3 >= INF)? INF : (c[u] + sum3);
        int cnt_inf_dp1 = count_inf_dp1_child[u] - (down[v][1] >= INF? 1 : 0);
        ll sum_dp1 = INF;
        if (cnt_inf_dp1 == 0) {
            sum_dp1 = sum_dp1_child[u];
            if (down[v][1] < INF) sum_dp1 -= down[v][1];
        }
        if (p!= -1) {
            if (up[u][1] >= INF) sum_dp1 = INF;
            else if (sum_dp1 < INF) sum_dp1 += up[u][1];
        }
        up[v][2] = sum_dp1;
        ll mv_v = min(down[v][0], down[v][1]);
        int cnt_inf_min = count_inf_min_child[u] - (mv_v >= INF? 1 : 0);
        ll sum_min = INF;
        if (cnt_inf_min == 0) {
            sum_min = sum_min_child[u];
            if (mv_v < INF) sum_min -= mv_v;
        }
        ll up_delta = INF;
        if (p!= -1) {
            ll up_mv = min(up[u][0], up[u][1]);
            if (up_mv >= INF) sum_min = INF;
            else if (sum_min < INF) sum_min += up_mv;
            up_delta = (up[u][1] >= INF)? -INF : (up[u][0] - up[u][1]);
        }
        if (sum_min >= INF) {
            up[v][1] = INF;
        } else {
            ll delta_v = (down[v][1] >= INF)? -INF : (down[v][0] - down[v][1]);
            ll child_min;
            if (delta_v > min1_delta[u]) child_min = min1_delta[u];
            else if (cnt1[u] > 1) child_min = min1_delta[u];
            else child_min = min2_delta[u];
            ll overall_min = min(child_min, up_delta);
            up[v][1] = (overall_min >= INF)? INF : (sum_min + max(0LL, overall_min));
        }
        dfs_pre(v, u);
    }
}
int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int n; ll K;
    cin >> n >> K;
    for (int i=1; i<=n; i++) cin >> c[i];
    for (int i=0; i<n-1; i++) {
        int u, v; cin >> u >> v;
        adj[u].push_back(v); adj[v].push_back(u);
    }
    dfs_post(1, -1);
    up[1][0] = up[1][1] = up[1][2] = INF;
    dfs_pre(1, -1);
    ll ans = INF;
    for (int v=1; v<=n; v++) {
        ll sum = 0;
        bool ok = true;
        for (int w : adj[v]) {
            ll m;
            if (w == parent[v]) m = min(up[v][0], min(up[v][1], up[v][2]));
            else m = min(down[w][0], min(down[w][1], down[w][2]));
            if (m >= INF) { ok = false; break; }
            sum += m;
        }
        if (ok) ans = min(ans, sum + K);
    }
    cout << ans << endl;
    return 0;
}
