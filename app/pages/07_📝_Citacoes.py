"""Análise de Citações — distribuição, artigos mais citados, referências mais citadas."""
import streamlit as st
import pandas as pd
import numpy as np
import re
import sys, os
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.parser import get_col, safe_split
from utils.data_processing import (
    extract_references, get_year_col, get_citations_col
)
from components.charts import histogram, box_plot, bar_chart, COLOR_PRIMARY, COLOR_SECONDARY
from components.filters import apply_filters, sidebar_upload
from components.tables import show_dataframe
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Citações", page_icon="📝", layout="wide")
st.title("📝 Análise de Citações e Referências")

sidebar_upload()
df = st.session_state.get('df')
if df is None or df.empty:
    st.warning("⚠️ Nenhum dado carregado. Volte à página inicial e faça upload dos arquivos.")
    st.stop()

df_f = apply_filters(df)
cit_col = get_citations_col(df_f)
year_col = get_year_col(df_f)
ti_col = get_col(df_f, 'TI')
au_col = get_col(df_f, 'AU')
so_col = get_col(df_f, 'SO')
doi_col = get_col(df_f, 'DI')

if cit_col is None or cit_col not in df_f.columns:
    st.error("Campo de citações não encontrado nos dados.")
    st.stop()

# --- Distribuição de citações ---
st.subheader("📊 Distribuição de Citações")
st.markdown("""
> A maioria dos artigos recebe poucas citações, enquanto poucos artigos são altamente citados.
> Essa distribuição segue um padrão de **lei de potência** (power law), típico da bibliometria.
""")

col1, col2, col3, col4 = st.columns(4)
citations = df_f[cit_col].fillna(0).astype(int)
col1.metric("Média", f"{citations.mean():.1f}")
col2.metric("Mediana", f"{citations.median():.0f}")
col3.metric("Máximo", f"{citations.max():,}")
col4.metric("% sem citações", f"{(citations == 0).mean() * 100:.1f}%")

col1, col2 = st.columns(2)
with col1:
    fig_hist = px.histogram(citations, nbins=50, title='Distribuição de Citações',
                            labels={'value': 'Citações', 'count': 'Nº Artigos'})
    fig_hist.update_traces(marker_color=COLOR_PRIMARY)
    st.plotly_chart(fig_hist, use_container_width=True)

with col2:
    fig_box = px.box(df_f, y=cit_col, title='Box Plot de Citações',
                     labels={cit_col: 'Citações'})
    st.plotly_chart(fig_box, use_container_width=True)

# Distribuição log
st.subheader("Distribuição Log-Log de Citações")
citations_nonzero = citations[citations > 0]
if len(citations_nonzero) > 0:
    cit_dist = citations_nonzero.value_counts().sort_index().reset_index()
    cit_dist.columns = ['Citações', 'Nº Artigos']
    fig_log = px.scatter(cit_dist, x='Citações', y='Nº Artigos',
                         log_x=True, log_y=True,
                         title='Distribuição de Citações (Escala Log-Log)')
    fig_log.update_traces(marker=dict(size=6, color=COLOR_PRIMARY))
    st.plotly_chart(fig_log, use_container_width=True)

st.markdown("---")

# --- Artigos mais citados ---
top_n = st.slider("Número de artigos mais citados", 5, 50, 20, key="cit_top_n")
st.subheader(f"🏆 Top {top_n} Artigos Mais Citados")

cols_to_show = [c for c in [ti_col, au_col, so_col, year_col, cit_col, doi_col] if c and c in df_f.columns]
top_articles = df_f.nlargest(top_n, cit_col)[cols_to_show].reset_index(drop=True)

# Adicionar link DOI
if doi_col and doi_col in top_articles.columns:
    top_articles['Link DOI'] = top_articles[doi_col].apply(
        lambda x: f"https://doi.org/{x}" if pd.notna(x) and str(x).strip() else ""
    )

# Adicionar citações/ano
if year_col and year_col in top_articles.columns:
    current_year = datetime.now().year
    top_articles['Citações/Ano'] = top_articles.apply(
        lambda r: round(r[cit_col] / max(1, current_year - int(r[year_col])), 1)
        if pd.notna(r.get(year_col)) else 0, axis=1
    )

show_dataframe(top_articles, f"Top {top_n} Artigos Mais Citados", key="dl_top_articles")

st.markdown("---")

# --- Citações por tipo de documento ---
dt_col = get_col(df_f, 'DT')
if dt_col and dt_col in df_f.columns:
    st.subheader("Citações por Tipo de Documento")
    st.markdown("> Comparação da distribuição de citações entre diferentes tipos de documento (Article, Review, etc.).")

    top_types = df_f[dt_col].value_counts().head(5).index.tolist()
    df_types = df_f[df_f[dt_col].isin(top_types)]

    fig_box_dt = px.box(df_types, x=dt_col, y=cit_col, color=dt_col,
                        title='Distribuição de Citações por Tipo de Documento',
                        labels={dt_col: 'Tipo', cit_col: 'Citações'})
    fig_box_dt.update_layout(showlegend=False)
    st.plotly_chart(fig_box_dt, use_container_width=True)

st.markdown("---")

# --- Referências mais citadas ---
st.subheader("📚 Referências Mais Citadas")
st.markdown("""
> Análise das referências que aparecem com mais frequência nos artigos do dataset.
> Identifica os trabalhos fundacionais mais influentes na área.
""")

cr_col = get_col(df_f, 'CR')
if cr_col and cr_col in df_f.columns:
    with st.spinner("Processando referências citadas..."):
        refs = extract_references(df_f)
        if not refs.empty:
            ref_counts = refs.value_counts().head(30).reset_index()
            ref_counts.columns = ['Referência', 'Frequência']

            fig_refs = bar_chart(ref_counts.head(15), 'Referência', 'Frequência',
                                 'Top 15 Referências Mais Citadas', orientation='h',
                                 color=COLOR_SECONDARY, height=500)
            st.plotly_chart(fig_refs, use_container_width=True)

            show_dataframe(ref_counts, "Top 30 Referências", key="dl_refs")

            # --- Price Index (idade das referências) ---
            st.markdown("---")
            st.subheader("📅 Índice de Price — Idade das Referências")
            st.markdown("""
            > O **Índice de Price** mede a proporção de referências recentes (últimos 5 anos).
            > Um valor alto indica que a área está se desenvolvendo rapidamente com base em pesquisa recente.
            """)

            # Tentar extrair anos das referências
            ref_years = []
            for ref in refs:
                match = re.search(r'\b(19|20)\d{2}\b', str(ref))
                if match:
                    ref_years.append(int(match.group()))

            if ref_years:
                ref_years_s = pd.Series(ref_years)
                ref_years_s = ref_years_s[(ref_years_s >= 1900) & (ref_years_s <= datetime.now().year)]

                fig_ref_year = px.histogram(ref_years_s, nbins=50,
                                            title='Distribuição dos Anos das Referências',
                                            labels={'value': 'Ano da Referência'})
                fig_ref_year.update_traces(marker_color='#9467bd')
                st.plotly_chart(fig_ref_year, use_container_width=True)

                # Price index (% referências dos últimos 5 anos)
                if year_col in df_f.columns:
                    median_pub_year = int(df_f[year_col].median())
                    recent = (ref_years_s >= median_pub_year - 5).sum()
                    price_idx = round(recent / len(ref_years_s) * 100, 1)
                    st.metric("Índice de Price", f"{price_idx}%",
                              help="% de referências publicadas nos últimos 5 anos (relativo à mediana do dataset)")
else:
    st.info("Campo de referências citadas (CR) não disponível nos dados.")
