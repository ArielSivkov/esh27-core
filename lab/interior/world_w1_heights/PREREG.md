# W1: open building-height sources for Ashdod (pre-registration, 2026-11-24)

The world's share of the Kaggle budget (approved by Ariel: "כן על הכל").
Context: twin/REPORT-b5-heights.md (codesandbox-template-nuxt @ twin-world).
- Every Ashdod building in the tiles has a rule-of-thumb height (7 distinct values).
- Overpass, Overture and others were blocked in the world's environment.
- The court's freeze (until 30.11) allows accuracy work only, and nothing here writes to the tiles.

## Question
How many Ashdod buildings get a height or floor count from open sources, and how well do independent sources agree?

## Method
A Kaggle **CPU** kernel (no GPU quota), with internet. Area: bbox lon 34.60–34.72, lat 31.74–31.86.
1. **OSM via Overpass:** buildings with `building:levels` and/or `height`, plus name.
2. **Overture Maps buildings:** release via the `overturemaps` package, with `height`, `num_floors` and per-property `sources`.
3. **Provenance.** A value counts as independent of OSM only if its Overture source for that property is not OpenStreetMap.
   - Overture copies OSM values.
   - Counting a copy as a second source would be fake agreement (red-team threat #1).
4. **Matching.** Overture ↔ OSM by shared OSM id where present, otherwise by centroid-in-polygon.
5. **Floors from height:** (h − 1.0) / 3.0, the world's own assumption (REPORT-b5).

## Outcomes (fixed in advance)
- **Coverage.**
  - N buildings in the bbox.
  - Count with OSM levels, OSM height, an independent (non-OSM) Overture height, and both.
- **Agreement.** Among buildings with OSM levels and an independent height:
  - the share within ±1 floor;
  - the median absolute difference in floors.
- **Task 7 candidate.** A building is a candidate only if n ≥ 2 independent sources agree within 1 floor
  (the queue's rule: n≥2, σ≤1). That count is the headline number.
- **Anchors.** The Dekel towers (w1280878706, w1013192689; the world uses 30 floors, σ = 8 m) are reported as a sanity check.
  They are not a criterion.
- Negative results are reported the same way. For example: "no independent source covers Ashdod".

## Threats (red team before reporting)
- Copied values (covered by the provenance rule).
- Default/placeholder heights in a source (spikes at one value are reported).
- Size bias: tall buildings are tagged more often, so coverage is reported by footprint-area bins.
- Matching errors: multiple matches are reported and excluded.

## Output
The kernel prints a summary and a compact CSV of candidates into the log, because file download is blocked here.
Nothing goes into the tiles; the world session/queue decides.
