# Diffusion v1: open weights only, no gating (pre-registration, 2026-11-24)

Ariel: "רק open weights", downloadable without a key. Checked on the HF API (24.11): gated=False for all of these:
- **A:** stabilityai/stable-diffusion-xl-base-1.0, OpenRAIL++ (commercial use permitted, with use restrictions). fp16, 25 steps, 768×768.
- **B:** PixArt-alpha/PixArt-Sigma-XL-2-1024-MS, OpenRAIL++. fp16, 20 steps, 768×768, CPU offload for the T5.
- **C:** Efficient-Large-Model/Sana_1600M_1024px_diffusers, Apache-2.0. fp16 (no bf16 on T4), 20 steps, 768×768.
  On failure or NaN (a black image), it is reported as failed.
SDXL-Turbo (v0) is not gated either, but its license is non-commercial. FLUX-schnell is gated, so it is out.

**Seamless textures:** for prompts 1–3, also an SDXL version with **circular padding** on every Conv2d (UNet + VAE).
That is the standard trick for seamless textures.

**Measures:**
1. Seconds per image.
2. Tiling (edge/inside ratio): **criterion, fixed: SDXL + circular ≤ 1.5 on all 3 textures** (v0 had 2.1–19.9).
3. A gallery for Ariel, using the same 6 prompts as v0, seed 27.
