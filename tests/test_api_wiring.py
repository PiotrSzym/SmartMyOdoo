"""Strażnik wpięcia zależności bezpieczeństwa w api.py (regresja B1/B2 z /review).

/review wykrył, że PII (S1.1) i TokenGovernor (S2.2) były zaimplementowane, ale NIE wpięte
w produkcyjne ścieżki — testy jednostkowe przechodziły tylko bo wstrzykiwały zależność ręcznie.
Ten test pilnuje, by każdy produkcyjny SkillExecutor dostawał pii=, a każdy OpenRouterClient governor=.
"""

import re
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "smartmyodoo" / "api.py"


def _calls(source: str, name: str):
    """Zwraca treść argumentów każdego wywołania `name(...)` (z dopasowaniem nawiasów)."""
    calls = []
    for m in re.finditer(rf"\b{name}\(", source):
        i = m.end()
        depth = 1
        start = i
        while i < len(source) and depth:
            if source[i] == "(":
                depth += 1
            elif source[i] == ")":
                depth -= 1
            i += 1
        calls.append(source[start : i - 1])
    return calls


def test_every_skillexecutor_gets_pii():
    src = _SRC.read_text(encoding="utf-8")
    calls = _calls(src, "SkillExecutor")
    assert calls, "Nie znaleziono wywołań SkillExecutor w api.py"
    for c in calls:
        assert "pii=" in c, f"SkillExecutor bez pii= (regresja B1): {c[:80]}"


def test_every_openrouterclient_gets_governor():
    src = _SRC.read_text(encoding="utf-8")
    calls = _calls(src, "OpenRouterClient")
    assert calls, "Nie znaleziono wywołań OpenRouterClient w api.py"
    for c in calls:
        assert (
            "governor=" in c
        ), f"OpenRouterClient bez governor= (regresja B2): {c[:80]}"
