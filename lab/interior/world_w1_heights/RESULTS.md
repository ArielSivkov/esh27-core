# W1 results (Kaggle CPU, 2026-11-24, ~15 s of compute, 0 GPU)

[F] = fact from `run_log_v1.txt`. [H] = hypothesis.
- [F] Overture (current release) has **20,571 buildings** in the Ashdod bbox: 12,315 from OpenStreetMap and 8,256 from Microsoft ML Buildings.
- [F] Height values:
  - **670 buildings have a floor count and 30 have a height**. Every one of them comes from **OpenStreetMap**.
  - Microsoft footprints carry no height. **0 independent values.**
- [F] Overpass from Kaggle failed on all three mirrors (406/429/504), so the direct OSM comparison did not run.
- **Pre-registered headline:** task-7 candidates (n ≥ 2 independent sources within 1 floor) = **0**.
  Open sources do not give two independent heights for any Ashdod building. This is a negative result.
- [H] Usable now as **one** source (n = 1, below the task-7 bar): 670 OSM floor counts. The world's tiles use rule-of-thumb heights
  (7 distinct values per LOG 23.11), so these 670 may not be in the tiles yet. To be checked by the world session.
  Not imported; the decision belongs to the queue and the court.
- [H] A second independent source must come from measurement: photos and floor counting, GBA/DSM rasters, or the survey office.
  This points the agent city's first job at buildings without a height source.
