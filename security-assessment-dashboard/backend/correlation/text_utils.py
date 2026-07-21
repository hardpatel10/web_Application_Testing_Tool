"""Tiny, dependency-free text helpers shared by rules that read NSE script output.

Several rule categories (TLS/SSH/SMB/HTTP) work by deterministically
scanning an ``Observation.detail`` string -- real text an NSE script wrote --
for known, fixed substrings (a weak cipher name, "message signing
disabled", etc.). This is still "deterministic correlation," not fabrication:
the rule never invents what the script said, it only decides whether the
script's own real output matches a fixed, documented condition.
"""


def contains_any(text: str | None, needles: tuple[str, ...]) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def matching(text: str | None, needles: tuple[str, ...]) -> list[str]:
    if not text:
        return []
    lowered = text.lower()
    return [needle for needle in needles if needle.lower() in lowered]
