"""Análise de Periódicos — rankings, Lei de Bradford, evolução temporal."""
import streamlit as st
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.parser import get_col
from utils.data_processing import bradford_law, get_year_col, get_citations_col
from components.charts import bar_chart, pie_chart, heatmap, COLOR_PRIMARY, COLOR_SECONDARY, COLORS
from components.filters import apply_filters, sidebar_upload
from components.tables import show_dataframe
import plotly.express as px

st.set_page_config(page_title="Periódicos", page_icon="📚", layout="wide")
st.title("📚 Análise de Periódicos")

sidebar_upload()
df = st.session_state.get('df')
if df is None or df.empty:
    st.warning("⚠️ Nenhum dado carregado. Volte à página inicial e faça upload dos arquivos.")
    st.stop()

df_f = apply_filters(df)
so_col = get_col(df_f, 'SO')
year_col = get_year_col(df_f)
cit_col = get_citations_col(df_f)

if so_col is None or so_col not in df_f.columns:
    st.error("Campo de periódico (SO) não encontrado nos dados.")
    st.stop()

top_n = st.slider("Número de periódicos a exibir (Top N)", 5, 50, 15, key="journals_top_n")

# --- Top por publicações ---
st.subheader(f"Top {top_n} Periódicos por Publicações")
journal_counts = df_f[so_col].value_counts().head(top_n).reset_index()
journal_counts.columns = ['Periódico', 'Publicações']

fig1 = bar_chart(journal_counts, 'Periódico', 'Publicações',
                 f'Top {top_n} Periódicos', orientation='h',
                 height=max(400, top_n * 28))
st.plotly_chart(fig1, use_container_width=True)

# --- Top por citações ---
if cit_col and cit_col in df_f.columns:
    st.subheader(f"Top {top_n} Periódicos por Citações Totais")
    journal_cit = df_f.groupby(so_col)[cit_col].sum().sort_values(ascending=False).head(top_n).reset_index()
    journal_cit.columns = ['Periódico', 'Citações']

    fig2 = bar_chart(journal_cit, 'Periódico', 'Citações',
                     f'Top {top_n} Periódicos — Citações', orientation='h',
                     color=COLOR_SECONDARY, height=max(400, top_n * 28))
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# --- Lei de Bradford ---
st.subheader("📐 Lei de Bradford — Zonas de Produtividade")
st.markdown("""
> A **Lei de Bradford** divide os periódicos em 3 zonas de produtividade:
> - **Zona 1 (Núcleo):** Poucos periódicos que publicam ~1/3 dos artigos
> - **Zona 2 (Semi-produtivo):** Número intermediário de periódicos com ~1/3 dos artigos
> - **Zona 3 (Periférico):** Muitos periódicos que publicam os ~1/3 restantes
>
> A proporção entre as zonas segue aproximadamente 1:n:n², demonstrando a concentração da produção.
""")

bradford = bradford_law(df_f)
if bradford['zone_summary'] is not None and not bradford['zone_summary'].empty:
    col1, col2 = st.columns(2)
    with col1:
        fig_bradford = pie_chart(bradford['zone_summary'], 'Zona de Bradford', 'Periódicos',
                                 'Distribuição de Periódicos por Zona')
        st.plotly_chart(fig_bradford, use_container_width=True)
    with col2:
        st.dataframe(bradford['zone_summary'], use_container_width=True)
        st.metric("Total de Periódicos", bradford['total_journals'])

    # Gráfico cumulativo
    journals = bradford['journals']
    journals['Rank'] = range(1, len(journals) + 1)
    journals['% Acumulado Artigos'] = (journals['Acumulado'] / journals['Artigos'].sum() * 100).round(1)

    fig_cum = px.line(journals, x='Rank', y='% Acumulado Artigos',
                      title='Curva Cumulativa de Bradford',
                      color='Zona de Bradford', color_discrete_sequence=COLORS)
    fig_cum.add_hline(y=33.3, line_dash='dash', line_color='gray', annotation_text='33%')
    fig_cum.add_hline(y=66.6, line_dash='dash', line_color='gray', annotation_text='66%')
    st.plotly_chart(fig_cum, use_container_width=True)

    show_dataframe(bradford['journals'], "Periódicos com Zonas de Bradford", key="dl_bradford")

st.markdown("---")

# --- Evolução temporal dos top periódicos ---
if year_col and year_col in df_f.columns:
    st.subheader("Evolução Temporal dos Top Periódicos")
    top_journals = list(journal_counts['Periódico'].head(8))
    df_top = df_f[df_f[so_col].isin(top_journals)]

    pivot = df_top.groupby([year_col, so_col]).size().reset_index(name='Publicações')
    pivot_wide = pivot.pivot_table(index=so_col, columns=year_col, values='Publicações', fill_value=0)

    fig_heat = px.imshow(pivot_wide, title='Publicações por Ano e Periódico (Top 8)',
                         aspect='auto', color_continuous_scale='Blues', text_auto=True)
    fig_heat.update_layout(height=400)
    st.plotly_chart(fig_heat, use_container_width=True)

# --- Tabela detalhada ---
st.markdown("---")
journal_detail = df_f.groupby(so_col).agg(
    Publicações=(so_col, 'count'),
    **({'Citações': (cit_col, 'sum'), 'Média Citações': (cit_col, 'mean')} if cit_col else {}),
    **({'Primeiro Ano': (year_col, 'min'), 'Último Ano': (year_col, 'max')} if year_col else {}),
).reset_index()
journal_detail.columns = ['Periódico'] + list(journal_detail.columns[1:])
if 'Média Citações' in journal_detail.columns:
    journal_detail['Média Citações'] = journal_detail['Média Citações'].round(1)
journal_detail = journal_detail.sort_values('Publicações', ascending=False).reset_index(drop=True)

# ISSN
issn_col = get_col(df_f, 'SN')
if issn_col and issn_col in df_f.columns:
    issn_map = df_f.dropna(subset=[issn_col]).drop_duplicates(subset=[so_col]).set_index(so_col)[issn_col]
    journal_detail['ISSN'] = journal_detail['Periódico'].map(issn_map)

show_dataframe(journal_detail, "Tabela Completa — Periódicos", key="dl_journals")
