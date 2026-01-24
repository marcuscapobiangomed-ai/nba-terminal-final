import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz

# Nome da planilha (deve combinar com o que está no secrets ou ser o nome do arquivo)
# Se usar URL no secrets, esse nome pode ser ignorado ou usado como worksheet name
SHEET_NAME = "NBA_Bets_Database"

def _get_connection():
    """Retorna conexão com Google Sheets"""
    return st.connection("gsheets", type=GSheetsConnection)

def load_history():
    """Carrega histórico de apostas da planilha"""
    try:
        conn = _get_connection()
        # Lê a planilha. ttl=0 garante que não cacheie (sempre pega dados novos)
        df = conn.read(worksheet=SHEET_NAME, ttl=0)
        
        # Garante que as colunas existem
        expected_cols = ["ID", "Data", "Jogo", "Tipo", "Aposta", "Odd", "Valor", "Resultado", "Lucro"]
        
        # Se planilha estiver vazia ou nova, retorna DF vazio com colunas certas
        if df.empty or len(df.columns) == 0:
            return pd.DataFrame(columns=expected_cols)
            
        # Garante int para ID
        if "ID" in df.columns:
            df["ID"] = pd.to_numeric(df["ID"], errors='coerce').fillna(0).astype(int)
            
        return df
    except Exception as e:
        # Se der erro (ex: planilha não existe ainda), retorna vazio mas avisa se for grave
        err_msg = str(e)
        if "worksheet" in err_msg.lower() or "not found" in err_msg.lower():
             print(f"Aviso: Planilha não encontrada ou nova ({err_msg})")
        else:
             st.error(f"⚠️ Erro de Conexão com Google Sheets: {err_msg}")
        
        return pd.DataFrame(columns=["ID", "Data", "Jogo", "Tipo", "Aposta", "Odd", "Valor", "Resultado", "Lucro"])


# ... existing imports ...

def save_bet(jogo, tipo, aposta, odd, valor):
    """Salva nova aposta adicionando linha na planilha"""
    try:
        df = load_history()
        
        # Gera novo ID
        new_id = 1
        if not df.empty and "ID" in df.columns:
            # Pega o maior ID e soma 1
            max_id = pd.to_numeric(df["ID"], errors='coerce').max()
            if pd.isna(max_id): max_id = 0
            new_id = int(max_id) + 1
            
        # Define timezone de SP
        tz_sp = pytz.timezone('America/Sao_Paulo')
        data_atual = datetime.now(tz_sp).strftime("%Y-%m-%d %H:%M")
        
        new_row = pd.DataFrame([{
            "ID": new_id,
            "Data": data_atual,
            "Jogo": jogo,
            "Tipo": tipo,
            "Aposta": aposta,
            "Odd": float(odd),
            "Valor": float(valor),
            "Resultado": "Pendente",
            "Lucro": 0.0
        }])
        
        # Adiciona ao DF existente
        updated_df = pd.concat([df, new_row], ignore_index=True)
        
        # Salva de volta na planilha
        conn = _get_connection()
        conn.update(worksheet=SHEET_NAME, data=updated_df)
        
        return True
    except Exception as e:
        st.error(f"Erro ao salvar no Google Sheets: {e}")
        return False

def update_bet_result(bet_id, resultado, lucro):
    """Atualiza resultado de uma aposta"""
    try:
        df = load_history()
        
        if df.empty: return
        
        # Localiza linha pelo ID
        mask = df["ID"] == bet_id
        
        if not mask.any(): return
        
        # Atualiza valores
        df.loc[mask, "Resultado"] = resultado
        df.loc[mask, "Lucro"] = float(lucro)
        
        # Salva tudo de volta
        conn = _get_connection()
        conn.update(worksheet=SHEET_NAME, data=df)
        
    except Exception as e:
        st.error(f"Erro ao atualizar Google Sheets: {e}")
