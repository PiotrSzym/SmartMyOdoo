---
name: odoo-website-domain
description: Dodanie i podpięcie domeny pod witrynę Odoo Website (multi-website) — pełny łańcuch DNS (SEOHOST) → hosting/przekierowania (Cyberfolks/.htaccess lub Cloudflare) → SSL → panel domen Odoo → website.domain → web.base.url → Azure App Registration. Użyj gdy trzeba podpiąć nową domenę do witryny, zmienić domenę główną lub zdiagnozować "domena nie otwiera właściwej witryny". Odoo 16-18, SaaS i Odoo.sh. Skodyfikowane z modułu Wiedza GF (art. 3797/3552/2569/3554) + audytu live prod gfcrm.
---

# Odoo — dodawanie i podpinanie domen do witryn Website

Skill lokalny SmartMyOdoo. Proces podpięcia domeny do witryny Odoo od DNS po pocztę — krok po kroku,
z weryfikacją XML-RPC. Źródło: moduł **Wiedza** na prod GF (artykuły [3797] „Odoo – Konfiguracja domen",
[3552]/[2569] Cloudflare-przekierowania, [3554] „gdzie są domeny/VPS") + fakty zweryfikowane live 2026-08-06.

## 🥇 Złote zasady (inaczej nie zadziała)
1. **`xxxx.pl` i `xxxx.com.pl` konfiguruje się LUSTRZANIE.** Domena kanoniczna: dla `xxxx.com.pl` — **naga** (bez www); dla `xxxx.pl` — **z www**. Ta zasada przewija się przez KAŻDY krok (htaccess, panel Odoo, Website). „Odoo nie przyjmuje domeny dwuczłonowej" [3797].
2. **Multi-website = jedna baza, wiele hostów.** Prod GF ma **12 witryn** na jednej bazie — Odoo routuje po dopasowaniu hosta żądania do `website.domain`. Domena wpisana w ZŁĄ witrynę = obie strony chodzą krzyżowo. Zawsze najpierw `search_read` po `website`, potem `write` po **konkretnym id**.
3. **`website.domain` wpisuj Z prefiksem `https://`** — tak trzyma to prod (`'https://www.gfcrm.pl'`); goły host bywa przyczyną złych linków kanonicznych.
4. **`web.base.url` steruje WSZYSTKIMI linkami wychodzącymi** (maile, powiadomienia) — to domena GŁÓWNA bazy, nie per witryna. Przy `web.base.url.freeze=true` (tak jest na prod GF) parametr **nie aktualizuje się sam** przy logowaniu admina — zmiana domeny głównej wymaga ręcznej edycji obu parametrów. Nie zmieniaj go przy podpinaniu domeny pod witrynę POBOCZNĄ.
5. **SaaS ≠ Odoo.sh.** Art. [3797] każe dodać domenę w `odoo.sh/project/gourmetfoods`, ale gfcrm to SaaS `gourmetfoods.odoo.com` — krok wykonuje się w **panelu odoo.com** (Bazy danych → Domain names). Na Odoo.sh: zakładka Settings → Domains projektu.
6. **Bez wpisu w Azure App Registration nie zadziała poczta przychodząca** na nowej domenie [3797] — to najczęściej zapominany krok.

## Procedura krok po kroku

### 0. Rekonesans (zawsze przed zmianą)
```python
# XML-RPC, read-only: mapa witryn + domena główna
websites = env["website"].search_read([], ["id", "name", "domain", "company_id"], order="id")
base = env["ir.config_parameter"].search_read(
    [("key", "in", ["web.base.url", "web.base.url.freeze"])], ["key", "value"])
```
Ustal: (a) do której witryny (id!) podpinasz, (b) czy domena ma być główną bazy, czy tylko witrynową,
(c) typ domeny (`.pl` vs `.com.pl`) → strona kanoniczna wg zasady 1.

### 1. DNS — SEOHOST (domeny GF są w SeoHost [3554])
- naga domena → **CNAME** na `gourmetfoods.odoo.com` (uwaga: część paneli nie przyjmuje CNAME na rootcie — wtedy ALIAS/ANAME albo rekord A wg wskazań Odoo),
- `www.domena` → **rekord A** na IP Cyberfolks,
- `domena` (naga) → **rekord A** na IP Cyberfolks.

### 2. Hosting — Cyberfolks (VPS-y GF [3554])
Konsola admin → dodaj domenę nagą + subdomenę `www`. Potem Manager Plików → `Domains/<domena>/public_html/.htaccess` — przekierowania HTTP→HTTPS i na stronę kanoniczną:
```apache
RewriteEngine On
# dla xxxx.com.pl: www + HTTP → naga; dla xxxx.pl LUSTRZANIE (naga → www)
RewriteCond %{HTTP_HOST} ^www\.gfit\.com\.pl [NC,OR]
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://gfit.com.pl/$1 [L,R=301]
```

### 3. SSL — Let's Encrypt
Panel Cyberfolks → domeny → Certyfikaty SSL → dodaj Let's Encrypt **dla wariantu z www** (i nagiego, jeśli panel pozwala).

### 4. Panel domen Odoo
- **SaaS** (gfcrm): odoo.com → zarządzanie bazą → **Domain names** → dodaj domenę kanoniczną.
- **Odoo.sh**: projekt → Settings → Domains.
- Wpisuj: **z www** dla `xxxx.pl`, **bez www** dla `xxxx.com.pl` (zasada 1).

### 5. Witryna w Odoo (Website)
UI: Website → Konfiguracja → Ustawienia → Domena (na WŁAŚCIWEJ witrynie!) — albo pewniej przez API:
```python
env["website"].write([WEBSITE_ID], {"domain": "https://gfit.com.pl"})  # kanoniczna, z https://
```

### 6. `web.base.url` — TYLKO gdy zmieniasz domenę główną bazy
```python
env["ir.config_parameter"].set_param("web.base.url", "https://nowa-domena.pl")
# freeze=true → bez tego edytu nic się samo nie zmieni; freeze zostawiamy true (chroni przed nadpisaniem)
```

### 7. Azure App Registration
Dodaj wpis dla nowej domeny (redirect URI / dozwolone originy wg standardu IT GF) — inaczej **poczta przychodząca** na tej domenie nie działa [3797].

### Wariant B: domena ma TYLKO przekierowywać (bez treści) — Cloudflare [3552]
1. Cloudflare → Add site; 2. DNS: rekord **A `@` → 192.0.2.1** i **A `www` → 192.0.2.1**, tryb **Proxied**;
3. u rejestratora delegacja na nameserwery Cloudflare (inne per witryna!); 4. Rules → Page Rules: **2 reguły**
(www i bez www) → `Forwarding URL` → destination **z prefiksem `https://`**; 5. SSL/TLS → Edge Certificates → **Always Use HTTPS**.

## Weryfikacja (po wdrożeniu — twardo)
1. `search_read` po `website` — domena wisi na właściwym id; `web.base.url` bez zmian (lub zmieniony świadomie).
2. `curl -sI https://<domena>` → 200/303 z Odoo (nagłówek `Set-Cookie: session_id` lub `server: Odoo`); wariant niekanoniczny → **301** na kanoniczny.
3. Wejdź na `https://<domena>` — renderuje się WŁAŚCIWA witryna (nie homepage innej witryny z tej samej bazy!).
4. Test poczty przychodzącej na domenie (krok Azure).
5. DNS: `nslookup <domena>` i `nslookup www.<domena>` zgodne z krokiem 1.

## Pułapki (z życia GF)
- **Krzyżówka witryn:** `www.gfcrm.pl` i `gfit.com.pl` to TA SAMA baza — linki względne w treściach (np. lekcjach eLearning) otwierają się na domenie, z której przyszedł user; w treściach dawaj linki ABSOLUTNE (patrz `odoo-website-embed`).
- **Witryna bez domeny** (`domain=False`, np. prod id=1, id=11) jest osiągalna tylko przełącznikiem `/website/force/<id>` z backendu — to nie błąd, to witryna „niepodpięta".
- Propagacja DNS + cache Cloudflare potrafią maskować poprawną konfigurację — patrz art. [3553] (czyszczenie cache CF).

## Live (audyt prod `rwyszewski-gourmetfoods-main-15940999`, 2026-08-06)
12 witryn, m.in.: **2 GF** `https://www.gfcrm.pl` (główna; `web.base.url`, freeze=true), **4 HELPDESK_IT** `https://gfit.com.pl`, **6 GFKadry** `https://gfkadry.com.pl`, **10 Eventy** `https://eventy.gourmetfoods.pl`, **12 Saquella** `https://www.saquella.pl`; **BEZ domeny: 1 Napojesezonowe2024, 11 Gourmetfoods**.
Źródła w Wiedzy (prod): `knowledge.article` **3797** (procedura domen), **3552**/**2569** (Cloudflare redirect), **3554** (SeoHost/Cyberfolks/dilmah), 3553 (cache CF).
