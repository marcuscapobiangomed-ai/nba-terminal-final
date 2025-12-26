"""
Módulo de Backoffice
Gerencia persistência de apostas, cálculo de métricas e histórico
"""
import os
import pandas as pd
from datetime import datetime
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from .config import get_config


@dataclass
class BetMetrics:
    """Métricas calculadas do histórico de apostas"""
    total_bets: int
    pending_bets: int
    completed_bets: int
    greens: int
    reds: int
    voids: int
    winrate: float
    total_invested: float
    total_profit: float
    roi: float
    current_streak: int  # Positivo = greens seguidos, Negativo = reds


def load_history(filepath: Optional[str] = None) -> pd.DataFrame:
    """
    Carrega histórico de apostas do CSV.
    
    Args:
        filepath: Caminho do arquivo (usa config se não fornecido)
    
    Returns:
        DataFrame com histórico ou DataFrame vazio se não existir
    """
    config = get_config()
    filepath = filepath or config.bets_history_file
    
    columns = ["Data", "Jogo", "Tipo", "Aposta", "Odd", "Valor", "Resultado", "Lucro"]
    
    if not os.path.exists(filepath):
        return pd.DataFrame(columns=columns)
    
    try:
        df = pd.read_csv(filepath)
        # Garante que todas as colunas existem
        for col in columns:
            if col not in df.columns:
                df[col] = None
        return df
    except Exception as e:
        print(f"Erro ao carregar histórico: {e}")
        return pd.DataFrame(columns=columns)


def save_bet(
    jogo: str,
    tipo: str,
    aposta: str,
    odd: float,
    valor: float,
    filepath: Optional[str] = None
) -> bool:
    """
    Salva uma nova aposta no histórico.
    
    Args:
        jogo: Descrição do jogo (ex: "Lakers @ Celtics")
        tipo: Tipo de aposta (Spread, Total, Prop, ML)
        aposta: Descrição da aposta (ex: "Lakers -3.5")
        odd: Odds decimais
        valor: Valor apostado em R$
        filepath: Caminho do arquivo
    
    Returns:
        True se salvou com sucesso
    """
    config = get_config()
    filepath = filepath or config.bets_history_file
    
    try:
        df = load_history(filepath)
        
        new_row = pd.DataFrame([{
            "Data": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Jogo": jogo,
            "Tipo": tipo,
            "Aposta": aposta,
            "Odd": odd,
            "Valor": valor,
            "Resultado": "Pendente",
            "Lucro": 0.0
        }])
        
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(filepath, index=False)
        return True
        
    except Exception as e:
        print(f"Erro ao salvar aposta: {e}")
        return False


def update_results(df: pd.DataFrame, filepath: Optional[str] = None) -> pd.DataFrame:
    """
    Recalcula o lucro baseado nos resultados e salva.
    
    Args:
        df: DataFrame com resultados atualizados (Green/Red/Void)
        filepath: Caminho do arquivo
    
    Returns:
        DataFrame atualizado com lucros calculados
    """
    config = get_config()
    filepath = filepath or config.bets_history_file
    
    for i, row in df.iterrows():
        if row['Resultado'] == 'Green':
            # Lucro = Valor * (Odd - 1)
            df.at[i, 'Lucro'] = row['Valor'] * (row['Odd'] - 1)
        elif row['Resultado'] == 'Red':
            df.at[i, 'Lucro'] = -row['Valor']
        else:  # Pendente ou Void
            df.at[i, 'Lucro'] = 0.0
    
    df.to_csv(filepath, index=False)
    return df


def calculate_metrics(df: pd.DataFrame) -> BetMetrics:
    """
    Calcula métricas de performance do histórico.
    
    Args:
        df: DataFrame com histórico de apostas
    
    Returns:
        BetMetrics com todas as métricas calculadas
    """
    if df.empty:
        return BetMetrics(
            total_bets=0, pending_bets=0, completed_bets=0,
            greens=0, reds=0, voids=0, winrate=0.0,
            total_invested=0.0, total_profit=0.0, roi=0.0,
            current_streak=0
        )
    
    total_bets = len(df)
    pending = len(df[df['Resultado'] == 'Pendente'])
    voids = len(df[df['Resultado'] == 'Void'])
    greens = len(df[df['Resultado'] == 'Green'])
    reds = len(df[df['Resultado'] == 'Red'])
    completed = greens + reds
    
    # Winrate (apenas apostas finalizadas)
    winrate = (greens / completed * 100) if completed > 0 else 0.0
    
    # ROI
    completed_df = df[df['Resultado'].isin(['Green', 'Red'])]
    total_invested = completed_df['Valor'].sum() if not completed_df.empty else 0.0
    total_profit = completed_df['Lucro'].sum() if not completed_df.empty else 0.0
    roi = (total_profit / total_invested * 100) if total_invested > 0 else 0.0
    
    # Streak atual
    streak = 0
    for result in df['Resultado'].iloc[::-1]:  # Inverte para pegar mais recentes
        if result == 'Green':
            if streak >= 0:
                streak += 1
            else:
                break
        elif result == 'Red':
            if streak <= 0:
                streak -= 1
            else:
                break
        elif result == 'Pendente':
            break
    
    return BetMetrics(
        total_bets=total_bets,
        pending_bets=pending,
        completed_bets=completed,
        greens=greens,
        reds=reds,
        voids=voids,
        winrate=winrate,
        total_invested=total_invested,
        total_profit=total_profit,
        roi=roi,
        current_streak=streak
    )


def get_cumulative_profit(df: pd.DataFrame) -> pd.Series:
    """
    Calcula lucro acumulado para gráfico.
    
    Args:
        df: DataFrame com histórico
    
    Returns:
        Series com lucro acumulado
    """
    return df['Lucro'].cumsum()


def get_daily_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrupa resultados por dia.
    
    Args:
        df: DataFrame com histórico
    
    Returns:
        DataFrame com resumo diário
    """
    if df.empty:
        return pd.DataFrame()
    
    df['Date'] = pd.to_datetime(df['Data']).dt.date
    
    summary = df.groupby('Date').agg({
        'Valor': 'sum',
        'Lucro': 'sum',
        'Resultado': lambda x: (x == 'Green').sum()
    }).rename(columns={
        'Valor': 'Investido',
        'Lucro': 'Lucro',
        'Resultado': 'Greens'
    })
    
    summary['Total_Apostas'] = df.groupby('Date').size()
    summary['ROI_Dia'] = (summary['Lucro'] / summary['Investido'] * 100).round(1)
    
    return summary.reset_index()


def export_to_excel(df: pd.DataFrame, filepath: str = "bets_export.xlsx") -> bool:
    """
    Exporta histórico para Excel com formatação.
    
    Args:
        df: DataFrame com histórico
        filepath: Caminho do arquivo Excel
    
    Returns:
        True se exportou com sucesso
    """
    try:
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Histórico completo
            df.to_excel(writer, sheet_name='Histórico', index=False)
            
            # Resumo diário
            daily = get_daily_summary(df)
            if not daily.empty:
                daily.to_excel(writer, sheet_name='Resumo Diário', index=False)
            
            # Métricas
            metrics = calculate_metrics(df)
            metrics_df = pd.DataFrame([{
                'Total Apostas': metrics.total_bets,
                'Greens': metrics.greens,
                'Reds': metrics.reds,
                'Winrate %': f"{metrics.winrate:.1f}%",
                'Investido': f"R$ {metrics.total_invested:.2f}",
                'Lucro': f"R$ {metrics.total_profit:.2f}",
                'ROI %': f"{metrics.roi:.1f}%"
            }])
            metrics_df.to_excel(writer, sheet_name='Resumo', index=False)
            
        return True
        
    except Exception as e:
        print(f"Erro ao exportar Excel: {e}")
        return False
