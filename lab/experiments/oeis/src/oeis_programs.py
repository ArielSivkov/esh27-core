# Programs exactly as they appear in the %o lines of the drafts (tested by test_programs below).

def a_schur(n, k=3, weak=False):
    # partitions of {1..n} into at most k sum-free sets (= k-colourings with no
    # monochromatic x+y=z, up to permuting colours); weak=True: only x != y forbidden
    col = [0]*(n+1)
    def rec(i, used):
        if i > n: return 1
        s = 0
        for c in range(min(used+1, k)):
            if all(col[x] != c or col[i-x] != c for x in range(1, (i+1)//2 if weak else i//2+1)):
                col[i] = c; s += rec(i+1, max(used, c+1))
        return s
    return rec(1, 0)

def T(n, k):
    # partitions of {1..n} into exactly k sum-free sets
    col = [0]*(n+1)
    def rec(i, used):
        if i > n: return int(used == k)
        if used + (n - i + 1) < k: return 0
        s = 0
        for c in range(min(used+1, k)):
            if all(col[x] != c or col[i-x] != c for x in range(1, i//2+1)):
                col[i] = c; s += rec(i+1, max(used, c+1))
        return s
    return rec(1, 0)

if __name__ == '__main__':
    print([a_schur(n, 3) for n in range(1, 15)])
    print([a_schur(n, 3, True) for n in range(1, 25)])
    print([a_schur(n, 4) for n in range(1, 16)])
    print([T(n, k) for n in range(1, 11) for k in range(1, n+1)])
