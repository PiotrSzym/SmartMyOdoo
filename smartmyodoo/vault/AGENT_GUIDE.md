# 🤖 Przewodnik dla Agentów AI: Integracja ze SmartMyVault

Ten dokument służy jako punkt odniesienia dla każdego agenta (Claude, GPT, Gemini itp.) wchodzącego w interakcję ze środowiskiem opartym na zabezpieczeniach `SmartMyVault`.

Został on zaprojektowany jako bezpieczna warstwa dostępu (Zero-Trust) zapobiegająca wyciekom kluczy do systemowych zmiennych środowiskowych, plików logów czy samej bazy wiedzy.

## 🔑 Kluczowe Wymagania (Nigdy nie łam tych zasad)
1. **NIGDY nie proś użytkownika o wklejenie tokenu/sekretu w czat.** 
2. Jeśli potrzebujesz klucza API, powiedz użytkownikowi: *"Proszę dodaj swój klucz do skarbca poleceniem `python vault.py add NAZWA_KLUCZA`, a następnie autoryzuj mój skrypt przez `python vault.py run twoj_skrypt.py`"*.
3. **Pamiętaj o architekturze Dual-Auth:** 
   - `PIN` jest przeznaczony dla zautomatyzowanych skryptów, poleceń konsolowych (CLI) i agentów.
   - `Master Password` przeznaczony jest tylko i wyłącznie do awaryjnego odzyskiwania dostępu oraz wprowadzania zmian administracyjnych (np. poprzez REST API).

## 🚀 Jak uruchamiać podprocesy i zautomatyzowane skrypty (ENV Flattener)
Zamiast pisać pliki `.env` w folderach projektu, używamy funkcjonalności "flattenera" środowiska, dostępnej bezpośrednio w poleceniu `run`:

```bash
python vault.py run <twoja_komenda>
```

Jeżeli skarbiec zawiera sekret `GITHUB` o wartości hasła `ghp_123`, to po odpaleniu `run`, do twojego skryptu docelowego trafią zmienne:
- `GITHUB_PASSWORD="ghp_123"`
- `GITHUB="ghp_123"` (skrót dla wygody)

Skarbiec najpierw poprosi o PIN, w locie zdeszyfruje pliki, stworzy "ulotne" środowisko ENV dla `<twoja_komenda>`, a zaraz po zakończeniu komendy całe środowisko wygaśnie w pamięci. Twoje hasło i tokeny nie zapiszą się w absolutnie żadnych systemowych plikach i historii bash/powershell.

## 🗑️ Kosz / Soft Delete (Polityka 3 dni)
Skarbiec obsługuje usuwanie w trybie "miękkim". Jeśli usuniesz klucz używając polecenia CLI `delete`, to zyska on sygnaturę czasową usunięcia `deleted_at`. Będzie przebywał w takim stanie (niewidoczny dla poleceń listowania `list` ani dołączenia przez `run`) przez równe **3 dni**.
Zostanie bezpowrotnie wykasowany na zawsze dopiero wtedy, gdy użytkownik lub agent spróbuje wykonać akcję na skarbcu np. `python vault.py list` po upływie tego czasu.

**Jak odzyskać usunięty klucz w ciągu 3 dni?**
```bash
python vault.py restore <nazwa_klucza>
```

## 🛠️ Zastosowanie dla deweloperów/agentów (Integracja z kodem Pythona)
Jeśli dopisujesz kod lub piszesz nowe testy korzystające bezpośrednio z `vault.py`, musisz zawsze oczekiwać bezpiecznego rzucania wyjątków (Exception) zamiast nagłych systemowych wyłączeń `sys.exit(1)`:

```python
import vault

try:
    vk = vault.get_vault_key_from_pin("1111", exit_on_fail=False)
    data = vault.load_vault(vk)
except vault.VaultDecryptionError as e:
    # Wystąpił błąd parsowania/dekryptażu struktury pliku
    print(f"Błąd skarbca: {e}")
except ValueError as e:
    # Błąd złego numeru PIN (lub problem niezainicjowanego skarbca)
    print(f"Błąd autoryzacji: {e}")
```

Zawsze używaj dedykowanych funkcji `load_vault(vk)`, `save_vault(vk, data)` lub `update_pin(vk, new_pin)` by zapewnić integralność kryptograficzną PBKDF2HMAC i Fernet, a nie odczytuj/nadpisuj `vault_data.enc` czy soli ręcznie.
