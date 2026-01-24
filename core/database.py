import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path

# Caminho do banco de dados (no diretório raiz do projeto ou relativo a este arquivo)
# Como este arquivo está em 'core/', o DB ficará em 'bets.db' na raiz
DB_PATH = Path(__file__).parent.parent / "bets.db"

def init_db():
    """Inicializa o banco de dados e cria a tabela se não existir."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Criar tabela de apostas
    # id: identificador único
    # data: data da aposta
    # jogo: descrição do jogo/confronto
    # tipo: tipo de aposta (ex: ML, Spread, Props)
    # aposta: detalhe da aposta (ex: Lakers -5.5)
    # odd: odd da aposta
    # valor: valor apostado
    # resultado: Pendente, Green, Red, Void
    # lucro: resultado financeiro da aposta
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            jogo TEXT NOT NULL,
            tipo TEXT NOT NULL,
            aposta TEXT NOT NULL,
            odd REAL NOT NULL,
            valor REAL NOT NULL,
            resultado TEXT DEFAULT 'Pendente',
            lucro REAL DEFAULT 0.0
        )
    ''')
    
    conn.commit()
    conn.close()

def save_bet(jogo, tipo, aposta, odd, valor):
    """Salva uma nova aposta no banco de dados."""
    # Garante que o DB existe
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    cursor.execute('''
        INSERT INTO bets (data, jogo, tipo, aposta, odd, valor)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (data_atual, jogo, tipo, aposta, odd, valor))
    
    conn.commit()
    conn.close()
    return True

def load_history():
    """Carrega o histórico de apostas como um DataFrame pandas."""
    # Garante que o DB existe
    if not DB_PATH.exists():
        init_db()
        
    try:
        conn = sqlite3.connect(DB_PATH)
        # Carrega direto para DataFrame
        df = pd.read_sql_query("SELECT * FROM bets ORDER BY id DESC", conn)
        conn.close()
        
        # Mapeamento para manter compatibilidade com o layout existente se necessário
        # As colunas no DB são lowercase, mas o app original usava Capitalized Title Case no CSV
        # Vamos renomear para manter compatibilidade visual se o frontend esperar isso
        df = df.rename(columns={
            "id": "ID",
            "data": "Data",
            "jogo": "Jogo",
            "tipo": "Tipo",
            "aposta": "Aposta",
            "odd": "Odd",
            "valor": "Valor",
            "resultado": "Resultado",
            "lucro": "Lucro"
        })
        
        return df
    except Exception as e:
        print(f"Erro ao carregar histórico: {e}")
        # Retorna DF vazio com colunas certas como fallback
        return pd.DataFrame(columns=["ID", "Data", "Jogo", "Tipo", "Aposta", "Odd", "Valor", "Resultado", "Lucro"])

def update_bet_result(bet_id, resultado, lucro):
    """Atualiza o resultado de uma aposta existente."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE bets 
        SET resultado = ?, lucro = ?
        WHERE id = ?
    ''', (resultado, lucro, bet_id))
    
    conn.commit()
    conn.close()
