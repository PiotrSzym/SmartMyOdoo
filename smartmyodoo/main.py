import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from smartmyodoo.core.log_config import setup_logging

# Inicjalizacja konfiguracji logowania przed startem aplikacji
setup_logging()

app = FastAPI(title="SmartMyOdoo API")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Logujemy pełny wyjątek w celach wewnętrznych - SecretFilter usunie hasła i tokeny z logów
    logging.getLogger("fastapi").error(
        f"Internal error on {request.url}: {exc}", exc_info=True
    )

    # Do klienta zwracamy bezpieczny generyczny komunikat (Zero Trust)
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


@app.get("/")
def read_root():
    return {"status": "ok"}
