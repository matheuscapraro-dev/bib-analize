"""Análise de Produção Científica — tendências temporais e crescimento."""
import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.parser import get_col
from utils.data_processing import yearly_stats, get_year_col, get_citations_col
from components.charts import dual_axis_chart, line_chart, bar_chart, pie_chart
from components.filters import apply_filters, sidebar_upload
from components.tables import show_dataframe

st.set_page_config(page_title="Produção Científica", page_icon="📈", layout="wide")
st.title("📈 Produção Científica")

sidebar_upload()
df = st.session_state.get('df')
if df is None or df.empty:
    st.warning("⚠️ Nenhum dado carregado. Volte à página inicial e faça upload dos arquivos.")
    st.stop()

df_f = apply_filters(df)
year_col = get_year_col(df_f)
cit_col = get_citations_col(df_f)

# --- Estatísticas anuais ---
stats = yearly_stats(df_f)

if not stats.empty:
    st.subheader("Tendência de Publicações e Citações por Ano")
    st.markdown("""
    > O gráfico abaixo mostra a evolução anual do número de publicações (barras) e citações (linha).
    > Permite identificar períodos de crescimento acelerado e o impacto acumulado da produção científica.
    """)
    if 'Citações' in stats.columns:
        fig = dual_axis_chart(stats, 'Ano', 'Publicações', 'Citações',
                              'Publicações', 'Citações',
                              'Publicações e Citações por Ano')
    else:
        fig = bar_chart(stats, 'Ano', 'Publicações', 'Publicações por Ano')
    st.plotly_chart(fig, use_container_width=True)

    # Crescimento acumulado
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Crescimento Acumulado")
        fig_cum = line_chart(stats, 'Ano', 'Acumulado Publicações',
                             'Publicações Acumuladas', height=350)
        st.plotly_chart(fig_cum, use_container_width=True)

    with col2:
        st.subheader("Taxa de Crescimento Anual (%)")
        st.markdown("> Porcentagem de crescimento nas publicações em relação ao ano anterior.")
        fig_growth = bar_chart(stats, 'Ano', 'Crescimento (%)',
                               'Crescimento Anual (%)', height=350)
        st.plotly_chart(fig_growth, use_container_width=True)

    # Tabela
    show_dataframe(stats, "Dados Anuais Detalhados", key="dl_yearly_stats")

st.markdown("---")

# --- Distribuição por tipo de documento ---
dt_col = get_col(df_f, 'DT')
if dt_col and dt_col in df_f.columns:
    st.subheader("Distribuição por Tipo de Documento")
    st.markdown("> Proporção de artigos, revisões, proceedings, etc. no conjunto de dados.")
    dt_counts = df_f[dt_col].value_counts().reset_index()
    dt_counts.columns = ['Tipo de Documento', 'Quantidade']

    col1, col2 = st.columns(2)
    with col1:
        fig_pie = pie_chart(dt_counts, 'Tipo de Documento', 'Quantidade',
                            'Tipos de Documento')
        st.plotly_chart(fig_pie, use_container_width=True)
    with col2:
        show_dataframe(dt_counts, "Tipo de Documento", key="dl_doc_types")

st.markdown("---")

# --- Distribuição por idioma ---
la_col = get_col(df_f, 'LA')
if la_col and la_col in df_f.columns:
    st.subheader("Distribuição por Idioma")
    lang_counts = df_f[la_col].value_counts().head(15).reset_index()
    lang_counts.columns = ['Idioma', 'Quantidade']
    fig_lang = bar_chart(lang_counts, 'Idioma', 'Quantidade',
                         'Top 15 Idiomas', orientation='h', height=400)
    st.plotly_chart(fig_lang, use_container_width=True)
