/* Method D: block-by-block enumerator (structurally different from A and B).
   A set partition is built one BLOCK at a time: the next block is any (weakly) sum-free subset of the
   still-unassigned elements that contains the smallest unassigned element.  Every set partition is
   produced exactly once.  Usage: schur_blockwise kmax n weak   (n <= 62)
   Prints, for the single given n:  n T(n,1) .. T(n,kmax)  (exactly j nonempty blocks). */
#include <stdio.h>
#include <stdlib.h>
typedef unsigned long long u64;
static int n,kmax,weak; static long long T[64];
static int elems[64];
static void partition(u64 rem,int blocks);
/* extend current block B (with sum-set F) by elements of list idx.., all from rem */
static void grow(u64 rem,int blocks,u64 B,u64 F,int *lst,int len,int pos){
  /* option: close the block here */
  partition(rem & ~B, blocks+1);
  for(int p=pos;p<len;p++){
    int z=lst[p]; u64 bz=1ULL<<z;
    if(F & bz) continue;                       /* z = x+y with x,y in B */
    /* z must also not be a summand creating a sum inside B: since elements are added in increasing
       order, any x+y=w with w in B has w > x,y; w<z impossible to be created later... but z+x could
       equal an element already in B?  No: elements of B are < z, and z+x > z. */
    u64 nF = F | (B<<z); if(!weak) nF |= (2*z<64)? (1ULL<<(2*z)) : 0;
    grow(rem,blocks,B|bz,nF,lst,len,p+1);
  }
}
static void partition(u64 rem,int blocks){
  if(rem==0){ T[blocks]++; return; }
  if(blocks==kmax) return;
  int lst[64],len=0;
  for(int i=1;i<=n;i++) if(rem>>i&1) lst[len++]=i;
  int m=lst[0];
  grow(rem,blocks,1ULL<<m,(!weak && 2*m<64)?(1ULL<<(2*m)):0,lst,len,1);
}
int main(int a,char**v){
  kmax=atoi(v[1]); n=atoi(v[2]); weak=a>3?atoi(v[3]):0;
  u64 all=0; for(int i=1;i<=n;i++) all|=1ULL<<i;
  partition(all,0);
  printf("%d",n); for(int j=1;j<=kmax;j++) printf(" %lld",T[j]); printf("\n");
  return 0;
}
