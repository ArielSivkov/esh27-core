"""מחלקת בתי הדין: טיוטות לפסקי הלכה.

The system never issues a psak. It manages *drafts* written by people or
produced with AI help, and records the review and signature of qualified
dayanim. A draft's status is computed from the ledger:

  draft         טיוטה: no valid dayan signature yet
  in_review     בעיון: at least one review note, not yet signed
  approved      אושר: approved by the required number of dayanim
  rejected      נדחה: a dayan rejected it

Every rendering of an unsigned draft carries the DRAFT_NOTICE. AI-assisted
drafts are flagged and require a human dayan signature like any other.
"""
from __future__ import annotations

import json

from .ledger import hidden, names, roles, row_to_event

DRAFT_NOTICE = "טיוטה בלבד. אין זה פסק הלכה ואין לנהוג על פיו עד שייחתם בידי דיין מוסמך."
AI_NOTICE = "טיוטה זו נכתבה בסיוע מודל ממוחשב. המודל אינו פוסק."
DEFAULT_REQUIRED_SIGNATURES = 1   # a beit din of three: set to 3


def draft_status(con, draft_id: str, required: int = DEFAULT_REQUIRED_SIGNATURES) -> dict:
    r = con.execute("SELECT * FROM events WHERE id=? AND kind='psak_draft'", (draft_id,)).fetchone()
    if not r:
        raise KeyError(draft_id)
    d = row_to_event(r)
    R = roles(con)
    N = names(con)
    reviews, sigs, ignored = [], [], []
    for x in con.execute("SELECT * FROM events WHERE target=? AND kind IN ('psak_review','psak_sign') ORDER BY ts, id", (draft_id,)):
        e = row_to_event(x)
        if e["kind"] == "psak_review":
            reviews.append({"by": N.get(e["author"], e["author"][:12]), "note": e["body"].get("note", ""), "ts": e["ts"]})
        elif "dayan" in R.get(e["author"], set()):
            sigs.append({"by": N.get(e["author"], e["author"][:12]), "decision": e["body"]["decision"],
                         "note": e["body"].get("note", ""), "ts": e["ts"], "key": e["author"]})
        else:
            ignored.append(e["id"])   # signed by someone who is not a dayan: no effect
    approvals = {s["key"] for s in sigs if s["decision"] == "approved"}
    if any(s["decision"] == "rejected" for s in sigs):
        status = "rejected"
    elif len(approvals) >= required:
        status = "approved"
    elif reviews or sigs:
        status = "in_review"
    else:
        status = "draft"
    notices = []
    if status != "approved":
        notices.append(DRAFT_NOTICE)
    if d["body"].get("ai_generated"):
        notices.append(AI_NOTICE)
    return {"id": draft_id, "status": status, "required": required, "approvals": len(approvals),
            "draft": d, "author_name": N.get(d["author"], ""), "reviews": reviews, "signatures": sigs,
            "ignored_signatures": ignored, "hidden": draft_id in hidden(con), "notices": notices}


def list_drafts(con) -> list[dict]:
    ids = [r["id"] for r in con.execute("SELECT id FROM events WHERE kind='psak_draft' ORDER BY ts DESC")]
    H = hidden(con)
    return [draft_status(con, i) for i in ids if i not in H]
