---
name: odoo-website-embed
description: Osadzenie SAMODZIELNEGO pliku HTML+JS (deck szkoleniowy, prezentacja, mini-SPA) w Odoo jako strona Website — bez custom modułu, tylko rekordy ORM (XML-RPC). Użyj gdy trzeba wystawić gotowy, offline'owy HTML pod adresem w Odoo (np. szkolenie, na które ktoś klika linkiem), z bramką „tylko dla zalogowanych". Omija pułapkę CSP na /web/content, która zabija inline JS/CSS. Odoo 16-18, działa na SaaS (.odoo.com).
---

# Odoo — osadzenie samodzielnego HTML+JS jako strona Website

Skill lokalny SmartMyOdoo. Jak wystawić gotowy, samodzielny plik HTML (własny `<head>`, inline `<style>` i `<script>`, silnik JS — np. deck szkoleniowy z wyszukiwarką/quizami) pod adresem w Odoo, tak żeby **działał w 100%** i był dostępny **tylko dla zalogowanych**.

## 🥇 Złote zasady (inaczej nie zadziała)
1. **NIE wklejaj do edytora Website (buildera).** Samodzielny dokument ma własny `<head>` i reset CSS (`*{margin:0}`, `body{...}`) — w treści strony Odoo koliduje z Bootstrap/motywem i wygląd się rozjeżdża (i deck, i strona).
2. **NIE serwuj surowo przez `/web/content/<att>` jako `src` iframe.** Odoo nakłada tam `Content-Security-Policy: default-src 'none'` + `X-Content-Type-Options: nosniff` → **blokuje inline `<script>` i `<style>`** → martwy, nieostylowany szkielet. (Zweryfikowane curl-em nagłówków.)
3. **Custom moduł-kontroler (`http.route`) — niewykonalny na SaaS.** `.odoo.com` = brak dostępu do filesystemu/gita (db-manager `Access Denied`). Odoo.sh wymagałby repo + build + deploy. Domyślnie zakładaj **tylko XML-RPC/ORM**.
4. **Wstrzykuj HTML do iframe przez property `.srcdoc` w JS — NIGDY jako atrybut `srcdoc` w arch XML.** Parser XML zwija `\n`→spacja w wartości atrybutu i **psuje `//`-komentarze JS** (cały skrypt w jednej linii → wszystko po `//` zjedzone). Property `.srcdoc = text` przekazuje bajty 1:1.

## Dlaczego to działa
- Strony **Website nie mają CSP** (zweryfikowane: homepage GF nie zwraca `Content-Security-Policy`).
- Dokument w `iframe.srcdoc` **dziedziczy CSP rodzica** (brak) → inline JS/CSS decka **działa**.
- Bajty decka trzymamy w `ir.attachment` (base64) — żadnej normalizacji XML/HTML po drodze.

## Wzorzec — 3 rekordy ORM

### 1. `ir.attachment` (plik decka, bramka „tylko zalogowani")
```python
att = env["ir.attachment"].create({
    "name": "Deck.html",
    "datas": base64.b64encode(open(path,"rb").read()).decode(),
    "mimetype": "text/html",
    "public": False,        # anon → 404; wymaga logowania
    "company_id": False,    # MULTI-COMPANY: czyta każdy zalogowany pracownik dowolnej firmy
    "res_model": False, "res_id": 0,
})
```
> Dostęp do załącznika egzekwuje `ir.attachment.check()` w Pythonie (NIE `ir.rule`). `res_model=False` → tylko ACL modelu (group_user ma read) → każdy zalogowany pracownik czyta; anon (public user, brak group_user) → odmowa. `company_id=False` = widoczny cross-company; ustawienie firmy odcięłoby pracowników innej spółki.

### 2. `ir.ui.view` (qweb) — standalone iframe + loader `fetch → srcdoc`
Arch to pełne `<html>` **bez** `t-call="website.layout"` (brak chrome/assetów Odoo → pełny ekran):
```xml
<t t-name="website.gf_deck">
<html lang="pl"><head><meta charset="utf-8"/>
<title>...</title>
<style>html,body{height:100%;margin:0;overflow:hidden;background:#0A0F1D}#deck{border:0;display:none;width:100vw;height:100vh}#msg{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;color:#9db0c7}</style>
</head><body>
<div id="msg">Ładowanie…</div>
<iframe id="deck" allowfullscreen="allowfullscreen"></iframe>
<script>
(function(){
  fetch('/web/content/__ATT__', {credentials:'same-origin'})
    .then(function(r){ if(!r.ok){throw new Error('HTTP '+r.status);} return r.text(); })
    .then(function(h){ var f=document.getElementById('deck'); f.srcdoc=h; f.style.display='block';
                       var m=document.getElementById('msg'); if(m){m.parentNode.removeChild(m);} })
    .catch(function(e){ var m=document.getElementById('msg'); if(m){m.textContent='Błąd: '+e.message;} });
})();
</script>
</body></html>
</t>
```
(`__ATT__` podmień na id załącznika. Loader JS nie zawiera `<`/`>`/`&`, więc jest bezpieczny jako tekst w arch XML.)

### 3. `website.page` (adres + bramka „zalogowani")
```python
env["website.page"].create({
    "name": "Szkolenie", "url": "/szkolenie-metodyka",
    "view_id": view_id, "website_id": WEBSITE_ID,
    "visibility": "connected",   # = „Signed In": tylko zalogowani (egzekwowane w PageController)
    "is_published": True, "website_indexed": False,
})
```

## Weryfikacja (po wdrożeniu — twardo)
Zaloguj sesję (`/web/session/authenticate`) i porównaj z anonimem:
- **anon** → strona `403`, `/web/content/<att>` `404` (bramka trzyma, nic nie wycieka)
- **zalogowany** → strona `200` **bez** nagłówka CSP; `/web/content/<att>` `200` z pełnymi bajtami decka (fetch zadziała)

## Utrzymanie
- **Podmiana treści** = nadpisanie `datas` (base64) TEGO SAMEGO załącznika → URL bez zmian.
- **Menu:** Website → Menu → nowa pozycja na `/<url>`.
- **eLearning (śledzenie ukończeń):** kurs + lekcja typu „Web Page" wskazująca ten sam URL. SCORM niepotrzebny, jeśli deck ma własny quiz.
- **Usunięcie:** skasuj `website.page`, `ir.ui.view`, `ir.attachment`.

## Live (baza testowa GF, Odoo 18+e)
`gourmetfoods-test-35412580`, website GF (id 2 / company 1): `/szkolenie-metodyka` — att 80408 / view 8502 / page 81. Deck: `Prezentacja_Metodyka_Projektowa_v4.html`. Instrukcja użytkownika: `...\03_Szkolenia\INSTRUKCJA_szkolenie_w_Odoo.md`.
