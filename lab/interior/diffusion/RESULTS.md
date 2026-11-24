# Diffusion v0: results (Kaggle T4, 2026-11-24, ~2 GPU minutes)
- [F] SDXL-Turbo fp16: 6/6 images, 1.3–1.4 s per image at 512×512, 4 steps. Gallery: https://claude.ai/artifact (gallery.html, private).
- [F] Tiling (edge/inside ratio): facade 19.9, stone 5.2, asphalt 2.1. None tile; enforcing seamlessness is needed (circular padding / tiling VAE) before they enter the world.
- [F] FLUX.1-schnell **failed**: Hugging Face now requires login for it (gated). It needs an HF token through request_credential, or another open model.
- License: SDXL-Turbo = non-commercial research only.
