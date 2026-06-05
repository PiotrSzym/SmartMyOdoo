from shadow_mode import create_proposal

def propose_magic_fix(fix_type: str, record_id: int, reason: str) -> dict:
    """
    Moduł 'Magii Bazodanowej' - pozwala agentowi przygotować skrypt naprawczy
    omijający standardowe zabezpieczenia Odoo (np. odwrócenie zamkniętej inwentaryzacji).
    
    Obsługiwane typy 'fix_type':
    - 'force_cancel_invoice' (Odwraca Posted do Cancel)
    - 'unlock_stock_move' (Odwraca stany magazynowe Done -> Draft)
    - 'change_uom_on_product' (Zmienia jednostkę miary mimo historii ruchów)
    """
    
    if fix_type not in ["force_cancel_invoice", "unlock_stock_move", "change_uom_on_product"]:
        raise ValueError(f"Nieznany typ magicznej naprawy: {fix_type}")
        
    proposal = create_proposal(
        action_type=f"magic_{fix_type}",
        model_name="N/A", # Zależne od skryptu
        record_ids=[record_id],
        values={"system_warning": "🚨 UWAGA: Ta akcja narusza standardowe zasady Odoo. Zostanie wykonana przez surowe zapytania SQL lub nadpisanie kontekstu."},
        reason=reason
    )
    
    return proposal
