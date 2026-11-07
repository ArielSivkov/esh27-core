/* Method A: canonical backtracker (colours introduced in order of first use).
   Usage: schur_canon k n weak
   weak=0: forbid monochromatic x+y=z with x<=y (x=y allowed)  -- classical Schur / sum-free
   weak=1: forbid monochromatic x+y=z with x<y only             -- weak Schur
   Output, for m=1..n: m  e_1 .. e_k   where e_j = number of set partitions of {1..m}
   into exactly j nonempty blocks, each block (weakly) sum-free.
   Derived: U(m)=sum_j e_j (unordered, <=k blocks); L(m)=sum_j e_j*k!/(k-j)! (labelled). */
#include <stdio.h>
#include <stdlib.h>
static int k,n,weak,col[300];
static long long e[300][40];
static void rec(int i,int used){
  e[i-1][used]++;
  if(i>n) return;
  for(int c=0;c<k && c<=used;c++){
    int ok=1;
    for(int x=1;2*x<=i;x++){
      if(weak && 2*x==i) continue;
      if(col[x]==c && col[i-x]==c){ok=0;break;}
    }
    if(!ok) continue;
    col[i]=c; rec(i+1, c==used?used+1:used); col[i]=-1;
  }
}
int main(int a,char**v){
  k=atoi(v[1]); n=atoi(v[2]); weak=a>3?atoi(v[3]):0;
  for(int i=0;i<300;i++) col[i]=-1;
  rec(1,0);
  for(int m=1;m<=n;m++){ printf("%d",m); for(int j=1;j<=k;j++) printf(" %lld",e[m][j]); printf("\n"); }
  return 0;
}
