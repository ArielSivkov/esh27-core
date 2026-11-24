# City v1, the agents' eyes: results (Kaggle T4, 2026-11-24, ~7 GPU minutes)

[F] fact from `run_log_v1.txt` · [H] hypothesis. Criteria are from PREREG.md and unchanged.
- [F] Images: 49 of 53 analysed. 3 returned 404 from Commons, and 1 was rate-limited (429).
- **Floor self-consistency: 23/35 = 65.7% < 70%. Fails.** Too noisy to count as a vote.
  [F] The floor answers pile up at round numbers (10: 7 images, 20: 6, 30: 5). [H] The model guesses rather than counts.
- **Street-sign check: 0/8. Fails.**
  - [F] On the 8 images where it read Hebrew, it read no street name.
  - [F] It read business names: "טמבור", "פינק", "דופר", "קופמטים", "כיכר הפונדקאים".
  - [F] One reading, "מגדל אוניברסיטת תל אביב", on a promenade photo, is probably a hallucination.
  - [H] Some of the business names are real signs; this has not been verified.
- [F] Coverage: a floor count on 43/49 images. Scene types: 25 residential, 18 commercial, 3 towers.
- **Conclusion:** at the 3B size, the model is not good enough to be the agents' eyes for floors. It does produce text from signs.
  [H] Next: a larger model (Qwen2.5-VL-7B in 4-bit on a T4) or counting by drawing a window grid, against a test set with
  known floors before any use. Nothing goes into the world.
