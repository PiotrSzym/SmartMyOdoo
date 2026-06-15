"""K2 (KEY-01): resolver poświadczeń po TYPIE (nie po magicznej nazwie).

`to_credential` mapuje surowy sekret z Vaulta na `Credential`:
- nowy format: sekret ma pole `type`,
- legacy (auto-tag, kompatybilność wsteczna): `OPENROUTER_KEY` → llm_provider/openrouter;
  `<ws>_ODOO` → odoo_data dla workspace `<ws>`.

`resolve_credential` wybiera właściwy klucz po `type` (+`workspace`, +`provider`),
preferując dopasowanie do workspace nad `default`.
"""

from typing import Any, Dict, Optional

from smartmyodoo.vault.schemas import Credential, CredentialType

_ODOO_SUFFIX = "_ODOO"


def to_credential(name: str, raw: Any) -> Optional[Credential]:
    """Zwraca Credential dla sekretu lub None (usunięty / nieklasyfikowalny / niekompletny)."""
    if not isinstance(raw, dict) or raw.get("deleted_at"):
        return None

    # 1) Nowy format — sekret ma jawny 'type'
    if raw.get("type"):
        fields = {
            k: v for k, v in raw.items() if k in Credential.model_fields and k != "name"
        }
        try:
            return Credential(name=name, **fields)
        except Exception:
            return None

    # 2) Legacy auto-tag (kompatybilność wsteczna)
    if name == "OPENROUTER_KEY":
        key = raw.get("api_key") or raw.get("password") or raw.get("key")
        if not key:
            return None
        return Credential(
            name=name,
            type=CredentialType.LLM_PROVIDER,
            provider="openrouter",
            api_key=key,
        )

    if name.endswith(_ODOO_SUFFIX):
        ws = name[: -len(_ODOO_SUFFIX)] or "default"
        try:
            return Credential(
                name=name,
                type=CredentialType.ODOO_DATA,
                workspace_id=ws,
                url=raw.get("url"),
                db=raw.get("db"),
                login=raw.get("login"),
                password=raw.get("password"),
            )
        except Exception:
            return None

    return None  # nie da się sklasyfikować (np. dowolny sekret bez typu)


def resolve_credential(
    vault_data: Dict[str, Any],
    type: CredentialType,
    workspace_id: str = "default",
    provider: Optional[str] = None,
) -> Optional[Credential]:
    """Zwraca najlepiej dopasowane poświadczenie danego typu lub None."""
    candidates = []
    for name, raw in vault_data.items():
        cred = to_credential(name, raw)
        if not cred or not cred.enabled or cred.type != type:
            continue
        if cred.workspace_id not in (workspace_id, "default"):
            continue
        if provider and cred.provider != provider:
            continue
        candidates.append(cred)

    # preferuj dopasowanie do workspace nad 'default'
    candidates.sort(key=lambda c: 0 if c.workspace_id == workspace_id else 1)
    return candidates[0] if candidates else None
