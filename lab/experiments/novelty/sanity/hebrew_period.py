# Hebrew calendar (Dershowitz-Reingold style): new-year day number with dehiyyot
from collections import Counter
P=25920  # parts per day? use halakim: 1 day = 24*1080 = 25920
def leap(y): return (7*y+1)%19<7
def elapsed_months(y): return (235*y-234)//19
def molad_parts(y):  # parts since epoch molad BaHaRaD (day 1 = Monday? we keep relative)
    return elapsed_months(y)*(29*P+12*1080+793) + (5*1080+204)  # BaHaRaD: 5h 204p
def ny0(y):  # day of Rosh Hashana before postponement for 3 rules applied as in calendar (DR's hebrew-calendar-elapsed-days)
    m=elapsed_months(y)
    parts=12084+13753*m
    day=29*m+parts//25920
    if (3*(day+1))%7<3: day+=1   # ADU
    return day
def ny(y):
    ny0_,nyp,nyn=ny0(y),ny0(y-1),ny0(y+1)
    if nyn-ny0_==356: d=2
    elif ny0_-nyp==382: d=1
    else: d=0
    return ny0_+d
N=689472
# year type = (weekday of RH, length)
def ytype(y):
    a=ny(y); b=ny(y+1); return ((a+1)%7, b-a)  # weekday offset arbitrary but consistent
L=2*N+2
nys=[ny(y) for y in range(1,L+2)]
types=[((nys[i]+1)%7, nys[i+1]-nys[i]) for i in range(L)]
c=Counter(types[:N]); print('distinct year types',len(c)); print(sorted(c))
print('lengths',sorted({t[1] for t in c}))
print('RH weekdays',sorted({t[0] for t in c}))
print('days in N years', nys[N]-nys[0], (nys[N]-nys[0])%7, 'weeks', (nys[N]-nys[0])/7)
per = all(types[i]==types[i+N] for i in range(N)); print('period N holds',per)
for d in [N//2,N//3,N//4,N//7,N//19,N//2**6,N//3**4, N//7*1 ]:
    pass
divs=[d for d in range(1,N) if N%d==0]
minimal=[d for d in divs if all(types[i]==types[i+d] for i in range(N))]
print('smaller periods',minimal)
