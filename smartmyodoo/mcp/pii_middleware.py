"""FIX-02 S3.3: shim — PiiMiddleware przeniesiony do kanonicznego smartmyodoo.security.pii.

Zachowane dla kompatybilności importów (api.py, mcp/server.py, testy). SSoT: security/pii/middleware.py.
"""

from smartmyodoo.security.pii.middleware import PiiMiddleware  # noqa: F401
