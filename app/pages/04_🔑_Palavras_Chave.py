"""Análise de Palavras-chave — rankings, word cloud, co-ocorrência, tendências."""
import streamlit as st
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.parser import get_col, safe_split
from utils.data_processing import (
    extract_keywords, keyword_cooccurrence_network, get_year_col
)
from components.charts import (
    bar_chart, wordcloud_to_fig, network_graph,
    COLOR_PRIMARY, COLOR_SECONDARY, COLORS
)
from components.filters import apply_filters, sidebar_upload
from components.tables import show_dataframe
import plotly.express as px

st.set_page_config(page_title="Palavras-chave", page_icon="🔑", layout="wide")
st.title("🔑 Análise de Palavras-chave")

sidebar_upload()
df = st.session_state.get('df')
if df is None or df.empty:
    st.warning("⚠️ Nenhum dado carregado. Volte à página inicial e faça upload dos arquivos.")
    st.stop()

df_f = apply_filters(df)
year_col = get_year_col(df_f)
top_n = st.slider("Número de palavras-chave (Top N)", 10, 100, 30, key="kw_top_n")

# Opção de excluir palavras genéricas
exclude_words = st.text_input(
    "Excluir palavras-chave (separadas por vírgula)",
    placeholder="ex: internet of things, edge computing, iot",
    key="kw_exclude"
)
exclude_set = set()
if exclude_words:
    exclude_set = {w.strip().lower() for w in exclude_words.split(',')}

# --- Palavras-chave do autor (DE) ---
de_col = get_col(df_f, 'DE')
if de_col and de_col in df_f.columns:
    st.subheader("Palavras-chave do Autor (Author Keywords)")
    kw_author = extract_keywords(df_f, 'DE')
    if exclude_set:
        kw_author = kw_author[~kw_author.isin(exclude_set)]

    kw_counts = kw_author.value_counts().head(top_n).reset_index()
    kw_counts.columns = ['Palavra-chave', 'Frequência']

    col1, col2 = st.columns([2, 1])
    with col1:
        fig1 = bar_chart(kw_counts, 'Palavra-chave', 'Frequência',
                         f'Top {top_n} Palavras-chave do Autor', orientation='h',
                         height=max(400, top_n * 22))
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        # Word Cloud
        st.subheader("☁️ Nuvem de Palavras (Autor)")
        wc_freq = kw_author.value_counts().to_dict()
        fig_wc = wordcloud_to_fig(wc_freq, height=350)
        st.plotly_chart(fig_wc, use_container_width=True)

# --- Keywords Plus (ID) ---
id_col = get_col(df_f, 'ID')
if id_col and id_col in df_f.columns:
    st.markdown("---")
    st.subheader("Keywords Plus (atribuídas pelo WoS)")
    st.markdown("> Keywords Plus são palavras-chave atribuídas automaticamente pelo Web of Science a partir das referências citadas.")
    kw_plus = extract_keywords(df_f, 'ID')
    if exclude_set:
        kw_plus = kw_plus[~kw_plus.isin(exclude_set)]

    kw_plus_counts = kw_plus.value_counts().head(top_n).reset_index()
    kw_plus_counts.columns = ['Keyword Plus', 'Frequência']

    col1, col2 = st.columns([2, 1])
    with col1:
        fig2 = bar_chart(kw_plus_counts, 'Keyword Plus', 'Frequência',
                         f'Top {top_n} Keywords Plus', orientation='h',
                         color=COLOR_SECONDARY, height=max(400, top_n * 22))
        st.plotly_chart(fig2, use_container_width=True)
    with col2:
        st.subheader("☁️ Nuvem de Palavras (Plus)")
        wc_freq2 = kw_plus.value_counts().to_dict()
        fig_wc2 = wordcloud_to_fig(wc_freq2, height=350)
        st.plotly_chart(fig_wc2, use_container_width=True)

# --- Evolução temporal de palavras-chave ---
if year_col and year_col in df_f.columns:
    st.markdown("---")
    st.subheader("📅 Evolução Temporal das Palavras-chave")
    st.markdown("> O heatmap mostra a frequência das top palavras-chave ao longo dos anos, permitindo identificar tendências emergentes e tópicos em declínio.")

    field_choice = st.radio("Campo", ["Palavras-chave do Autor (DE)", "Keywords Plus (ID)"],
                            key="kw_temporal_field", horizontal=True)
    field_code = 'DE' if 'Autor' in field_choice else 'ID'
    kw_col = get_col(df_f, field_code)

    if kw_col and kw_col in df_f.columns:
        # Top 15 keywords para o heatmap
        top_kws = extract_keywords(df_f, field_code)
        if exclude_set:
            top_kws = top_kws[~top_kws.isin(exclude_set)]
        top_15 = top_kws.value_counts().head(15).index.tolist()

        records = []
        for idx, row in df_f.iterrows():
            if pd.isna(row.get(kw_col)) or pd.isna(row.get(year_col)):
                continue
            year = int(row[year_col])
            kws = [k.strip().lower() for k in str(row[kw_col]).split('; ')]
            for kw in kws:
                if kw in top_15 and kw not in exclude_set:
                    records.append({'Ano': year, 'Palavra-chave': kw})

        if records:
            temporal_df = pd.DataFrame(records)
            pivot = temporal_df.groupby(['Palavra-chave', 'Ano']).size().reset_index(name='Freq')
            pivot_wide = pivot.pivot_table(index='Palavra-chave', columns='Ano', values='Freq', fill_value=0)

            fig_heat = px.imshow(pivot_wide, title='Frequência de Palavras-chave por Ano (Top 15)',
                                 aspect='auto', color_continuous_scale='YlOrRd', text_auto=True)
            fig_heat.update_layout(height=500)
            st.plotly_chart(fig_heat, use_container_width=True)

# --- Rede de co-ocorrência ---
st.markdown("---")
st.subheader("🕸️ Rede de Co-ocorrência de Palavras-chave")
st.markdown("""
> A rede mostra como palavras-chave aparecem juntas nos mesmos artigos.
> As cores representam **clusters** (comunidades) detectados pelo algoritmo de Louvain.
> Nós maiores = maior frequência. Arestas mais grossas = co-ocorrência mais frequente.
""")

col_net1, col_net2 = st.columns(2)
with col_net1:
    net_field = st.radio("Campo para rede", ["Palavras-chave do Autor (DE)", "Keywords Plus (ID)"],
                         key="kw_net_field", horizontal=True)
with col_net2:
    min_freq = st.slider("Frequência mínima", 2, 50, 5, key="kw_min_freq")
    net_top_n = st.slider("Máximo de nós", 20, 100, 50, key="kw_net_top_n")

net_code = 'DE' if 'Autor' in net_field else 'ID'
with st.spinner("Construindo rede de co-ocorrência..."):
    nodes, edges = keyword_cooccurrence_network(df_f, net_code, min_freq, net_top_n)

if not nodes.empty and not edges.empty:
    fig_net = network_graph(nodes, edges, 'Palavra-chave', 'Frequência', 'Cluster',
                            'Rede de Co-ocorrência de Palavras-chave', height=650)
    st.plotly_chart(fig_net, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        show_dataframe(nodes.sort_values('Frequência', ascending=False),
                       "Nós da Rede", key="dl_kw_nodes")
    with col2:
        show_dataframe(edges.sort_values('Peso', ascending=False),
                       "Arestas da Rede", key="dl_kw_edges")
else:
    st.info("Dados insuficientes para gerar a rede. Tente reduzir a frequência mínima.")
