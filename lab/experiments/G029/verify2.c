/* Verifier 2 (C, different algorithm): for every difference d and every residue
   class s mod d, walk the chain s, s+d, s+2d, ... (1-indexed positions <= n) and track
   the length of the current run of equal colours.  A monochromatic k-AP exists iff
   some run reaches length k.  Reads the same certificate format as verify.py.
   Usage: verify2 FILE r k */
#include <stdio.h>
#include <stdlib.h>
int main(int argc, char **argv) {
  if (argc != 4) { fprintf(stderr, "usage: verify2 FILE r k\n"); return 2; }
  int r = atoi(argv[2]), k = atoi(argv[3]);
  FILE *f = fopen(argv[1], "r"); if (!f) { perror("open"); return 2; }
  size_t cap = 1 << 20, n = 0; unsigned char *c = malloc(cap + 2);
  int ch, comment = 0, bol = 1;
  while ((ch = fgetc(f)) != EOF) {
    if (bol && ch == '#') comment = 1;
    bol = (ch == '\n'); if (ch == '\n') { comment = 0; continue; }
    if (comment || ch == ' ' || ch == '\t' || ch == '\r') continue;
    if (ch < '0' || ch - '0' >= r) { fprintf(stderr, "bad colour char\n"); return 2; }
    if (n + 2 >= cap) { cap *= 2; c = realloc(c, cap + 2); }
    c[++n] = (unsigned char)(ch - '0');
  }
  fclose(f);
  for (size_t d = 1; (k - 1) * d < n; d++)
    for (size_t s = 1; s <= d && s <= n; s++) {
      int run = 1;
      for (size_t x = s + d; x <= n; x += d) {
        run = (c[x] == c[x - d]) ? run + 1 : 1;
        if (run >= k) {
          printf("FAIL n=%zu r=%d k=%d: monochromatic AP a=%zu d=%zu\n", n, r, k, x - (k - 1) * d, d);
          return 1;
        }
      }
    }
  printf("OK n=%zu r=%d k=%d: no monochromatic %d-AP\n", n, r, k, k);
  return 0;
}
