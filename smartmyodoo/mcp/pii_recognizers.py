"""FIX-02 S3.3: shim — recognizery PII przeniesione do kanonicznego smartmyodoo.security.pii.

Zachowane dla kompatybilności importów (mcp/server.py, stary kod). SSoT: security/pii/recognizers.py.
"""

from smartmyodoo.security.pii.recognizers import (  # noqa: F401
    NipRecognizer,
    PeselRecognizer,
    setup_analyzer,
)
