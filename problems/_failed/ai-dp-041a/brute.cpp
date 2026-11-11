#include <iostream>
#include <vector>
#include <climits>
#include <algorithm>
using namespace std;

int main() {
    int n, k;
    cin >> n >> k;
    vector<int> u(n-1), v(n-1), w(n-1);
    for (int i = 0; i < n-1; ++i) {
        cin >> u[i] >> v[i] >> w[i];
    }
    vector<int> a(n+1);
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
    }

    vector<vector<long long>> dist(n+1, vector<long long>(n+1, 1e18));
    for (int i = 1; i <= n; ++i) dist[i][i] = 0;
    for (int i = 0; i < n-1; ++i) {
        dist[u[i]][v[i]] = w[i];
        dist[v[i]][u[i]] = w[i];
    }
    for (int kk = 1; kk <= n; ++kk) {
        for (int i = 1; i <= n; ++i) {
            for (int j = 1; j <= n; ++j) {
                dist[i][j] = min(dist[i][j], dist[i][kk] + dist[kk][j]);
            }
        }
    }

    vector<vector<long long>> c(n-1, vector<long long>(n+1, 0));
    for (int e = 0; e < n-1; ++e) {
        int x = u[e], y = v[e], we = w[e];
        for (int r = 1; r <= n; ++r) {
            long long sum = 0;
            for (int uu = 1; uu <= n; ++uu) {
                if (dist[uu][x] + we + dist[y][r] == dist[uu][r] || dist[uu][y] + we + dist[x][r] == dist[uu][r]) {
                    sum += a[uu];
                }
            }
            c[e][r] = sum;
        }
    }

    vector<long long> total(n+1, 0);
    for (int r = 1; r <= n; ++r) {
        for (int uu = 1; uu <= n; ++uu) {
            total[r] += 1LL * a[uu] * dist[uu][r];
        }
    }

    long long ans = 1e18;
    for (int r = 1; r <= n; ++r) {
        long long max_sum = 0;
        for (int mask = 0; mask < (1 << (n-1)); ++mask) {
            int cnt = __builtin_popcount(mask);
            if (cnt > k) continue;
            long long sum = 0;
            for (int e = 0; e < n-1; ++e) {
                if (mask & (1 << e)) {
                    sum += 1LL * w[e] * c[e][r];
                }
            }
            max_sum = max(max_sum, sum);
        }
        ans = min(ans, total[r] - max_sum);
    }
    cout << ans << endl;
    return 0;
}
