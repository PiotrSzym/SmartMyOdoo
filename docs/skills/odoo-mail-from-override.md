---
name: odoo-mail-from-override
description: Wymuszenie dedykowanego adresu nadawcy (email_from) dla maili wychodzących z KONKRETNEGO modułu Odoo (np. Projekty) — przez Automated Action na mail.mail. Użyj gdy trzeba zmienić „z jakiego adresu" system wysyła powiadomienia danego modułu, zmienić alias/adres nadawcy, albo naprawić „ludzie kasują maile bo wyglądają jak automat". Odoo 16-19. Wymusza dopasowanie from_filter serwera i ochronę reply_to (wątkowanie).
---

# Odoo — override nadawcy maili per moduł (email_from)

Skill lokalny SmartMyOdoo. Jak sprawić, żeby maile z danego modułu (Projekty, itp.) wychodziły z WYBRANEGO adresu, a nie z prywatnego adresu pracownika / ignorowanego `powiadomienia@`.

## 🥇 Złote zasady (inaczej nie zadziała)
1. **`from_filter` MUSI pasować.** Serwer wychodzący (`ir.mail_server`) musi mieć docelowy adres w `from_filter`, inaczej Odoo (17/18 strict) **przepisze nagłówek From** na dozwolony adres, a Twój wyląduje w Reply-To. W kodzie przypnij serwer jawnie (`mail_server_id`).
2. **NIE ruszaj `reply_to`.** To on wątkuje odpowiedzi do rekordu (alias projektu / `catchall@`). Zmiana reply_to na skrzynkę, której Odoo NIE pobiera (brak fetchmail / nie catchall), = **odpowiedzi przepadają lub bounce**. Zmieniamy TYLKO `email_from`.
3. **Trigger `on_create`, nie `on_create_or_write`.** Unika ponownego odpalania przy zapisie `state` po wysłaniu.
4. **Chroń adresy szablonowe** (np. Field Service `serwis@`) — wyklucz je w domenie, inaczej nadpiszesz im nadawcę.
5. **`mail.mail` z `auto_delete=True` znika po wysłaniu** — do weryfikacji użyj testu create+cancel+unlink (niżej) LUB nagłówka From w odebranym mailu, nie licz na to że rekord zostanie.
6. **Powiadomienia do userów WEWNĘTRZNYCH idą in-app (Discuss), NIE mailem** → nie tworzą `mail.mail`. Testuj akcją, która realnie wysyła e-mail (np. **przypisanie zadania** — „Zostałeś przydzielony").

## Mechanizm (dlaczego mail.mail, a nie project.task)
Każdy mail — szablonowy i powiadomienie Discuss — przechodzi przez `mail.mail` z ustawionym `model` (np. `project.task`). To jedyny wspólny „choke point". Automat na `project.task` NIE złapie powiadomień Discuss. Natywne `mail.default.from` / `alias_domain.default_from` NIE wymuszają From dla powiadomień (From = adres autora). Dlatego: **base.automation na `mail.mail`, on_create, akcja Python przepisująca `email_from`.**

## Przepis — kroki w UI Odoo
1. Tryb developera: Ustawienia → Aktywuj tryb developera.
2. Ustawienia → Techniczne → Automatyzacja → **Reguły automatyzacji** → Nowa:
   - Model: `E-mail` (`mail.mail`)
   - Wyzwalacz: **Przy tworzeniu** (`on_create`)
   - Domena (Edytuj domenę), parametryzuj `<MODELE>`, `<ADRES>`, chronione adresy:
     ```
     [("model","in",["project.task","project.project"]),
      ("email_from","not ilike","<ADRES_DOCELOWY>"),
      ("email_from","not ilike","serwis@gourmetfoods.pl")]
     ```
3. Akcja → **Wykonaj kod Pythona**:
   ```python
   DEDICATED_FROM = "GF Projekty <gf-komunikacja@gourmetfoods.pl>"   # <-- zmień adres tutaj
   PROJECT_MODELS = ("project.task", "project.project")
   srv = env["ir.mail_server"].sudo().search(
       [("from_filter", "ilike", "gf-komunikacja@gourmetfoods.pl")], limit=1)  # <-- i tutaj
   for record in records:
       if record.model not in PROJECT_MODELS:
           continue
       ef = record.email_from or ""
       if "gf-komunikacja@gourmetfoods.pl" in ef or "serwis@gourmetfoods.pl" in ef:
           continue
       vals = {"email_from": DEDICATED_FROM}
       if srv:
           vals["mail_server_id"] = srv.id
       record.write(vals)
       # reply_to CELOWO nietknięte
   ```
4. Zapisz nieaktywną → test (niżej) → aktywuj.

## Test bezpieczny przez XML-RPC (create+cancel+unlink — NIC nie wysyła)
```python
# połączenie: patrz sekcja „Dostęp" niżej; K = execute_kw helper
PRIV = '"Test" <test.prywatny@firma.pl>'
nid = K('mail.mail','create',[{'model':'project.task','res_id':<ISTNIEJACY_ID>,
        'email_from':PRIV,'subject':'TEST','body_html':'<p>t</p>','state':'cancel'}])
a = K('mail.mail','read',[[nid]],{'fields':['email_from','reply_to','mail_server_id']})[0]
K('mail.mail','unlink',[[nid]])          # sprząta, state=cancel => nigdy nie wyszło
# oczekiwane: email_from = <ADRES_DOCELOWY>, reply_to = catchall@ (nietknięte)
```
Realny test: **przypisz zadanie do kogoś** → sprawdź nagłówek From w odebranym mailu.

## Zmiana adresu / cofnięcie aliasu (częsta operacja)
- **Zmiana nadawcy:** podmień adres w `DEDICATED_FROM` i w `search(from_filter ilike ...)` w kodzie akcji (`ir.actions.server.code`) + w domenie reguły. Upewnij się, że nowy adres ma serwer z `from_filter`.
- **Alias projektu (reply_to):** jeśli ktoś nada projektowi alias na nieodbieranej skrzynce → reply_to się przełącza i odpowiedzi giną. Cofnięcie: `mail.alias.write([alias_id],{'alias_name': False})` → reply_to wraca na `catchall@`. Sprawdź serwery przychodzące: `fetchmail.server` (które skrzynki Odoo realnie pobiera) — `catchall@` zwykle jest, dedykowany adres projektu zwykle NIE.

## 🔥 4 lekcje z produkcji (zmiana na NOWY adres, 2026-07-30)
Wpadki, na które łatwo wpaść przy przełączaniu nadawcy na inny adres:

1. **Reguła bywa ZARCHIWIZOWANA — nie „zniknęła".** Jeśli `base.automation` nie widać, czytaj z `active_test=False`:
   `search_read([[...]], {"context":{"active_test":False}})`. Reaktywacja = `write({"active": True})`. (U nas automat „Maile z projektów" był `active=false` → maile znów leciały z prywatnych adresów.)
2. **Zmiana na ISTNIEJĄCY adres ≠ na NOWY.** Gdy docelowy adres ma już `ir.mail_server` (jak `gf-komunikacja@`/`powiadomienia@`) — hasła nie potrzebujesz, tylko wskazujesz serwer. **Nowy adres** (np. `gf-projekty@`) wymaga serwera z pasującym `from_filter`, a ten — uwierzytelnienia: **skrzynka M365 + app password** (osobny serwer) ALBO **Send-As** dla istniejącego konta (dopisz adres do `from_filter` istniejącego serwera). Bez tego strict-From przepisze nagłówek. Sprawdź brak serwera: `search([[("from_filter","ilike","<adres>")]])`.
3. **`test_smtp_connection` = realny test logowania SMTP** (to co robi przycisk „Testuj połączenie"). Rób go PRZED podpięciem reguły: `execute_kw(...,"ir.mail_server","test_smtp_connection",[[srv_id]])` → sukces zwraca notyfikację „Test połączenia zakończony powodzeniem!", błąd rzuca Fault. Zielone = konto się uwierzytelnia.
4. **Test bezpieczny MUSI mieć realny `res_id`.** `mail.mail` _inherits_ `mail.message`, więc `create` z `model="project.task"` + `res_id=0` **crashuje** na `_get_reply_to` (`KeyError: False`). Użyj **tymczasowego `project.task`** (utwórz → test → `unlink` zadania i maila). Nie celuj w realne zadanie (mail.message zaśmieca jego chatter). Wzorzec: utwórz tmp task w dowolnym projekcie, mail `state="cancel"`, sprawdź `email_from`+`mail_server_id`, posprzątaj oba; przy niepowodzeniu od razu `active=False` (rollback).

## Dostęp (SmartMyOdoo → instancja klienta)
Klucz Odoo klienta jest w Skarbcu per workspace. Połączenie in-process (read/write przez ORM):
```python
from smartmyodoo.api_deps import get_auth_key
from smartmyodoo.vault import vault
from smartmyodoo.api_routers.chat import _inject_odoo_creds
from smartmyodoo.mcp.odoo_client import get_odoo_client
vk,_ = get_auth_key('<PIN>'); data = vault.get_secrets(vk)
_inject_odoo_creds(data, '<WORKSPACE_ID>')
c = get_odoo_client('default'); c.connect()
K = lambda m,meth,a,kw={}: c.models.execute_kw(c.db,c.uid,c.password,m,meth,a,kw)
```

## Konfiguracja live — Gourmet Foods (gfcrm.pl, Odoo 18)
- Instancja: `www.gfcrm.pl`, db `rwyszewski-gourmetfoods-main-15940999`, Odoo 18 Enterprise. Workspace SMO: `rwyszewski-gourmetfoods-main-15940999`, PIN 1111.
- Reguła: **„Maile z projektów"** = `base.automation` **id 90** (model `mail.mail`, `on_create`) → server action **id 1844**. Bywa zarchiwizowana → czytaj z `active_test=False`.
- **AKTUALNY nadawca (od 2026-07-30): `GF Projekty <gf-projekty@gourmetfoods.pl>`**, serwer `mail_server_id` = **id 14** („gf-projekty", `from_filter=gf-projekty@gourmetfoods.pl`, smtp.outlook.com:587 STARTTLS, `test_smtp_connection` OK). Serwer 14 to PRZEROBIONY dawny „Komunikacja GF" → `gf-komunikacja@` nie ma już własnego serwera.
- Historia: `powiadomienia@` → `gf-komunikacja@` (2026-07-29, ludzie kasowali „powiadomienia") → **`gf-projekty@` (2026-07-30)**.
- reply_to: **`catchall@gourmetfoods.pl`** (fetchmail działa). Alias `projekty@` (id 2658) **wyłączony** (`alias_name=False`).
- Chronione: `serwis@gourmetfoods.pl` (Field Service) — wykluczone w domenie.
- Zweryfikowane testem bezpiecznym (tmp `project.task`, mail `state=cancel`) → email_from `gf-projekty@`, mail_server_id 14, reply_to catchall@; rekordy skasowane.
