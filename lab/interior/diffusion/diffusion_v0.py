"""Diffusion v0 (Kaggle T4): SDXL-Turbo fp16 vs FLUX.1-schnell NF4. Images go to the log as base64 JPEG. See PREREG.md."""
import base64, io, json, time, gc, subprocess
import numpy as np, torch
T0 = time.time()
def log(*a): print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
subprocess.run("pip install -q -U diffusers bitsandbytes accelerate sentencepiece 2>&1 | tail -1", shell=True)
PROMPTS = [
 ("facade", "seamless tileable texture, facade of a 1970s Israeli apartment block in Ashdod, white plaster, rows of windows and small balconies, front orthographic view, even daylight, no perspective"),
 ("stone", "seamless tileable texture, Jerusalem stone wall cladding, warm limestone blocks, orthographic, even light"),
 ("asphalt", "seamless tileable texture, worn grey asphalt road surface, top-down, even light"),
 ("promenade", "Ashdod beach promenade at golden hour, palm trees, Mediterranean sea, people walking, photo"),
 ("tower", "street-level photo of a modern residential tower in Ashdod Israel, white and glass, blue sky"),
 ("sky", "Mediterranean sky with scattered cumulus clouds, wide view, photo"),
]
def tile_ratio(img):
    a = np.asarray(img.convert("L"), float)
    edge = (np.abs(a[:, 0] - a[:, -1]).mean() + np.abs(a[0, :] - a[-1, :]).mean()) / 2
    inner = (np.abs(a[:, 255] - a[:, 256]).mean() + np.abs(a[255, :] - a[256, :]).mean()) / 2
    return round(float(edge / max(inner, 1e-6)), 2)
def emit(arm, key, img, secs):
    b = io.BytesIO(); img.convert("RGB").resize((384, 384)).save(b, "JPEG", quality=72)
    rec = {"arm": arm, "key": key, "secs": round(secs, 1), "tile_ratio": tile_ratio(img) if key in ("facade", "stone", "asphalt") else None}
    print("IMG " + json.dumps(rec) + " " + base64.b64encode(b.getvalue()).decode(), flush=True)
def run(arm, pipe, kw):
    g = torch.Generator("cpu").manual_seed(27)
    pipe(PROMPTS[0][1], generator=g, **kw)  # warm-up
    for key, pr in PROMPTS:
        g = torch.Generator("cpu").manual_seed(27); t = time.time()
        img = pipe(pr, generator=g, **kw).images[0]; emit(arm, key, img, time.time() - t)
from diffusers import AutoPipelineForText2Image
try:
    log("A: sdxl-turbo")
    pipe = AutoPipelineForText2Image.from_pretrained("stabilityai/sdxl-turbo", torch_dtype=torch.float16, variant="fp16").to("cuda")
    run("A_sdxl_turbo", pipe, dict(num_inference_steps=4, guidance_scale=0.0, height=512, width=512))
    del pipe; gc.collect(); torch.cuda.empty_cache()
except Exception as e: log("A FAILED", repr(e)[:300])
try:
    log("B: flux-schnell nf4")
    from diffusers import FluxPipeline, FluxTransformer2DModel, BitsAndBytesConfig
    q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16)
    tr = FluxTransformer2DModel.from_pretrained("black-forest-labs/FLUX.1-schnell", subfolder="transformer", quantization_config=q, torch_dtype=torch.float16)
    pipe = FluxPipeline.from_pretrained("black-forest-labs/FLUX.1-schnell", transformer=tr, torch_dtype=torch.float16)
    pipe.enable_model_cpu_offload()
    log("B loaded; GPU GB", round(torch.cuda.max_memory_allocated() / 1e9, 1))
    run("B_flux_schnell_nf4", pipe, dict(num_inference_steps=4, guidance_scale=0.0, height=512, width=512, max_sequence_length=256))
except Exception as e: log("B FAILED", repr(e)[:400])
log("DONE")
