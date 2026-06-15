"""S2.4 (dowód): kolejka jest NIEZAWODNA — redelivery, ack, TTL, brak regresji statusu.

PRZED naprawą: BRPOP atomowo usuwał job (crash przed update_job -> utrata); brak TTL (wyciek);
nieatomowy update_job (completed mógł nadpisać failed).
PO naprawie: BLMOVE->processing + ack + requeue_stale; TTL na job:*; atomowy update_job z guardem.
"""

import warnings

import fakeredis.aioredis
import pytest

from smartmyodoo.core.queue import JobQueue

pytestmark = pytest.mark.filterwarnings(
    "ignore::DeprecationWarning:redis",
    "ignore::DeprecationWarning:fakeredis",
)


def _queue():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    return JobQueue(redis_client=fake, job_ttl=3600)


async def test_crash_before_ack_redelivers_job():
    q = _queue()
    jid = await q.enqueue("ops", {"x": 1})

    # worker pobiera zadanie, ale PADA przed ack (brak q.ack)
    job = await q.dequeue("ops", timeout=1)
    assert job["id"] == jid

    # redelivery: nieack-nięte wraca do kolejki — zadanie NIE zginęło
    moved = await q.requeue_stale("ops")
    assert moved == 1
    again = await q.dequeue("ops", timeout=1)
    assert again["id"] == jid
    await q.close()


async def test_ack_prevents_redelivery():
    q = _queue()
    jid = await q.enqueue("ops", {"x": 1})
    await q.dequeue("ops", timeout=1)
    await q.ack("ops", jid)  # potwierdzone

    moved = await q.requeue_stale("ops")
    assert moved == 0  # nic do ponownego dostarczenia
    await q.close()


async def test_job_has_ttl():
    q = _queue()
    jid = await q.enqueue("ops", {"x": 1})
    r = await q.get_redis()
    ttl = await r.ttl(f"job:{jid}")
    assert ttl > 0  # PRZED: brak TTL (-1) -> wyciek pamięci
    await q.close()


async def test_update_job_no_status_regression():
    q = _queue()
    jid = await q.enqueue("ops", {"x": 1})

    assert await q.update_job(jid, "failed", {"err": "boom"}) is True
    # próba regresji: failed -> completed musi zostać ODRZUCONA
    assert await q.update_job(jid, "completed", {"ok": True}) is False

    st = await q.get_status(jid)
    assert st["status"] == "failed"  # status terminalny zachowany
    await q.close()
