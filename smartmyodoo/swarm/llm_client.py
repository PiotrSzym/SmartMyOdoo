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

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        self.api_key = api_key
        self.model = model
        # Dodatkowe headery
        litellm.headers = {
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "SmartMyOdoo Agent",
        }  # type: ignore

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Any:
        """
        Wysyła messages do LLM via litellm. Obsługuje tool calling.
        Zwraca pełny obiekt odpowiedzi litellm. W przypadku błędu zwraca None.
        """
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 1000,
                "api_key": self.api_key,
            }
            if tools:
                kwargs["tools"] = tools

            response = litellm.completion(**kwargs)
            return response
        except Exception as e:
            logger.warning(f"[LLM] Błąd komunikacji z modelem: {e}")
            return None

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
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 1000,
                "api_key": self.api_key,
                "stream": True,
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


def create_client(api_key: Optional[str] = None) -> Optional[OpenRouterClient]:
    """
    Fabryka klienta LLM.
    Zwraca None jeśli brak klucza API (Dispatcher fallback na heurystyki).
    """
    if not api_key:
        logger.info("[LLM] Brak klucza OpenRouter — tryb heurystyczny (offline).")
        return None

    logger.info("[LLM] Klucz OpenRouter wykryty — tryb LLM aktywny.")
    return OpenRouterClient(api_key=api_key)
