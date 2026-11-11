/* Method B: independent, structurally different enumerator.
   Fully LABELLED colourings (no symmetry breaking), each colour class kept as a bitmask,
   plus a bitmask F[c] of all sums already "spanned" by class c; z may join class c iff bit z of F[c] is 0.
   Usage: schur_labelled_bits k n weak     (n <= 126)
   Output for m=1..n:  m  L(m)  where L(m) = number of maps {1..m}->{1..k} with no monochromatic
   x+y=z (weak=0: x<=y; weak=1: x<y). */
#include <stdio.h>
#include <stdlib.h>
typedef unsigned __int128 u128;
static int k,n,weak; static long long L[130];
static u128 M[8],F[8];
static void rec(int z){
  L[z-1]++;
  if(z>n) return;
  u128 bz=((u128)1)<<z;
  for(int c=0;c<k;c++){
    if(F[c]&bz) continue;
    u128 oM=M[c], oF=F[c];
    F[c] |= (M[c]<<z);                 /* sums z+x, x already in class c (x<z) */
    if(!weak && 2*z<128) F[c] |= ((u128)1)<<(2*z);   /* z+z */
    M[c] |= bz;
    rec(z+1);
    M[c]=oM; F[c]=oF;
  }
}
int main(int a,char**v){
  k=atoi(v[1]); n=atoi(v[2]); weak=a>3?atoi(v[3]):0;
  if(n>62){ /* shifting M<<z must stay within 128 bits for sums <= n: M has bits < z <= n, so M<<z < 2^(2n); bits above 127 dropped, harmless since only bits <= n are tested */ }
  rec(1);
  for(int m=1;m<=n;m++) printf("%d %lld\n",m,L[m]);
  return 0;
}
