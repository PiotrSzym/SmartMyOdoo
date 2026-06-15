import warnings

import pytest
import pytest_asyncio
import fakeredis.aioredis
from smartmyodoo.core.queue import JobQueue

# fakeredis internally passes deprecated args (retry_on_timeout, lib_name, lib_version)
# to redis-py >=7.x. These are upstream issues, not ours.
# Ref: https://github.com/cunla/fakeredis-py/issues
pytestmark = pytest.mark.filterwarnings(
    "ignore::DeprecationWarning:redis",
    "ignore::DeprecationWarning:fakeredis",
)


@pytest_asyncio.fixture
async def mock_queue():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        fake_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    queue = JobQueue(redis_client=fake_client)
    yield queue
    await queue.close()


@pytest.mark.asyncio
async def test_enqueue_dequeue(mock_queue: JobQueue):
    # Enqueue
    payload = {"data": "test_123"}
    job_id = await mock_queue.enqueue("test_queue", payload, job_type="test_job")

    assert job_id is not None

    # Check status
    status = await mock_queue.get_status(job_id)
    assert status is not None
    assert status["id"] == job_id
    assert status["status"] == "pending"
    assert status["payload"] == payload

    # Dequeue
    job = await mock_queue.dequeue("test_queue", timeout=1)
    assert job is not None
    assert job["id"] == job_id
    assert job["type"] == "test_job"


@pytest.mark.asyncio
async def test_update_job(mock_queue: JobQueue):
    job_id = await mock_queue.enqueue("test_queue", {"test": "data"}, "test_job")

    # Zmiana statusu
    await mock_queue.update_job(job_id, status="completed", result={"success": True})

    status = await mock_queue.get_status(job_id)
    assert status is not None
    assert status["status"] == "completed"
    assert status["result"] == {"success": True}


@pytest.mark.asyncio
async def test_dequeue_timeout(mock_queue: JobQueue):
    # Pusta kolejka
    job = await mock_queue.dequeue("empty_queue", timeout=1)
    assert job is None
