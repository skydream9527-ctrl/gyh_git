class Solution {
public:
    int numberOfRoutes(vector<string>& g, int d) {
        int n=g.size(),m=g[0].size(),M=1e9+7,vd=sqrt(1.*d*d-1);
        while((long long)(vd+1)*(vd+1)<=1LL*d*d-1)vd++;
        vector<long long>u(m),s(m),p(m+1);
        for(int c=0;c<m;c++)u[c]=g[n-1][c]=='.';
        for(int r=n-1;r>=0;r--){
            p[0]=0;for(int c=0;c<m;c++)p[c+1]=p[c]+u[c];
            for(int c=0;c<m;c++)s[c]=g[r][c]=='.'?(p[min(m,c+d+1)]-p[max(0,c-d)]-u[c]%M+M)%M:0;
            for(int c=0;c<m;c++)u[c]=(u[c]+s[c])%M;
            if(!r){long long a=0;for(int c=0;c<m;c++)a+=u[c];return a%M;}
            p[0]=0;for(int c=0;c<m;c++)p[c+1]=p[c]+u[c];
            for(int c=0;c<m;c++)u[c]=g[r-1][c]=='.'?(p[min(m,c+vd+1)]-p[max(0,c-vd)])%M:0;
        }
        return 0;
    }
};
