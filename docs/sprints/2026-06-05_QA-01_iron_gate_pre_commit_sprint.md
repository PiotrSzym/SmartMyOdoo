# 2026-06-05_QA-01_iron_gate_pre_commit_sprint.md

## Meta
- **Typ**: Czystość Kodu / Technical Debt (Faza 5 QA)
- **Status**: TODO
- **Data**: 2026-06-05
- **Cel**: Wdrożenie systemu Pre-Commit (Ruff, Mypy, Bandit) i sformatowanie projektu SmartMyOdoo do zunifikowanego standardu, uodparniając go na błędne komity (The Iron Law).

## Zadania do wykonania:
- [x] Zaktualizować `pyproject.toml` (narzędzia dev: pre-commit, ruff, mypy, bandit).
- [x] Utworzyć plik konfiguracyjny `.pre-commit-config.yaml`.
- [x] Wywołać `pre-commit install` na lokalnym gicie (`.git/hooks`).
- [x] Przeprowadzić globalny audyt: `pre-commit run --all-files`.
- [x] Wymusić naprawę błędów i wylistować ręczne konieczne poprawki.
- [x] Zaktualizować `roadmap.md` oraz napisać raport lekcji (`walkthrough.md`).

## Ryzyka
- Masowa zmiana (przeformatowanie) istniejących plików może utrudnić czytanie starych logów w Git, ale ujednolica jakość. Należy to zrobić w osobnym izolowanym komicie.
