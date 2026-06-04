import os

def main():
    print("Sprawdzam wstrzyknięte sekrety w pamięci (ENV)...")
    
    # Próbujemy odczytać sekret RUN_SECRET z środowiska
    run_secret = os.environ.get("RUN_SECRET", None)
    
    if run_secret:
        print(f"SUKCES! Ukryty skrypt wykrył klucz w pamięci!")
        print(f"Zamaskowana wartość (pierwsze 3 znaki): {run_secret[:3]}***")
    else:
        print("PORAŻKA! Brak klucza 'RUN_SECRET' w zmiennych środowiskowych.")

if __name__ == "__main__":
    main()
