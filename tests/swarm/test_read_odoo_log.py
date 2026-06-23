"""T2a/T2b (WIRE-01) — `read_odoo_log` hosting-aware (on-premise plik + odoo.sh SSH).

Kontrakt narzędzia NIE zmienia się: nazwa `read_odoo_log`, parametr `lines: int = 50`.
- on-premise: czyta `ODOO_LOG_PATH` (env) z fallbackiem na standardową ścieżkę Odoo;
  brak/niedostępny plik → JAWNY błąd z instrukcją konfiguracji (BEZ słowa „symulowane").
- odoo.sh: SSH `tail -n {lines}` log brancha; creds z vaultu; argv-list (nie shell=True);
  zero echa creds do logów/wyniku.
"""

import logging

import pytest

from smartmyodoo.swarm import tools
from smartmyodoo.swarm.tools import read_odoo_log


# --------------------------------------------------------------------------- #
# T2a — on-premise (plik)
# --------------------------------------------------------------------------- #


def test_reads_last_n_lines_from_env_path(tmp_path, monkeypatch):
    """on-premise: czyta `ODOO_LOG_PATH` i zwraca ostatnie `lines` linii."""
    log_file = tmp_path / "odoo-server.log"
    log_file.write_text("\n".join(f"line {i}" for i in range(1, 11)) + "\n", encoding="utf-8")

    monkeypatch.setenv("ODOO_LOG_PATH", str(log_file))
    # Wymuś gałąź on-premise (brak/nieistotny hosting odoo.sh).
    monkeypatch.delenv("ODOO_HOSTING", raising=False)

    out = read_odoo_log(lines=3)

    assert "line 8" in out and "line 9" in out and "line 10" in out
    assert "line 7" not in out
    assert "symulowane" not in out.lower()


def test_missing_path_returns_explicit_error_without_simulated_word(tmp_path, monkeypatch):
    """Brak konfiguracji/pliku → jawny błąd z instrukcją; NIGDY „symulowane"."""
    missing = tmp_path / "does-not-exist.log"
    monkeypatch.setenv("ODOO_LOG_PATH", str(missing))
    monkeypatch.delenv("ODOO_HOSTING", raising=False)

    out = read_odoo_log(lines=10)

    assert "symulowane" not in out.lower()
    # Komunikat ma instruować jak skonfigurować (env ODOO_LOG_PATH), ale wskazuje błąd.
    assert "ODOO_LOG_PATH" in out
    assert out.startswith("❌") or "nie" in out.lower()


def test_error_message_does_not_leak_secrets(tmp_path, monkeypatch):
    """Sekcja D: komunikat błędu nie ujawnia sekretów (tylko instrukcja konfiguracji)."""
    monkeypatch.delenv("ODOO_LOG_PATH", raising=False)
    monkeypatch.delenv("ODOO_HOSTING", raising=False)

    out = read_odoo_log(lines=5)

    assert "symulowane" not in out.lower()
    # Brak sekretów/PIN-ów/kluczy w treści.
    for leak in ("password", "api_key", "BEGIN RSA", "PRIVATE KEY", "master_pwd"):
        assert leak.lower() not in out.lower()


# --------------------------------------------------------------------------- #
# T2b — odoo.sh (SSH, mock)
# --------------------------------------------------------------------------- #


class _FakeCompleted:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def _patch_ssh_creds(monkeypatch, host="branch.odoo.sh", user="staging-123", key_path="/tmp/fake_key"):
    """Podstawia pobieranie SSH creds z vaultu (bez realnego skarbca)."""
    from smartmyodoo.swarm import vault_auth

    creds = vault_auth.SSHCredentials(host=host, user=user, key_path=key_path)
    monkeypatch.setattr(
        vault_auth.VaultAuthProvider, "get_ssh_credentials", staticmethod(lambda: creds)
    )
    return creds


def test_odoo_sh_calls_ssh_tail_with_argv(monkeypatch):
    """odoo.sh: wołane `ssh ... tail -n {lines} ...` jako argv-list (nie shell=True)."""
    monkeypatch.setenv("ODOO_HOSTING", "odoo_sh")
    _patch_ssh_creds(monkeypatch)

    captured = {}

    def fake_run(cmd, capture_output=True, text=True, timeout=None, **kwargs):
        captured["cmd"] = cmd
        captured["shell"] = kwargs.get("shell", False)
        return _FakeCompleted(stdout="2026-06-23 ERROR boom\n", returncode=0)

    monkeypatch.setattr(tools.subprocess, "run", fake_run)

    out = read_odoo_log(lines=42)

    assert captured["shell"] is False
    assert isinstance(captured["cmd"], list)  # argv-list, nie string
    assert captured["cmd"][0] == "ssh"
    # tail -n {lines} obecne w argv
    joined = " ".join(captured["cmd"])
    assert "tail" in joined and "-n" in joined and "42" in joined
    assert "boom" in out


def test_odoo_sh_missing_creds_returns_error(monkeypatch):
    """odoo.sh bez creds w vaultcie → jawny błąd, brak echa sekretów."""
    monkeypatch.setenv("ODOO_HOSTING", "odoo_sh")
    from smartmyodoo.swarm import vault_auth

    def boom():
        raise vault_auth.PipelineError("AUTH failed: Missing SSH secrets in Vault.")

    monkeypatch.setattr(
        vault_auth.VaultAuthProvider, "get_ssh_credentials", staticmethod(boom)
    )

    out = read_odoo_log(lines=10)
    assert "symulowane" not in out.lower()
    assert out.startswith("❌")


def test_odoo_sh_does_not_echo_credentials_to_logs(monkeypatch, caplog):
    """Sekcja D (wzór db_manager:36): klucz/host/user nie trafiają do logów ani wyniku."""
    monkeypatch.setenv("ODOO_HOSTING", "odoo_sh")
    creds = _patch_ssh_creds(
        monkeypatch, host="secret-host.odoo.sh", user="secret-user", key_path="/secret/key.pem"
    )

    def fake_run(cmd, capture_output=True, text=True, timeout=None, **kwargs):
        return _FakeCompleted(stdout="log line\n", returncode=0)

    monkeypatch.setattr(tools.subprocess, "run", fake_run)

    with caplog.at_level(logging.DEBUG):
        out = read_odoo_log(lines=5)

    log_text = " ".join(r.getMessage() for r in caplog.records)
    # Sekrety SSH nie mogą wyciec do logów.
    assert creds.key_path not in log_text
    assert creds.user not in log_text
    # Wynik narzędzia zawiera logi, nie creds.
    assert "log line" in out
    assert creds.key_path not in out
