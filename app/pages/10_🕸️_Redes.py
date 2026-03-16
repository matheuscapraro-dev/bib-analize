"""Análise de Redes — redes de co-autoria com métricas de centralidade."""
import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.parser import get_col
from utils.data_processing import coauthorship_network, get_citations_col
from components.charts import network_graph, bar_chart, COLOR_PRIMARY, COLOR_SECONDARY, COLORS
from components.filters import apply_filters, sidebar_upload
from components.tables import show_dataframe
import plotly.express as px

st.set_page_config(page_title="Redes de Co-autoria", page_icon="🕸️", layout="wide")
st.title("🕸️ Redes de Co-autoria")

sidebar_upload()
df = st.session_state.get('df')
if df is None or df.empty:
    st.warning("⚠️ Nenhum dado carregado. Volte à página inicial e faça upload dos arquivos.")
    st.stop()

df_f = apply_filters(df)

st.markdown("""
> A **rede de co-autoria** conecta autores que publicaram juntos. Ela revela:
> - **Comunidades de pesquisa:** grupos de autores que colaboram frequentemente
> - **Autores-ponte:** pesquisadores que conectam diferentes comunidades
> - **Centralidade:** autores mais influentes na rede de colaboração
>
> **Métricas de centralidade:**
> - **Grau (Degree):** número de co-autores. Alta = autor altamente colaborativo.
> - **Intermediação (Betweenness):** frequência como caminho mais curto entre outros. Alta = autor-ponte.
""")

# --- Configuração ---
col1, col2 = st.columns(2)
with col1:
    top_n = st.slider("Número de autores na rede", 10, 100, 40, key="net_top_n")
with col2:
    st.info(f"A rede será construída com os **{top_n} autores mais produtivos** e suas co-autorias.")

# --- Construir rede ---
with st.spinner("Construindo rede de co-autoria (pode levar alguns segundos)..."):
    nodes, edges = coauthorship_network(df_f, top_n)

if nodes.empty or edges.empty:
    st.warning("Dados insuficientes para construir a rede. Tente aumentar o número de autores.")
    st.stop()

# KPIs da rede
c1, c2, c3, c4 = st.columns(4)
c1.metric("Nós (Autores)", len(nodes))
c2.metric("Arestas (Colaborações)", len(edges))
n_communities = nodes['Comunidade'].nunique()
c3.metric("Comunidades", n_communities)
c4.metric("Colaborações Total", int(edges['Peso'].sum()))

# --- Visualização da rede ---
st.subheader("Rede de Co-autoria")
fig_net = network_graph(nodes, edges, 'Autor', 'Publicações', 'Comunidade',
                        f'Rede de Co-autoria (Top {top_n} Autores)', height=700)
st.plotly_chart(fig_net, use_container_width=True)

st.markdown("---")

# --- Métricas de centralidade ---
st.subheader("📊 Métricas de Centralidade")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Top 15 por Centralidade de Grau**")
    st.markdown("> Autores com mais co-autores na rede.")
    top_degree = nodes.nlargest(15, 'Centralidade Grau')
    fig_deg = bar_chart(top_degree, 'Autor', 'Centralidade Grau',
                        'Centralidade de Grau', orientation='h',
                        color=COLOR_PRIMARY, height=450)
    st.plotly_chart(fig_deg, use_container_width=True)

with col2:
    st.markdown("**Top 15 por Centralidade de Intermediação**")
    st.markdown("> Autores que servem de *ponte* entre diferentes grupos de pesquisa.")
    top_between = nodes.nlargest(15, 'Centralidade Intermediação')
    fig_bet = bar_chart(top_between, 'Autor', 'Centralidade Intermediação',
                        'Centralidade de Intermediação', orientation='h',
                        color=COLOR_SECONDARY, height=450)
    st.plotly_chart(fig_bet, use_container_width=True)

# Scatter: publicações vs centralidade
st.subheader("Relação Publicações × Centralidade")
fig_scatter = px.scatter(
    nodes, x='Publicações', y='Centralidade Grau',
    size='Grau', color='Comunidade', hover_name='Autor',
    title='Publicações vs Centralidade de Grau',
    color_discrete_sequence=COLORS,
)
st.plotly_chart(fig_scatter, use_container_width=True)

st.markdown("---")

# --- Comunidades ---
st.subheader("👥 Comunidades Detectadas")
st.markdown("> Comunidades detectadas pelo algoritmo de Louvain (maximização de modularidade).")

community_summary = nodes.groupby('Comunidade').agg(
    Membros=('Autor', 'count'),
    **{'Total Publicações': ('Publicações', 'sum')},
    **{'Média Publicações': ('Publicações', 'mean')},
).reset_index()
community_summary['Média Publicações'] = community_summary['Média Publicações'].round(1)
community_summary = community_summary.sort_values('Membros', ascending=False)

col1, col2 = st.columns(2)
with col1:
    st.dataframe(community_summary, use_container_width=True)
with col2:
    fig_com = px.pie(community_summary, names='Comunidade', values='Membros',
                     title='Distribuição por Comunidade')
    st.plotly_chart(fig_com, use_container_width=True)

# Membros por comunidade
selected_com = st.selectbox("Selecione uma comunidade para ver membros",
                            sorted(nodes['Comunidade'].unique()), key="sel_community")
members = nodes[nodes['Comunidade'] == selected_com].sort_values('Publicações', ascending=False)
show_dataframe(members, f"Membros da Comunidade {selected_com}", key="dl_community_members")

st.markdown("---")

# Tabelas completas
col1, col2 = st.columns(2)
with col1:
    show_dataframe(nodes.sort_values('Publicações', ascending=False),
                   "Todos os Nós (Autores)", key="dl_net_nodes")
with col2:
    show_dataframe(edges.sort_values('Peso', ascending=False),
                   "Todas as Arestas (Colaborações)", key="dl_net_edges")
