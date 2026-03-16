"""Cards de métricas KPI reutilizáveis."""
import streamlit as st
import pandas as pd
from utils.parser import get_col, safe_split
from utils.data_processing import get_year_col, get_citations_col


def show_kpis(df: pd.DataFrame):
    """Exibe cards de métricas principais no topo da página."""
    if df.empty:
        st.warning("Nenhum dado carregado.")
        return

    year_col = get_year_col(df)
    cit_col = get_citations_col(df)
    au_col = get_col(df, 'AU')
    so_col = get_col(df, 'SO')

    total_articles = len(df)
    total_citations = int(df[cit_col].sum()) if cit_col and cit_col in df.columns else 0
    avg_citations = round(total_citations / total_articles, 1) if total_articles > 0 else 0

    # Contar autores únicos
    n_authors = 0
    if au_col and au_col in df.columns:
        n_authors = safe_split(df[au_col], sep='; ').nunique()

    # Contar periódicos
    n_journals = 0
    if so_col and so_col in df.columns:
        n_journals = df[so_col].nunique()

    # Período
    period = ""
    if year_col and year_col in df.columns:
        years = df[year_col].dropna()
        if len(years) > 0:
            period = f"{int(years.min())} - {int(years.max())}"

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("📄 Artigos", f"{total_articles:,}")
    c2.metric("👥 Autores", f"{n_authors:,}")
    c3.metric("📚 Periódicos", f"{n_journals:,}")
    c4.metric("📅 Período", period)
    c5.metric("📈 Citações Total", f"{total_citations:,}")
    c6.metric("📊 Média Citações", f"{avg_citations}")
