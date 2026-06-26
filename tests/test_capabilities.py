"""SELFDOC-01: wiarygodny self-opis czatu (z rejestru, bez konfabulacji)."""

import re

from smartmyodoo.swarm.capabilities import (
    is_self_describe_query,
    build_capabilities,
    SKILL_DESC,
)
from smartmyodoo.swarm.skills.registry import SKILL_REGISTRY


def test_detects_self_describe_queries():
    for q in [
        "co potrafisz?",
        "co umiesz robić",
        "opowiedz o sobie",
        "jakie masz umiejętności",
        "kim jesteś",
        "do czego służysz",
        "what can you do?",
        "who are you",
    ]:
        assert is_self_describe_query(q), f"nie wykryto: {q!r}"


def test_ignores_normal_queries():
    for q in [
        "ile szans w crm",
        "edytuj nazwę zadania traktory",
        "pokaż projekty rmo",
        "dodaj kontakt ACME",
        "kto zmienił fakturę",
    ]:
        assert not is_self_describe_query(q), f"fałszywy pozytyw: {q!r}"


def test_build_includes_all_registered_skills():
    text = build_capabilities()
    for sn in SKILL_REGISTRY:
        _, name, _ = SKILL_DESC.get(sn.value, ("", sn.value, ""))
        assert name in text, f"brak realnego skilla w opisie: {name}"


def test_build_grounded_no_invented_skill():
    """Anty-konfabulacja (D4): opis nie zawiera wymyślonych zdolności."""
    text = build_capabilities()
    assert "Quantum" not in text and "Wizard" not in text
    # liczba wypunktowanych eksperów == liczba realnie zarejestrowanych skili
    experts_block = text.split("### 🧩 Moi eksperci")[1].split("###")[0]
    bullets = re.findall(r"^- ", experts_block, re.MULTILINE)
    assert len(bullets) == len(SKILL_REGISTRY)


def test_build_has_safety_and_write_info():
    text = build_capabilities()
    low = text.lower()
    assert "shadow mode" in low and "pii" in low
    assert "🔴" in text and "🟢" in text  # tryb zapisu/odczytu
    assert "zapisywać" in low  # informuje, że potrafi pisać (w 🔴+PIN)
