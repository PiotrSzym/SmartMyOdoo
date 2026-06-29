"""SH-LOG-01: parser wklejanych logów Odoo.sh / Odoo.

Po co: skill `ODOO_SH_LOGS` chwali się czytaniem tracebacków „bottom-up", ale dotąd
nie miał czym ich czytać — dostawał surowy tekst. Ten moduł zamienia wklejony log
w strukturę: pojedyncze wpisy (timestamp/pid/level/db/logger/message), zgrupowane
wieloliniowe tracebacki, root cause wyłuskany metodą bottom-up (ostatnia linia
wyjątku = realna przyczyna) oraz błędy HTTP 5xx/4xx z werkzeug.

Czysty moduł — bez I/O, bez zależności od FastAPI/ORM. Łatwy do testów i reużycia
przez warstwę czatu (ODOO_SH_LOGS) oraz endpoint `/api/logs/parse`.

Format linii logu Odoo (standard logging):
    2024-01-15 14:00:23,456 12345 ERROR dbname odoo.sql_db: bad query ...
    <timestamp>             <pid> <level> <db>  <logger>: <message>
Linie nie pasujące do nagłówka traktujemy jako kontynuację poprzedniego wpisu
(traceback, treść SQL, itp.).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Nagłówek wpisu logu Odoo. db = \S+ (bywa „?" gdy brak bazy), logger = [\w.]+.
_HEADER_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) "
    r"(?P<pid>\d+) "
    r"(?P<level>DEBUG|INFO|WARNING|ERROR|CRITICAL) "
    r"(?P<db>\S+) "
    r"(?P<logger>[\w.]+): "
    r"(?P<msg>.*)$"
)

# Werkzeug access-log w treści: "POST /web/... HTTP/1.1" 500 -
_HTTP_RE = re.compile(r'"(?P<method>[A-Z]+) (?P<path>\S+) HTTP/[\d.]+" (?P<status>\d{3})')

# Linie-łączniki w tracebackach łańcuchowych — pomijamy przy szukaniu root cause.
_TB_CONNECTORS = (
    "Traceback (most recent call last)",
    "During handling of the above exception",
    "The above exception was the direct cause",
)

_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


@dataclass
class HttpAccess:
    method: str
    path: str
    status: int

    def to_dict(self) -> Dict[str, Any]:
        return {"method": self.method, "path": self.path, "status": self.status}


@dataclass
class LogEntry:
    line_no: int
    timestamp: str
    pid: str
    level: str
    db: str
    logger: str
    message: str
    traceback: List[str] = field(default_factory=list)
    root_cause: Optional[str] = None
    http: Optional[HttpAccess] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "line_no": self.line_no,
            "timestamp": self.timestamp,
            "pid": self.pid,
            "level": self.level,
            "db": self.db,
            "logger": self.logger,
            "message": self.message,
            "traceback": self.traceback,
            "root_cause": self.root_cause,
            "http": self.http.to_dict() if self.http else None,
        }


@dataclass
class ParseResult:
    entries: List[LogEntry]
    unparsed: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {"entries": [e.to_dict() for e in self.entries], "summary": self.summary()}

    def summary(self) -> Dict[str, Any]:
        by_level: Dict[str, int] = {lvl: 0 for lvl in _LEVELS}
        for e in self.entries:
            by_level[e.level] = by_level.get(e.level, 0) + 1

        problems = [e for e in self.entries if e.level in ("ERROR", "CRITICAL")]
        http_errors = [
            e for e in self.entries if e.http and e.http.status >= 400
        ]

        # Root causes — unikalne, zachowując kolejność wystąpienia.
        seen: set[str] = set()
        root_causes: List[str] = []
        for e in problems:
            if e.root_cause and e.root_cause not in seen:
                seen.add(e.root_cause)
                root_causes.append(e.root_cause)

        timestamps = [e.timestamp for e in self.entries]
        return {
            "parsed_entries": len(self.entries),
            "unparsed_lines": len(self.unparsed),
            "by_level": by_level,
            "time_range": {
                "start": timestamps[0] if timestamps else None,
                "end": timestamps[-1] if timestamps else None,
            },
            "errors": [
                {
                    "line_no": e.line_no,
                    "timestamp": e.timestamp,
                    "level": e.level,
                    "logger": e.logger,
                    "message": e.message,
                    "root_cause": e.root_cause,
                }
                for e in problems
            ],
            "http_errors": [
                {**e.http.to_dict(), "line_no": e.line_no, "timestamp": e.timestamp}
                for e in http_errors
            ],
            "root_causes": root_causes,
        }


def extract_root_cause(traceback_lines: List[str]) -> Optional[str]:
    """Bottom-up: realna przyczyna = OSTATNIA linia wyjątku w tracebacku.

    W tracebacku Pythona linia wyjątku jest niewcięta (np. `ValueError: ...`),
    a ramki stosu są wcięte (`  File "...", line N`). Przy wyjątkach łańcuchowych
    interesuje nas ostatni (najgłębiej wyrzucony) — stąd bierzemy ostatniego kandydata.
    """
    candidates: List[str] = []
    for raw in traceback_lines:
        s = raw.rstrip()
        if not s.strip():
            continue
        if s[0].isspace():  # ramka stosu / kod
            continue
        if s.lstrip().startswith(_TB_CONNECTORS):
            continue
        candidates.append(s.strip())
    return candidates[-1] if candidates else None


def parse_odoo_sh_log(text: str) -> ParseResult:
    """Sparsuj wklejony tekst logów Odoo.sh do struktury `ParseResult`."""
    entries: List[LogEntry] = []
    unparsed: List[str] = []
    current: Optional[LogEntry] = None

    for idx, raw_line in enumerate(text.splitlines(), start=1):
        m = _HEADER_RE.match(raw_line)
        if m:
            if current is not None:
                _finalize(current)
            current = LogEntry(
                line_no=idx,
                timestamp=m.group("ts"),
                pid=m.group("pid"),
                level=m.group("level"),
                db=m.group("db"),
                logger=m.group("logger"),
                message=m.group("msg"),
            )
            http = _HTTP_RE.search(m.group("msg"))
            if http:
                current.http = HttpAccess(
                    method=http.group("method"),
                    path=http.group("path"),
                    status=int(http.group("status")),
                )
            entries.append(current)
        elif current is not None:
            # Kontynuacja bieżącego wpisu (traceback, SQL, stack frame).
            current.traceback.append(raw_line)
        elif raw_line.strip():
            # Tekst przed pierwszym nagłówkiem — nie wiemy, do czego należy.
            unparsed.append(raw_line)

    if current is not None:
        _finalize(current)

    return ParseResult(entries=entries, unparsed=unparsed)


def _finalize(entry: LogEntry) -> None:
    """Domknij wpis: wylicz root cause, jeśli ma traceback."""
    if entry.traceback:
        entry.root_cause = extract_root_cause(entry.traceback)
