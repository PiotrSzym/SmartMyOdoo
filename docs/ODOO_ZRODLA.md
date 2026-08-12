# Odoo — gdzie sprawdzamy (hub źródeł)

Stałe, wiarygodne źródła do sprawdzania Odoo/Odoo.sh: dokumentacja, fora z reputacją, realne błędy i fixy. Podział na **poziomy wiarygodności** — im niżej, tym bardziej weryfikuj z górą. Podmieniaj wersję w URL (`/19.0/` ↔ `/17.0/` ↔ `/16.0/`).

## 1. Oficjalne (autorytet — zawsze najpierw)
- **Dokumentacja Odoo:** https://www.odoo.com/documentation/19.0/
  - Odoo.sh (indeks): https://www.odoo.com/documentation/19.0/administration/odoo_sh.html
  - Upgrade: https://www.odoo.com/documentation/19.0/administration/upgrade.html
  - Developer reference: https://www.odoo.com/documentation/19.0/developer.html
  - Skrypty migracyjne: https://www.odoo.com/documentation/19.0/developer/reference/upgrades/upgrade_scripts.html
- **Release notes (co zmienione per wersja):** https://www.odoo.com/odoo-19-release-notes
- **Apps Store (moduły, wersje, zależności):** https://apps.odoo.com
- **Runbot (stan testów Odoo core):** https://runbot.odoo.com

## 2. Q&A z reputacją (dobry rating odpowiedzi)
- **Oficjalne forum Odoo:** https://www.odoo.com/forum/help-1 — pytania z **akceptowanymi/upvote'owanymi** odpowiedziami. Szukaj po komunikacie błędu; patrz na ✓ i głosy.
- **Stack Overflow, tag [odoo]:** https://stackoverflow.com/questions/tagged/odoo — odpowiedzi **ważone reputacją**; sortuj po *Votes*, patrz na zielony ✓ (accepted) i wysokie głosy. Najlepsze na **konkretne błędy/kod**.
  - Bezpośrednio błędy: https://stackoverflow.com/questions/tagged/odoo?tab=Votes

## 3. Kod + realne błędy (traceback → fix)
- **Repo Odoo:** https://github.com/odoo/odoo — **Issues** (zgłoszone błędy) + **Pull Requests** (fixy). Wklej fragment tracebacku w search → często jest issue/PR z rozwiązaniem i numerem wersji.
  - Szukanie po błędzie: https://github.com/odoo/odoo/issues
- **OCA (Odoo Community Association):** https://github.com/OCA — wysokiej jakości moduły + wytyczne + wzorce/fixy.
- **OpenUpgrade (migracje między wersjami):** https://github.com/OCA/OpenUpgrade · https://oca.github.io/OpenUpgrade/
- **Enterprise (jeśli mamy dostęp):** https://github.com/odoo/enterprise (issues/kod modułów EE).

## KSeF (osobny priorytet — inna kolejność sprawdzania)
Dla KSeF sprawdzamy w tej kolejności: **Trilab + nasza wiedza → oficjalne MF → OCA/SO/Odoo.**

**A. Trilab — praktyka Odoo↔KSeF (sprawdzamy NAJPIERW):**
- Moduł `trilab_ksef`: https://apps.odoo.com/apps/modules/18.0/trilab_ksef (dep: Trilab Invoice / Enterprise)
- Blog/instrukcje: https://www.trilab.pl/blog · Odoo instrukcje: https://www.trilab.pl/en_US/blog/odoo-instrukcje-2
- KSeF 2.0: https://www.trilab.pl/en_US/blog/news-3/ksef-2-0-nadchodzi-75
- Strona/wsparcie: https://www.trilab.pl _(forum/support Trilab — jeśli masz bezpośredni URL forum, dopnę)_

**B. Nasza wiedza (wewnętrzna):**
- Baza wiedzy myodoo.pl (`knowledge.article`): m.in. art. 63 (instalacja księgowości Trilab), 88 (JPK_MAG Trilab).
- Lokalne zasoby: `trilab_ksef` 18.0 (dep Enterprise), `l10n_pl_edi`/KSeF w Community 19 (patrz pamięć `local-odoo-assets-map`).

**C. Oficjalne MF (autorytet dla standardu/API/prawa):**
- Portal KSeF: https://ksef.podatki.gov.pl · Krajowy System e-Faktur (KAS): https://www.gov.pl/web/kas/krajowy-system-e-faktur
- **API KSeF** (KAS): https://www.gov.pl/web/kas/api-krajowego-system-e-faktur
- Wsparcie dla integratorów (SDK Java/.Net, OpenAPI 3.0.4, endpointy): https://ksef.podatki.gov.pl/ksef-na-okres-obligatoryjny/wsparcie-dla-integratorow/
- Dokumentacja API 2.0 + struktura FA(3): https://ksef.podatki.gov.pl/wyjasnienia/publikacja-dokumentacji-api-ksef-20-oraz-struktury-logicznej-fa-3-30062025/
- **Środowiska API:** prod `https://api.ksef.mf.gov.pl` · demo `https://api-demo.ksef.mf.gov.pl` · test `https://api-test.ksef.mf.gov.pl`

**D. OCA / Odoo (best-practice PL):**
- OCA l10n-poland: https://github.com/OCA/l10n-poland (lokalizacja PL, w tym prace KSeF)
- Odoo docs — lokalizacja fiskalna Polska / `l10n_pl_edi` (pod Accounting → Fiscal localizations).
- Reszta: Stack Overflow [odoo] i github odoo/odoo jak w tier 2–3 wyżej.

## 4. Społeczność / tutoriale (przydatne, ale WERYFIKUJ z tier 1–3)
- **Cybrosys** (partner Odoo, dużo how-to): https://www.cybrosys.com/blog
- **Odoo Mates:** https://www.odoomates.tech
- **Reddit r/odoo:** https://www.reddit.com/r/odoo — dyskusje/opinie, jakość zmienna.
> Zasada: tier 4 = trop. Potwierdź w tier 1–3 zanim wdrożysz na prod.

## Jak szukać BŁĘDU (praktyka)
1. Weź **najgłębszy wyjątek** z tracebacku (bottom-up — skill `odoo-sh-logs`).
2. Wklej **klasę wyjątku + kluczową frazę** kolejno do: **GitHub `odoo/odoo`** (Issues + Code), potem **SO [odoo]** (sort Votes), potem **forum Odoo**.
3. Zawsze patrz na **WERSJĘ** (16/17/18/19) — rozwiązania bywają wersyjne.
4. Preferuj **accepted/upvoted** i oficjalne **PR-y**; społeczność (tier 4) tylko jako trop.

## Powiązane u nas
- Playbook Odoo.sh/GitHub: `docs/skills/odoo-devops-github.md`
- Diagnostyka logów: skill `odoo-sh-logs` + `scripts/odoo_sh_logs.py`
- Baza wiedzy myodoo.pl (wewnętrzna, `knowledge.article` — 112 art., READONLY przez API uid=42).
