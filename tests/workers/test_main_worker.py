"""S2.5 (dowód): handlery workera są UCZCIWE — realny shadow_ops, not_implemented zamiast fałszywego completed.

PRZED naprawą: każda kolejka oznaczała job jako 'completed' mimo zerowej pracy (placeholdery).
PO naprawie: shadow_ops wykonuje realny accept/reject; niezaimplementowane kolejki -> 'not_implemented'.
"""

import warnings

import fakeredis.aioredis
import pytest

from smartmyodoo.core.queue import JobQueue
from smartmyodoo.workers.main_worker import WorkerDaemon

pytestmark = pytest.mark.filterwarnings(
    "ignore::DeprecationWarning:redis",
    "ignore::DeprecationWarning:fakeredis",
)


def _worker():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    w = WorkerDaemon()
    w.queue = JobQueue(redis_client=fake)
    return w


async def test_shadow_ops_executes_real_accept(monkeypatch):
    import smartmyodoo.mcp.shadow_mode as sm

    monkeypatch.setattr(sm, "accept_proposal", lambda pid: True)

    w = _worker()
    jid = await w.queue.enqueue(
        "shadow_ops", {"proposal_id": "p1", "action": "accept"}, job_type="shadow"
    )
    job = await w.queue.get_status(jid)
    await w.handle_job(job, "shadow_ops")

    st = await w.queue.get_status(jid)
    assert st["status"] == "completed"
    assert st["result"]["applied"] is True
    await w.queue.close()


async def test_shadow_ops_without_payload_is_not_implemented():
    w = _worker()
    jid = await w.queue.enqueue("shadow_ops", {}, job_type="shadow")
    job = await w.queue.get_status(jid)
    await w.handle_job(job, "shadow_ops")

    st = await w.queue.get_status(jid)
    assert st["status"] == "not_implemented"  # nie 'completed'!
    await w.queue.close()


async def test_knowledge_parsing_marks_not_implemented():
    w = _worker()
    jid = await w.queue.enqueue("knowledge_parsing", {"doc": "x"})
    job = await w.queue.get_status(jid)
    await w.handle_job(job, "knowledge_parsing")

    st = await w.queue.get_status(jid)
    assert st["status"] == "not_implemented"  # koniec fałszywego 'completed'
    await w.queue.close()


async def test_unknown_queue_fails():
    w = _worker()
    jid = await w.queue.enqueue("nieznana", {"x": 1})
    job = await w.queue.get_status(jid)
    await w.handle_job(job, "nieznana")

    st = await w.queue.get_status(jid)
    assert st["status"] == "failed"
    await w.queue.close()


async def test_stop_is_graceful_without_tasks():
    w = _worker()
    await w.stop()  # brak tasków -> czyste zamknięcie, bez wyjątków
    assert w.is_running is False
