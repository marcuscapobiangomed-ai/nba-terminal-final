import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz

# Usa "Sheet1" que é a aba padrão que já existe na planilha
# Isso evita erro de worksheet não encontrada
SHEET_NAME = "Sheet1"

# Colunas esperadas no histórico de apostas
EXPECTED_COLUMNS = ["ID", "Data", "Jogo", "Tipo", "Aposta", "Odd", "Valor", "Resultado", "Lucro"]

def _get_connection():
    """Retorna conexão com Google Sheets com validação"""
    try:
        # Verifica se secrets existem antes de tentar conectar
        if "connections" not in st.secrets or "gsheets" not in st.secrets["connections"]:
            return None
        return st.connection("gsheets", type=GSheetsConnection)
    except Exception as e:
        print(f"[sheets_db] Erro ao conectar: {e}")
        return None

def _ensure_headers(conn):
    """Garante que a planilha tenha os headers corretos"""
    try:
        df = conn.read(worksheet=SHEET_NAME, ttl=0)
        # Se planilha vazia ou sem colunas corretas, cria headers
        if df is None or df.empty or list(df.columns) != EXPECTED_COLUMNS:
            empty_df = pd.DataFrame(columns=EXPECTED_COLUMNS)
            conn.update(worksheet=SHEET_NAME, data=empty_df)
            return empty_df
        return df
    except Exception:
        # Tenta criar planilha com headers
        empty_df = pd.DataFrame(columns=EXPECTED_COLUMNS)
        try:
            conn.update(worksheet=SHEET_NAME, data=empty_df)
        except:
            pass
        return empty_df

def load_history():
    """Carrega histórico de apostas da planilha"""
    try:
        conn = _get_connection()
        if conn is None:
            st.warning("⚠️ **Configuração:** Adicione as credenciais do Google Sheets no Streamlit Secrets.")
            return pd.DataFrame(columns=EXPECTED_COLUMNS)
        
        # Garante que os headers existem e lê os dados
        df = _ensure_headers(conn)
        
        # Se planilha estiver vazia, retorna DF vazio com colunas certas
        if df is None or df.empty or len(df.columns) == 0:
            return pd.DataFrame(columns=EXPECTED_COLUMNS)
            
        # Garante int para ID
        if "ID" in df.columns:
            df["ID"] = pd.to_numeric(df["ID"], errors='coerce').fillna(0).astype(int)
            
        return df
    except Exception as e:
        err_msg = str(e)
        print(f"[sheets_db] load_history erro: {err_msg}")
        st.error(f"⚠️ Erro de Conexão com Google Sheets: {SHEET_NAME}")
        return pd.DataFrame(columns=EXPECTED_COLUMNS)


def save_bet(jogo, tipo, aposta, odd, valor):
    """Salva nova aposta adicionando linha na planilha"""
    try:
        # Verifica conexão
        conn = _get_connection()
        if conn is None:
            st.error("⚠️ Configuração: Configure os Secrets do Google Sheets.")
            return False

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
        
        # Adiciona ao DF existente (ignore_index evita warning)
        if df.empty:
            updated_df = new_row
        else:
            updated_df = pd.concat([df, new_row], ignore_index=True)
        
        # Salva de volta na planilha
        conn.update(worksheet=SHEET_NAME, data=updated_df)
        print(f"[sheets_db] Aposta salva: ID={new_id}")
        
        return True
    except Exception as e:
        print(f"[sheets_db] save_bet erro: {e}")
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
