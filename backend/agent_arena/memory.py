"""Appwrite-backed battle memory (D13): store winner insights + retrieval.

Collection: `memories`. Each doc stores a free-text insight plus structured
metadata (battle_id, format, model_id, skills, theory excerpt, timestamp) and a
tokenized keyword index for cheap substring/lexical retrieval without a vector DB.

Replaces the dormant mem0 push with an Appwrite-native store.
"""

from __future__ import annotations

import json
import re
import time

from appwrite.query import Query

_STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "of",
    "to",
    "in",
    "on",
    "for",
    "with",
    "by",
    "as",
    "at",
    "from",
    "into",
    "that",
    "this",
    "which",
    "was",
    "were",
    "is",
    "are",
    "be",
    "been",
    "have",
    "has",
    "had",
    "it",
    "its",
    "their",
    "they",
    "we",
    "you",
    "your",
    "our",
    "not",
    "no",
    "but",
    "do",
    "does",
    "did",
    "then",
    "than",
    "also",
    "each",
    "every",
    "after",
    "before",
    "between",
    "during",
    "will",
    "would",
    "should",
    "could",
    "can",
    "may",
}
_TOKEN_RE = re.compile(r"[a-z0-9]{3,}")


def _tokens(text: str) -> list[str]:
    words = _TOKEN_RE.findall((text or "").lower())
    return [w for w in words if w not in _STOPWORDS]


def remember(
    databases,
    database_id: str,
    *,
    insight: str,
    battle_id: str = "",
    model_id: str = "",
    format_name: str = "",
    chosen_skills: list[str] | None = None,
    theory: str = "",
    outcome: str = "",
    user_id: str = "",
) -> dict:
    """Persist one battle memory. Returns the created doc payload."""
    payload = {
        "user_id": user_id or "villain",
        "insight": insight[:2000],
        "tokens": _tokens(insight + " " + theory),
        "battle_id": battle_id,
        "model_id": model_id,
        "format": format_name,
        "chosen_skills": chosen_skills or [],
        "theory": (theory or "")[:500],
        "outcome": outcome,
        "created_at": time.time(),
    }
    doc = databases.create_document(database_id, "memories", "unique()", payload)
    return doc.data


def retrieve(
    databases,
    database_id: str,
    query: str,
    *,
    limit: int = 5,
    user_id: str = "",
    skills: list[str] | None = None,
) -> list[dict]:
    """Lexical retrieval: score memories by token overlap + skill + recency."""
    q_tokens = set(_tokens(query))
    skills = skills or []
    res = databases.list_documents(
        database_id,
        "memories",
        queries=[Query.limit(limit * 10 if limit else 50)],
    )
    scored: list[dict] = []
    for d in res.documents:
        data = d.data
        doc_tokens = set(data.get("tokens") or [])
        overlap = len(q_tokens & doc_tokens) if q_tokens else 0
        skill_bonus = 3 * len(set(skills) & set(data.get("chosen_skills") or []))
        recency = 1.0 + 0.05 * max(
            0, min(20, (time.time() - float(data.get("created_at") or 0)) / 86400)
        )
        score = overlap + skill_bonus
        if score <= 0:
            continue
        if user_id and data.get("user_id") and data["user_id"] != user_id:
            continue
        scored.append({"score": round(score / recency, 3), **data})
    scored.sort(key=lambda m: m["score"], reverse=True)
    return scored[:limit]


def forget(databases, database_id: str, older_than_days: int = 180) -> int:
    """Best-effort cleanup of stale memories. Returns number deleted."""
    cutoff = time.time() - older_than_days * 86400
    res = databases.list_documents(
        database_id,
        "memories",
        queries=[Query.limit(100)],
    )
    removed = 0
    for d in res.documents:
        if float(d.data.get("created_at") or 0) < cutoff:
            try:
                databases.delete_document(database_id, "memories", d.id)
                removed += 1
            except Exception:
                pass
    return removed


def dump(databases, database_id: str, limit: int = 20) -> list[dict]:
    """Recent memories as plain JSON (for stats/debug endpoints)."""
    res = databases.list_documents(
        database_id,
        "memories",
        queries=[Query.limit(limit)],
    )
    out = []
    for d in res.documents:
        data = dict(d.data)
        data.pop("tokens", None)
        data.pop("theory", None)
        out.append(data)
    return out


def encode_metadata(meta: dict) -> dict:
    """Coerce a JSON-safe metadata dict into Appwrite-friendly flat fields."""
    out: dict = {}
    for k, v in (meta or {}).items():
        if isinstance(v, (list, dict)):
            out[k] = json.dumps(v)
        else:
            out[k] = v
    return out


def novelty_score(
    databases,
    database_id: str,
    *,
    insight: str,
    skills: list[str] | None = None,
    theory: str = "",
) -> float:
    """E15 novelty fingerprint: 0.0 (duplicate) .. 1.0 (novel).

    Compares token overlap against recent memories, then applies a skill
    diversity bonus. Used to gate whether a memory is worth persisting and to
    surface fresh tactics to judges/agents.
    """
    q_tokens = set(_tokens(insight + " " + theory))
    if not q_tokens:
        return 1.0
    res = databases.list_documents(
        database_id,
        "memories",
        queries=[Query.limit(100)],
    )
    best_sim = 0.0
    seen_skills: set[str] = set()
    for d in res.documents:
        data = d.data
        doc_tokens = set(data.get("tokens") or [])
        if not doc_tokens:
            continue
        inter = len(q_tokens & doc_tokens)
        union = len(q_tokens | doc_tokens)
        best_sim = max(best_sim, inter / union)
        seen_skills.update(data.get("chosen_skills") or [])
    if not res.documents:
        return 1.0
    skills = skills or []
    diversity = (
        1.0
        if not seen_skills
        else min(
            1.0, 0.5 + 0.5 * len(set(skills) - seen_skills) / max(1, len(set(skills)))
        )
    )
    return round(max(0.0, 1.0 - best_sim) * diversity, 3)


def maybe_remember(
    databases, database_id: str, *, novelty_threshold: float = 0.25, **kwargs
) -> dict | None:
    """Persist a memory only if it clears the novelty threshold. Returns doc or None."""
    score = novelty_score(
        databases,
        database_id,
        insight=kwargs.get("insight", ""),
        skills=kwargs.get("chosen_skills"),
        theory=kwargs.get("theory", ""),
    )
    if score < novelty_threshold:
        return None
    return remember(databases, database_id, **kwargs)
