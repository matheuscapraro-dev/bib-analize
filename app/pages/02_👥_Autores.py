"""Análise de Autores — rankings, Lei de Lotka, índice h."""
import streamlit as st
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.parser import get_col, safe_split
from utils.data_processing import (
    extract_authors, lotka_law, author_metrics, get_citations_col
)
from components.charts import bar_chart, line_chart, COLORS, COLOR_PRIMARY, COLOR_SECONDARY
from components.filters import apply_filters, sidebar_upload
from components.tables import show_dataframe
import plotly.express as px

st.set_page_config(page_title="Autores", page_icon="👥", layout="wide")
st.title("👥 Análise de Autores")

sidebar_upload()
df = st.session_state.get('df')
if df is None or df.empty:
    st.warning("⚠️ Nenhum dado carregado. Volte à página inicial e faça upload dos arquivos.")
    st.stop()

df_f = apply_filters(df)

# --- Controle de Top N ---
top_n = st.slider("Número de autores a exibir (Top N)", 5, 50, 10, key="authors_top_n")

# --- Métricas por autor ---
with st.spinner("Calculando métricas dos autores..."):
    metrics = author_metrics(df_f)

if not metrics.empty:
    # Top por publicações
    st.subheader(f"Top {top_n} Autores por Publicações")
    top_pub = metrics.head(top_n)
    fig1 = bar_chart(top_pub, 'Autor', 'Publicações',
                     f'Top {top_n} Autores — Publicações', orientation='h',
                     color=COLOR_PRIMARY, height=max(350, top_n * 30))
    st.plotly_chart(fig1, use_container_width=True)

    # Top por citações
    st.subheader(f"Top {top_n} Autores por Citações Totais")
    top_cit = metrics.sort_values('Citações Total', ascending=False).head(top_n)
    fig2 = bar_chart(top_cit, 'Autor', 'Citações Total',
                     f'Top {top_n} Autores — Citações', orientation='h',
                     color=COLOR_SECONDARY, height=max(350, top_n * 30))
    st.plotly_chart(fig2, use_container_width=True)

    # Top por h-index
    st.subheader(f"Top {top_n} Autores por Índice h")
    st.markdown("""
    > O **índice h** de um autor é o maior número *h* tal que *h* de seus artigos tenham pelo menos *h* citações cada.
    > Ele mede simultaneamente produtividade e impacto.
    """)
    top_h = metrics.sort_values('Índice h', ascending=False).head(top_n)
    fig3 = bar_chart(top_h, 'Autor', 'Índice h',
                     f'Top {top_n} Autores — Índice h', orientation='h',
                     color='#2ca02c', height=max(350, top_n * 30))
    st.plotly_chart(fig3, use_container_width=True)

    # Top por média citações/artigo
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(f"Top {top_n} por Média Citações/Artigo")
        # Filtrar autores com pelo menos 3 publicações para média relevante
        min_pubs = st.number_input("Mínimo de publicações para média", 1, 20, 3, key="min_pubs_avg")
        top_avg = metrics[metrics['Publicações'] >= min_pubs].sort_values(
            'Média Citações', ascending=False
        ).head(top_n)
        fig4 = bar_chart(top_avg, 'Autor', 'Média Citações',
                         f'Média Citações/Artigo (mín. {min_pubs} pubs)', orientation='h',
                         color='#9467bd', height=max(350, top_n * 30))
        st.plotly_chart(fig4, use_container_width=True)

    with col2:
        st.subheader("Publicações vs Citações")
        fig_scatter = px.scatter(
            metrics.head(100), x='Publicações', y='Citações Total',
            size='Índice h', hover_name='Autor',
            title='Relação Publicações × Citações (Top 100 autores)',
            color='Índice h', color_continuous_scale='Viridis',
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    st.markdown("---")

    # --- Lei de Lotka ---
    st.subheader("📐 Lei de Lotka — Produtividade dos Autores")
    st.markdown("""
    > A **Lei de Lotka** descreve a distribuição de produtividade científica.
    > Poucos autores produzem muitos trabalhos, enquanto a maioria produz poucos.
    > O limiar para autores-núcleo é: **M = 0.749 × √(Nmax)**, onde Nmax é o número máximo de publicações.
    """)

    lotka = lotka_law(df_f)
    if lotka['threshold'] > 0:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Nmax (maior produção)", lotka['n_max'])
        c2.metric("Limiar M", lotka['threshold'])
        c3.metric("Autores-núcleo", f"{lotka['core_count']:,}")
        c4.metric("Total de autores", f"{lotka['total_authors']:,}")

        # Gráfico log-log da distribuição
        dist = lotka['distribution']
        if not dist.empty:
            fig_lotka = px.scatter(
                dist, x='Nº Publicações', y='Nº Autores',
                title='Distribuição de Produtividade (Lei de Lotka) — Escala Log-Log',
                log_x=True, log_y=True,
            )
            fig_lotka.update_traces(marker=dict(size=8, color=COLOR_PRIMARY))
            st.plotly_chart(fig_lotka, use_container_width=True)

        # Tabela de autores-núcleo
        show_dataframe(lotka['core_authors'], "Autores-Núcleo (Lei de Lotka)", key="dl_lotka")

    st.markdown("---")

    # --- Tabela completa de métricas ---
    show_dataframe(metrics, "Tabela Completa — Métricas por Autor", key="dl_author_metrics")
