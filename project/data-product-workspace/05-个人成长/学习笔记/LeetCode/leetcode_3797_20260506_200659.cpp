#include <bits/stdc++.h>
using namespace std;

class Solution {
public:
    int numberOfRoutes(vector<string>& grid, int d) {
        const int MOD = 1000000007;
        int m = grid[0].size();
        vector<long long> sf(m + 1, 0);
        vector<long long> sg(m + 1, 0);

        for (int i = 0; i < (int)grid.size(); i++) {
            for (int j = 0; j < m; j++) {
                if (grid[i][j] == '#') {
                    sf[j + 1] = sf[j];
                } else if (i == 0) {
                    sf[j + 1] = sf[j] + 1;
                } else {
                    int hi = j + d < m ? j + d : m;
                    int lo = j - d + 1 > 0 ? j - d + 1 : 0;
                    sf[j + 1] = (sf[j] + sg[hi] - sg[lo]) % MOD;
                }
            }

            for (int j = 0; j < m; j++) {
                if (grid[i][j] == '#') {
                    sg[j + 1] = sg[j];
                } else {
                    int hi = j + d + 1 < m ? j + d + 1 : m;
                    int lo = j - d > 0 ? j - d : 0;
                    sg[j + 1] = (sg[j] + sf[hi] - sf[lo]) % MOD;
                }
            }
        }

        return (int)((sg[m] % MOD + MOD) % MOD);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, d;
    cin >> n >> d;
    vector<string> grid(n);
    for (int i = 0; i < n; i++) {
        cin >> grid[i];
    }

    Solution sol;
    cout << sol.numberOfRoutes(grid, d) << endl;
    return 0;
}
