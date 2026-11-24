# The agent city (v0), 24.11.2026

Live page, private: https://claude.ai/artifact/BQxNpx6Tbk7CQW3P7yHZTX

**What there is:**
- **The agents:** 100 agents (50/50). Each has a plot: a real building from the twin world's Ashdod tiles (twin-world branch, read-only).
- **Movement:** they walk the real street graph (22,009 nodes) on Israel time.
- **Shared state, no server:** everything is a function of the clock and the date, so everyone who opens the page sees the same city.
- **Work for now: checking photos (87 jobs).**
  - 34 photos from Ariel's walk: is the estimated position consistent with the street name, and which buildings are within ±error?
  - 53 Commons street photos: is the street in the map?
  - The results were computed in `build_city.py` (`jobs_v0.json`). The page shows them when an agent "finishes" the job.

**v0 results ([F] fact, [H] hypothesis):**
- [F] 32 of 34 photos are consistent with their street; 2 have no street on record.
- [F] 47 of 53 Commons streets were found in the map.
- [F] Spelling variants of one street name: רוגזין / רוגוזין.
- [F] 7,425 of 7,427 buildings have a rule-of-thumb height.
- [H] The street check is consistency, not independent verification: the photos' street match was probably derived from the same map.

**Not yet real:**
- The agents don't see images.
- There is no learning or memory.
- There is no "children" mechanism or coin.

**Next steps (proposed):**
1. A vision model on Kaggle (the world's third of the budget), comparing a photo to a view rendered from the twin world, as the agents' real job.
2. Memory and a reputation score per agent, from verified work.
3. A permanent host for an actual agent loop. That needs a server, and Kaggle can't host one.

This lives in the lab and does not touch world.esh27.com or the twin-world branch (court freeze until 30.11).
