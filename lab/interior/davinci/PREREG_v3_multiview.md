# Da Vinci v3: lots of photos together → 3D (pre-registration, 2026-11-24)

Ariel: "השוואה לתמונות אחרות, בעזרת כל מיני תמונות ביחד" ("compare against other photos, using lots of photos together").

**Data:** Ariel's 14 Givat Yona photos (083–096, 23.11 at 17:09–17:11). They are already public in
`codesandbox-template-nuxt/twin-world/twin/data/photos/`. The kernel fetches them from there; no new exposure.

**Arms**
- **A: COLMAP** (pycolmap, BSD). Classic SIFT + exhaustive matching + incremental SfM, max 1600 px.
- **B: VGGT-1B** (Meta 2025, a feed-forward multi-view foundation model; open weights, CC-BY-NC: research only).
  14 images at 518 px → cameras + a point cloud.

**Criteria, fixed in advance**
1. **COLMAP:** ≥ 6/14 images registered in a single model, with mean reprojection error < 2 px. This is the baseline question
   of whether there is enough parallax at all. If most photos were taken from one spot, it will fail, and that is a real
   finding about how to photograph.
2. **Independent cross-check:** for images registered in both, the median angle between COLMAP's and VGGT's relative
   rotations is < 10°. If it holds, the two methods agree on the geometry.
3. **For Ariel:** a point cloud (up to 20k points, colored), for a 3D viewer.

**No metric scale yet:** both methods give shape up to an unknown scale. A scale from the map (e.g. the known pergola or water tower) is the next step, not v3.
