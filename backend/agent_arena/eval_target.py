"""Thin eval target for DeepEval — answers Agent Arena domain questions."""

from .elo import INITIAL_RATING, K_FACTOR, expected_score, update_ratings
from .redact import redact


def run_ai_app(user_input: str) -> str:
    q = user_input.lower().strip()

    if "initial" in q and "elo" in q:
        return (
            f"Agent Arena initializes every model at Elo {INITIAL_RATING:.0f}. "
            f"Ratings update with K-factor {K_FACTOR:.0f}."
        )

    if "k-factor" in q or "k factor" in q:
        return f"The Elo K-factor used by Agent Arena is {K_FACTOR:.0f}."

    if "expected score" in q or "win probability" in q:
        ea = expected_score(1200.0, 1200.0)
        return (
            f"When two models share the same rating, the expected score is {ea:.2f} "
            "(equal win probability)."
        )

    if "update" in q and "elo" in q:
        new_a, new_b = update_ratings(1200.0, 1200.0, 1.0)
        return (
            f"If model A beats model B at equal ratings, ratings become "
            f"A={new_a}, B={new_b}."
        )

    if "redact" in q or "secret" in q or "api key" in q:
        sample = redact("leak sk-abcdefghijklmnopqrstuvwxyz012345")
        return (
            "Battle artifacts are sanitized before storage or streaming. "
            f"Provider secrets are stripped; example output: {sample}."
        )

    if "judge" in q:
        return (
            "The default judge is host-owned Kimi-K3 on the operator Modal account. "
            "Users may override the judge per battle with any configured provider."
        )

    if "sandbox" in q:
        return (
            "Battles run in disposable Modal Sandboxes. Network egress is allowed, "
            "no provider secrets are mounted into the sandbox, and resources are capped "
            "with a default 600s timeout."
        )

    return (
        "Agent Arena is a multi-user platform where AI models compete in security, "
        "coding, and adversarial formats. Users add providers, create battles, watch "
        "live SSE streams, and track per-format Elo leaderboards."
    )
