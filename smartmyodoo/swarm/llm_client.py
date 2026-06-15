"""
LLM Client Factory dla SmartMyOdoo Swarm.
Obsługuje komunikację z modelami (domyślnie OpenRouter) za pomocą litellm.
Wzorzec: Fallback — brak klucza API = None → Dispatcher używa heurystyk.
"""

import logging
from typing import Optional, List, Dict, Any

import litellm

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "openrouter/meta-llama/llama-3.1-8b-instruct"


class OpenRouterClient:
    """Klient LLM wykorzystujący litellm do komunikacji (domyślnie OpenRouter)."""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        governor: Optional[Any] = None,
        fallback_model: Optional[str] = None,
        num_retries: int = 2,
    ):
        self.api_key = api_key
        self.model = model
        # S2.2: TokenGovernor podłączony — realna kontrola kosztów (pre-flight + record usage)
        self.governor = governor
        # K5: odporność — retry + fallback na tańszy/zapasowy model
        self.fallback_model = fallback_model
        self.num_retries = num_retries
        # Dodatkowe headery
        litellm.headers = {
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "SmartMyOdoo Agent",
        }  # type: ignore

    def _preflight(self) -> None:
        """Hard-block: jeśli budżet wyczerpany, blokujemy wywołanie LLM ZANIM je wyślemy."""
        if self.governor and not self.governor.get_status().get("can_continue", True):
            raise PermissionError(
                "🚨 TOKEN GOVERNOR: budżet sesji wyczerpany — wywołania LLM zablokowane."
            )

    def _record_usage(self, response: Any) -> None:
        """Odczytuje realne zużycie z odpowiedzi i raportuje do governora (S2.2)."""
        if not self.governor or response is None:
            return
        usage = getattr(response, "usage", None)
        tokens = int(getattr(usage, "total_tokens", 0) or 0) if usage else 0
        try:
            cost = litellm.completion_cost(completion_response=response) or 0.0
        except Exception:
            cost = 0.0
        # może podnieść PermissionError przy przekroczeniu budżetu (hard-block)
        self.governor.record(tokens=tokens, cost=float(cost), model=self.model)

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Any:
        """
        Wysyła messages do LLM via litellm. Obsługuje tool calling.
        Zwraca pełny obiekt odpowiedzi litellm. W przypadku błędu zwraca None.
        """
        self._preflight()
        # K5: kolejka modeli do próby — primary, potem fallback
        models_to_try = [self.model]
        if self.fallback_model and self.fallback_model != self.model:
            models_to_try.append(self.fallback_model)

        response = None
        last_err: Optional[Exception] = None
        for mdl in models_to_try:
            for attempt in range(self.num_retries + 1):
                try:
                    kwargs = {
                        "model": mdl,
                        "messages": messages,
                        "temperature": 0.1,
                        "max_tokens": 1000,
                        "api_key": self.api_key,
                    }
                    if tools:
                        kwargs["tools"] = tools
                    response = litellm.completion(**kwargs)
                    break
                except Exception as e:  # noqa: BLE001 — retry/fallback na dowolnym błędzie LLM
                    last_err = e
                    logger.warning(
                        f"[LLM] próba {attempt + 1}/{self.num_retries + 1} dla '{mdl}' nieudana: {e}"
                    )
            if response is not None:
                break

        if response is None:
            logger.warning(f"[LLM] wszystkie próby/fallbacki nieudane: {last_err}")
            return None

        # poza try: ewentualny PermissionError (przekroczony budżet) ma się propagować
        self._record_usage(response)
        return response

    def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Any:
        """
        Wysyła messages do LLM via litellm w trybie strumieniowym.
        Obsługuje tool calling.
        Zwraca generator obiektów chunk. W przypadku błędu zwraca wygenerowany chunk błędu.
        """
        self._preflight()
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 1000,
                "api_key": self.api_key,
                "stream": True,
                "stream_options": {"include_usage": True},
            }
            if tools:
                kwargs["tools"] = tools

            response = litellm.completion(**kwargs)
            for chunk in response:
                yield chunk
        except Exception as e:
            logger.warning(f"[LLM] Błąd komunikacji z modelem (stream): {e}")

            class _ErrorDelta:
                content = f"Błąd serwera LLM: {str(e)}"
                tool_calls = None

            class _ErrorChoice:
                delta = _ErrorDelta()

            class _ErrorChunk:
                choices = [_ErrorChoice()]

            yield _ErrorChunk()


def create_client(
    api_key: Optional[str] = None, governor: Optional[Any] = None
) -> Optional[OpenRouterClient]:
    """
    Fabryka klienta LLM.
    Zwraca None jeśli brak klucza API (Dispatcher fallback na heurystyki).
    Domyślnie podłącza globalny TokenGovernor (S2.2 — realna kontrola kosztów).
    """
    if not api_key:
        logger.info("[LLM] Brak klucza OpenRouter — tryb heurystyczny (offline).")
        return None

    if governor is None:
        try:
            from smartmyodoo.mcp.token_governor import governor as _global_governor

            governor = _global_governor
        except Exception:
            governor = None

    logger.info("[LLM] Klucz OpenRouter wykryty — tryb LLM aktywny.")
    return OpenRouterClient(api_key=api_key, governor=governor)
