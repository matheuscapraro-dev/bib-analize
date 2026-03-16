"""Exportação de dados e relatório resumo."""
import streamlit as st
import pandas as pd
import numpy as np
import sys, os, io, zipfile, re
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.parser import get_col, safe_split
from utils.data_processing import (
    yearly_stats, lotka_law, bradford_law, author_metrics,
    extract_countries, extract_institutions, extract_keywords,
    extract_references, get_year_col, get_citations_col,
    coauthorship_network, keyword_cooccurrence_network,
    country_collaboration_network, institution_collaboration_network,
    COUNTRY_ISO,
)
from components.charts import (
    bar_chart, line_chart, dual_axis_chart, pie_chart, histogram,
    box_plot, heatmap, choropleth_map, network_graph, wordcloud_to_fig,
    treemap_chart, stacked_area, COLOR_PRIMARY, COLOR_SECONDARY, COLORS,
)
from components.filters import apply_filters, sidebar_upload
import plotly.express as px
import plotly.graph_objects as go

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from PIL import Image

st.set_page_config(page_title="Exportar", page_icon="💾", layout="wide")
st.title("💾 Exportar Dados e Relatório")

sidebar_upload()
df = st.session_state.get('df')
if df is None or df.empty:
    st.warning("⚠️ Nenhum dado carregado. Volte à página inicial e faça upload dos arquivos.")
    st.stop()

df_f = apply_filters(df)


# =====================================================================
# FUNÇÃO AUXILIAR: exportar figura plotly como PNG bytes
# =====================================================================
def _fig_to_png(fig, width=1200, height=600):
    """Converte uma figura Plotly em bytes PNG."""
    fig.update_layout(
        paper_bgcolor='white',
        plot_bgcolor='white',
    )
    return fig.to_image(format='png', width=width, height=height, scale=2)


def _df_to_png(df_table, title="", max_rows=30):
    """Converte um DataFrame em imagem PNG via Plotly Table."""
    display_df = df_table.head(max_rows)
    header_values = list(display_df.columns)
    cell_values = [display_df[col].astype(str).tolist() for col in display_df.columns]
    fig = go.Figure(data=[go.Table(
        header=dict(values=header_values,
                    fill_color='#1f77b4', font=dict(color='white', size=12),
                    align='left'),
        cells=dict(values=cell_values,
                   fill_color='lavender', font=dict(size=11),
                   align='left'),
    )])
    suffix = f" (primeiras {max_rows} linhas)" if len(df_table) > max_rows else ""
    fig.update_layout(title=f"{title}{suffix}", height=max(400, min(900, 50 + len(display_df) * 25)),
                      margin=dict(l=10, r=10, t=40, b=10))
    return fig.to_image(format='png', width=1400, height=max(400, min(900, 50 + len(display_df) * 25)), scale=2)


def _images_to_pdf(images, page_size=landscape(letter), margin=40):
    """Gera bytes de PDF contendo cada imagem em uma página."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=page_size)
    page_width, page_height = page_size

    for _, img_bytes, desc in images:
        try:
            img = Image.open(io.BytesIO(img_bytes))
        except Exception:
            # Skip if image cannot be opened
            continue

        # Ajustar escala da imagem para caber na página, mantendo proporção
        max_width = page_width - 2 * margin
        max_height = page_height - 2 * margin - 50  # espaço para legenda
        img_w, img_h = img.size
        ratio = min(max_width / img_w, max_height / img_h, 1)
        draw_w = img_w * ratio
        draw_h = img_h * ratio

        x = (page_width - draw_w) / 2
        y = (page_height - draw_h) / 2 + 20

        # Desenhar imagem
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        c.drawImage(Image.open(img_buffer), x, y, width=draw_w, height=draw_h)

        # Desenho do texto descritivo
        c.setFont('Helvetica', 10)
        text_y = y - 20
        for line in desc.split('\n'):
            if text_y < margin:
                break
            c.drawString(margin, text_y, line)
            text_y -= 12

        c.showPage()

    c.save()
    buffer.seek(0)
    return buffer.getvalue()


# =====================================================================
# EXPORTAR TUDO EM ZIP
# =====================================================================
st.subheader("📸 Exportar Todos os Gráficos e Tabelas em ZIP")
st.markdown("""
> Gera **todas as visualizações** (gráficos e tabelas) como imagens PNG dentro de um arquivo ZIP,
> acompanhado de um arquivo `descricao.txt` explicando cada imagem.
""")

if st.button("🗜️ Gerar ZIP com Todas as Imagens", type="primary", key="btn_zip_export"):
    images = []  # lista de (nome_arquivo, bytes_png, descricao)
    progress = st.progress(0, text="Preparando exportação...")

    year_col = get_year_col(df_f)
    cit_col = get_citations_col(df_f)
    au_col = get_col(df_f, 'AU')
    so_col = get_col(df_f, 'SO')
    dt_col = get_col(df_f, 'DT')
    la_col = get_col(df_f, 'LA')
    ti_col = get_col(df_f, 'TI')
    doi_col = get_col(df_f, 'DI')
    cr_col = get_col(df_f, 'CR')
    oa_col = get_col(df_f, 'OA')
    fu_col = get_col(df_f, 'FU')
    wc_col = get_col(df_f, 'WC')
    sc_col = get_col(df_f, 'SC')

    total_steps = 13
    step = 0

    # ======== 1. PRODUÇÃO CIENTÍFICA ========
    progress.progress(step / total_steps, text="1/13 — Produção Científica...")
    try:
        stats = yearly_stats(df_f)
        if not stats.empty:
            if 'Citações' in stats.columns:
                fig = dual_axis_chart(stats, 'Ano', 'Publicações', 'Citações',
                                      'Publicações', 'Citações', 'Publicações e Citações por Ano')
            else:
                fig = bar_chart(stats, 'Ano', 'Publicações', 'Publicações por Ano')
            images.append(("01_producao/01_publicacoes_citacoes_ano.png",
                           _fig_to_png(fig),
                           "Gráfico de barras com publicações por ano e linha de citações. Mostra a evolução temporal da produção científica."))

            fig_cum = line_chart(stats, 'Ano', 'Acumulado Publicações', 'Publicações Acumuladas', height=400)
            images.append(("01_producao/02_publicacoes_acumuladas.png",
                           _fig_to_png(fig_cum),
                           "Gráfico de linha com o acumulado de publicações ao longo dos anos."))

            fig_growth = bar_chart(stats, 'Ano', 'Crescimento (%)', 'Crescimento Anual (%)', height=400)
            images.append(("01_producao/03_crescimento_anual.png",
                           _fig_to_png(fig_growth),
                           "Gráfico de barras com a taxa de crescimento percentual anual das publicações."))

            images.append(("01_producao/04_tabela_dados_anuais.png",
                           _df_to_png(stats, "Dados Anuais Detalhados"),
                           "Tabela com dados anuais: publicações, citações, acumulados e taxa de crescimento."))

        if dt_col and dt_col in df_f.columns:
            dt_counts = df_f[dt_col].value_counts().reset_index()
            dt_counts.columns = ['Tipo de Documento', 'Quantidade']
            fig_pie = pie_chart(dt_counts, 'Tipo de Documento', 'Quantidade', 'Tipos de Documento')
            images.append(("01_producao/05_tipos_documento.png",
                           _fig_to_png(fig_pie),
                           "Gráfico de rosca com a distribuição dos tipos de documento (Article, Review, etc.)."))

        if la_col and la_col in df_f.columns:
            lang_counts = df_f[la_col].value_counts().head(15).reset_index()
            lang_counts.columns = ['Idioma', 'Quantidade']
            fig_lang = bar_chart(lang_counts, 'Idioma', 'Quantidade', 'Top 15 Idiomas', orientation='h', height=400)
            images.append(("01_producao/06_idiomas.png",
                           _fig_to_png(fig_lang),
                           "Gráfico de barras horizontais com os 15 idiomas mais frequentes nas publicações."))
    except Exception as e:
        st.warning(f"Aviso na seção Produção: {e}")

    step += 1

    # ======== 2. AUTORES ========
    progress.progress(step / total_steps, text="2/13 — Autores...")
    try:
        metrics = author_metrics(df_f)
        top_n_exp = 20

        if not metrics.empty:
            top_pub = metrics.head(top_n_exp)
            fig1 = bar_chart(top_pub, 'Autor', 'Publicações',
                             f'Top {top_n_exp} Autores — Publicações', orientation='h',
                             color=COLOR_PRIMARY, height=max(400, top_n_exp * 30))
            images.append(("02_autores/01_top_autores_publicacoes.png",
                           _fig_to_png(fig1, height=max(500, top_n_exp * 30)),
                           f"Gráfico de barras horizontais com os {top_n_exp} autores mais produtivos por número de publicações."))

            top_cit = metrics.sort_values('Citações Total', ascending=False).head(top_n_exp)
            fig2 = bar_chart(top_cit, 'Autor', 'Citações Total',
                             f'Top {top_n_exp} Autores — Citações', orientation='h',
                             color=COLOR_SECONDARY, height=max(400, top_n_exp * 30))
            images.append(("02_autores/02_top_autores_citacoes.png",
                           _fig_to_png(fig2, height=max(500, top_n_exp * 30)),
                           f"Gráfico de barras horizontais com os {top_n_exp} autores com mais citações totais."))

            top_h = metrics.sort_values('Índice h', ascending=False).head(top_n_exp)
            fig3 = bar_chart(top_h, 'Autor', 'Índice h',
                             f'Top {top_n_exp} Autores — Índice h', orientation='h',
                             color='#2ca02c', height=max(400, top_n_exp * 30))
            images.append(("02_autores/03_top_autores_h_index.png",
                           _fig_to_png(fig3, height=max(500, top_n_exp * 30)),
                           f"Gráfico de barras horizontais com os {top_n_exp} autores com maior índice h."))

            top_avg = metrics[metrics['Publicações'] >= 3].sort_values(
                'Média Citações', ascending=False).head(top_n_exp)
            if not top_avg.empty:
                fig4 = bar_chart(top_avg, 'Autor', 'Média Citações',
                                 f'Média Citações/Artigo (mín. 3 pubs)', orientation='h',
                                 color='#9467bd', height=max(400, top_n_exp * 30))
                images.append(("02_autores/04_top_autores_media_citacoes.png",
                               _fig_to_png(fig4, height=max(500, top_n_exp * 30)),
                               f"Gráfico de barras horizontais com os {top_n_exp} autores com maior média de citações por artigo (mínimo 3 publicações)."))

            fig_scatter = px.scatter(
                metrics.head(100), x='Publicações', y='Citações Total',
                size='Índice h', hover_name='Autor',
                title='Relação Publicações × Citações (Top 100 autores)',
                color='Índice h', color_continuous_scale='Viridis',
            )
            images.append(("02_autores/05_scatter_publicacoes_citacoes.png",
                           _fig_to_png(fig_scatter),
                           "Gráfico de dispersão mostrando a relação entre publicações e citações dos 100 autores mais produtivos. O tamanho e cor representam o índice h."))

            images.append(("02_autores/06_tabela_metricas_autores.png",
                           _df_to_png(metrics, "Métricas por Autor"),
                           "Tabela com métricas detalhadas por autor: publicações, citações totais, média de citações, índice h, primeiro e último ano de publicação."))

        lotka = lotka_law(df_f)
        if lotka['threshold'] > 0:
            dist = lotka['distribution']
            if not dist.empty:
                fig_lotka = px.scatter(
                    dist, x='Nº Publicações', y='Nº Autores',
                    title='Distribuição de Produtividade (Lei de Lotka) — Escala Log-Log',
                    log_x=True, log_y=True,
                )
                fig_lotka.update_traces(marker=dict(size=8, color=COLOR_PRIMARY))
                images.append(("02_autores/07_lotka_log_log.png",
                               _fig_to_png(fig_lotka),
                               f"Gráfico log-log da Lei de Lotka. Limiar M={lotka['threshold']}, {lotka['core_count']} autores-núcleo de {lotka['total_authors']} total."))

            if not lotka['core_authors'].empty:
                images.append(("02_autores/08_tabela_autores_nucleo.png",
                               _df_to_png(lotka['core_authors'], "Autores-Núcleo (Lei de Lotka)"),
                               "Tabela com autores-núcleo identificados pela Lei de Lotka (publicações >= limiar M)."))
    except Exception as e:
        st.warning(f"Aviso na seção Autores: {e}")

    step += 1

    # ======== 3. PERIÓDICOS ========
    progress.progress(step / total_steps, text="3/13 — Periódicos...")
    try:
        bradford = bradford_law(df_f)
        top_n_exp = 20

        if so_col and so_col in df_f.columns:
            journal_counts = df_f[so_col].value_counts().head(top_n_exp).reset_index()
            journal_counts.columns = ['Periódico', 'Publicações']
            fig_j = bar_chart(journal_counts, 'Periódico', 'Publicações',
                              f'Top {top_n_exp} Periódicos', orientation='h',
                              height=max(400, top_n_exp * 28))
            images.append(("03_periodicos/01_top_periodicos.png",
                           _fig_to_png(fig_j, height=max(500, top_n_exp * 28)),
                           f"Gráfico de barras horizontais com os {top_n_exp} periódicos com mais publicações."))

            if cit_col and cit_col in df_f.columns:
                journal_cit = df_f.groupby(so_col)[cit_col].sum().nlargest(top_n_exp).reset_index()
                journal_cit.columns = ['Periódico', 'Citações']
                fig_jc = bar_chart(journal_cit, 'Periódico', 'Citações',
                                   f'Top {top_n_exp} Periódicos — Citações', orientation='h',
                                   color=COLOR_SECONDARY, height=max(400, top_n_exp * 28))
                images.append(("03_periodicos/02_top_periodicos_citacoes.png",
                               _fig_to_png(fig_jc, height=max(500, top_n_exp * 28)),
                               f"Gráfico de barras horizontais com os {top_n_exp} periódicos com mais citações totais."))

        if bradford.get('zone_summary') is not None and not bradford['zone_summary'].empty:
            fig_bz = pie_chart(bradford['zone_summary'], 'Zona de Bradford', 'Periódicos',
                               'Distribuição de Periódicos por Zona')
            images.append(("03_periodicos/03_bradford_zonas.png",
                           _fig_to_png(fig_bz),
                           "Gráfico de rosca com a distribuição dos periódicos nas 3 zonas de Bradford (Núcleo, Semi-produtivo, Periférico)."))

            images.append(("03_periodicos/04_tabela_zonas_bradford.png",
                           _df_to_png(bradford['zone_summary'], "Zonas de Bradford"),
                           "Tabela resumo das zonas de Bradford: quantidade de periódicos e artigos em cada zona."))

        if bradford.get('journals') is not None and not bradford['journals'].empty:
            journals_df = bradford['journals']
            if 'Rank' not in journals_df.columns:
                journals_df = journals_df.reset_index(drop=True)
                journals_df['Rank'] = range(1, len(journals_df) + 1)
            if '% Acumulado Artigos' not in journals_df.columns:
                journals_df['% Acumulado Artigos'] = (journals_df['Acumulado'] / journals_df['Artigos'].sum() * 100)
            fig_bc = px.line(journals_df, x='Rank', y='% Acumulado Artigos',
                             title='Curva Cumulativa de Bradford')
            fig_bc.add_hline(y=33, line_dash='dash', line_color='red', annotation_text='33%')
            fig_bc.add_hline(y=66, line_dash='dash', line_color='red', annotation_text='66%')
            images.append(("03_periodicos/05_bradford_curva.png",
                           _fig_to_png(fig_bc),
                           "Curva cumulativa de Bradford mostrando a concentração de artigos por periódico. Linhas tracejadas em 33% e 66% delimitam as zonas."))

        # Heatmap periódicos × ano
        if so_col and year_col and so_col in df_f.columns and year_col in df_f.columns:
            top8_journals = df_f[so_col].value_counts().head(8).index.tolist()
            df_top_j = df_f[df_f[so_col].isin(top8_journals)]
            if not df_top_j.empty:
                pivot_wide = df_top_j.groupby([year_col, so_col]).size().reset_index(name='Artigos')
                pivot_table = pivot_wide.pivot_table(index=so_col, columns=year_col, values='Artigos', fill_value=0)
                fig_hm = px.imshow(pivot_table, title='Publicações por Ano e Periódico (Top 8)',
                                   aspect='auto', color_continuous_scale='Blues', text_auto=True)
                fig_hm.update_layout(height=400)
                images.append(("03_periodicos/06_heatmap_periodicos_ano.png",
                               _fig_to_png(fig_hm, height=500),
                               "Heatmap mostrando o número de publicações por ano para os 8 periódicos mais produtivos."))
    except Exception as e:
        st.warning(f"Aviso na seção Periódicos: {e}")

    step += 1

    # ======== 4. PALAVRAS-CHAVE ========
    progress.progress(step / total_steps, text="4/13 — Palavras-chave...")
    try:
        top_n_exp = 20

        kw_author = extract_keywords(df_f, 'DE')
        if not kw_author.empty:
            kw_counts = kw_author.value_counts().head(top_n_exp).reset_index()
            kw_counts.columns = ['Palavra-chave', 'Frequência']
            fig_kw = bar_chart(kw_counts, 'Palavra-chave', 'Frequência',
                               f'Top {top_n_exp} Palavras-chave do Autor', orientation='h',
                               height=max(400, top_n_exp * 22))
            images.append(("04_palavras_chave/01_top_palavras_chave_autor.png",
                           _fig_to_png(fig_kw, height=max(500, top_n_exp * 22)),
                           f"Gráfico de barras horizontais com as {top_n_exp} palavras-chave do autor (DE) mais frequentes."))

            wc_freq = kw_author.value_counts().to_dict()
            fig_wc = wordcloud_to_fig(wc_freq, '☁️ Nuvem de Palavras (Autor)', height=400)
            images.append(("04_palavras_chave/02_nuvem_palavras_autor.png",
                           _fig_to_png(fig_wc, height=450),
                           "Nuvem de palavras das palavras-chave do autor. Termos maiores têm maior frequência."))

        kw_plus = extract_keywords(df_f, 'ID')
        if not kw_plus.empty:
            kw_plus_counts = kw_plus.value_counts().head(top_n_exp).reset_index()
            kw_plus_counts.columns = ['Keyword Plus', 'Frequência']
            fig_kwp = bar_chart(kw_plus_counts, 'Keyword Plus', 'Frequência',
                                f'Top {top_n_exp} Keywords Plus', orientation='h',
                                color=COLOR_SECONDARY, height=max(400, top_n_exp * 22))
            images.append(("04_palavras_chave/03_top_keywords_plus.png",
                           _fig_to_png(fig_kwp, height=max(500, top_n_exp * 22)),
                           f"Gráfico de barras horizontais com as {top_n_exp} Keywords Plus (ID) mais frequentes."))

            wcp_freq = kw_plus.value_counts().to_dict()
            fig_wcp = wordcloud_to_fig(wcp_freq, '☁️ Nuvem de Palavras (Plus)', height=400)
            images.append(("04_palavras_chave/04_nuvem_palavras_plus.png",
                           _fig_to_png(fig_wcp, height=450),
                           "Nuvem de palavras das Keywords Plus (termos indexados automaticamente pela WoS)."))

        # Heatmap palavras-chave × ano
        de_col = get_col(df_f, 'DE')
        if de_col and year_col and de_col in df_f.columns and year_col in df_f.columns:
            top15_kw = kw_author.value_counts().head(15).index.tolist() if not kw_author.empty else []
            if top15_kw:
                rows = []
                for idx, row in df_f.iterrows():
                    if pd.isna(row.get(de_col)):
                        continue
                    for kw in str(row[de_col]).split('; '):
                        kw_low = kw.strip().lower()
                        if kw_low in top15_kw:
                            rows.append({'Ano': row[year_col], 'Palavra-chave': kw_low})
                if rows:
                    kw_year_df = pd.DataFrame(rows)
                    pivot_kw = kw_year_df.groupby(['Palavra-chave', 'Ano']).size().reset_index(name='Freq')
                    pivot_table = pivot_kw.pivot_table(index='Palavra-chave', columns='Ano', values='Freq', fill_value=0)
                    fig_hm_kw = px.imshow(pivot_table, title='Frequência de Palavras-chave por Ano (Top 15)',
                                          aspect='auto', color_continuous_scale='YlOrRd', text_auto=True)
                    fig_hm_kw.update_layout(height=500)
                    images.append(("04_palavras_chave/05_heatmap_palavras_ano.png",
                                   _fig_to_png(fig_hm_kw, height=550),
                                   "Heatmap com a frequência das 15 palavras-chave mais comuns por ano de publicação."))

        # Rede de co-ocorrência de palavras-chave
        nodes_kw, edges_kw = keyword_cooccurrence_network(df_f, field='DE', min_freq=3, top_n=50)
        if not nodes_kw.empty and not edges_kw.empty:
            fig_net_kw = network_graph(nodes_kw, edges_kw, 'Palavra-chave', 'Frequência', 'Cluster',
                                       'Rede de Co-ocorrência de Palavras-chave', height=650)
            images.append(("04_palavras_chave/06_rede_coocorrencia.png",
                           _fig_to_png(fig_net_kw, width=1400, height=700),
                           "Rede de co-ocorrência de palavras-chave. Nós representam termos, arestas indicam co-ocorrência em artigos. Cores representam clusters/comunidades."))
    except Exception as e:
        st.warning(f"Aviso na seção Palavras-chave: {e}")

    step += 1

    # ======== 5. GEOGRÁFICO ========
    progress.progress(step / total_steps, text="5/13 — Geográfico...")
    try:
        countries_df = extract_countries(df_f)
        top_n_exp = 20

        if not countries_df.empty:
            country_counts = countries_df['País'].value_counts().head(top_n_exp).reset_index()
            country_counts.columns = ['País', 'Publicações']
            fig_c = bar_chart(country_counts, 'País', 'Publicações',
                              f'Top {top_n_exp} Países', orientation='h',
                              height=max(400, top_n_exp * 28))
            images.append(("05_geografico/01_top_paises.png",
                           _fig_to_png(fig_c, height=max(500, top_n_exp * 28)),
                           f"Gráfico de barras horizontais com os {top_n_exp} países com mais publicações."))

            if cit_col and cit_col in df_f.columns:
                merged = countries_df.merge(df_f[[cit_col]].reset_index(), left_on='index', right_on='index', how='left')
                country_cit = merged.groupby('País')[cit_col].sum().nlargest(top_n_exp).reset_index()
                country_cit.columns = ['País', 'Citações']
                fig_cc = bar_chart(country_cit, 'País', 'Citações',
                                   f'Top {top_n_exp} Países — Citações', orientation='h',
                                   color=COLOR_SECONDARY, height=max(400, top_n_exp * 28))
                images.append(("05_geografico/02_top_paises_citacoes.png",
                               _fig_to_png(fig_cc, height=max(500, top_n_exp * 28)),
                               f"Gráfico de barras horizontais com os {top_n_exp} países com mais citações totais."))

            # Mapa Choropleth publicações
            all_countries = countries_df['País'].value_counts().reset_index()
            all_countries.columns = ['País', 'Publicações']
            all_countries['ISO'] = all_countries['País'].map(COUNTRY_ISO)
            map_valid = all_countries.dropna(subset=['ISO'])
            if not map_valid.empty:
                fig_map = px.choropleth(
                    map_valid, locations='ISO', color='Publicações',
                    title='Publicações por País',
                    color_continuous_scale='Blues', projection='natural earth',
                )
                fig_map.update_layout(geo=dict(showframe=False, showcoastlines=True), height=500)
                images.append(("05_geografico/03_mapa_publicacoes.png",
                               _fig_to_png(fig_map, width=1400, height=600),
                               "Mapa mundi (choropleth) com a distribuição geográfica das publicações por país. Cores mais escuras indicam maior produção."))

            # Evolução top 5 países
            if year_col and year_col in df_f.columns:
                top5_countries = countries_df['País'].value_counts().head(5).index.tolist()
                temp_rows = []
                for idx_row, row in df_f.iterrows():
                    c_data = countries_df[countries_df['index'] == idx_row]
                    for _, c_row in c_data.iterrows():
                        if c_row['País'] in top5_countries:
                            temp_rows.append({'Ano': row[year_col], 'País': c_row['País']})
                if temp_rows:
                    temp_df = pd.DataFrame(temp_rows)
                    temp_counts = temp_df.groupby(['Ano', 'País']).size().reset_index(name='Publicações')
                    fig_evol = px.line(temp_counts, x='Ano', y='Publicações', color='País',
                                      title='Evolução dos Top 5 Países', height=450)
                    images.append(("05_geografico/04_evolucao_top5_paises.png",
                                   _fig_to_png(fig_evol, height=500),
                                   "Gráfico de linhas com a evolução temporal das publicações dos 5 países mais produtivos."))

        # Rede de colaboração internacional
        nodes_c, edges_c = country_collaboration_network(df_f, top_n=30)
        if not nodes_c.empty and not edges_c.empty:
            fig_net_c = network_graph(nodes_c, edges_c, 'País', 'Publicações', 'Comunidade',
                                      'Rede de Colaboração Internacional', height=600)
            images.append(("05_geografico/05_rede_colaboracao_paises.png",
                           _fig_to_png(fig_net_c, width=1400, height=650),
                           "Rede de colaboração internacional entre países. Arestas indicam co-autoria entre pesquisadores de países diferentes."))

        images.append(("05_geografico/06_tabela_paises.png",
                       _df_to_png(countries_df['País'].value_counts().reset_index().rename(
                           columns={'index': 'País', 'count': 'Publicações'}), "Publicações por País"),
                       "Tabela com todos os países e o número de publicações."))
    except Exception as e:
        st.warning(f"Aviso na seção Geográfico: {e}")

    step += 1

    # ======== 6. INSTITUIÇÕES ========
    progress.progress(step / total_steps, text="6/13 — Instituições...")
    try:
        insts = extract_institutions(df_f)
        top_n_exp = 20

        if not insts.empty:
            inst_counts = insts.value_counts().head(top_n_exp).reset_index()
            inst_counts.columns = ['Instituição', 'Publicações']
            fig_i = bar_chart(inst_counts, 'Instituição', 'Publicações',
                              f'Top {top_n_exp} Instituições', orientation='h',
                              height=max(400, top_n_exp * 28))
            images.append(("06_instituicoes/01_top_instituicoes.png",
                           _fig_to_png(fig_i, height=max(500, top_n_exp * 28)),
                           f"Gráfico de barras horizontais com as {top_n_exp} instituições com mais publicações."))

        nodes_i, edges_i = institution_collaboration_network(df_f, top_n=30)
        if not nodes_i.empty and not edges_i.empty:
            fig_net_i = network_graph(nodes_i, edges_i, 'Instituição', 'Publicações', 'Comunidade',
                                      'Rede de Colaboração Institucional', height=650)
            images.append(("06_instituicoes/02_rede_colaboracao_institucional.png",
                           _fig_to_png(fig_net_i, width=1400, height=700),
                           "Rede de colaboração institucional. Nós representam instituições, arestas indicam co-autoria entre pesquisadores de instituições diferentes."))
    except Exception as e:
        st.warning(f"Aviso na seção Instituições: {e}")

    step += 1

    # ======== 7. CITAÇÕES ========
    progress.progress(step / total_steps, text="7/13 — Citações...")
    try:
        if cit_col and cit_col in df_f.columns:
            citations_series = df_f[cit_col].fillna(0).astype(int)

            fig_hist = px.histogram(citations_series, nbins=50, title='Distribuição de Citações',
                                    labels={'value': 'Citações', 'count': 'Nº Artigos'})
            fig_hist.update_traces(marker_color=COLOR_PRIMARY)
            images.append(("07_citacoes/01_distribuicao_citacoes.png",
                           _fig_to_png(fig_hist),
                           "Histograma com a distribuição de citações. A maioria dos artigos recebe poucas citações (distribuição de lei de potência)."))

            fig_box = px.box(df_f, y=cit_col, title='Box Plot de Citações',
                             labels={cit_col: 'Citações'})
            images.append(("07_citacoes/02_boxplot_citacoes.png",
                           _fig_to_png(fig_box),
                           "Box plot mostrando a mediana, quartis e outliers da distribuição de citações."))

            citations_nonzero = citations_series[citations_series > 0]
            if len(citations_nonzero) > 0:
                cit_dist = citations_nonzero.value_counts().sort_index().reset_index()
                cit_dist.columns = ['Citações', 'Nº Artigos']
                fig_log = px.scatter(cit_dist, x='Citações', y='Nº Artigos',
                                     log_x=True, log_y=True,
                                     title='Distribuição de Citações (Escala Log-Log)')
                fig_log.update_traces(marker=dict(size=6, color=COLOR_PRIMARY))
                images.append(("07_citacoes/03_citacoes_log_log.png",
                               _fig_to_png(fig_log),
                               "Gráfico log-log da distribuição de citações. Padrão linear em escala log indica lei de potência."))

            # Top artigos mais citados
            cols_show = [c for c in [ti_col, au_col, so_col, year_col, cit_col] if c and c in df_f.columns]
            if cols_show:
                top_articles = df_f.nlargest(20, cit_col)[cols_show].reset_index(drop=True)
                images.append(("07_citacoes/04_tabela_top_artigos_citados.png",
                               _df_to_png(top_articles, "Top 20 Artigos Mais Citados"),
                               "Tabela com os 20 artigos mais citados do dataset, incluindo título, autores, periódico, ano e citações."))

            # Box por tipo documento
            if dt_col and dt_col in df_f.columns:
                top_types = df_f[dt_col].value_counts().head(5).index.tolist()
                df_types = df_f[df_f[dt_col].isin(top_types)]
                fig_box_dt = px.box(df_types, x=dt_col, y=cit_col, color=dt_col,
                                    title='Distribuição de Citações por Tipo de Documento',
                                    labels={dt_col: 'Tipo', cit_col: 'Citações'})
                fig_box_dt.update_layout(showlegend=False)
                images.append(("07_citacoes/05_boxplot_citacoes_tipo.png",
                               _fig_to_png(fig_box_dt),
                               "Box plot comparando a distribuição de citações entre diferentes tipos de documento (Article, Review, etc.)."))

        # Referências mais citadas
        if cr_col and cr_col in df_f.columns:
            refs = extract_references(df_f)
            if not refs.empty:
                ref_counts = refs.value_counts().head(15).reset_index()
                ref_counts.columns = ['Referência', 'Frequência']
                fig_refs = bar_chart(ref_counts, 'Referência', 'Frequência',
                                     'Top 15 Referências Mais Citadas', orientation='h',
                                     color=COLOR_SECONDARY, height=500)
                images.append(("07_citacoes/06_top_referencias.png",
                               _fig_to_png(fig_refs, height=550),
                               "Gráfico de barras horizontais com as 15 referências mais frequentemente citadas no dataset."))

                # Distribuição anos referências
                ref_years = []
                for ref in refs:
                    match = re.search(r'\b(19|20)\d{2}\b', str(ref))
                    if match:
                        ref_years.append(int(match.group()))
                if ref_years:
                    ref_years_s = pd.Series(ref_years)
                    ref_years_s = ref_years_s[(ref_years_s >= 1900) & (ref_years_s <= datetime.now().year)]
                    if len(ref_years_s) > 0:
                        fig_ry = px.histogram(ref_years_s, nbins=50,
                                              title='Distribuição dos Anos das Referências',
                                              labels={'value': 'Ano da Referência'})
                        fig_ry.update_traces(marker_color='#9467bd')
                        images.append(("07_citacoes/07_anos_referencias.png",
                                       _fig_to_png(fig_ry),
                                       "Histograma com a distribuição dos anos das referências citadas. Permite avaliar a idade média da literatura citada."))
    except Exception as e:
        st.warning(f"Aviso na seção Citações: {e}")

    step += 1

    # ======== 8. FINANCIAMENTO ========
    progress.progress(step / total_steps, text="8/13 — Financiamento...")
    try:
        if fu_col and fu_col in df_f.columns:
            agencies = safe_split(df_f[fu_col], sep='; ')
            if not agencies.empty:
                agency_counts = agencies.value_counts().head(20).reset_index()
                agency_counts.columns = ['Agência', 'Artigos']
                fig_fu = bar_chart(agency_counts, 'Agência', 'Artigos',
                                   'Top 20 Agências Financiadoras', orientation='h',
                                   height=max(400, 20 * 28))
                images.append(("08_financiamento/01_top_agencias.png",
                               _fig_to_png(fig_fu, height=max(500, 20 * 28)),
                               "Gráfico de barras horizontais com as 20 agências financiadoras mais frequentes."))

            # Financiados vs não financiados
            if cit_col and cit_col in df_f.columns:
                df_funded = df_f.copy()
                df_funded['Financiamento'] = df_funded[fu_col].apply(
                    lambda x: 'Sim' if pd.notna(x) and str(x).strip() else 'Não'
                )
                fig_box_fu = px.box(df_funded, x='Financiamento', y=cit_col,
                                    title='Citações: Financiados vs Não Financiados',
                                    color='Financiamento')
                images.append(("08_financiamento/02_boxplot_financiamento.png",
                               _fig_to_png(fig_box_fu),
                               "Box plot comparando citações de artigos financiados vs não financiados. Permite avaliar o impacto do financiamento."))
    except Exception as e:
        st.warning(f"Aviso na seção Financiamento: {e}")

    step += 1

    # ======== 9. ACESSO ABERTO ========
    progress.progress(step / total_steps, text="9/13 — Acesso Aberto...")
    try:
        if oa_col and oa_col in df_f.columns:
            oa_counts = df_f[oa_col].value_counts().reset_index()
            oa_counts.columns = ['Tipo OA', 'Artigos']

            fig_oa_pie = pie_chart(oa_counts, 'Tipo OA', 'Artigos', 'Distribuição de Acesso Aberto')
            images.append(("09_acesso_aberto/01_distribuicao_oa.png",
                           _fig_to_png(fig_oa_pie),
                           "Gráfico de rosca com a distribuição dos tipos de acesso aberto (Gold, Green, Bronze, etc.)."))

            fig_oa_bar = bar_chart(oa_counts, 'Tipo OA', 'Artigos', 'Artigos por Tipo OA', height=350)
            images.append(("09_acesso_aberto/02_barras_oa.png",
                           _fig_to_png(fig_oa_bar),
                           "Gráfico de barras com a quantidade de artigos por tipo de acesso aberto."))

            if cit_col and cit_col in df_f.columns:
                fig_box_oa = px.box(df_f, x=oa_col, y=cit_col, color=oa_col,
                                    title='Distribuição de Citações por Tipo de Acesso',
                                    labels={oa_col: 'Tipo OA', cit_col: 'Citações'})
                images.append(("09_acesso_aberto/03_boxplot_citacoes_oa.png",
                               _fig_to_png(fig_box_oa),
                               "Box plot comparando distribuição de citações entre diferentes tipos de acesso aberto."))
    except Exception as e:
        st.warning(f"Aviso na seção Acesso Aberto: {e}")

    step += 1

    # ======== 10. REDES DE CO-AUTORIA ========
    progress.progress(step / total_steps, text="10/13 — Redes de Co-autoria...")
    try:
        nodes_co, edges_co = coauthorship_network(df_f, top_n=50)
        if not nodes_co.empty and not edges_co.empty:
            fig_net_co = network_graph(nodes_co, edges_co, 'Autor', 'Publicações', 'Comunidade',
                                       'Rede de Co-autoria (Top 50 Autores)', height=700)
            images.append(("10_redes/01_rede_coautoria.png",
                           _fig_to_png(fig_net_co, width=1400, height=750),
                           "Rede de co-autoria dos 50 autores mais produtivos. Nós representam autores, arestas indicam co-autoria. Cores representam comunidades detectadas pelo algoritmo de Louvain."))

            if 'Centralidade Grau' in nodes_co.columns:
                top_degree = nodes_co.nlargest(15, 'Centralidade Grau')
                fig_deg = bar_chart(top_degree, 'Autor', 'Centralidade Grau',
                                    'Centralidade de Grau', orientation='h',
                                    color=COLOR_PRIMARY, height=450)
                images.append(("10_redes/02_centralidade_grau.png",
                               _fig_to_png(fig_deg, height=500),
                               "Gráfico de barras horizontais com os 15 autores com maior centralidade de grau na rede de co-autoria."))

            if 'Centralidade Intermediação' in nodes_co.columns:
                top_between = nodes_co.nlargest(15, 'Centralidade Intermediação')
                fig_bet = bar_chart(top_between, 'Autor', 'Centralidade Intermediação',
                                    'Centralidade de Intermediação', orientation='h',
                                    color=COLOR_SECONDARY, height=450)
                images.append(("10_redes/03_centralidade_intermediacao.png",
                               _fig_to_png(fig_bet, height=500),
                               "Gráfico de barras horizontais com os 15 autores com maior centralidade de intermediação (betweenness) na rede."))

            fig_scatter_net = px.scatter(
                nodes_co, x='Publicações', y='Centralidade Grau',
                size='Grau', color='Comunidade',
                title='Publicações vs Centralidade de Grau',
                hover_name='Autor',
            )
            images.append(("10_redes/04_scatter_publicacoes_centralidade.png",
                           _fig_to_png(fig_scatter_net),
                           "Gráfico de dispersão relacionando publicações com centralidade de grau. Tamanho indica grau (conexões). Cores indicam comunidades."))

            community_summary = nodes_co.groupby('Comunidade').agg(
                Membros=('Autor', 'count')).reset_index()
            fig_com = px.pie(community_summary, names='Comunidade', values='Membros',
                             title='Distribuição por Comunidade')
            images.append(("10_redes/05_distribuicao_comunidades.png",
                           _fig_to_png(fig_com),
                           "Gráfico de pizza com a distribuição de autores por comunidade detectada na rede de co-autoria."))

            images.append(("10_redes/06_tabela_nos_rede.png",
                           _df_to_png(nodes_co.sort_values('Publicações', ascending=False), "Nós da Rede de Co-autoria"),
                           "Tabela com métricas de cada autor na rede: publicações, comunidade, grau, centralidade de grau e intermediação."))
    except Exception as e:
        st.warning(f"Aviso na seção Redes: {e}")

    step += 1

    # ======== 11. CATEGORIAS ========
    progress.progress(step / total_steps, text="11/13 — Categorias...")
    try:
        top_n_exp = 20
        if wc_col and wc_col in df_f.columns:
            cats = safe_split(df_f[wc_col], sep='; ').str.strip()
            if not cats.empty:
                cat_counts = cats.value_counts().head(top_n_exp).reset_index()
                cat_counts.columns = ['Categoria', 'Artigos']
                fig_cat = bar_chart(cat_counts, 'Categoria', 'Artigos',
                                    f'Top {top_n_exp} Categorias WoS', orientation='h',
                                    height=max(400, top_n_exp * 28))
                images.append(("11_categorias/01_top_categorias_wos.png",
                               _fig_to_png(fig_cat, height=max(500, top_n_exp * 28)),
                               f"Gráfico de barras horizontais com as {top_n_exp} categorias WoS mais frequentes."))

                cat_tree = cats.value_counts().head(30).reset_index()
                cat_tree.columns = ['Categoria', 'Artigos']
                fig_tree = px.treemap(cat_tree, path=['Categoria'], values='Artigos',
                                      title='Treemap das Categorias',
                                      color='Artigos', color_continuous_scale='Blues')
                fig_tree.update_layout(height=500)
                images.append(("11_categorias/02_treemap_categorias.png",
                               _fig_to_png(fig_tree, height=550),
                               "Treemap (mapa de árvore) das 30 categorias mais frequentes. A área de cada bloco é proporcional ao número de artigos."))

        if sc_col and sc_col in df_f.columns:
            areas = safe_split(df_f[sc_col], sep='; ').str.strip()
            if not areas.empty:
                area_counts = areas.value_counts().head(top_n_exp).reset_index()
                area_counts.columns = ['Área de Pesquisa', 'Artigos']
                fig_area = bar_chart(area_counts, 'Área de Pesquisa', 'Artigos',
                                     'Top 20 Áreas de Pesquisa', orientation='h',
                                     color=COLOR_SECONDARY, height=550)
                images.append(("11_categorias/03_areas_pesquisa.png",
                               _fig_to_png(fig_area, height=600),
                               "Gráfico de barras horizontais com as 20 áreas de pesquisa (Research Areas SC) mais frequentes."))
    except Exception as e:
        st.warning(f"Aviso na seção Categorias: {e}")

    step += 1

    # ======== 12. VISÃO GERAL / MÉTRICAS ========
    progress.progress(step / total_steps, text="12/13 — Métricas gerais...")
    try:
        total = len(df_f)
        years = df_f[year_col] if year_col and year_col in df_f.columns else pd.Series()
        period = f"{int(years.min())}–{int(years.max())}" if len(years) > 0 else "N/A"
        total_cit = int(df_f[cit_col].sum()) if cit_col and cit_col in df_f.columns else 0
        avg_cit = round(total_cit / total, 1) if total > 0 else 0
        n_authors = safe_split(df_f[au_col], sep='; ').nunique() if au_col and au_col in df_f.columns else 0
        n_journals = df_f[so_col].nunique() if so_col and so_col in df_f.columns else 0

        overview = pd.DataFrame({
            'Métrica': ['Total de artigos', 'Período', 'Total de autores', 'Total de periódicos',
                        'Total de citações', 'Média citações/artigo'],
            'Valor': [f'{total:,}', period, f'{n_authors:,}', f'{n_journals:,}',
                      f'{total_cit:,}', str(avg_cit)]
        })
        images.append(("00_visao_geral/01_tabela_visao_geral.png",
                       _df_to_png(overview, "Visão Geral do Dataset"),
                       "Tabela resumo com as principais métricas do dataset: total de artigos, período, autores, periódicos, citações."))
    except Exception as e:
        st.warning(f"Aviso na seção Métricas: {e}")

    step += 1

    # ======== 13. GERAR ZIP ========
    progress.progress(step / total_steps, text="13/13 — Gerando ZIP...")
    try:
        # Gerar arquivo de descrição
        desc_lines = ["DESCRIÇÃO DAS IMAGENS EXPORTADAS",
                       "=" * 50,
                       f"Data de exportação: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                       f"Total de imagens: {len(images)}",
                       f"Total de registros no dataset: {len(df_f):,}",
                       "",
                       "=" * 50,
                       ""]

        for filename, _, desc in sorted(images, key=lambda x: x[0]):
            folder = filename.split('/')[0]
            folder_name = folder.replace('_', ' ').lstrip('0123456789').strip().upper()
            desc_lines.append(f"Arquivo: {filename}")
            desc_lines.append(f"Descrição: {desc}")
            desc_lines.append("")

        desc_text = "\n".join(desc_lines)

        # Criar ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("descricao.txt", desc_text.encode('utf-8'))
            for filename, png_bytes, _ in images:
                zf.writestr(filename, png_bytes)

        zip_buffer.seek(0)
        progress.progress(1.0, text="Concluído!")

        st.success(f"✅ ZIP gerado com **{len(images)} imagens** organizadas em pastas temáticas!")
        st.download_button(
            "📥 Baixar ZIP com Todas as Imagens",
            zip_buffer.getvalue(),
            f"bibliometria_imagens_{datetime.now().strftime('%Y%m%d_%H%M')}.zip",
            "application/zip",
            key="dl_zip_all_images"
        )

        # Também gerar PDF com todas as páginas (1 imagem por página)
        try:
            pdf_bytes = _images_to_pdf(images)
            st.download_button(
                "📄 Baixar PDF com Todas as Páginas",
                pdf_bytes,
                f"bibliometria_paginas_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                "application/pdf",
                key="dl_pdf_all_pages"
            )
        except Exception as e:
            st.warning(f"Não foi possível gerar PDF: {e}")

    except Exception as e:
        st.error(f"Erro ao gerar ZIP: {e}")

st.markdown("---")
st.subheader("📦 Exportar Dataset Completo")
st.markdown("> Baixe o dataset consolidado (com filtros aplicados) em formato CSV.")

csv_full = df_f.to_csv(index=False).encode('utf-8-sig')
st.download_button(
    "⬇️ Baixar Dataset Completo (CSV)",
    csv_full,
    "dataset_bibliometrico_completo.csv",
    "text/csv",
    key="dl_full_dataset"
)

col1, col2 = st.columns(2)
with col1:
    st.metric("Registros", f"{len(df_f):,}")
with col2:
    st.metric("Colunas", f"{len(df_f.columns)}")

st.markdown("---")

# --- Exportar análises individuais ---
st.subheader("📊 Exportar Análises Individuais")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Dados Anuais", "Autores", "Periódicos", "Palavras-chave", "Países"
])

with tab1:
    stats = yearly_stats(df_f)
    if not stats.empty:
        csv = stats.to_csv(index=False).encode('utf-8-sig')
        st.download_button("⬇️ Dados Anuais (CSV)", csv, "dados_anuais.csv", "text/csv", key="dl_annual")
        st.dataframe(stats, use_container_width=True, height=300)

with tab2:
    metrics = author_metrics(df_f)
    if not metrics.empty:
        csv = metrics.to_csv(index=False).encode('utf-8-sig')
        st.download_button("⬇️ Métricas de Autores (CSV)", csv, "autores_metricas.csv", "text/csv", key="dl_authors")
        st.dataframe(metrics.head(50), use_container_width=True, height=300)

with tab3:
    bradford = bradford_law(df_f)
    if bradford['journals'] is not None and not bradford['journals'].empty:
        csv = bradford['journals'].to_csv(index=False).encode('utf-8-sig')
        st.download_button("⬇️ Periódicos Bradford (CSV)", csv, "periodicos_bradford.csv", "text/csv", key="dl_bradford_exp")
        st.dataframe(bradford['journals'].head(50), use_container_width=True, height=300)

with tab4:
    kw = extract_keywords(df_f, 'DE')
    if not kw.empty:
        kw_df = kw.value_counts().reset_index()
        kw_df.columns = ['Palavra-chave', 'Frequência']
        csv = kw_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("⬇️ Palavras-chave (CSV)", csv, "palavras_chave.csv", "text/csv", key="dl_kw_exp")
        st.dataframe(kw_df.head(50), use_container_width=True, height=300)

with tab5:
    countries = extract_countries(df_f)
    if not countries.empty:
        c_df = countries['País'].value_counts().reset_index()
        c_df.columns = ['País', 'Publicações']
        csv = c_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("⬇️ Países (CSV)", csv, "paises.csv", "text/csv", key="dl_countries_exp")
        st.dataframe(c_df.head(50), use_container_width=True, height=300)

st.markdown("---")

# --- Relatório resumo ---
st.subheader("📝 Relatório Resumo")
st.markdown("> Gera um relatório textual com as principais métricas e achados.")

if st.button("📄 Gerar Relatório", type="primary"):
    with st.spinner("Gerando relatório..."):
        year_col = get_year_col(df_f)
        cit_col = get_citations_col(df_f)
        au_col = get_col(df_f, 'AU')
        so_col = get_col(df_f, 'SO')

        # Dados
        total = len(df_f)
        years = df_f[year_col] if year_col else pd.Series()
        period = f"{int(years.min())}–{int(years.max())}" if len(years) > 0 else "N/A"
        total_cit = int(df_f[cit_col].sum()) if cit_col else 0
        avg_cit = round(total_cit / total, 1) if total > 0 else 0

        n_authors = safe_split(df_f[au_col], sep='; ').nunique() if au_col else 0
        n_journals = df_f[so_col].nunique() if so_col else 0

        # Lotka
        lotka = lotka_law(df_f)

        # Bradford
        brad = bradford_law(df_f)

        # Top artigo
        top_article = ""
        if cit_col:
            top = df_f.nlargest(1, cit_col)
            ti_col = get_col(df_f, 'TI')
            if ti_col and not top.empty:
                top_article = f"{top.iloc[0].get(ti_col, 'N/A')} ({int(top.iloc[0][cit_col])} citações)"

        report = f"""# Relatório Bibliométrico

## Visão Geral
- **Total de artigos:** {total:,}
- **Período:** {period}
- **Total de autores:** {n_authors:,}
- **Total de periódicos:** {n_journals:,}
- **Total de citações:** {total_cit:,}
- **Média de citações/artigo:** {avg_cit}

## Análise de Autores (Lei de Lotka)
- **Autor mais produtivo:** {lotka['n_max']} publicações
- **Limiar para autores-núcleo (M):** {lotka['threshold']}
- **Autores-núcleo identificados:** {lotka['core_count']:,} de {lotka['total_authors']:,} ({round(lotka['core_count']/max(1,lotka['total_authors'])*100, 1)}%)

## Análise de Periódicos (Lei de Bradford)
- **Total de periódicos:** {brad.get('total_journals', 'N/A')}

## Artigo Mais Citado
- {top_article or 'N/A'}

---
*Relatório gerado automaticamente pelo BibAnalyze.*
"""

        st.markdown(report)

        st.download_button(
            "⬇️ Baixar Relatório (Markdown)",
            report.encode('utf-8'),
            "relatorio_bibliometrico.md",
            "text/markdown",
            key="dl_report"
        )
