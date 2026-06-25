"""TRUST-02 T2 (D2) + T3 regresja: deterministyczne utrzymanie zakresu projektu.

/qa LIVE TRUST-01 ujawnił, że scope_hint (podpowiedź dla modelu) gubił się, gdy
user nazwał zadanie ("opis price list" → zadanie 2671 z innego projektu SO276)
albo zmienił intencję ("dodaj test" → "2920"). enforce_scope dokleja project_id
DETERMINISTYCZNIE na warstwie narzędzia, z furtkami (global / inny projekt).

Ground-truth: RMO Henk Molenkamp = project_id 136 (2 zadania).
"""

from smartmyodoo.swarm.conversation_scope import ConversationScope

RMO = 136


def _scoped():
    s = ConversationScope()
    s.capture_domain("ws", "sess", [("project_id", "=", RMO)])
    return s


def _extract(domain):
    for c in domain:
        if isinstance(c, (list, tuple)) and c[0] == "project_id":
            return c[2]
    return None


# ── T2: doklejanie gdy zakres aktywny ──
def test_enforce_injects_project_id_on_task_search():
    s = _scoped()
    args = {"model": "project.task", "domain": [("name", "ilike", "price list")]}
    changed = s.enforce_scope("ws", "sess", "odoo_search_read", args, "opis zadania price list")
    assert changed is True
    assert _extract(args["domain"]) == RMO  # zawężone do RMO, nie globalnie


def test_enforce_injects_on_empty_domain():
    s = _scoped()
    args = {"model": "project.task", "domain": []}
    assert s.enforce_scope("ws", "sess", "odoo_search", args, "jakie są zadania")
    assert _extract(args["domain"]) == RMO


def test_enforce_handles_string_domain():
    s = _scoped()
    args = {"model": "project.task", "domain": "[('name','ilike','price list')]"}
    assert s.enforce_scope("ws", "sess", "odoo_search", args, "opis zadania price list")
    assert isinstance(args["domain"], str)
    assert "project_id" in args["domain"] and str(RMO) in args["domain"]


# ── T2: furtki (NIE narzucaj) ──
def test_enforce_skips_when_no_scope():
    s = ConversationScope()  # brak capture
    args = {"model": "project.task", "domain": []}
    assert s.enforce_scope("ws", "sess", "odoo_search", args, "zadania") is False
    assert _extract(args["domain"]) is None


def test_enforce_skips_when_user_asks_global():
    s = _scoped()
    args = {"model": "project.task", "domain": []}
    assert s.enforce_scope("ws", "sess", "odoo_search", args, "pokaż WSZYSTKIE zadania w bazie") is False
    assert _extract(args["domain"]) is None


def test_enforce_skips_when_user_names_other_project():
    s = _scoped()
    args = {"model": "project.task", "domain": []}
    assert s.enforce_scope("ws", "sess", "odoo_search", args, "zadania w projekcie SO276") is False
    assert _extract(args["domain"]) is None


def test_enforce_skips_when_domain_already_scoped():
    s = _scoped()
    args = {"model": "project.task", "domain": [("project_id", "=", 999)]}
    assert s.enforce_scope("ws", "sess", "odoo_search", args, "zadania") is False
    assert _extract(args["domain"]) == 999  # nie nadpisujemy jawnego wyboru


def test_enforce_skips_non_search_tool():
    s = _scoped()
    args = {"model": "project.task", "domain": []}
    # narzędzie zapisu (create/write) — enforce dotyczy tylko szukania
    assert s.enforce_scope("ws", "sess", "odoo_create", args, "dodaj zadanie") is False


def test_enforce_skips_non_task_model():
    s = _scoped()
    args = {"model": "res.partner", "domain": []}
    assert s.enforce_scope("ws", "sess", "odoo_search", args, "ile kontaktów") is False


# ── T3: 3 tryby awarii z /qa LIVE ──
def test_regression_followup_by_task_name_stays_in_project():
    """Tura 3 LIVE: 'opis zadania price list' NIE może wyjść do projektu 2671/SO276."""
    s = _scoped()
    args = {"model": "project.task", "domain": [("name", "ilike", "price list")]}
    s.enforce_scope("ws", "sess", "odoo_search_read", args, "jaki jest opis zadania price list")
    assert _extract(args["domain"]) == RMO


def test_regression_write_intent_inherits_scope_on_search():
    """Tura 4 LIVE: 'dodaj test do opisu zadania' — krok szukania zadania dziedziczy RMO,
    więc model nie widzi '2920', tylko zadania projektu."""
    s = _scoped()
    args = {"model": "project.task", "domain": []}
    changed = s.enforce_scope(
        "ws", "sess", "odoo_search", args, "dodaj do opisu zadania słowo test"
    )
    assert changed is True
    assert _extract(args["domain"]) == RMO
