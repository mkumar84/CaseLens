"""Deterministic, offline fallback logic used only when ANTHROPIC_API_KEY is
not configured, so the seed data, gateway, and demo script are runnable and
testable without live API access. This is not a substitute for the real
Claude-backed reasoning in anthropic_client.py — see README for when each
path is used."""

SUSPICION_KEYWORDS = [
    "don't cc",
    "no secondary approval",
    "residential mail-forwarding",
    "unsaved number",
    "not on the company's approved software list",
    "expedite",
    "without the usual po matching",
    "no po number",
    "changed on file",
    "my cut goes to",
    "no prior business history",
    "retroactively",
    "dual sign-off",
    "four weeks before the first invoice",
]


def triage_flags(artifacts: list[dict]) -> list[dict]:
    flags = []
    for artifact in artifacts:
        content = artifact["raw_content"].lower()
        hits = [kw for kw in SUSPICION_KEYWORDS if kw in content]
        if hits:
            confidence = min(0.55 + 0.12 * len(hits), 0.97)
            rationale = (
                "Contains language consistent with irregular vendor-payment activity "
                f"({'; '.join(hits[:3])})."
            )
            flags.append(
                {
                    "artifact_id": artifact["id"],
                    "rationale": rationale,
                    "confidence_score": round(confidence, 2),
                }
            )
    return flags


def _summarize(raw_content: str, min_len: int = 40, max_len: int = 220) -> str:
    sentences = raw_content.split(". ")
    summary = ""
    for sentence in sentences:
        candidate = f"{summary} {sentence}".strip() if summary else sentence
        summary = candidate
        if len(summary) >= min_len or len(summary) >= max_len:
            break
    summary = summary[:max_len].strip()
    if not summary.endswith("."):
        summary += "."
    return summary


def timeline_entries(approved_artifacts: list[dict]) -> list[dict]:
    entries = []
    for artifact in approved_artifacts:
        metadata = artifact.get("metadata") or {}
        date = metadata.get("date", "2026-01-01")
        summary = _summarize(artifact["raw_content"])
        entries.append(
            {
                "artifact_id": artifact["artifact_id"],
                "event_timestamp": f"{date}T00:00:00+00:00",
                "event_description": summary,
            }
        )
    return entries


def report_claims(approved_artifacts: list[dict]) -> tuple[str, list[dict]]:
    claims = []
    lines = []
    for i, artifact in enumerate(approved_artifacts, start=1):
        claim_id = f"claim-{i}"
        text = artifact.get("rationale") or artifact["raw_content"].split(". ")[0]
        lines.append(f"{i}. {text} [{claim_id}]")
        claims.append({"claim_id": claim_id, "claim_text": text, "artifact_id": artifact["artifact_id"]})
    content = "Findings:\n" + "\n".join(lines)
    return content, claims
