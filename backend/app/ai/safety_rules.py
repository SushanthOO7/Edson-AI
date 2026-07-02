from dataclasses import dataclass


UNVERIFIED_COMPLETION_CLAIMS = (
    "issue resolved",
    "ticket closed",
    "device replaced",
    "access granted",
    "user confirmed",
    "completed successfully",
    "work completed",
    "ticket resolved",
)


@dataclass(frozen=True)
class SafetyResult:
    passed: bool
    unverified_claims: list[str]


class SafetyRules:
    @staticmethod
    def check_unverified_completion_claims(*, source_text: str, generated_text: str) -> SafetyResult:
        normalized_source = SafetyRules._normalize(source_text)
        normalized_generated = SafetyRules._normalize(generated_text)
        claims = [
            claim
            for claim in UNVERIFIED_COMPLETION_CLAIMS
            if claim in normalized_generated and claim not in normalized_source
        ]
        return SafetyResult(passed=not claims, unverified_claims=claims)

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.lower().split())
