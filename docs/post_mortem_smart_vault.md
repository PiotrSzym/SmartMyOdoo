# Post-Mortem: SmartMyVault Refactoring Sprint (Czerwiec 2026)

## 1. Wstęp
**Data:** 4 Czerwca 2026
**Zespoły/Role biorące udział:** /arch, /qa, /auditor, /dev
**Kontekst:** Aplikacja `SmartMyVault` (wewnętrzne narzędzie: `smart_vault`) borykała się z problemami ze stabilnością, w szczególności "wyciekiem" logiki kryptograficznej do warstwy API, co objawiało się m.in. tzw. "Ghost Keys" (zamrożone procesy serwera). Sprint miał na celu refaktoryzację architektury do standardu "Zero-Trust" oraz wdrożenie testów.

## 2. Lekcje Nauczone (Lessons Learned)

### 2.1 Co poszło źle przed refaktoryzacją?
- **Anti-Pattern `sys.exit()` w warstwie logicznej:** Główne funkcje kryptograficzne (np. `get_vault_key_from_pin`) wywoływały `sys.exit(1)` po napotkaniu błędu (np. zły klucz). W kontekście CLI było to akceptowalne, ale po podpięciu serwera REST API (Flask), zły PIN od użytkownika powodował bezwzględne zabicie całego procesu serwera, zamiast zwrócenia błędu HTTP 401/500.
- **Wyciek kryptograficzny do kontrolerów (Crypto Leakage):** Endpoint `/api/change-pin` próbował ręcznie generować sole i używać `Fernet` zamiast korzystać ze zhermetyzowanej logiki `vault.py`. W przypadku zmian algorytmu, musielibyśmy modyfikować to w dwóch miejscach (złamanie zasady DRY).
- **Złota rączka wyjątku (`except Exception: pass`):** Część błędów kryptograficznych lub błędów parsowania JSON była połykana, przez co awarie w `vault_data.enc` były niezwykle trudne do zdiagnozowania (aplikacja udawała, że skarbiec jest po prostu pusty).

### 2.2 Jakie kroki naprawcze zadziałały?
- **Silne typowanie (PEP 484):** Dodanie jasnych deklaracji typów na wejściu i wyjściu sprawiło, że błędy składniowe przestały występować.
- **Centralizacja do `VaultDecryptionError`:** Wszystkie nieoczekiwane zdarzenia ze skarbca rzucają dedykowany wyjątek `VaultDecryptionError`, co pozwala Flaskowi bezpiecznie odpowiedzieć kodem `500 Internal Server Error`, zamiast zamykać serwer i powodować wspomniane "Ghost Keys".
- **Dual-Auth Protocol:** Podział na PIN (dla automatów) i Master Password (do konfiguracji i zyskiwania dostępu Admina) ustabilizował warstwę API.
- **TDD (Test-Driven Development):** Dodanie testów `test_vault.py` uodporniło kod na przyszłe regresje, dając 100% pewności, że cykl logowania, dodawania, usuwania i zmiany PIN-u działa.

## 3. Zgodność z Best Practices (Wniosek /auditor)
Obecna architektura **JEST ZGODNA** z branżowymi standardami (Best Practices):
1. **Oddzielenie logiki biznesowej od warstwy prezentacji:** `vault.py` pozostaje agnostyczny co do Flaska i przeglądarki. `vault_server.py` skupia się tylko na HTTP.
2. **Zero-Trust Security:** Hasła nigdy nie logują się do konsoli. Zmienne ENV w `run_wrapped_command` żyją tylko w czasie trwania podprocesu.
3. **Fail-Fast & Graceful Degradation:** Błędne tokeny są wcześnie odrzucane i właściwie raportowane na granicy systemu.
4. **Git Hygiene:** Pliki konfiguracyjne `.enc` oraz `.cfg` są rygorystycznie oznaczane w `.gitignore`. Dodatkowo, ADR'y dokumentujące te architektoniczne wybory zostały zapisane w katalogu `docs/adr/`.

## 4. Rekomendacje i Następne Kroki (Next Steps)
- Przejście do fazy "Premium UI" w technologii ciemnego motywu, kafelków (Tailwind).
- Stworzenie "Pulpitu", który będzie konsumował oczyszczone endpointy API.
- Możliwość testowania "chaos engineering", ewentualne sprawdzenie odporności plików lokalnych na symultaniczny odczyt/zapis (File Locks w Pythonie), jeśli serwer byłby mocniej obciążony równoległymi requestami agentów.
