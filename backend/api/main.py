# backend/api/main.py
"""
ASGI entrypoint for the esh27-core FastAPI application.

- Initializes FastAPI app
- Mounts the router from backend.api.routes
- Adds CORS middleware (configurable via CORS_ORIGINS)
- Serves the repository openapi.yaml at /openapi.yaml
- If PyYAML is available, uses openapi.yaml to populate the FastAPI OpenAPI schema so /docs (Swagger UI)
  shows the provided spec. If PyYAML is missing, the app falls back to FastAPI's auto-generated OpenAPI.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Import and mount router
from backend.api import routes as api_routes

logger = logging.getLogger("esh27-core")
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

# Configure docs and openapi endpoints. We'll attempt to wire the YAML spec into FastAPI if possible.
DOCS_URL = "/docs"
REDOC_URL = "/redoc"
OPENAPI_JSON_URL = "/openapi.json"
OPENAPI_YAML_PATH = Path(__file__).resolve().parents[2] / "openapi.yaml"  # repo-root/openapi.yaml

app = FastAPI(
    title="esh27-core LLM Microservice",
    description="Core microservice for esh27 AI ecosystem",
    version="1.0.0",
    docs_url=DOCS_URL,
    redoc_url=REDOC_URL,
    openapi_url=OPENAPI_JSON_URL,
)

# CORS configuration
_cors_origins_env = os.getenv("CORS_ORIGINS", "*")  # comma-separated or '*' (not recommended for prod)
if _cors_origins_env.strip() == "*" or _cors_origins_env.strip() == "":
    origins: List[str] = ["*"]
else:
    origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_routes.router)


@app.get("/openapi.yaml", include_in_schema=False)
async def openapi_yaml():
    """
    Serve the repository openapi.yaml as-is. Useful for external tooling and for manual inspection.
    """
    if OPENAPI_YAML_PATH.exists():
        return FileResponse(path=str(OPENAPI_YAML_PATH), media_type="application/yaml")
    return JSONResponse(status_code=404, content={"detail": "openapi.yaml not found"})


@app.on_event("startup")
async def startup_event():
    """
    At startup, attempt to load openapi.yaml and use it as the app.openapi schema.
    This requires PyYAML to be installed. If PyYAML is unavailable, the app will use the
    auto-generated OpenAPI schema built from the FastAPI routes.
    """
    try:
        import yaml  # type: ignore
    except Exception:
        logger.warning(
            "PyYAML not available; using FastAPI-generated OpenAPI schema. "
            "To use repository openapi.yaml for /docs, install pyyaml."
        )
        return

    if not OPENAPI_YAML_PATH.exists():
        logger.warning("openapi.yaml not found at %s; using generated OpenAPI schema.", OPENAPI_YAML_PATH)
        return

    try:
        with OPENAPI_YAML_PATH.open("r", encoding="utf-8") as fh:
            loaded = yaml.safe_load(fh)
    except Exception as exc:
        logger.exception("Failed to parse openapi.yaml: %s", exc)
        return

    # Attach the loaded YAML as the app's OpenAPI schema.
    # FastAPI expects a dict for openapi schema; ensure it's a dict.
    if not isinstance(loaded, dict):
        logger.error("openapi.yaml did not parse to a dict; ignoring.")
        return

    # Set app.openapi to a function returning our loaded schema.
    def _custom_openapi():
        return loaded

    app.openapi = _custom_openapi  # type: ignore
    logger.info("Loaded openapi.yaml into FastAPI OpenAPI schema; /docs will use repository spec.")


# Root health endpoint (short-circuit)
@app.get("/", include_in_schema=False)
async def root():
    return {"status": "ok", "service": "esh27-core"}


if __name__ == "__main__":
    # Allow running locally with `python backend/api/main.py`
    import uvicorn

    port = int(os.getenv("PORT", 8080))
    uvicorn.run("backend.api.main:app", host="0.0.0.0", port=port, reload=False)
