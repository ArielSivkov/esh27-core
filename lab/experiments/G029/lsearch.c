/* lsearch: min-conflicts / WalkSAT-style local search for AP-free r-colourings of [1,n].
   cost = number of monochromatic k-APs.  Per AP (a,d) we keep cnt[colour].
   Usage: lsearch INIT_FILE r k n_target seed max_steps noise_permille free_mode [out_file] [time_limit_s]
     INIT_FILE: digit string (may be shorter than n -> padded randomly, longer -> truncated);
                "-" = random start.
     free_mode: 0 = all positions free; m>0 = only positions x with x % m == 1 % m
                (i.e. 1-indexed multiples-of-m "zero" slots, x-1 = 0 mod m) are free.
   Writes the best (lowest cost) colouring to out_file (default: stdout) when cost hits 0,
   and prints progress lines "step cost best".  Exit 0 iff a 0-cost colouring was found. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>

static int n, r, k, dmax;
static uint8_t *col;          /* 1..n */
static int64_t *off;          /* off[d] = index of AP (1,d) */
static uint8_t *cnt;          /* [ap*r + c] */
static int64_t nap;
static int64_t *viol, *vpos; static int64_t nviol;  /* set of mono APs */
static uint64_t rng = 88172645463325252ULL;
static inline uint64_t xr(void){ rng ^= rng << 13; rng ^= rng >> 7; rng ^= rng << 17; return rng; }

static inline int64_t apid(int a, int d){ return off[d] + (a - 1); }
static void vadd(int64_t id){ vpos[id] = nviol; viol[nviol++] = id; }
static void vdel(int64_t id){ int64_t p = vpos[id], last = viol[--nviol]; viol[p] = last; vpos[last] = p; vpos[id] = -1; }

static void setcol(int x, int c) {
  int old = col[x]; if (old == c) return;
  for (int i = 0; i < k; i++)
    for (int d = 1; d <= dmax; d++) {
      int a = x - i * d; if (a < 1) break;
      if (a + (k - 1) * d > n) continue;
      int64_t id = apid(a, d); uint8_t *q = cnt + id * r;
      if (q[old] == k) vdel(id);
      q[old]--; q[c]++;
      if (q[c] == k) vadd(id);
    }
  col[x] = (uint8_t)c;
}
/* delta[c] = (#APs through x that become mono if x->c) - (#mono APs through x broken) */
static void deltas(int x, int *delta) {
  int old = col[x]; int brk = 0;
  for (int c = 0; c < r; c++) delta[c] = 0;
  for (int i = 0; i < k; i++)
    for (int d = 1; d <= dmax; d++) {
      int a = x - i * d; if (a < 1) break;
      if (a + (k - 1) * d > n) continue;
      uint8_t *q = cnt + apid(a, d) * r;
      if (q[old] == k) brk++;
      else for (int c = 0; c < r; c++) if (q[c] == k - 1 && c != old) delta[c]++;
    }
  for (int c = 0; c < r; c++) delta[c] -= brk;
  delta[old] = 0;
}

int main(int argc, char **argv) {
  if (argc < 9) { fprintf(stderr, "usage\n"); return 2; }
  const char *init = argv[1]; r = atoi(argv[2]); k = atoi(argv[3]); n = atoi(argv[4]);
  rng ^= (uint64_t)atoll(argv[5]) * 0x9E3779B97F4A7C15ULL; for (int i = 0; i < 10; i++) xr();
  long long maxsteps = atoll(argv[6]); int noise = atoi(argv[7]); int fm = atoi(argv[8]);
  const char *outf = argc > 9 ? argv[9] : NULL; double tlim = argc > 10 ? atof(argv[10]) : 1e18;
  dmax = (n - 1) / (k - 1);
  off = malloc(sizeof(int64_t) * (dmax + 2)); nap = 0;
  for (int d = 1; d <= dmax; d++) { off[d] = nap; nap += n - (k - 1) * d; }
  cnt = calloc((size_t)nap * r, 1); viol = malloc(sizeof(int64_t) * nap); vpos = malloc(sizeof(int64_t) * nap);
  for (int64_t i = 0; i < nap; i++) vpos[i] = -1;
  col = malloc(n + 2);
  int len0 = 0;
  if (strcmp(init, "-")) { FILE *f = fopen(init, "r"); int ch; if (!f) { perror("init"); return 2; }
    while ((ch = fgetc(f)) != EOF && len0 < n) if (ch >= '0' && ch <= '9') col[++len0] = ch - '0'; fclose(f); }
  for (int x = len0 + 1; x <= n; x++) col[x] = xr() % r;
  for (int d = 1; d <= dmax; d++) for (int a = 1; a + (k - 1) * d <= n; a++) {
    int64_t id = apid(a, d); uint8_t *q = cnt + id * r;
    for (int i = 0; i < k; i++) q[col[a + i * d]]++;
    if (q[col[a]] == k) vadd(id);
  }
  int *isfree = calloc(n + 2, sizeof(int));
  for (int x = 1; x <= n; x++) isfree[x] = fm == 0 ? 1 : ((x - 1) % fm == 0);
  long long *tabu = calloc((size_t)(n + 2) * r, sizeof(long long));
  int tt = 10 + n / 100;
  int64_t best = nviol; uint8_t *bestc = malloc(n + 2); memcpy(bestc, col, n + 2);
  fprintf(stderr, "init n=%d r=%d k=%d aps=%lld cost=%lld\n", n, r, k, (long long)nap, (long long)nviol);
  clock_t t0 = clock(); long long step;
  int delta[16];
  for (step = 0; step < maxsteps && nviol > 0; step++) {
    if ((step & 4095) == 0) {
      double el = (double)(clock() - t0) / CLOCKS_PER_SEC;
      if (el > tlim) break;
      if ((step & ((1 << 20) - 1)) == 0) fprintf(stderr, "step %lld cost %lld best %lld t=%.0fs\n", step, (long long)nviol, (long long)best, el);
    }
    int64_t id = viol[xr() % nviol];
    int d = 0; /* recover (a,d) from id */
    { int lo = 1, hi = dmax; while (lo < hi) { int mid = (lo + hi + 1) / 2; if (off[mid] <= id) lo = mid; else hi = mid - 1; } d = lo; }
    int a = (int)(id - off[d]) + 1;
    int bx = -1, bc = -1, bv = 1 << 30, nt = 0;
    if ((int)(xr() % 1000) < noise) {
      int tries = 0;
      do { bx = a + (int)(xr() % k) * d; tries++; } while (!isfree[bx] && tries < 50);
      if (!isfree[bx]) continue;
      bc = (col[bx] + 1 + xr() % (r - 1)) % r;
    } else {
      for (int i = 0; i < k; i++) {
        int x = a + i * d; if (!isfree[x]) continue;
        deltas(x, delta);
        for (int c = 0; c < r; c++) { if (c == col[x]) continue;
          int v = delta[c];
          int tb = tabu[(size_t)x * r + c] > step && !(nviol + v < best);
          if (tb) continue;
          if (v < bv || (v == bv && (xr() % (++nt)) == 0)) { if (v < bv) nt = 1; bv = v; bx = x; bc = c; }
        }
      }
      if (bx < 0) continue;
    }
    int old = col[bx]; setcol(bx, bc);
    tabu[(size_t)bx * r + old] = step + tt + (long long)(xr() % tt);
    if (nviol < best) { best = nviol; memcpy(bestc, col, n + 2); }
  }
  double el = (double)(clock() - t0) / CLOCKS_PER_SEC;
  fprintf(stderr, "end step %lld best %lld time %.1fs\n", step, (long long)best, el);
  printf("RESULT n=%d r=%d k=%d best=%lld steps=%lld time=%.1f\n", n, r, k, (long long)best, step, el);
  if (outf) { FILE *f = fopen(outf, "w"); for (int x = 1; x <= n; x++) fputc('0' + bestc[x], f); fputc('\n', f); fclose(f); }
  return best == 0 ? 0 : 1;
}
