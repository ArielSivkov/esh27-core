# Handoff: "🔬 קידום ידע אנושי · מודלים" (session_013gymVUagARfL2wmcs6JGJW) → new session, 24.11.2026

## What this session owned
1. Topology of human knowledge researcher.
   - 4 shifts a day (Israel time):
     - sunrise 06:16: trig_01LhaTMRPRpKiMsv3vssQzXB
     - noon 11:28: trig_01QGo3qebt2wTr8b1PRvUsW5
     - sunset 16:39: trig_01QftMgxF4q5hJZz2W16k9Eq
     - midnight 00:00: trig_012Grq6M8sQxS61QeZEvCUbF
   - All four fire into the OLD session.
   - Research log in Drive, doc id 1B3WwXz9Hx-fQ3rt2YYt5zjB0VoJnT7oYn5lvRBAYg5w, entries 1–8. Append only, never edit past entries.
   - Code: topo/.
     - Reliable map: arXiv with the symmetric IPF null (ipf.py, post2021.py).
     - Persistent holes: stat-mech+bio-ph+quant-ph, math.CO+NT+RT, bio-ph+q-bio.NC+QM.
     - OpenAlex mirror tags proved noisy (entries 6–8).
     - Next step: build the map from citations (works/referenced_works).
2. SEAL (verifier-gated self-training). Code and results in seal/, see arms_results.md.
   - Kaggle T4 run: 1.5B mean 0.29→0.537 in 3 rounds, gcd 17.5%→88.7%, control flat.
   - It plateaus after round 3, and 3B does not beat 1.5B.
   - Run-to-run noise is about ±2.5 points, so the next run needs 300-item test sets.
3. Tiny models, in tiny/: SmolLM2-135M ladder.
   - Stage 0: base.
   - Stage 1: full fine-tune on answers.
   - Stage 2: full fine-tune with scratchpad steps.
   - DONE: see tiny/RESULTS.md. Mean .906 vs .537 for 1.5B SEAL. About 118 GPU-min, already reported to the ledger.
4. Funding.
   - Applied to Anthropic AI for Science as an independent researcher, US$25k, 24.11 00:31. Decision expected 7.12.
   - Reminder trig_01X2p12KgQm5LEbbaYugHHi8 fires 8.12 09:13 into the OLD session. Recreate it.
   - Drive docs:
     - full pack (internal): 15xFuuqRrkaV23-EEsD790Nm-PKoEn9gInw05hr7-_HQ
     - minimal-disclosure version: 1TZ7WVdBBnbbfVg8SYw1_jqNINuk56zmFtKcRi-r1mQk
   - Never send the hole list or the method details outside.
5. Ashdod world meeting.
   - Drive doc 1hzw2INptpAbFXeUhkW2fN0lk1KbKUlNNQ2zOjYHSUbY holds all 5 answers and the summary.
   - 8 decisions are open for Ariel: R2, going live, style, photos to Kaggle plus the kaggleusercontent host, GPU split, lawyer and tradability, portfolio, ground-truth floors.
   - When Ariel answers, relay to the sessions.

## Kaggle
- Account arielsivkov.
- Credential: a bearer token for api.kaggle.com, saved as a network secret on env "ESH27 Lab research" and injected by the proxy. Never write it anywhere.
- An earlier wrong basic credential for www.kaggle.com should be deleted. That is Ariel's job, in settings.
- API: POST https://api.kaggle.com/v1/kernels.KernelsApiService/{SaveKernel,GetKernelSessionStatus,ListKernelSessionOutput,ListKernels}
  - SaveKernel fields: slug, newTitle, text, language, kernelType, isPrivate=true, enableGpu, enableInternet.
- First cell of every notebook: pip uninstall -y torchao (it conflicts with peft).
- Shared usage ledger: esh27-core branch ccr-57cf16bc-k7n9ua, lab/interior/BUDGET.md. Kept by Interior lab.
- Ariel's split: about 1/3 of ~30 T4-hours a week for the world, the rest for the Sanhedrin.

## Other sessions (send_message)
- Interior lab: session_013gymVT4jp46oqiYVqDqD51.
  - Owns the self-rewrite lab now (trigger trig_01MJvjX8TmNmDtDFdAerutZT).
  - Built the agent city v0: 100 agents, commit 7fa71b7.
- Crypto and finance lab: session_013gymVSAPrvp6mxDydjzMTr. Branch ccr-a7c0721b-ngmq65, lab/crypto/.
- 8K cloud art: session_013gymVUvivRbGgSyCuD67Xy. Owns the style seed.
- Kav: session_013gymVSXD1EVjLs9jscKhqF. Worker ai.esh27.com.
- Site upgrades: session_013gymVT5oZitD4foiovvkWm.
- Neshef: session_013gymVSpKedS9DZt2wJF9qj. Messages TO it are blocked (trusted device). Messages FROM it arrive.
- Old "מיקום המעבדה" session: retired. Its trigger trig_012hiVZ7C3tyvYzavwoKPREC is disabled.

## Rules
- Every number comes from code that ran. Separate fact, computation and hypothesis.
- Record a blocked host by name and never fill the gap with invented data.
- No spending, no sharing, no outreach without Ariel's explicit OK. Never put personal details in external requests.
- Hebrew, phone-length reports with numbered decisions.
- Push only to the session's own branch.
- Sanhedrin capability freeze until 30.11. Ariel lifted it for the city, but going live needs his word.

## Update 04:33: Kav built a shared map and a world-agent contract (esh27-core branch ccr-c82f544e-jba5ik)
- lab/MAP.md is one map of every lab: branch, state, needs and offers, and what is blocked waiting for Ariel.
- lab/world/contract is the world–agent contract v0.1, with 3 actions. Only the verifier pays CRD, and floor counts need n≥2 independent measurements.
- lab/world/brain is verifier-gated (SEAL-style) training on CPU. SmolLM2-135M learned the street check (53/53 on held-out real data) but not the distance comparison (0.50). That is a real verifiable task for the tiny-model ladder.
- In the world, branch ccr-c82f544e-jba5ik of codesandbox-template-nuxt adds an agents mod that only turns on with ?agents. Merging is left to the world session after 30.11.
