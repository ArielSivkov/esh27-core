"""Diffusion v1 (Kaggle T4): open-weights only (SDXL base, PixArt-Sigma, Sana-1600M) + seamless SDXL via circular padding."""
import base64, io, json, time, gc, subprocess
import numpy as np, torch
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
subprocess.run("pip install -q -U diffusers accelerate sentencepiece 2>&1 | tail -1", shell=True)
PROMPTS = [
 ("facade", "seamless tileable texture, facade of a 1970s Israeli apartment block in Ashdod, white plaster, rows of windows and small balconies, front orthographic view, even daylight, no perspective"),
 ("stone", "seamless tileable texture, Jerusalem stone wall cladding, warm limestone blocks, orthographic, even light"),
 ("asphalt", "seamless tileable texture, worn grey asphalt road surface, top-down, even light"),
 ("promenade", "Ashdod beach promenade at golden hour, palm trees, Mediterranean sea, people walking, photo"),
 ("tower", "street-level photo of a modern residential tower in Ashdod Israel, white and glass, blue sky"),
 ("sky", "Mediterranean sky with scattered cumulus clouds, wide view, photo"),
]
TEX = ("facade", "stone", "asphalt")
def tile_ratio(img):
    a = np.asarray(img.convert("L"), float); h, w = a.shape
    edge = (np.abs(a[:, 0] - a[:, -1]).mean() + np.abs(a[0, :] - a[-1, :]).mean()) / 2
    inner = (np.abs(a[:, w // 2 - 1] - a[:, w // 2]).mean() + np.abs(a[h // 2 - 1, :] - a[h // 2, :]).mean()) / 2
    return round(float(edge / max(inner, 1e-6)), 2)
def emit(arm, key, img, secs):
    arr = np.asarray(img.convert("RGB")); black = bool(arr.mean() < 3)
    b = io.BytesIO(); img.convert("RGB").resize((384, 384)).save(b, "JPEG", quality=72)
    rec = {"arm": arm, "key": key, "secs": round(secs, 1), "black": black, "tile_ratio": tile_ratio(img) if key in TEX else None}
    print("IMG " + json.dumps(rec) + " " + base64.b64encode(b.getvalue()).decode(), flush=True)
def run(arm, pipe, kw, keys=None):
    g = torch.Generator("cpu").manual_seed(27); pipe(PROMPTS[0][1], generator=g, **kw)
    for key, pr in PROMPTS:
        if keys and key not in keys: continue
        g = torch.Generator("cpu").manual_seed(27); t = time.time()
        emit(arm, key, pipe(pr, generator=g, **kw).images[0], time.time() - t)
def free(): gc.collect(); torch.cuda.empty_cache()
import diffusers
from diffusers import StableDiffusionXLPipeline, AutoencoderKL
try:
    log("A: SDXL base 1.0")
    vae = AutoencoderKL.from_pretrained("madebyollin/sdxl-vae-fp16-fix", torch_dtype=torch.float16)
    pipe = StableDiffusionXLPipeline.from_pretrained("stabilityai/stable-diffusion-xl-base-1.0", vae=vae, torch_dtype=torch.float16, variant="fp16", use_safetensors=True).to("cuda")
    kw = dict(num_inference_steps=25, guidance_scale=6.0, height=768, width=768)
    run("A_sdxl_base", pipe, kw)
    for mod in (pipe.unet, pipe.vae):
        for m in mod.modules():
            if isinstance(m, torch.nn.Conv2d): m.padding_mode = "circular"
    run("A2_sdxl_seamless", pipe, kw, keys=TEX)
    del pipe, vae; free()
except Exception as e: log("A FAILED", repr(e)[:300]); free()
try:
    log("B: PixArt-Sigma")
    from diffusers import PixArtSigmaPipeline
    pipe = PixArtSigmaPipeline.from_pretrained("PixArt-alpha/PixArt-Sigma-XL-2-1024-MS", torch_dtype=torch.float16)
    pipe.enable_model_cpu_offload()
    run("B_pixart_sigma", pipe, dict(num_inference_steps=20, height=768, width=768))
    del pipe; free()
except Exception as e: log("B FAILED", repr(e)[:300]); free()
try:
    log("C: Sana 1600M")
    from diffusers import SanaPipeline
    pipe = SanaPipeline.from_pretrained("Efficient-Large-Model/Sana_1600M_1024px_diffusers", torch_dtype=torch.float16)
    pipe.vae.to(torch.float32); pipe.text_encoder.to(torch.float16); pipe.enable_model_cpu_offload()
    run("C_sana_1600m", pipe, dict(num_inference_steps=20, height=768, width=768))
    del pipe; free()
except Exception as e: log("C FAILED", repr(e)[:300]); free()
log("DONE")
