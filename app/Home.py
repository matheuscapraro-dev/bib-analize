"""
BibAnalyze — Análise Bibliométrica de Exportações Web of Science
Dashboard principal com upload de dados e visão geral.
"""
import streamlit as st
import pandas as pd
import sys
import os

# Adicionar diretório app ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.parser import FIELD_MAP
from components.metrics import show_kpis
from components.filters import apply_filters, sidebar_upload

st.set_page_config(
    page_title="BibAnalyze — Análise Bibliométrica WoS",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 BibAnalyze")
st.markdown("### Análise Bibliométrica de Exportações Web of Science")

# --- Upload de dados (sidebar compartilhado) ---
sidebar_upload()

# --- Conteúdo principal ---
df = st.session_state.get('df')

if df is not None and not df.empty:
    # Aplicar filtros
    df_filtered = apply_filters(df)
    st.session_state.df_filtered = df_filtered

    # KPIs
    show_kpis(df_filtered)

    st.markdown("---")

    # Resumo dos dados
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📋 Campos Disponíveis")
        available_fields = []
        for col_name in df.columns:
            inv_map = {v: k for k, v in FIELD_MAP.items()}
            wos_code = inv_map.get(col_name, "")
            non_null = df[col_name].notna().sum()
            pct = round(non_null / len(df) * 100, 1)
            available_fields.append({
                'Campo': col_name,
                'Código WoS': wos_code,
                'Preenchimento': f"{pct}%",
                'Registros': non_null,
            })
        fields_df = pd.DataFrame(available_fields)
        st.dataframe(fields_df, use_container_width=True, height=400)

    with col2:
        st.subheader("📊 Amostra dos Dados")
        st.dataframe(df_filtered.head(20), use_container_width=True, height=400)

    st.markdown("---")
    st.markdown("""
    ### 📖 Como usar
    Use o menu lateral esquerdo para navegar entre as análises disponíveis:

    | Página | Análise |
    |--------|---------|
    | 📈 Produção Científica | Tendências temporais, crescimento, tipos de documento |
    | 👥 Autores | Rankings, Lei de Lotka, índice h, métricas por autor |
    | 📚 Periódicos | Rankings, Lei de Bradford, evolução temporal |
    | 🔑 Palavras-chave | Rankings, word cloud, rede de co-ocorrência, tendências |
    | 🌍 Geográfico | Mapas, rankings por país, colaboração internacional |
    | 🏛️ Instituições | Rankings, rede de colaboração institucional |
    | 📝 Citações | Distribuição, artigos mais citados, referências mais citadas |
    | 💰 Financiamento | Agências financiadoras, impacto do financiamento |
    | 🔓 Acesso Aberto | Distribuição OA, impacto nas citações |
    | 🕸️ Redes | Redes de co-autoria com métricas de centralidade |
    | 📂 Categorias WoS | Áreas de pesquisa, interdisciplinaridade |
    | 💾 Exportar | Download de dados e relatório resumo |
    """)
else:
    st.info("""
    ### 👋 Bem-vindo ao BibAnalyze!

    **Como começar:**
    1. No menu lateral, faça upload dos arquivos de exportação do **Web of Science** (formato `.txt` tab-delimited)
    2. Clique em **Processar Dados**
    3. Explore as análises usando o menu de páginas no sidebar

    **Formatos suportados:**
    - Exportação completa do Web of Science (`.txt` tab-delimited) — recomendado
    - Arquivo CSV já consolidado

    **Dica:** Você pode fazer upload de múltiplos arquivos de uma vez. O sistema consolidará
    automaticamente e removerá duplicatas usando o ID único WoS.

    ---
    **Análises disponíveis:** Produção científica, autores (Lei de Lotka), periódicos (Lei de Bradford),
    palavras-chave (word cloud + redes), análise geográfica (mapas), instituições, citações e referências,
    financiamento, acesso aberto, redes de co-autoria, categorias WoS, e exportação de dados.
    """)
