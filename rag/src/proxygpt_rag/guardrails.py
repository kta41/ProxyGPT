from __future__ import annotations

import re


MAX_QUESTION_CHARS = 8_000

_SENSITIVE_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16})\b"),
    re.compile(r"(?i)\b(?:api[_ -]?key|password|secret|token)\s*[:=]\s*\S+"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
)
_CITATION_PATTERN = re.compile(r"\[([^\]\r\n]+#chunk-\d{4})\]")


class GuardrailViolation(ValueError):
    pass


def validate_question(question: str) -> str:
    normalized = question.strip()
    if not normalized:
        raise ValueError("Question must not be empty.")
    if len(normalized) > MAX_QUESTION_CHARS:
        raise GuardrailViolation(
            f"Question exceeds the {MAX_QUESTION_CHARS}-character safety limit."
        )
    if _contains_sensitive_data(normalized):
        raise GuardrailViolation(
            "Question rejected by the sensitive-data guardrail; remove credentials or personal data."
        )
    return normalized


def validate_answer(answer: str, allowed_citations: set[str]) -> str:
    normalized = answer.strip()
    if not normalized:
        raise RuntimeError("Generator returned an empty answer.")
    if _contains_sensitive_data(normalized):
        raise GuardrailViolation(
            "Response blocked by the sensitive-data guardrail."
        )

    for citation in _CITATION_PATTERN.findall(normalized):
        if citation not in allowed_citations:
            raise GuardrailViolation(
                "Response blocked because it contains a citation outside the retrieved evidence."
            )
    return normalized


def _contains_sensitive_data(value: str) -> bool:
    return any(pattern.search(value) for pattern in _SENSITIVE_PATTERNS)
