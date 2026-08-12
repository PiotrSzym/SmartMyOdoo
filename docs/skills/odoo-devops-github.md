# Skill: odoo-devops-github — pełny flow GitHub → Odoo.sh

> Wersjonowany mirror skilla `odoo-devops-github` (żywy skill: `.claude/skills/odoo-devops-github/SKILL.md` + `REFERENCE.md` — lokalne, bo `.claude/` jest gitignored). Ten plik trzyma wiedzę w gicie. Źródło: baza wiedzy myodoo.pl (art. 83/85/93/103/116/219/224) scalona z oficjalną dokumentacją Odoo.sh/GitHub (2026-08-12).

Powiązane narzędzie: `scripts/odoo_sh_logs.py` (pull logów Odoo.sh przez SSH). Logi/diagnostyka: skill `odoo-sh-logs`.

## Złote zasady
1. **Staging Isolation + Feature Branches.** `feature/*`|`fix/*` → PR (review) → merge do **staging** (test na neutralizowanej kopii proda) → promocja do **production**.
2. **Bump wersji w `__manifest__.py` OBOWIĄZKOWY** przy każdej zmianie modułu — inaczej Odoo.sh wgra kod, ale nie odpali update'u.
3. **Prod nie zostaje na złym kodzie** — auto-rollback do ostatniego udanego builda, gdy restart/update padnie (nie ratuje kodu „ładowalnego, lecz logicznie złego" → dlatego staging).

## HARD blokady
- **Nigdy `git push --force` na branch produkcyjny Odoo.sh** — prod ładuje istniejącą bazę na nowej rewizji; przepisanie historii = rozjazd schema↔kod, utrata commitów, zerwane statusy PR. Cofasz przez `git revert`.
- **Nie zmieniaj DNS** bez zgody (skill `odoo-website-domain`).
- **Nie testuj na produkcji** — Odoo shell/console auto-commituje.
- **Config ze staging NIE wraca do proda przy merge** — merge przenosi tylko kod; ustawienia odtwórz jako XML data / ręcznie.

## Kanoniczny flow
```
feature/fix ──PR──▶ staging ──promocja(drag&drop UI / merge)──▶ production
  dev lokalny      neutralizowana KOPIA proda           jedyny prod branch
  (Odoo.sh dev:    crony OFF, maile→mailcatcher,         bump manifest = trigger update
   demo+testy)     payment/shipping test, IAP OFF        auto-rollback przy failu
```

## Typy branchy Odoo.sh
| Stage | Baza | Przy push | Uwaga |
|---|---|---|---|
| **Production** | realna, jedna | ładuje istniejącą bazę na nowej rewizji | tylko 1 prod branch; auto-rollback |
| **Staging** | kopia proda, neutralizowana | świeża kopia za każdym pushem | crony/maile/płatności/IAP OFF; config nie wraca do proda |
| **Development** | od zera | rebuild, demo data, testy jednostkowe | throwaway; fail testów = fail builda |

Statusy builda: 🟢 sukces · 🟡 warningi · 🔴 fail.

## Wersjonowanie modułu (SemVer domowy) — art. 93
- Format **`<wersja_odoo>.X.Y.Z`** (np. `16.0.1.2.3`): X major (zeruje Y,Z), Y minor (zeruje Z), Z patch.
- Sufiksy: `-alpha`, `-in.progress`. Metadana tłumaczeń `+T`. Changelog wg sekcji wersji (styl OCA).
- **Parsuj/bump regexem — nigdy `eval()`.**

## Skrypty migracyjne — art. 219
- `<modul>/migrations/<pełna_wersja>/` (`pre-*.py`/`post-*.py`/`end-*.py`), sygnatura `def migrate(cr, version)`.
- Odoo odpala foldery o wersji > zainstalowanej i ≤ docelowej → **bump manifestu = wyzwalacz**.

## GitHub — setup (art. 103)
- Org `myOdoo-pl`; konta admin (`myodoopl`, `dp-myodoo`) tylko do struktury. Konta osób wg schematu `xx-myodoo` + klucze SSH.
- ⚠️ Po dodaniu do org trzeba **ręcznie** dodać usera do projektu na Odoo.sh (admin projektu).
- Branch protection: Require PR + approvals + status checks + review Code Owners; blokuj force-push i kasowanie. CODEOWNERS w `.github/` (ostatni pasujący wzorzec wygrywa).

## Role Odoo.sh (art. 224)
- **Admin** — pełna kontrola (członkowie, branche, SSH, backupy, domeny, klucze, integracja git).
- **Developer** — push kodu, testy, logi, SSH; nie tworzy/kasuje branchy z UI (tylko git); nie zarządza członkami/ustawieniami.
- **Tester** — tylko preview/staging przez frontend; zero terminala/kodu. Rola dla klienta.

## Operacje Odoo.sh (skrót)
- **Logi** (`~/logs`): `install.log`, `update.log`, `odoo.log`, `pip.log`. FS: `/src`, `/data`, `/logs`. → `odoo-sh-logs` + `scripts/odoo_sh_logs.py`.
- **Backupy**: auto tylko dla prod (7 dziennych/4 tygodniowe/3 miesięczne); staging/dev ulotne.
- **Submoduły** (private repo): SSH URL + deploy key (HTTPS nie zadziała) → inaczej build fail.
- **requirements.txt** w root brancha (submoduły: folder nadrzędny modułów).
- **Domeny + SSL**: Branch → Settings → Custom domains; Let's Encrypt auto (~godzina), CAA musi dopuszczać LE, brak certu dla naked domain (www + redirect), własnego certu wgrać się nie da. → `odoo-website-domain`.
- **Upgrade**: test upgrade (na ostatnim backupie prod, na temp/staging branchu) → production upgrade (= downtime). Rewizja per branch, okno wsparcia ~90 dni (art. 83/85).

## Pułapki (red flags)
- Force-push na prod; staging nie przenosi configu; brak bumpu manifestu (`-u` się nie odpala); staging resetuje dane co push; crony/maile na staging OFF (mailcatcher); naked domain bez SSL; Odoo shell auto-commituje; private submodule bez deploy key = fail; production upgrade = downtime; `requirements.txt` w złym miejscu.

## Ustalenia SSH Odoo.sh (z wdrożenia narzędzia, 2026-08-12)
- Klucz SSH dodaje się w **Profilu Odoo.sh** (menu konta, z wnętrza projektu), **NIE na GitHubie**. Rola Admin/Developer wymagana.
- **Host builda = `<nazwa-builda>.dev.odoo.com`**, **user = nazwa builda** (nawias `[stage/wersja]` to etykieta, nie adres). Host zmienia się przy przebudowie.
- Fallback bez lokalnego SSH: web-Shell builda → `tail -n N ~/logs/odoo.log`.

## Źródła
Odoo.sh: [branches](https://www.odoo.com/documentation/17.0/administration/odoo_sh/getting_started/branches.html) · [builds](https://www.odoo.com/documentation/17.0/administration/odoo_sh/getting_started/builds.html) · [online-editor/logs](https://www.odoo.com/documentation/16.0/administration/odoo_sh/getting_started/online-editor.html) · [submodules](https://www.odoo.com/documentation/17.0/administration/odoo_sh/advanced/submodules.html) · [containers](https://www.odoo.com/documentation/17.0/administration/odoo_sh/advanced/containers.html) · [upgrade](https://www.odoo.com/documentation/17.0/administration/upgrade.html) · [upgrade_scripts](https://www.odoo.com/documentation/19.0/developer/reference/upgrades/upgrade_scripts.html). GitHub: [protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) · [CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners). Baza wiedzy myodoo.pl: art. 83/85/93/103/116/219/224.
