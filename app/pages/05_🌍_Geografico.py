"""Análise Geográfica — mapas, ranking de países, colaboração internacional."""
import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.parser import get_col
from utils.data_processing import (
    extract_countries, normalize_country, country_collaboration_network,
    get_year_col, get_citations_col, COUNTRY_ISO
)
from components.charts import (
    bar_chart, choropleth_map, network_graph, line_chart,
    COLOR_PRIMARY, COLOR_SECONDARY, COLORS
)
from components.filters import apply_filters, sidebar_upload
from components.tables import show_dataframe
import plotly.express as px

st.set_page_config(page_title="Geográfico", page_icon="🌍", layout="wide")
st.title("🌍 Análise Geográfica")

sidebar_upload()
df = st.session_state.get('df')
if df is None or df.empty:
    st.warning("⚠️ Nenhum dado carregado. Volte à página inicial e faça upload dos arquivos.")
    st.stop()

df_f = apply_filters(df)
year_col = get_year_col(df_f)
cit_col = get_citations_col(df_f)
top_n = st.slider("Número de países (Top N)", 5, 50, 20, key="geo_top_n")

# --- Extrair países ---
with st.spinner("Extraindo informações geográficas..."):
    countries_df = extract_countries(df_f)

if countries_df.empty:
    st.warning("Não foi possível extrair informações de países. Os campos de endereços (C1/RP) podem estar vazios.")
    st.info("Verifique se o arquivo de exportação contém informações de endereços/afiliações.")
    st.stop()

# Contagem por país
country_counts = countries_df['País'].value_counts().reset_index()
country_counts.columns = ['País', 'Publicações']

# --- Top N por publicações ---
st.subheader(f"Top {top_n} Países por Publicações")
top_countries = country_counts.head(top_n)
fig1 = bar_chart(top_countries, 'País', 'Publicações',
                 f'Top {top_n} Países', orientation='h',
                 height=max(400, top_n * 28))
st.plotly_chart(fig1, use_container_width=True)

# --- Top por citações ---
if cit_col and cit_col in df_f.columns:
    st.subheader(f"Top {top_n} Países por Citações")
    # Associar citações por país usando o índice original
    merged = countries_df.merge(
        df_f[[cit_col]].reset_index().rename(columns={'index': 'index'}),
        left_on='index', right_on='index', how='left'
    )
    country_cit = merged.groupby('País')[cit_col].sum().sort_values(ascending=False).head(top_n).reset_index()
    country_cit.columns = ['País', 'Citações']

    fig2 = bar_chart(country_cit, 'País', 'Citações',
                     f'Top {top_n} Países — Citações', orientation='h',
                     color=COLOR_SECONDARY, height=max(400, top_n * 28))
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# --- Mapa mundi ---
st.subheader("🗺️ Mapa Mundi — Publicações por País")
st.markdown("> O mapa mostra a distribuição geográfica da produção científica. Cores mais escuras indicam maior número de publicações.")

map_df = country_counts.copy()
map_df['ISO'] = map_df['País'].map(COUNTRY_ISO)
# Para países sem mapeamento ISO, tentar usar o nome direto
map_df_valid = map_df.dropna(subset=['ISO'])

if not map_df_valid.empty:
    fig_map = px.choropleth(
        map_df_valid, locations='ISO', color='Publicações',
        hover_name='País', color_continuous_scale='Blues',
        projection='natural earth',
        title='Publicações por País'
    )
    fig_map.update_layout(height=500, geo=dict(showframe=False, showcoastlines=True))
    st.plotly_chart(fig_map, use_container_width=True)

    # Mapa por citações
    if cit_col and cit_col in df_f.columns:
        cit_map = country_cit.copy()
        cit_map['ISO'] = cit_map['País'].map(COUNTRY_ISO)
        cit_map_valid = cit_map.dropna(subset=['ISO'])
        if not cit_map_valid.empty:
            fig_map2 = px.choropleth(
                cit_map_valid, locations='ISO', color='Citações',
                hover_name='País', color_continuous_scale='Reds',
                projection='natural earth',
                title='Citações por País'
            )
            fig_map2.update_layout(height=500, geo=dict(showframe=False, showcoastlines=True))
            st.plotly_chart(fig_map2, use_container_width=True)

st.markdown("---")

# --- Evolução temporal dos top 5 países ---
if year_col and year_col in df_f.columns:
    st.subheader("📅 Evolução Temporal dos Top 5 Países")
    top_5 = country_counts.head(5)['País'].tolist()

    # Usar C1 ou RP como fallback para extração temporal
    addr_col = get_col(df_f, 'C1') or get_col(df_f, 'RP')
    temporal_records = []
    if addr_col:
        for idx, row in df_f.iterrows():
            if pd.isna(row.get(addr_col)) or pd.isna(row.get(year_col)):
                continue
            year = int(row[year_col])
            for part in str(row[addr_col]).split('; '):
                elements = part.split(', ')
                if elements:
                    c = elements[-1].strip().rstrip('.')
                    if len(c) > 2 and not c.isdigit() and '@' not in c and len(c) < 50:
                        country = normalize_country(c)
                        if country in top_5:
                            temporal_records.append({'Ano': year, 'País': country})

    if temporal_records:
        temp_df = pd.DataFrame(temporal_records)
        temp_counts = temp_df.groupby(['Ano', 'País']).size().reset_index(name='Publicações')

        fig_temp = px.line(temp_counts, x='Ano', y='Publicações', color='País',
                           title='Evolução dos Top 5 Países', markers=True,
                           color_discrete_sequence=COLORS)
        fig_temp.update_layout(height=450)
        st.plotly_chart(fig_temp, use_container_width=True)

st.markdown("---")

# --- Rede de colaboração internacional ---
st.subheader("🕸️ Rede de Colaboração Internacional")
st.markdown("""
> A rede mostra colaborações entre países (artigos com co-autores de diferentes países).
> Nós maiores = mais publicações. Arestas mais grossas = mais colaborações.
> Cores representam comunidades de pesquisa detectadas automaticamente.
""")

net_n = st.slider("Máximo de países na rede", 10, 50, 25, key="geo_net_n")
with st.spinner("Construindo rede de colaboração..."):
    nodes, edges = country_collaboration_network(df_f, net_n)

if not nodes.empty and not edges.empty:
    fig_net = network_graph(nodes, edges, 'País', 'Publicações', 'Comunidade',
                            'Rede de Colaboração Internacional', height=600)
    st.plotly_chart(fig_net, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        show_dataframe(nodes.sort_values('Publicações', ascending=False),
                       "Países na Rede", key="dl_geo_nodes")
    with col2:
        show_dataframe(edges.sort_values('Peso', ascending=False),
                       "Colaborações", key="dl_geo_edges")
else:
    st.info("Dados insuficientes para gerar a rede de colaboração.")

st.markdown("---")
show_dataframe(country_counts, "Tabela Completa — Publicações por País", key="dl_countries")
