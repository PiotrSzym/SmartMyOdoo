"""
LLM Client Factory dla SmartMyOdoo Swarm.
Obsługuje komunikację z OpenRouter API.
Wzorzec: Fallback — brak klucza API = None → Dispatcher używa heurystyk.
"""

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "meta-llama/llama-3.1-8b-instruct"


class OpenRouterClient:
    """Klient HTTP do komunikacji z OpenRouter API."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        self.api_key = api_key
        self.model = model

    def chat(self, prompt: str) -> str:
        """
        Wysyła prompt do OpenRouter i zwraca surowy tekst odpowiedzi.
        W przypadku błędu zwraca pusty string (Dispatcher fallback na H).
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "SmartMyOdoo Agent",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 100,
            "temperature": 0.1,
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(
                    OPENROUTER_API_URL, headers=headers, json=payload
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"[LLM] Błąd komunikacji z OpenRouter: {e}")
            return ""


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
