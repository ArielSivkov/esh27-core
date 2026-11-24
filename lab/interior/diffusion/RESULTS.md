# Diffusion v0: results (Kaggle T4, 2026-11-24, ~2 GPU minutes)
- [F] SDXL-Turbo fp16: 6/6 images, 1.3–1.4 s per image at 512×512, 4 steps. Gallery: https://claude.ai/artifact (gallery.html, private).
- [F] Tiling (edge/inside ratio): facade 19.9, stone 5.2, asphalt 2.1. None tile; enforcing seamlessness is needed (circular padding / tiling VAE) before they enter the world.
- [F] FLUX.1-schnell **failed**: Hugging Face now requires login for it (gated). It needs an HF token through request_credential, or another open model.
- License: SDXL-Turbo = non-commercial research only.

## v1: open weights only, not gated (Kaggle T4, ~16 GPU minutes)
| Model | License | Seconds/image (768²) | Tiling facade/stone/asphalt |
|---|---|---|---|
| SDXL base 1.0 | OpenRAIL++ | 11.6–13.2 | 9.35 / 2.12 / 0.88 |
| **SDXL + circular padding** | OpenRAIL++ | 14.6–15.1 | **0.16 / 0.03 / 0.46: passes the bar (≤1.5)** |
| PixArt-Sigma | OpenRAIL++ | ~38.6 | 1.67 / 2.30 / 1.63 |
| Sana 1.6B | Apache-2.0 | ~22.5 | 1.77 / 2.69 / 1.65 |
- [F] No black image (no fp16 NaN) in any arm.
- [Visual, my look and not a measure] The seamless facade tiles with no seam, but it is cluttered and cubist,
  less realistic than plain SDXL. Seamless ≠ usable. Next: seamless on stone/asphalt (they look natural), and for facades the
  world's procedural engine plus a diffusion texture only for materials (plaster, stone).
- Gallery: https://claude.ai/artifact/WMUCHB1sANQ64j6jd7YzML (private).
