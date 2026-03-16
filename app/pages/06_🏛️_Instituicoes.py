"""Análise de Instituições — rankings e rede de colaboração institucional."""
import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.parser import get_col, safe_split
from utils.data_processing import (
    extract_institutions, institution_collaboration_network,
    get_citations_col, normalize_country
)
from components.charts import bar_chart, network_graph, COLOR_PRIMARY, COLOR_SECONDARY
from components.filters import apply_filters, sidebar_upload
from components.tables import show_dataframe

st.set_page_config(page_title="Instituições", page_icon="🏛️", layout="wide")
st.title("🏛️ Análise de Instituições")

sidebar_upload()
df = st.session_state.get('df')
if df is None or df.empty:
    st.warning("⚠️ Nenhum dado carregado. Volte à página inicial e faça upload dos arquivos.")
    st.stop()

df_f = apply_filters(df)
cit_col = get_citations_col(df_f)
top_n = st.slider("Número de instituições (Top N)", 5, 50, 20, key="inst_top_n")

# --- Top por publicações ---
st.subheader(f"Top {top_n} Instituições por Publicações")
institutions = extract_institutions(df_f)
if institutions.empty:
    st.error("Não foi possível extrair instituições. Verifique se os dados incluem campos C3 ou RP.")
    st.stop()

inst_counts = institutions.value_counts().head(top_n).reset_index()
inst_counts.columns = ['Instituição', 'Publicações']

fig1 = bar_chart(inst_counts, 'Instituição', 'Publicações',
                 f'Top {top_n} Instituições', orientation='h',
                 height=max(400, top_n * 28))
st.plotly_chart(fig1, use_container_width=True)

# --- Top por citações ---
if cit_col and cit_col in df_f.columns:
    st.subheader(f"Top {top_n} Instituições por Citações")
    # Determinar campo de instituição: C3 ou RP (fallback)
    inst_col = get_col(df_f, 'C3') or get_col(df_f, 'RP')
    if inst_col and inst_col in df_f.columns:
        records = []
        for idx, row in df_f.iterrows():
            if pd.isna(row.get(inst_col)):
                continue
            cit = int(row.get(cit_col, 0) or 0)
            # Extrair instituições de acordo com o campo usado
            if inst_col == get_col(df_f, 'C3'):
                insts = [i.strip() for i in str(row[inst_col]).split('; ') if i.strip()]
            else:
                # RP: extrair instituição
                val = str(row[inst_col])
                parts = val.split('), ')
                if len(parts) > 1:
                    inst_parts = parts[1].split(', ')
                    insts = [inst_parts[0].strip()] if inst_parts else []
                else:
                    inst_parts = val.split(', ')
                    insts = [inst_parts[0].strip()] if len(inst_parts) > 1 else []
            for inst in insts:
                if inst:
                    records.append({'Instituição': inst, 'Citações': cit})

    if records:
        inst_cit = pd.DataFrame(records).groupby('Instituição')['Citações'].sum()
        inst_cit = inst_cit.sort_values(ascending=False).head(top_n).reset_index()
        inst_cit.columns = ['Instituição', 'Citações']

        fig2 = bar_chart(inst_cit, 'Instituição', 'Citações',
                         f'Top {top_n} Instituições — Citações', orientation='h',
                         color=COLOR_SECONDARY, height=max(400, top_n * 28))
        st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# --- Rede de colaboração institucional ---
st.subheader("🕸️ Rede de Colaboração Institucional")
st.markdown("""
> A rede mostra colaborações entre instituições (artigos com múltiplas afiliações).
> Nós maiores = mais publicações. Arestas mais grossas = mais colaborações conjuntas.
""")

net_n = st.slider("Máximo de instituições na rede", 10, 50, 25, key="inst_net_n")
with st.spinner("Construindo rede institucional..."):
    nodes, edges = institution_collaboration_network(df_f, net_n)

if not nodes.empty and not edges.empty:
    fig_net = network_graph(nodes, edges, 'Instituição', 'Publicações', 'Comunidade',
                            'Rede de Colaboração Institucional', height=650)
    st.plotly_chart(fig_net, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        show_dataframe(nodes.sort_values('Publicações', ascending=False),
                       "Instituições na Rede", key="dl_inst_nodes")
    with col2:
        show_dataframe(edges.sort_values('Peso', ascending=False),
                       "Colaborações", key="dl_inst_edges")
else:
    st.info("Dados insuficientes para gerar a rede.")

# --- Tabela detalhada ---
st.markdown("---")
inst_detail = institutions.value_counts().reset_index()
inst_detail.columns = ['Instituição', 'Publicações']

# Tentar associar país via RP
rp_col = get_col(df_f, 'RP')
if rp_col and rp_col in df_f.columns:
    inst_country_map = {}
    for _, row in df_f.iterrows():
        if pd.isna(row.get(rp_col)):
            continue
        val = str(row[rp_col])
        elements = val.split(', ')
        if len(elements) >= 2:
            country = normalize_country(elements[-1].strip().rstrip('.'))
            # Extrair instituição do RP
            parts = val.split('), ')
            inst_name = parts[1].split(', ')[0].strip() if len(parts) > 1 else elements[0].strip()
            if inst_name and country:
                inst_country_map[inst_name] = country

    inst_detail['País'] = inst_detail['Instituição'].map(inst_country_map)

show_dataframe(inst_detail, "Tabela Completa — Instituições", key="dl_institutions")
