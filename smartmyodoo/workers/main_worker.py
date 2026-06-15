import asyncio
import logging
import os
import signal
from typing import Dict, Any

from smartmyodoo.core.queue import JobQueue

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

QUEUES = ["shadow_ops", "knowledge_parsing", "external_sync"]


class WorkerDaemon:
    def __init__(self):
        self.queue = JobQueue()
        self.is_running = False
        self._tasks: list = []

    # ── Handlery per kolejka (S2.5: uczciwe — bez udawania pracy) ──

    async def _handle_shadow_ops(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Realne wykonanie: accept/reject propozycji shadow-mode.

        Pełne zastosowanie zmiany do Odoo nie jest jeszcze zaimplementowane — bez
        payloadu {proposal_id, action} zwracamy not_implemented (zero fałszywego 'completed').
        """
        payload = job.get("payload") or {}
        proposal_id = payload.get("proposal_id")
        action = payload.get("action")
        if not proposal_id or action not in ("accept", "reject"):
            return {
                "status": "not_implemented",
                "reason": "shadow_ops wymaga payload {proposal_id, action: accept|reject}; "
                "pełne wykonanie propozycji do Odoo nie jest zaimplementowane",
            }
        from smartmyodoo.mcp.shadow_mode import accept_proposal, reject_proposal

        fn = accept_proposal if action == "accept" else reject_proposal
        applied = await asyncio.to_thread(fn, proposal_id)
        return {
            "status": "completed" if applied else "failed",
            "proposal_id": proposal_id,
            "action": action,
            "applied": bool(applied),
        }

    async def _handle_not_implemented(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Kolejka bez realnej integracji — uczciwy status zamiast fałszywego 'completed'."""
        return {
            "status": "not_implemented",
            "reason": "integracja niezaimplementowana (placeholder)",
        }

    def _handler_for(self, queue_name: str):
        return {
            "shadow_ops": self._handle_shadow_ops,
            "knowledge_parsing": self._handle_not_implemented,  # MarkItDown TODO
            "external_sync": self._handle_not_implemented,  # Jira/Linear TODO
        }.get(queue_name)

    async def handle_job(self, job: Dict[str, Any], queue_name: str):
        job_id = job.get("id")
        job_type = job.get("type")
        logger.info(
            f"Processing job {job_id} of type {job_type} from queue {queue_name}"
        )

        await self.queue.update_job(job_id, status="processing")

        handler = self._handler_for(queue_name)
        if handler is None:
            logger.warning(f"Unknown queue: {queue_name}")
            await self.queue.update_job(
                job_id,
                status="failed",
                result={"error": f"Unknown queue {queue_name}"},
            )
            return

        try:
            result = await handler(job)
            # S2.5: not_implemented NIE jest 'completed' (koniec udawania)
            final_status = (
                "not_implemented"
                if result.get("status") == "not_implemented"
                else result.get("status", "completed")
            )
            await self.queue.update_job(job_id, status=final_status, result=result)
            logger.info(f"Job {job_id} -> {final_status}")
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}")
            await self.queue.update_job(
                job_id, status="failed", result={"error": str(e)}
            )

    async def run_queue(self, queue_name: str):
        logger.info(f"Listening on queue: {queue_name}")
        while self.is_running:
            try:
                # 1 second timeout to allow graceful shutdown checking
                job = await self.queue.dequeue(queue_name, timeout=1)
                if job:
                    await self.handle_job(job, queue_name)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error polling queue {queue_name}: {e}")
                await asyncio.sleep(1)

    async def start(self):
        self.is_running = True
        logger.info("Worker daemon starting...")

        # Start a polling task for each queue (zapamiętane do graceful shutdown)
        self._tasks = [asyncio.create_task(self.run_queue(q)) for q in QUEUES]
        await asyncio.gather(*self._tasks)

    async def stop(self):
        """Graceful shutdown (S2.5/S3.4): najpierw zatrzymaj i poczekaj na taski,
        DOPIERO potem zamknij Redis (koniec close() pod aktywnym BRPOP i podwójnego aclose)."""
        logger.info("Worker daemon stopping...")
        self.is_running = False
        for t in self._tasks:
            t.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks = []
        await self.queue.close()


worker = WorkerDaemon()


def handle_signal(sig, frame):
    logger.info("Received exit signal.")
    worker.is_running = False


async def main():
    loop = asyncio.get_running_loop()
    if os.name != "nt":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(worker.stop()))

    try:
        await worker.start()
    except asyncio.CancelledError:
        pass
    finally:
        await worker.stop()


if __name__ == "__main__":
    if os.name == "nt":
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)
    asyncio.run(main())
