ARM I (0.5B, euler+gcd, K4, s27): mean 0.069->0.306->0.412; gcd .075->.525->.738; euler .062->.087->.087; ctrl .762->.812->.863; both promoted; 7.7 min
ARM C (0.5B, all, K4, s28): mean .141->.218->.316; mul .438->.45->.45; betti .025->.062->.188; euler .025->.037->.025; gcd .075->.325->.6; ctrl .75->.875->.863; both promoted; 14 min
ARM H (0.5B, mul only, K4, s27): mul .412->.537(REJECT, ctrl .675->.65)->.525(PROMOTE, ctrl .875); 9.8 min
ARM F (0.5B, all, K4, s29): mean .156->.328(PROMOTE)->.334(REJECT: gain <3pts); mul .425->.60->.537; betti .025->.113->.10; euler .062->.05->.05; gcd .113->.55->.65; ctrl .675->.675->.738; 14.4 min
ARM B (0.5B, betti only, K8, s27): betti 0.0->0.30(PROMOTE)->0.487(REJECT ctrl .762->.738); 22.6 min
NOTE: betti frozen set (s27): best constant guess (1,2)=17.5%; shortcut 'connected, b1=E-V+1'=51.25%. B's 48.7% may be the shortcut; need split connected/disconnected.
LOCAL (0.5B, all, K4, s27): mean .147->.300->.344 both PROMOTE; mul .412->.525->.55; betti .025->.037->.138; euler .05->.05->.062; gcd .10->.588->.625; ctrl .762->.80->.887; 16 min
ARM G (0.5B, betti only, K16, s27): betti 0.0->0.163(PROMOTE)->0.412(REJECT ctrl .812->.75); 37 min. Same frozen set as B.
ARM J (SmolLM2-1.7B, all, K4, s27): mean .072->.207->.294 both PROMOTE; mul .225->.275->.388; betti 0->.138->.138; euler 0->.025->.025; gcd .062->.388->.625; ctrl .45->.575->.675; 46 min
ARM A (Qwen 1.5B, all, K4, s27): mean .29->.416->.484 both PROMOTE; mul .70->.75->.762; betti .20->.138->.225; euler .087->.125->.138; gcd .175->.65->.812; ctrl .9875 flat; 51 min (+17 min OOM first try; fixed with MALLOC_ARENA_MAX=2)
ARM E (Qwen 1.5B, all, K4, s28): mean .263->.403->.456 both PROMOTE; mul .675->.75->.825; betti .113->.138->.125; euler .037->.075->.062; gcd .225->.65->.812; ctrl .9625 flat; 52.5 min (2 OOM attempts first)
ARM D (Qwen 1.5B, betti only, K8, s27): FAILED - OOM twice in round-1 LoRA training (fp32 1.5B + batch 8 > 15GB). Base betti .225 on SAME frozen set as B/G (0.5B base 0.0 -> 0.30/0.163 after round 1). ctrl 1.0

## Arm J — 5-round rerun (SmolLM2-1.7B, all tasks, K4, s27), reported 23.11 11:36 UTC
round | kept | mul betti euler gcd | mean | ctrl | decision
0 | - | .225 .000 .000 .062 | .072 | .450 | base
1 | 38 | .300 .212 .025 .500 | .259 | .725 | PROMOTE
2 | 110 | .362 .212 .013 .650 | .309 | .775 | PROMOTE
3 | 124 | .400 .212 .013 .725 | .338 | .7625 | REJECT (+.029)
4 | 136 | .362 .212 .037 .738 | .337 | .775 | REJECT (+.028)
5 | 112 | .425 .237 .025 .750 | .359 | .775 | PROMOTE
Takeaway: most gain in R1-2, then ~1-3pt/round (noise level at n=80); no forgetting; euler ~0, betti plateau ~.21-.24.

## Kaggle GPU (Tesla T4) — Qwen2.5-1.5B, all tasks, K4, s27, 3 rounds — 24.11.2026 01:21–01:31 Israel (≈10 min)
Base identical to CPU arm A (reproducible): mul .70 betti .20 euler .087 gcd .175 mean .29 ctrl .9875
R1 kept 109 → mean .406 (gcd .65) PROMOTE
R2 kept 163 → mean .475 (gcd .85) PROMOTE
R3 kept 197 → mean .537 (mul .725 betti .338 euler .20 gcd .887) PROMOTE; ctrl flat .9875 all rounds
Speed: ~10 min for 3 rounds vs ~2 h for 2 rounds on 4-CPU container.
