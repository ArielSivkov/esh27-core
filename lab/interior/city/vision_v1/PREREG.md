# City v1: the agents' eyes, a vision model on street photos (pre-registration, 2026-11-24)

Approved by Ariel: "1. זה גם תוך כדי" ("1. that too, in parallel"). From the world's third of the Kaggle budget.

**Data:** the 53 Commons street photos of Ashdod (`twin/publicdata/images_catalog.csv`). They are public, with no private photos
and no people's details. Images are fetched inside the kernel via `commons.wikimedia.org/wiki/Special:FilePath/<name>?width=1024`.

**Model:** Qwen2.5-VL-3B-Instruct, fp16, on one T4.

**Each image is asked twice, with two different wordings:**
(a) the floor count of the most prominent building;
(b) any readable text (signs, street names, businesses);
(c) the scene type.
The output is JSON.

**Measures, fixed in advance:**
1. **Self-consistency of floors:** the share of images where both wordings agree within ±1 floor. Below 70% means the floor counts are
   too noisy to use as a vote.
2. **Street-sign check:** among images where the model read a street name, the share that matches the catalog's street
   (normalized Hebrew, ignoring ו/י). This is a real, verifiable check.
3. **Coverage:** the share of images where it produced a floor count at all.
4. **No height enters the world** in any case. By the court's ruling, model-derived heights don't enter tiles. These are notes
   for the agents and a list of buildings to measure.

**Threats (for the red team):** the model may "read" a street name that appears in the file name? No: the model sees only pixels,
never the file name. Still, any OCR hit that exactly equals the catalog's description text gets a second look.
Hallucinated text, and floor counts on photos of non-buildings, are reported per image.
