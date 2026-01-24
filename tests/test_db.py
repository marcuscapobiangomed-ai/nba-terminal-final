import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import init_db, save_bet, load_history, update_bet_result

def test_workflow():
    print("--- 1. Inicializando DB ---")
    init_db()
    print("DB incializado.")
    
    print("\n--- 2. Salvando Aposta de Teste ---")
    save_bet("Lakers vs Warriors", "ML", "Lakers ML", 1.90, 100.0)
    print("Aposta salva.")
    
    print("\n--- 3. Carregando Histórico ---")
    df = load_history()
    print("Histórico carregado:")
    print(df.to_string())
    
    if df.empty:
        print("FALHA: DataFrame vazio!")
        return
        
    last_id = df.iloc[0]['ID']
    print(f"\nID da última aposta: {last_id}")
    
    print("\n--- 4. Atualizando Resultado ---")
    # Atualiza para Green com lucro de 90
    update_bet_result(last_id, "Green", 90.0)
    print("Resultado atualizado.")
    
    print("\n--- 5. Verificando Atualização ---")
    df_new = load_history()
    row = df_new[df_new['ID'] == last_id].iloc[0]
    print(f"Status: {row['Resultado']}, Lucro: {row['Lucro']}")
    
    if row['Resultado'] == 'Green' and row['Lucro'] == 90.0:
        print("\n✅ TESTE PASSOU COM SUCESSO!")
    else:
        print("\n❌ FALHA NA ATUALIZAÇÃO!")

if __name__ == "__main__":
    test_workflow()
