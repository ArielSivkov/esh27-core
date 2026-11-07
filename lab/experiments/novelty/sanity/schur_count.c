#include <stdio.h>
#include <stdlib.h>
/* count sum-free k-colourings of [1..n] (x+y=z, x=y allowed), up to colour permutation (canonical: colours appear in order of first use) */
int k,n,col[200]; long long cnt[200];
void rec(int i,int used){
  cnt[i-1]++;               /* prefix [1..i-1] is valid */
  if(i>n) return;
  for(int c=0;c<k && c<=used;c++){
    int ok=1;
    for(int x=1;x<=i/2;x++) if(col[x]==c && col[i-x]==c){ok=0;break;}
    if(!ok) continue;
    col[i]=c; rec(i+1, c==used?used+1:used); col[i]=-1;
  }
}
int main(int a,char**v){k=atoi(v[1]);n=atoi(v[2]);for(int i=0;i<200;i++)col[i]=-1;rec(1,0);
 for(int m=1;m<=n;m++) printf("%lld%s",cnt[m],m<n?",":"\n");}
