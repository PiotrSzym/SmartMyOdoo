"""FIX-02 S5.1: cache odpowiedzi LLM + backoff + parametry z konfiguracji."""

from smartmyodoo.swarm import llm_client as llm_mod
from smartmyodoo.core.llm_cache import InMemoryLLMCache, make_cache_key


class _Resp:
    choices: list = []
    usage = None


def test_cache_key_stable_and_input_sensitive():
    msgs = [{"role": "user", "content": "hi"}]
    k1 = make_cache_key("m", msgs)
    k2 = make_cache_key("m", msgs)
    assert k1 == k2  # deterministyczny
    assert k1 != make_cache_key("m2", msgs)  # czuły na model
    assert k1 != make_cache_key("m", [{"role": "user", "content": "yo"}])  # i na treść


def test_cache_hit_skips_litellm(monkeypatch):
    calls = {"n": 0}

    def counted(**kw):
        calls["n"] += 1
        return _Resp()

    monkeypatch.setattr(llm_mod.litellm, "completion", counted)
    cache = InMemoryLLMCache()
    client = llm_mod.OpenRouterClient(api_key="x", cache=cache)
    msgs = [{"role": "user", "content": "hi"}]

    r1 = client.chat(messages=msgs)  # miss → wywołuje LLM + zapis do cache
    r2 = client.chat(messages=msgs)  # hit → bez wywołania LLM
    assert r1 is not None and r2 is r1
    assert calls["n"] == 1  # tylko raz dotknięto LLM


def test_no_cache_calls_every_time(monkeypatch):
    calls = {"n": 0}

    def counted(**kw):
        calls["n"] += 1
        return _Resp()

    monkeypatch.setattr(llm_mod.litellm, "completion", counted)
    client = llm_mod.OpenRouterClient(api_key="x")  # cache=None
    msgs = [{"role": "user", "content": "hi"}]
    client.chat(messages=msgs)
    client.chat(messages=msgs)
    assert calls["n"] == 2  # brak cache → dwa wywołania


def test_backoff_invoked_between_retries(monkeypatch):
    sleeps = []
    monkeypatch.setattr(llm_mod.time, "sleep", lambda s: sleeps.append(s))

    calls = {"n": 0}

    def flaky(**kw):
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("503")
        return _Resp()

    monkeypatch.setattr(llm_mod.litellm, "completion", flaky)
    client = llm_mod.OpenRouterClient(api_key="x", num_retries=3, backoff_base=0.5)
    resp = client.chat(messages=[{"role": "user", "content": "hi"}])
    assert resp is not None
    # 2 nieudane próby → 2 backoffy: 0.5*2^0, 0.5*2^1
    assert sleeps == [0.5, 1.0]


def test_temperature_and_max_tokens_passed(monkeypatch):
    seen = {}

    def capture(**kw):
        seen.update(kw)
        return _Resp()

    monkeypatch.setattr(llm_mod.litellm, "completion", capture)
    client = llm_mod.OpenRouterClient(api_key="x", temperature=0.7, max_tokens=4096)
    client.chat(messages=[{"role": "user", "content": "hi"}])
    assert seen["temperature"] == 0.7
    assert seen["max_tokens"] == 4096
