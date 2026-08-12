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
