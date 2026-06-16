"""FIX-02 S5.2: distributed lock (anty-TOCTOU) — równoległe approve = jedno przejście."""

import threading
import time

import pytest
from fastapi.testclient import TestClient

from smartmyodoo.api import app
from smartmyodoo.core.lock import DistributedLock, LockTimeout

HEADERS = {"Authorization": "Bearer 1111"}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_vault_env(tmp_path):
    import smartmyodoo.vault.vault as vault
    from smartmyodoo.core.database import engine
    from smartmyodoo.core import models as db_models

    # Inne testy (test_database.py) robią drop_all na współdzielonym engine — upewnij się,
    # że tabele istnieją niezależnie od kolejności kolekcji.
    db_models.Base.metadata.create_all(bind=engine)

    vault.PIN_SALT_FILE = str(tmp_path / "pin_salt.cfg")
    vault.MASTER_SALT_FILE = str(tmp_path / "master_salt.cfg")
    vault.PIN_KEY_FILE = str(tmp_path / "pin_key.enc")
    vault.MASTER_KEY_FILE = str(tmp_path / "master_key.enc")
    vault.VAULT_DATA_FILE = str(tmp_path / "vault_data.enc")
    vault.init_vault_core("1111", "master")
    yield


def _make_proposal(pid: str):
    from smartmyodoo.core.database import SessionLocal
    from smartmyodoo.core import models

    db = SessionLocal()
    try:
        db.add(
            models.Proposal(
                id=pid,
                workspace_id="default",
                odoo_model="res.partner",
                method="CREATE",
                values="{}",
                reason="test",
                status="pending",
            )
        )
        db.commit()
    finally:
        db.close()


def test_parallel_approve_single_transition(client):
    """8 równoległych approve tej samej propozycji → DOKŁADNIE jedno pending→approved."""
    _make_proposal("p-conc-s52")
    results: list = []

    def call():
        r = client.post("/api/proposals/p-conc-s52/approve", headers=HEADERS)
        results.append(r.json())

    threads = [threading.Thread(target=call) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    firsts = [r for r in results if r.get("already") is False]
    assert len(firsts) == 1, f"oczekiwano 1 przejścia, było {len(firsts)}"
    assert all(r["status"] == "approved" for r in results)
    assert len(results) == 8


def test_approve_idempotent_sequential(client):
    """Drugie approve tej samej propozycji = no-op (already=True) — gwarancja exactly-once."""
    _make_proposal("p-idem-s52")
    r1 = client.post("/api/proposals/p-idem-s52/approve", headers=HEADERS).json()
    r2 = client.post("/api/proposals/p-idem-s52/approve", headers=HEADERS).json()
    assert r1["already"] is False and r1["status"] == "approved"
    assert r2["already"] is True and r2["status"] == "approved"


def test_lock_mutual_exclusion():
    """Sekcje krytyczne nie przeplatają się (proces-lokalny fallback)."""
    lock = DistributedLock()  # brak redis_url → proces-lokalny
    events: list = []

    def worker(n):
        with lock.acquire("excl-key", timeout=2.0):
            events.append(f"in-{n}")
            time.sleep(0.05)
            events.append(f"out-{n}")

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # każde 'in-X' musi być natychmiast zamknięte przez 'out-X' (brak przeplotu)
    for i in range(0, len(events), 2):
        assert events[i].split("-")[1] == events[i + 1].split("-")[1]


def test_lock_timeout():
    """Zajęty lock → LockTimeout przy próbie wejścia z krótkim timeoutem."""
    lock = DistributedLock()
    with lock.acquire("busy-key", timeout=2.0):
        with pytest.raises(LockTimeout):
            with lock.acquire("busy-key", timeout=0.2):
                pass
