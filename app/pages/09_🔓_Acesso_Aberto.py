"""Análise de Acesso Aberto — distribuição OA, impacto nas citações."""
import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.parser import get_col
from utils.data_processing import get_year_col, get_citations_col
from components.charts import pie_chart, bar_chart, COLOR_PRIMARY, COLORS
from components.filters import apply_filters, sidebar_upload
from components.tables import show_dataframe
import plotly.express as px

st.set_page_config(page_title="Acesso Aberto", page_icon="🔓", layout="wide")
st.title("🔓 Análise de Acesso Aberto")

sidebar_upload()
df = st.session_state.get('df')
if df is None or df.empty:
    st.warning("⚠️ Nenhum dado carregado. Volte à página inicial e faça upload dos arquivos.")
    st.stop()

df_f = apply_filters(df)
oa_col = get_col(df_f, 'OA')
year_col = get_year_col(df_f)
cit_col = get_citations_col(df_f)

if oa_col is None or oa_col not in df_f.columns:
    st.error("Campo de Acesso Aberto (OA) não encontrado nos dados. Verifique se a exportação inclui esse campo.")
    st.stop()

# --- Distribuição por tipo OA ---
st.subheader("Distribuição por Tipo de Acesso Aberto")
st.markdown("""
> **Gold:** Publicado em periódico totalmente open access.
> **Green:** Versão disponível em repositório (preprint/postprint).
> **Bronze:** Livre para ler no site do publisher, mas sem licença aberta.
> **Hybrid:** Artigo OA em periódico de assinatura.
> Sem indicação = acesso restrito (closed).
""")

df_oa = df_f.copy()
df_oa[oa_col] = df_oa[oa_col].fillna('Acesso Restrito')

oa_counts = df_oa[oa_col].value_counts().reset_index()
oa_counts.columns = ['Tipo OA', 'Artigos']

col1, col2 = st.columns(2)
with col1:
    fig_pie = pie_chart(oa_counts, 'Tipo OA', 'Artigos', 'Distribuição de Acesso Aberto')
    st.plotly_chart(fig_pie, use_container_width=True)
with col2:
    fig_bar = bar_chart(oa_counts, 'Tipo OA', 'Artigos', 'Artigos por Tipo OA', height=350)
    st.plotly_chart(fig_bar, use_container_width=True)

# KPIs
total = len(df_oa)
oa_total = (df_oa[oa_col] != 'Acesso Restrito').sum()
c1, c2 = st.columns(2)
c1.metric("% Acesso Aberto", f"{oa_total / total * 100:.1f}%")
c2.metric("Total OA", f"{oa_total:,} de {total:,}")

st.markdown("---")

# --- Impacto OA nas citações ---
if cit_col and cit_col in df_f.columns:
    st.subheader("📊 Impacto do Acesso Aberto nas Citações")
    st.markdown("> Comparação das citações entre artigos de acesso aberto e acesso restrito.")

    fig_box = px.box(df_oa, x=oa_col, y=cit_col, color=oa_col,
                     title='Distribuição de Citações por Tipo de Acesso',
                     labels={oa_col: 'Tipo OA', cit_col: 'Citações'},
                     color_discrete_sequence=COLORS)
    fig_box.update_layout(showlegend=False)
    st.plotly_chart(fig_box, use_container_width=True)

    # Tabela resumo
    summary = df_oa.groupby(oa_col).agg(
        Artigos=(cit_col, 'count'),
        **{'Média Citações': (cit_col, 'mean')},
        **{'Mediana Citações': (cit_col, 'median')},
        **{'Total Citações': (cit_col, 'sum')},
    ).reset_index()
    summary.columns = ['Tipo OA'] + list(summary.columns[1:])
    summary['Média Citações'] = summary['Média Citações'].round(1)
    summary = summary.sort_values('Média Citações', ascending=False)
    show_dataframe(summary, "Resumo por Tipo OA", key="dl_oa_summary")

st.markdown("---")

# --- Tendência OA ao longo dos anos ---
if year_col and year_col in df_f.columns:
    st.subheader("📅 Tendência de Acesso Aberto ao Longo do Tempo")

    yearly_oa = df_oa.groupby([year_col, oa_col]).size().reset_index(name='Artigos')

    fig_stack = px.bar(yearly_oa, x=year_col, y='Artigos', color=oa_col,
                       title='Distribuição de Acesso Aberto por Ano',
                       color_discrete_sequence=COLORS,
                       labels={year_col: 'Ano', oa_col: 'Tipo OA'})
    fig_stack.update_layout(barmode='stack')
    st.plotly_chart(fig_stack, use_container_width=True)

    # Percentual OA por ano
    yearly_total = df_oa.groupby(year_col).size().reset_index(name='Total')
    yearly_open = df_oa[df_oa[oa_col] != 'Acesso Restrito'].groupby(year_col).size().reset_index(name='OA')
    yearly_pct = yearly_total.merge(yearly_open, on=year_col, how='left').fillna(0)
    yearly_pct['% OA'] = (yearly_pct['OA'] / yearly_pct['Total'] * 100).round(1)

    fig_pct = px.line(yearly_pct, x=year_col, y='% OA',
                      title='% de Acesso Aberto por Ano', markers=True)
    fig_pct.update_traces(line_color=COLOR_PRIMARY)
    st.plotly_chart(fig_pct, use_container_width=True)
