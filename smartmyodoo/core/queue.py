import os
import json
import uuid
import datetime
from typing import Any, Dict, Optional
import redis.asyncio as redis  # type: ignore[import-untyped]
from redis.exceptions import WatchError  # type: ignore[import-untyped]

# Wczytywanie z konfiguracji lub zmiennych środowiskowych
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
# S2.4: TTL meta-danych zadania (zapobiega wyciekowi pamięci `job:*`)
JOB_TTL_SECONDS = int(os.environ.get("JOB_TTL_SECONDS", str(24 * 3600)))

# Statusy terminalne — nie wolno ich regresować (np. failed -> completed)
_TERMINAL_STATUSES = {"failed", "completed", "not_implemented"}


class JobQueue:
    """
    Niezawodna kolejka zadań na Redisie (S2.4).

    Reliability:
    - reliable dequeue: BLMOVE queue -> processing (atomowe; brak utraty zadania przy crashu)
    - ack(): potwierdzenie po sukcesie usuwa z `processing`
    - requeue_stale(): redelivery nieack-niętych zadań po awarii workera
    - TTL na `job:*` (brak wycieku pamięci)
    - update_job(): atomowy WATCH/MULTI z ochroną przed regresją statusu terminalnego
    """

    def __init__(
        self,
        redis_url: str = REDIS_URL,
        redis_client: Optional[redis.Redis] = None,
        job_ttl: int = JOB_TTL_SECONDS,
    ):
        self.redis_url = redis_url
        self._redis = redis_client
        self.job_ttl = job_ttl

    async def get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    async def enqueue(
        self, queue_name: str, payload: Dict[str, Any], job_type: str = "generic"
    ) -> str:
        r = await self.get_redis()
        job_id = str(uuid.uuid4())
        job_data = {
            "id": job_id,
            "type": job_type,
            "payload": payload,
            "status": "pending",
            "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
            "result": None,
        }
        # Meta-dane zadania z TTL (S2.4 — koniec wycieku pamięci)
        await r.set(f"job:{job_id}", json.dumps(job_data), ex=self.job_ttl)
        await r.lpush(f"queue:{queue_name}", job_id)
        return job_id

    async def dequeue(
        self, queue_name: str, timeout: int = 0
    ) -> Optional[Dict[str, Any]]:
        """Reliable dequeue: atomowo przenosi job_id z kolejki do listy `processing`.

        Dzięki temu crash workera PRZED ack nie gubi zadania — odzyska je requeue_stale().
        """
        r = await self.get_redis()
        # BLMOVE (zamiast BRPOP): FIFO przez RIGHT-pop kolejki -> LEFT-push processing
        job_id = await r.blmove(
            f"queue:{queue_name}", f"processing:{queue_name}", timeout, "RIGHT", "LEFT"
        )
        if not job_id:
            return None
        job_data_str = await r.get(f"job:{job_id}")
        if job_data_str:
            return json.loads(job_data_str)
        # meta wygasło/zniknęło — nie zostawiaj sieroty w processing
        await r.lrem(f"processing:{queue_name}", 1, job_id)
        return None

    async def ack(self, queue_name: str, job_id: str) -> int:
        """Potwierdza zakończenie zadania — usuwa z listy `processing`."""
        r = await self.get_redis()
        return await r.lrem(f"processing:{queue_name}", 1, job_id)

    async def requeue_stale(self, queue_name: str) -> int:
        """Redelivery: nieack-nięte zadania z `processing` wracają do kolejki (po awarii)."""
        r = await self.get_redis()
        moved = 0
        while True:
            job_id = await r.lmove(
                f"processing:{queue_name}", f"queue:{queue_name}", "RIGHT", "LEFT"
            )
            if not job_id:
                break
            moved += 1
        return moved

    async def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        r = await self.get_redis()
        job_data_str = await r.get(f"job:{job_id}")
        if job_data_str:
            return json.loads(job_data_str)
        return None

    async def update_job(self, job_id: str, status: str, result: Any = None) -> bool:
        """Atomowa aktualizacja statusu (S2.4): WATCH/MULTI + ochrona przed regresją.

        Zwraca True gdy zaktualizowano; False gdy job nie istnieje lub próbowano
        zregresować status terminalny (np. nadpisać 'failed' przez 'completed').
        """
        r = await self.get_redis()
        key = f"job:{job_id}"
        async with r.pipeline() as pipe:
            for _ in range(10):  # optymistyczny retry przy kolizji WATCH
                try:
                    await pipe.watch(key)
                    cur = await pipe.get(key)
                    if cur is None:
                        await pipe.unwatch()
                        return False
                    data = json.loads(cur)
                    if (
                        data.get("status") in _TERMINAL_STATUSES
                        and data["status"] != status
                    ):
                        # ochrona: nie regresuj statusu terminalnego
                        await pipe.unwatch()
                        return False
                    data["status"] = status
                    data["result"] = result
                    ttl = await pipe.ttl(key)
                    pipe.multi()
                    if ttl and ttl > 0:
                        pipe.set(key, json.dumps(data), ex=ttl)
                    else:
                        pipe.set(key, json.dumps(data))
                    await pipe.execute()
                    return True
                except WatchError:
                    continue
        return False

    async def close(self):
        if self._redis:
            await self._redis.aclose()
