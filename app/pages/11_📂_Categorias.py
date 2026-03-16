"""Análise de Categorias WoS — áreas de pesquisa, interdisciplinaridade."""
import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.parser import get_col, safe_split
from utils.data_processing import get_year_col, get_citations_col
from components.charts import bar_chart, pie_chart, treemap_chart, COLOR_PRIMARY, COLOR_SECONDARY, COLORS
from components.filters import apply_filters, sidebar_upload
from components.tables import show_dataframe
import plotly.express as px

st.set_page_config(page_title="Categorias WoS", page_icon="📂", layout="wide")
st.title("📂 Categorias e Áreas de Pesquisa")

sidebar_upload()
df = st.session_state.get('df')
if df is None or df.empty:
    st.warning("⚠️ Nenhum dado carregado. Volte à página inicial e faça upload dos arquivos.")
    st.stop()

df_f = apply_filters(df)
wc_col = get_col(df_f, 'WC')
sc_col = get_col(df_f, 'SC')
year_col = get_year_col(df_f)
cit_col = get_citations_col(df_f)

# --- Categorias WoS (WC) ---
if wc_col and wc_col in df_f.columns:
    st.subheader("📊 Categorias Web of Science")
    st.markdown("> Categorias atribuídas pelo WoS a cada periódico. Um artigo pode pertencer a múltiplas categorias.")

    top_n = st.slider("Número de categorias (Top N)", 5, 50, 20, key="cat_top_n")

    categories = safe_split(df_f[wc_col], sep='; ').str.strip()
    cat_counts = categories.value_counts().head(top_n).reset_index()
    cat_counts.columns = ['Categoria', 'Artigos']

    col1, col2 = st.columns([2, 1])
    with col1:
        fig1 = bar_chart(cat_counts, 'Categoria', 'Artigos',
                         f'Top {top_n} Categorias WoS', orientation='h',
                         height=max(400, top_n * 28))
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        # Treemap
        fig_tree = px.treemap(cat_counts.head(30), path=['Categoria'], values='Artigos',
                              title='Treemap das Categorias', color='Artigos',
                              color_continuous_scale='Blues')
        fig_tree.update_layout(height=500)
        st.plotly_chart(fig_tree, use_container_width=True)

    st.markdown("---")

    # Interdisciplinaridade
    st.subheader("🔗 Interdisciplinaridade")
    st.markdown("> Artigos classificados em múltiplas categorias indicam pesquisa interdisciplinar.")

    n_cats_per_article = df_f[wc_col].dropna().apply(
        lambda x: len([c.strip() for c in str(x).split('; ') if c.strip()])
    )
    avg_cats = n_cats_per_article.mean()
    max_cats = n_cats_per_article.max()
    multi_cat = (n_cats_per_article > 1).sum()
    pct_multi = round(multi_cat / len(n_cats_per_article) * 100, 1) if len(n_cats_per_article) > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Média de categorias/artigo", f"{avg_cats:.1f}")
    c2.metric("Máx. categorias em um artigo", max_cats)
    c3.metric("% artigos multidisciplinares", f"{pct_multi}%")

    fig_dist = px.histogram(n_cats_per_article, nbins=max_cats,
                            title='Distribuição do Nº de Categorias por Artigo',
                            labels={'value': 'Nº de Categorias', 'count': 'Artigos'})
    fig_dist.update_traces(marker_color=COLOR_PRIMARY)
    st.plotly_chart(fig_dist, use_container_width=True)

    # Top pares de categorias
    st.subheader("🔀 Pares de Categorias Mais Comuns")
    pairs = []
    for _, row in df_f.iterrows():
        if pd.isna(row.get(wc_col)):
            continue
        cats = sorted([c.strip() for c in str(row[wc_col]).split('; ') if c.strip()])
        for i, c1_val in enumerate(cats):
            for c2_val in cats[i+1:]:
                pairs.append(f"{c1_val} + {c2_val}")

    if pairs:
        pair_counts = pd.Series(pairs).value_counts().head(15).reset_index()
        pair_counts.columns = ['Par de Categorias', 'Artigos']
        fig_pairs = bar_chart(pair_counts, 'Par de Categorias', 'Artigos',
                              'Top 15 Pares de Categorias', orientation='h',
                              color='#9467bd', height=450)
        st.plotly_chart(fig_pairs, use_container_width=True)

    # Evolução temporal das top categorias
    if year_col and year_col in df_f.columns:
        st.markdown("---")
        st.subheader("📅 Evolução Temporal das Categorias")
        top_5_cats = cat_counts.head(8)['Categoria'].tolist()

        records = []
        for idx, row in df_f.iterrows():
            if pd.isna(row.get(wc_col)) or pd.isna(row.get(year_col)):
                continue
            year = int(row[year_col])
            cats = [c.strip() for c in str(row[wc_col]).split('; ')]
            for cat in cats:
                if cat in top_5_cats:
                    records.append({'Ano': year, 'Categoria': cat})

        if records:
            temp_df = pd.DataFrame(records)
            temp_counts = temp_df.groupby(['Ano', 'Categoria']).size().reset_index(name='Artigos')

            fig_temp = px.line(temp_counts, x='Ano', y='Artigos', color='Categoria',
                               title='Evolução das Top 8 Categorias', markers=True,
                               color_discrete_sequence=COLORS)
            fig_temp.update_layout(height=450)
            st.plotly_chart(fig_temp, use_container_width=True)

else:
    st.info("Campo de Categorias WoS (WC) não encontrado.")

st.markdown("---")

# --- Áreas de Pesquisa (SC) ---
if sc_col and sc_col in df_f.columns:
    st.subheader("🔬 Áreas de Pesquisa (Research Areas)")
    areas = safe_split(df_f[sc_col], sep='; ').str.strip()
    area_counts = areas.value_counts().head(20).reset_index()
    area_counts.columns = ['Área de Pesquisa', 'Artigos']

    fig_area = bar_chart(area_counts, 'Área de Pesquisa', 'Artigos',
                         'Top 20 Áreas de Pesquisa', orientation='h',
                         color=COLOR_SECONDARY, height=550)
    st.plotly_chart(fig_area, use_container_width=True)

    show_dataframe(area_counts, "Áreas de Pesquisa", key="dl_research_areas")
