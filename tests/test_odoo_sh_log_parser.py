"""SH-LOG-01: testy parsera logów Odoo.sh."""

from smartmyodoo.core.odoo_sh_log_parser import (
    extract_root_cause,
    parse_odoo_sh_log,
)

SAMPLE = """\
2024-01-15 14:00:01,100 12345 INFO myodoo-prod odoo.modules.loading: Modules loaded.
2024-01-15 14:00:23,456 12345 INFO myodoo-prod werkzeug: 1.2.3.4 - - [15/Jan/2024 14:00:23] "POST /web/dataset/call_kw HTTP/1.1" 500 - 12 0.045 0.200
2024-01-15 14:00:23,460 12345 ERROR myodoo-prod odoo.http: Exception during request handling.
Traceback (most recent call last):
  File "/odoo/addons/web/controllers/main.py", line 100, in call_kw
    result = func(*args)
KeyError: 'partner_id'

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/odoo/odoo/http.py", line 200, in dispatch
    raise ValidationError("Pole partner_id jest wymagane")
odoo.exceptions.ValidationError: Pole partner_id jest wymagane
2024-01-15 14:00:25,000 12345 WARNING myodoo-prod odoo.sql_db: bad query: SELECT ...
"""


def test_parses_headers_and_levels():
    res = parse_odoo_sh_log(SAMPLE)
    s = res.summary()
    assert s["parsed_entries"] == 4
    assert s["by_level"]["INFO"] == 2
    assert s["by_level"]["ERROR"] == 1
    assert s["by_level"]["WARNING"] == 1
    assert s["unparsed_lines"] == 0


def test_fields_extracted():
    res = parse_odoo_sh_log(SAMPLE)
    first = res.entries[0]
    assert first.timestamp == "2024-01-15 14:00:01,100"
    assert first.pid == "12345"
    assert first.db == "myodoo-prod"
    assert first.logger == "odoo.modules.loading"
    assert first.message == "Modules loaded."


def test_traceback_grouped_under_error_entry():
    res = parse_odoo_sh_log(SAMPLE)
    err = [e for e in res.entries if e.level == "ERROR"][0]
    # Wszystkie linie tracebacku (oba łańcuchy) trafiają do tego wpisu.
    assert any("KeyError: 'partner_id'" in ln for ln in err.traceback)
    assert any("ValidationError" in ln for ln in err.traceback)


def test_root_cause_is_bottom_up_last_exception():
    res = parse_odoo_sh_log(SAMPLE)
    err = [e for e in res.entries if e.level == "ERROR"][0]
    # Bottom-up: realna przyczyna = ostatni (najgłębszy) wyjątek łańcucha.
    assert err.root_cause == (
        "odoo.exceptions.ValidationError: Pole partner_id jest wymagane"
    )


def test_http_500_extracted():
    res = parse_odoo_sh_log(SAMPLE)
    s = res.summary()
    assert len(s["http_errors"]) == 1
    http = s["http_errors"][0]
    assert http["status"] == 500
    assert http["method"] == "POST"
    assert http["path"] == "/web/dataset/call_kw"


def test_summary_root_causes_deduped():
    res = parse_odoo_sh_log(SAMPLE)
    s = res.summary()
    assert s["root_causes"] == [
        "odoo.exceptions.ValidationError: Pole partner_id jest wymagane"
    ]
    assert s["time_range"]["start"] == "2024-01-15 14:00:01,100"
    assert s["time_range"]["end"] == "2024-01-15 14:00:25,000"


def test_extract_root_cause_ignores_stack_frames_and_connectors():
    lines = [
        "Traceback (most recent call last):",
        '  File "x.py", line 1, in f',
        "    do()",
        "ValueError: boom",
    ]
    assert extract_root_cause(lines) == "ValueError: boom"
    assert extract_root_cause(["  just a frame"]) is None


def test_text_before_first_header_is_unparsed():
    res = parse_odoo_sh_log("śmieci przed logiem\n2024-01-15 14:00:01,100 1 INFO db odoo: ok")
    assert res.unparsed == ["śmieci przed logiem"]
    assert res.summary()["parsed_entries"] == 1


def test_empty_input():
    res = parse_odoo_sh_log("")
    s = res.summary()
    assert s["parsed_entries"] == 0
    assert s["time_range"]["start"] is None
