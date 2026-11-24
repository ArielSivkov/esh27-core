# A local diffusion model of our own, v0 (pre-registration, 2026-11-24)

Ariel: "אני רוצה מודל לוקלי של דיפוזי" ("I want a local diffusion model"). Open weights, no paid API, on Kaggle (his directive:
build the world on Kaggle). From the world's third.

**Arms**
- **A:** stabilityai/sdxl-turbo, fp16, 4 steps, 512×512.
- **B:** black-forest-labs/FLUX.1-schnell; the transformer in 4-bit NF4 (bitsandbytes), CPU offload, 4 steps, 512×512.
  If it fails or OOMs, it is reported as failed.

**Prompts:** 6, fixed, for the world:
1. a facade texture of a 1970s Ashdod apartment block (white plaster, balconies);
2. Jerusalem-stone cladding;
3. a seamless asphalt texture;
4. Ashdod beach promenade at golden hour;
5. a street view of a residential tower in Ashdod;
6. a Mediterranean sky with clouds.
Seed 27, one image per prompt per arm.

**Measures, fixed in advance**
1. Seconds per image on a T4 (after warm-up).
2. **Tiling** for the texture prompts (1–3): mean absolute difference between opposite edges, against the same measure inside
   the image (a ratio of ~1 means it tiles well). Reported, with no pass criterion in v0.
3. The images go back through the log (small JPEG base64), into a gallery for Ariel. His opinion is the quality criterion.
   I make no claim of "beautiful" or "realistic".

**Licensing:** SDXL-Turbo is under a non-commercial research license; FLUX.1-schnell is Apache-2.0. This matters if the world
becomes a product. Noted for Ariel.
