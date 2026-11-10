"""המחלקה המשפטית: מדיניות רישוי ושער כניסה לכל טקסט שנכנס לספרייה.

Every text version that enters the library passes through `review()`.
Nothing is imported on a guess: a version whose license is missing,
"unknown", non-commercial or proprietary is rejected, and the rejection
is written to the legal log so a human can follow up.

Tiers
-----
A  "certain"      Public Domain / CC0. Free to copy, modify and redistribute.
B  "conditional"  CC-BY / CC-BY-SA. Allowed only while we keep the obligations
                  (attribution; share-alike for adaptations of the text itself).
                  Imported only when the operator enables tier B.
X  "rejected"     anything else (NC, ND, unknown, copyright, empty).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

TIER_A = "certain"
TIER_B = "conditional"
REJECT = "rejected"


@dataclass
class Decision:
    tier: str
    license: str
    reason: str
    obligations: list[str] = field(default_factory=list)

    @property
    def allowed(self) -> bool:
        return self.tier in (TIER_A, TIER_B)


def _norm(lic: str | None) -> str:
    return re.sub(r"\s+", " ", (lic or "").strip()).lower()


def classify(lic: str | None) -> Decision:
    raw = (lic or "").strip()
    n = _norm(lic)
    if not n or n in ("unknown", "none", "copyright", "all rights reserved"):
        return Decision(REJECT, raw, "רישיון לא ידוע או שמור: אין לייבא ללא הסכם")
    if "nc" in re.split(r"[-\s]", n) or "noncommercial" in n or "non-commercial" in n:
        return Decision(REJECT, raw, "רישיון לא-מסחרי (NC): מגביל את הפצת המערכת")
    if "nd" in re.split(r"[-\s]", n) or "noderiv" in n:
        return Decision(REJECT, raw, "רישיון ללא יצירות נגזרות (ND)")
    if n in ("public domain", "publicdomain", "pd") or n.startswith("public domain"):
        return Decision(TIER_A, raw, "נחלת הכלל")
    if n.startswith("cc0") or n == "cc-0":
        return Decision(TIER_A, raw, "CC0: ויתור על זכויות")
    if n.startswith("cc-by-sa") or n.startswith("cc by-sa") or n.startswith("cc by sa"):
        return Decision(TIER_B, raw, "CC-BY-SA",
                        ["ייחוס: שם הגרסה, המקור והרישיון בכל תצוגה", "שיתוף זהה: שינויים בטקסט עצמו יופצו תחת CC-BY-SA"])
    if n.startswith("cc-by") or n.startswith("cc by"):
        return Decision(TIER_B, raw, "CC-BY", ["ייחוס: שם הגרסה, המקור והרישיון בכל תצוגה"])
    return Decision(REJECT, raw, "רישיון שאינו מוכר למדיניות: נדרשת בדיקה משפטית ידנית")


MODERN_YEAR = 1950
YEAR = re.compile(r"(?<!\d)(1[89]\d\d|20\d\d)(?!\d)")

# Versions a human has checked and approved despite the automatic rules
# (title, versionTitle). Add entries only with a written justification.
MANUAL_ALLOW: dict[tuple[str, str], str] = {}


def _modern_year(meta: dict) -> int | None:
    years = [int(y) for f in ("versionTitle", "versionSource") for y in YEAR.findall(str(meta.get(f) or ""))]
    years = [y for y in years if y >= MODERN_YEAR]
    return max(years) if years else None


def review(version_meta: dict, allow_tier_b: bool = False) -> Decision:
    """Decide whether a text version may be imported."""
    d = classify(version_meta.get("license"))
    key = (version_meta.get("title"), version_meta.get("versionTitle"))
    if key in MANUAL_ALLOW:
        return Decision(TIER_A, d.license, f"אושר ידנית: {MANUAL_ALLOW[key]}")
    if d.tier == TIER_A:
        y = _modern_year(version_meta)
        if y:
            return Decision(REJECT, d.license,
                            f"מסומן נחלת הכלל אך נראה כיצירה מודרנית ({y}): דורש אימות ידני של המחלקה המשפטית")
    if d.tier == TIER_B and not allow_tier_b:
        return Decision(REJECT, d.license, f"{d.reason}: מותר בתנאים, אך שכבה B לא הופעלה", d.obligations)
    return d
