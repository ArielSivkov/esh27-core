"""Feature plugins.

Each feature is one module `bhm/features/<name>.py` that defines:

    def make_router(node) -> fastapi.APIRouter
        All routes must start with /api/<name>/ (or /api/<name>).
        Use `node.con` for the database (one SQLite connection per thread).
    NAV = {"label": "עברית", "href": "#/<name>"}   # optional: adds a top-nav link
    (optional) a web module at web/features/<name>.js, loaded automatically.

A web module registers its pages with the core app:

    BHM.register('<name>', async (parts) => { BHM.$app.innerHTML = ... })
    // parts = the hash split on '/', e.g. #/<name>/x  ->  ['<name>', 'x']

BHM also exposes: api(path, opts), post({kind, ref, target, body}), esc(s),
enc(s), postHTML(event), wirePosts(root, reload), META, $app, he(category).

A feature must not edit core files (api.py, ledger.py, db.py, library.py,
bundle.py, web/app.js, web/index.html, web/style.css). New tables are created
by the feature itself with CREATE TABLE IF NOT EXISTS, prefixed <name>_.
"""
from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from pathlib import Path

WEB_FEATURES = Path(__file__).resolve().parent.parent.parent / "web" / "features"


@dataclass
class Feature:
    name: str
    module: object
    nav: dict | None
    js: str | None


def load_features() -> list[Feature]:
    out = []
    for m in sorted(pkgutil.iter_modules(__path__), key=lambda m: m.name):
        if m.name.startswith("_"):
            continue
        mod = importlib.import_module(f"{__name__}.{m.name}")
        if not hasattr(mod, "make_router"):
            continue
        js = f"/static/features/{m.name}.js" if (WEB_FEATURES / f"{m.name}.js").exists() else None
        out.append(Feature(m.name, mod, getattr(mod, "NAV", None), js))
    return out
