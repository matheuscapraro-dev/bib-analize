"""Resumo Geral — visão consolidada de todas as análises com botão de copiar e PDF completo."""
import streamlit as st
import pandas as pd
import numpy as np
import re, io
from datetime import datetime
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.parser import get_col, safe_split
from utils.data_processing import (
    yearly_stats, lotka_law, bradford_law, author_metrics,
    extract_countries, extract_institutions, extract_keywords,
    extract_references, extract_authors,
    get_year_col, get_citations_col,
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

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
    Table as RLTable, TableStyle, PageBreak, KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor, white, black, lightgrey
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from PIL import Image as PILImage

st.set_page_config(page_title="Resumo Geral", page_icon="📋", layout="wide")
st.title("📋 Resumo Geral — Relatório Completo")

sidebar_upload()
df = st.session_state.get('df')
if df is None or df.empty:
    st.warning("⚠️ Nenhum dado carregado. Volte à página inicial e faça upload dos arquivos.")
    st.stop()

df_f = apply_filters(df)


st.set_page_config(page_title="Resumo Geral", page_icon="📋", layout="wide")
st.title("📋 Resumo Geral — Relatório Completo")

sidebar_upload()
df = st.session_state.get('df')
if df is None or df.empty:
    st.warning("⚠️ Nenhum dado carregado. Volte à página inicial e faça upload dos arquivos.")
    st.stop()

df_f = apply_filters(df)


# =====================================================================
#  Helpers para geração de imagens (PNG bytes)
# =====================================================================

def _fig_to_png(fig, width=1200, height=600):
    fig.update_layout(paper_bgcolor='white', plot_bgcolor='white')
    return fig.to_image(format='png', width=width, height=height, scale=2)


def _df_to_png(df_table, title="", max_rows=30):
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
    h = max(400, min(900, 50 + len(display_df) * 25))
    fig.update_layout(title=f"{title}{suffix}", height=h, margin=dict(l=10, r=10, t=40, b=10))
    return fig.to_image(format='png', width=1400, height=h, scale=2)


# =====================================================================
#  PDF Builder — reportlab Platypus
# =====================================================================

def _build_pdf(df: pd.DataFrame) -> bytes:
    """Gera PDF completo com texto + gráficos de todas as seções."""

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )
    page_w = landscape(A4)[0] - 3 * cm
    styles = getSampleStyleSheet()

    # ----- estilos customizados -----
    styles.add(ParagraphStyle('CoverTitle', parent=styles['Title'],
                              fontSize=28, spaceAfter=12, alignment=TA_CENTER,
                              textColor=HexColor('#1f77b4')))
    styles.add(ParagraphStyle('CoverSub', parent=styles['Normal'],
                              fontSize=14, alignment=TA_CENTER, spaceAfter=6,
                              textColor=HexColor('#555555')))
    styles.add(ParagraphStyle('Section', parent=styles['Heading1'],
                              fontSize=18, spaceBefore=20, spaceAfter=8,
                              textColor=HexColor('#1f77b4'),
                              borderPadding=(0, 0, 4, 0)))
    styles.add(ParagraphStyle('SubSection', parent=styles['Heading2'],
                              fontSize=14, spaceBefore=12, spaceAfter=6,
                              textColor=HexColor('#333333')))
    styles.add(ParagraphStyle('Body', parent=styles['Normal'],
                              fontSize=10, spaceAfter=4, leading=14))
    styles.add(ParagraphStyle('SmallBody', parent=styles['Normal'],
                              fontSize=9, spaceAfter=3, leading=12,
                              textColor=HexColor('#444444')))
    styles.add(ParagraphStyle('Caption', parent=styles['Normal'],
                              fontSize=8, alignment=TA_CENTER, spaceAfter=10,
                              textColor=HexColor('#666666'), italic=True))

    elems = []  # flowable list

    # Colunas auxiliares
    year_col = get_year_col(df);  cit_col = get_citations_col(df)
    au_col = get_col(df, 'AU');   so_col = get_col(df, 'SO')
    ti_col = get_col(df, 'TI');   de_col = get_col(df, 'DE')
    id_col = get_col(df, 'ID');   dt_col = get_col(df, 'DT')
    la_col = get_col(df, 'LA');   fu_col = get_col(df, 'FU')
    oa_col = get_col(df, 'OA');   cr_col = get_col(df, 'CR')
    doi_col = get_col(df, 'DI');  wc_col = get_col(df, 'WC')
    sc_col = get_col(df, 'SC')
    total = len(df)

    # ---------- helpers internos ----------
    def _add_img(png_bytes, caption="", max_w=None):
        """Adiciona imagem PNG ao flowable list."""
        try:
            img = PILImage.open(io.BytesIO(png_bytes))
        except Exception:
            return
        w, h = img.size
        mw = max_w or page_w
        ratio = min(mw / w, 500 / h, 1)
        rw, rh = w * ratio, h * ratio
        img_buf = io.BytesIO(png_bytes)
        elems.append(RLImage(img_buf, width=rw, height=rh))
        if caption:
            elems.append(Paragraph(caption, styles['Caption']))

    def _add_table(data, col_widths=None):
        """Adiciona tabela reportlab a partir de lista de listas."""
        t = RLTable(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1f77b4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, lightgrey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#f5f5f5')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elems.append(t)
        elems.append(Spacer(1, 8))

    def _p(text, style='Body'):
        elems.append(Paragraph(text, styles[style]))

    def _sp(h=10):
        elems.append(Spacer(1, h))

    # ============================================================
    #  CAPA
    # ============================================================
    _sp(80)
    _p("RELATÓRIO BIBLIOMÉTRICO COMPLETO", 'CoverTitle')
    _sp(20)
    period = "N/A"
    if year_col and year_col in df.columns:
        years = df[year_col].dropna()
        if len(years) > 0:
            period = f"{int(years.min())} – {int(years.max())}"
    _p(f"Período: {period}", 'CoverSub')
    _p(f"Total de registros: {total:,}", 'CoverSub')
    _p(f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')} pelo BibAnalyze", 'CoverSub')
    _sp(30)

    total_cit = int(df[cit_col].sum()) if cit_col and cit_col in df.columns else 0
    avg_cit = round(total_cit / total, 1) if total > 0 else 0
    n_authors = safe_split(df[au_col], sep='; ').nunique() if au_col and au_col in df.columns else 0
    n_journals = df[so_col].nunique() if so_col and so_col in df.columns else 0

    overview_data = [
        ['Indicador', 'Valor'],
        ['Total de artigos', f'{total:,}'],
        ['Período coberto', period],
        ['Total de autores únicos', f'{n_authors:,}'],
        ['Total de periódicos', f'{n_journals:,}'],
        ['Total de citações', f'{total_cit:,}'],
        ['Média de citações/artigo', str(avg_cit)],
    ]
    if dt_col and dt_col in df.columns:
        dt_top = df[dt_col].value_counts()
        overview_data.append(['Tipo predominante', f'{dt_top.index[0]} ({dt_top.iloc[0]:,})'])
    if la_col and la_col in df.columns:
        la_top = df[la_col].value_counts().head(1)
        overview_data.append(['Idioma predominante', f'{la_top.index[0]} ({la_top.iloc[0]:,})'])
    _add_table(overview_data)
    elems.append(PageBreak())

    # ============================================================
    #  SEÇÃO 1 — PRODUÇÃO CIENTÍFICA
    # ============================================================
    _p("1. Produção Científica", 'Section')
    try:
        stats = yearly_stats(df)
        if not stats.empty:
            best = stats.loc[stats['Publicações'].idxmax()]
            _p(f"<b>Ano mais produtivo:</b> {int(best['Ano'])} ({int(best['Publicações'])} publicações)", 'Body')
            if len(stats) >= 2:
                f5 = stats.head(5)['Publicações'].mean()
                l5 = stats.tail(5)['Publicações'].mean()
                gr = round((l5 / max(1, f5) - 1) * 100, 1)
                _p(f"<b>Crescimento</b> (primeiros 5 vs últimos 5 anos): {gr:+.1f}%", 'Body')
            _sp()

            if 'Citações' in stats.columns:
                fig = dual_axis_chart(stats, 'Ano', 'Publicações', 'Citações',
                                      'Publicações', 'Citações', 'Publicações e Citações por Ano')
            else:
                fig = bar_chart(stats, 'Ano', 'Publicações', 'Publicações por Ano')
            _add_img(_fig_to_png(fig), "Publicações e citações por ano")

            fig_cum = line_chart(stats, 'Ano', 'Acumulado Publicações', 'Publicações Acumuladas', height=400)
            _add_img(_fig_to_png(fig_cum), "Publicações acumuladas")

            fig_growth = bar_chart(stats, 'Ano', 'Crescimento (%)', 'Crescimento Anual (%)', height=400)
            _add_img(_fig_to_png(fig_growth), "Taxa de crescimento anual (%)")

            _add_img(_df_to_png(stats, "Dados Anuais"), "Tabela de dados anuais detalhados")

        if dt_col and dt_col in df.columns:
            dt_counts = df[dt_col].value_counts().reset_index()
            dt_counts.columns = ['Tipo de Documento', 'Quantidade']
            fig_pie = pie_chart(dt_counts, 'Tipo de Documento', 'Quantidade', 'Tipos de Documento')
            _add_img(_fig_to_png(fig_pie), "Distribuição por tipo de documento")

        if la_col and la_col in df.columns:
            lang_c = df[la_col].value_counts().head(15).reset_index()
            lang_c.columns = ['Idioma', 'Quantidade']
            fig_lang = bar_chart(lang_c, 'Idioma', 'Quantidade', 'Top 15 Idiomas', orientation='h', height=400)
            _add_img(_fig_to_png(fig_lang), "Top 15 idiomas das publicações")
    except Exception:
        pass
    elems.append(PageBreak())

    # ============================================================
    #  SEÇÃO 2 — AUTORES
    # ============================================================
    _p("2. Análise de Autores", 'Section')
    try:
        am = author_metrics(df)
        top_n = 20
        if not am.empty:
            top_pub = am.head(top_n)
            fig1 = bar_chart(top_pub, 'Autor', 'Publicações',
                             f'Top {top_n} Autores — Publicações', orientation='h',
                             color=COLOR_PRIMARY, height=max(400, top_n * 30))
            _add_img(_fig_to_png(fig1, height=max(500, top_n * 30)),
                     f"Top {top_n} autores por número de publicações")

            top_cit = am.sort_values('Citações Total', ascending=False).head(top_n)
            fig2 = bar_chart(top_cit, 'Autor', 'Citações Total',
                             f'Top {top_n} Autores — Citações', orientation='h',
                             color=COLOR_SECONDARY, height=max(400, top_n * 30))
            _add_img(_fig_to_png(fig2, height=max(500, top_n * 30)),
                     f"Top {top_n} autores por citações totais")

            top_h = am.sort_values('Índice h', ascending=False).head(top_n)
            fig3 = bar_chart(top_h, 'Autor', 'Índice h',
                             f'Top {top_n} Autores — Índice h', orientation='h',
                             color='#2ca02c', height=max(400, top_n * 30))
            _add_img(_fig_to_png(fig3, height=max(500, top_n * 30)),
                     f"Top {top_n} autores por índice h")

            fig_scatter = px.scatter(
                am.head(100), x='Publicações', y='Citações Total',
                size='Índice h', hover_name='Autor',
                title='Publicações × Citações (Top 100 autores)',
                color='Índice h', color_continuous_scale='Viridis',
            )
            _add_img(_fig_to_png(fig_scatter), "Relação publicações × citações dos 100 autores mais produtivos")

            _add_img(_df_to_png(am, "Métricas por Autor"), "Tabela de métricas detalhadas por autor")

        lotka = lotka_law(df)
        if lotka.get('total_authors', 0) > 0:
            _p("2.1 Lei de Lotka", 'SubSection')
            _p(f"<b>Limiar M:</b> {lotka['threshold']}  |  "
               f"<b>Autores-núcleo:</b> {lotka['core_count']} de {lotka['total_authors']} "
               f"({lotka['core_count']/lotka['total_authors']*100:.1f}%)", 'Body')
            dist = lotka['distribution']
            if not dist.empty:
                fig_l = px.scatter(dist, x='Nº Publicações', y='Nº Autores',
                                   title='Lei de Lotka — Escala Log-Log', log_x=True, log_y=True)
                fig_l.update_traces(marker=dict(size=8, color=COLOR_PRIMARY))
                _add_img(_fig_to_png(fig_l), "Distribuição log-log (Lei de Lotka)")
            if not lotka['core_authors'].empty:
                _add_img(_df_to_png(lotka['core_authors'], "Autores-Núcleo"),
                         "Tabela de autores-núcleo (Lei de Lotka)")

        if au_col and au_col in df.columns:
            avg_co = round(df[au_col].str.count('; ').mean() + 1, 1)
            n_single = (df[au_col].str.count('; ') == 0).sum()
            _p(f"<b>Média de autores/artigo:</b> {avg_co}  |  "
               f"<b>Artigos com autor único:</b> {n_single} ({n_single/total*100:.1f}%)", 'Body')
    except Exception:
        pass
    elems.append(PageBreak())

    # ============================================================
    #  SEÇÃO 3 — PERIÓDICOS
    # ============================================================
    _p("3. Análise de Periódicos", 'Section')
    try:
        bradford = bradford_law(df)
        top_n = 20
        if so_col and so_col in df.columns:
            jc = df[so_col].value_counts().head(top_n).reset_index()
            jc.columns = ['Periódico', 'Publicações']
            fig_j = bar_chart(jc, 'Periódico', 'Publicações',
                              f'Top {top_n} Periódicos', orientation='h',
                              height=max(400, top_n * 28))
            _add_img(_fig_to_png(fig_j, height=max(500, top_n * 28)),
                     f"Top {top_n} periódicos por publicações")

            if cit_col and cit_col in df.columns:
                jcit = df.groupby(so_col)[cit_col].sum().nlargest(top_n).reset_index()
                jcit.columns = ['Periódico', 'Citações']
                fig_jc = bar_chart(jcit, 'Periódico', 'Citações',
                                   f'Top {top_n} Periódicos — Citações', orientation='h',
                                   color=COLOR_SECONDARY, height=max(400, top_n * 28))
                _add_img(_fig_to_png(fig_jc, height=max(500, top_n * 28)),
                         f"Top {top_n} periódicos por citações")

        if bradford.get('zone_summary') is not None and not bradford['zone_summary'].empty:
            _p("3.1 Lei de Bradford", 'SubSection')
            _p(f"<b>Total de periódicos:</b> {bradford['total_journals']}", 'Body')
            fig_bz = pie_chart(bradford['zone_summary'], 'Zona de Bradford', 'Periódicos',
                               'Distribuição por Zona de Bradford')
            _add_img(_fig_to_png(fig_bz), "Periódicos por zona de Bradford")
            _add_img(_df_to_png(bradford['zone_summary'], "Zonas de Bradford"),
                     "Resumo das zonas de Bradford")

        if bradford.get('journals') is not None and not bradford['journals'].empty:
            journals_df = bradford['journals'].copy()
            if 'Rank' not in journals_df.columns:
                journals_df['Rank'] = range(1, len(journals_df) + 1)
            if '% Acumulado Artigos' not in journals_df.columns:
                journals_df['% Acumulado Artigos'] = journals_df['Acumulado'] / journals_df['Artigos'].sum() * 100
            fig_bc = px.line(journals_df, x='Rank', y='% Acumulado Artigos', title='Curva de Bradford')
            fig_bc.add_hline(y=33, line_dash='dash', line_color='red', annotation_text='33%')
            fig_bc.add_hline(y=66, line_dash='dash', line_color='red', annotation_text='66%')
            _add_img(_fig_to_png(fig_bc), "Curva cumulativa de Bradford")

        if so_col and year_col and so_col in df.columns and year_col in df.columns:
            top8 = df[so_col].value_counts().head(8).index.tolist()
            df_t8 = df[df[so_col].isin(top8)]
            if not df_t8.empty:
                piv = df_t8.groupby([year_col, so_col]).size().reset_index(name='Artigos')
                pt = piv.pivot_table(index=so_col, columns=year_col, values='Artigos', fill_value=0)
                fig_hm = px.imshow(pt, title='Publicações por Ano × Periódico (Top 8)',
                                   aspect='auto', color_continuous_scale='Blues', text_auto=True)
                fig_hm.update_layout(height=400)
                _add_img(_fig_to_png(fig_hm, height=500), "Heatmap periódicos × ano")
    except Exception:
        pass
    elems.append(PageBreak())

    # ============================================================
    #  SEÇÃO 4 — PALAVRAS-CHAVE
    # ============================================================
    _p("4. Palavras-Chave", 'Section')
    try:
        top_n = 20
        kw_author = extract_keywords(df, 'DE')
        if not kw_author.empty:
            kw_c = kw_author.value_counts().head(top_n).reset_index()
            kw_c.columns = ['Palavra-chave', 'Frequência']
            fig_kw = bar_chart(kw_c, 'Palavra-chave', 'Frequência',
                               f'Top {top_n} Palavras-chave do Autor', orientation='h',
                               height=max(400, top_n * 22))
            _add_img(_fig_to_png(fig_kw, height=max(500, top_n * 22)),
                     f"Top {top_n} palavras-chave do autor (DE)")

            wc_freq = kw_author.value_counts().to_dict()
            fig_wc = wordcloud_to_fig(wc_freq, 'Nuvem de Palavras (Autor)', height=400)
            _add_img(_fig_to_png(fig_wc, height=450), "Nuvem de palavras — palavras-chave do autor")

        kw_plus = extract_keywords(df, 'ID')
        if not kw_plus.empty:
            kwp = kw_plus.value_counts().head(top_n).reset_index()
            kwp.columns = ['Keyword Plus', 'Frequência']
            fig_kwp = bar_chart(kwp, 'Keyword Plus', 'Frequência',
                                f'Top {top_n} Keywords Plus', orientation='h',
                                color=COLOR_SECONDARY, height=max(400, top_n * 22))
            _add_img(_fig_to_png(fig_kwp, height=max(500, top_n * 22)),
                     f"Top {top_n} Keywords Plus (ID)")

            wcp_freq = kw_plus.value_counts().to_dict()
            fig_wcp = wordcloud_to_fig(wcp_freq, 'Nuvem de Palavras (Plus)', height=400)
            _add_img(_fig_to_png(fig_wcp, height=450), "Nuvem de palavras — Keywords Plus")

        # Heatmap kw × ano
        if de_col and year_col and de_col in df.columns and year_col in df.columns and not kw_author.empty:
            top15_kw = kw_author.value_counts().head(15).index.tolist()
            rows_kw = []
            for _, row in df.iterrows():
                if pd.isna(row.get(de_col)):
                    continue
                for kw in str(row[de_col]).split('; '):
                    kw_low = kw.strip().lower()
                    if kw_low in top15_kw:
                        rows_kw.append({'Ano': row[year_col], 'Palavra-chave': kw_low})
            if rows_kw:
                kdf = pd.DataFrame(rows_kw)
                piv_kw = kdf.groupby(['Palavra-chave', 'Ano']).size().reset_index(name='Freq')
                pt_kw = piv_kw.pivot_table(index='Palavra-chave', columns='Ano', values='Freq', fill_value=0)
                fig_hm_kw = px.imshow(pt_kw, title='Frequência de Palavras-chave por Ano (Top 15)',
                                      aspect='auto', color_continuous_scale='YlOrRd', text_auto=True)
                fig_hm_kw.update_layout(height=500)
                _add_img(_fig_to_png(fig_hm_kw, height=550), "Heatmap palavras-chave × ano")

        # Rede co-ocorrência
        nkw, ekw = keyword_cooccurrence_network(df, field='DE', min_freq=3, top_n=50)
        if not nkw.empty and not ekw.empty:
            fig_nkw = network_graph(nkw, ekw, 'Palavra-chave', 'Frequência', 'Cluster',
                                    'Rede de Co-ocorrência de Palavras-chave', height=650)
            _add_img(_fig_to_png(fig_nkw, width=1400, height=700),
                     "Rede de co-ocorrência de palavras-chave")
    except Exception:
        pass
    elems.append(PageBreak())

    # ============================================================
    #  SEÇÃO 5 — GEOGRÁFICO
    # ============================================================
    _p("5. Análise Geográfica", 'Section')
    try:
        countries_df = extract_countries(df)
        top_n = 20
        if not countries_df.empty:
            cc = countries_df['País'].value_counts()
            _p(f"<b>Total de países:</b> {cc.shape[0]}", 'Body')

            cc_top = cc.head(top_n).reset_index()
            cc_top.columns = ['País', 'Publicações']
            fig_c = bar_chart(cc_top, 'País', 'Publicações',
                              f'Top {top_n} Países', orientation='h',
                              height=max(400, top_n * 28))
            _add_img(_fig_to_png(fig_c, height=max(500, top_n * 28)),
                     f"Top {top_n} países por publicações")

            if cit_col and cit_col in df.columns:
                merged = countries_df.merge(df[[cit_col]].reset_index(), left_on='index', right_on='index', how='left')
                ccit = merged.groupby('País')[cit_col].sum().nlargest(top_n).reset_index()
                ccit.columns = ['País', 'Citações']
                fig_cc = bar_chart(ccit, 'País', 'Citações',
                                   f'Top {top_n} Países — Citações', orientation='h',
                                   color=COLOR_SECONDARY, height=max(400, top_n * 28))
                _add_img(_fig_to_png(fig_cc, height=max(500, top_n * 28)),
                         f"Top {top_n} países por citações")

            # Mapa
            all_c = cc.reset_index()
            all_c.columns = ['País', 'Publicações']
            all_c['ISO'] = all_c['País'].map(COUNTRY_ISO)
            mv = all_c.dropna(subset=['ISO'])
            if not mv.empty:
                fig_map = px.choropleth(mv, locations='ISO', color='Publicações',
                                        title='Publicações por País',
                                        color_continuous_scale='Blues', projection='natural earth')
                fig_map.update_layout(geo=dict(showframe=False, showcoastlines=True), height=500)
                _add_img(_fig_to_png(fig_map, width=1400, height=600),
                         "Mapa mundi — distribuição geográfica das publicações")

            # Evolução top 5
            if year_col and year_col in df.columns:
                top5c = cc.head(5).index.tolist()
                t_rows = []
                for idx_r, row in df.iterrows():
                    cd = countries_df[countries_df['index'] == idx_r]
                    for _, cr in cd.iterrows():
                        if cr['País'] in top5c:
                            t_rows.append({'Ano': row[year_col], 'País': cr['País']})
                if t_rows:
                    tdf = pd.DataFrame(t_rows)
                    tc = tdf.groupby(['Ano', 'País']).size().reset_index(name='Publicações')
                    fig_ev = px.line(tc, x='Ano', y='Publicações', color='País',
                                    title='Evolução dos Top 5 Países', height=450)
                    _add_img(_fig_to_png(fig_ev, height=500), "Evolução temporal dos 5 países mais produtivos")

        # Rede colaboração internacional
        nc, ec = country_collaboration_network(df, top_n=30)
        if not nc.empty and not ec.empty:
            fig_nc = network_graph(nc, ec, 'País', 'Publicações', 'Comunidade',
                                   'Rede de Colaboração Internacional', height=600)
            _add_img(_fig_to_png(fig_nc, width=1400, height=650),
                     "Rede de colaboração internacional entre países")
    except Exception:
        pass
    elems.append(PageBreak())

    # ============================================================
    #  SEÇÃO 6 — INSTITUIÇÕES
    # ============================================================
    _p("6. Instituições", 'Section')
    try:
        insts = extract_institutions(df)
        top_n = 20
        if not insts.empty:
            ic = insts.value_counts()
            _p(f"<b>Total de instituições:</b> {ic.shape[0]}", 'Body')
            ic_top = ic.head(top_n).reset_index()
            ic_top.columns = ['Instituição', 'Publicações']
            fig_i = bar_chart(ic_top, 'Instituição', 'Publicações',
                              f'Top {top_n} Instituições', orientation='h',
                              height=max(400, top_n * 28))
            _add_img(_fig_to_png(fig_i, height=max(500, top_n * 28)),
                     f"Top {top_n} instituições por publicações")

        ni, ei = institution_collaboration_network(df, top_n=30)
        if not ni.empty and not ei.empty:
            fig_ni = network_graph(ni, ei, 'Instituição', 'Publicações', 'Comunidade',
                                   'Rede de Colaboração Institucional', height=650)
            _add_img(_fig_to_png(fig_ni, width=1400, height=700),
                     "Rede de colaboração institucional")
    except Exception:
        pass
    elems.append(PageBreak())

    # ============================================================
    #  SEÇÃO 7 — CITAÇÕES
    # ============================================================
    _p("7. Análise de Citações", 'Section')
    try:
        if cit_col and cit_col in df.columns:
            cits = df[cit_col].fillna(0).astype(int)
            _p(f"<b>Total:</b> {int(cits.sum()):,}  |  <b>Média:</b> {cits.mean():.1f}  |  "
               f"<b>Mediana:</b> {cits.median():.0f}  |  <b>Máx:</b> {int(cits.max()):,}  |  "
               f"<b>Sem citações:</b> {(cits==0).sum()} ({(cits==0).mean()*100:.1f}%)", 'Body')
            _sp()

            fig_hist = px.histogram(cits, nbins=50, title='Distribuição de Citações',
                                    labels={'value': 'Citações', 'count': 'Nº Artigos'})
            fig_hist.update_traces(marker_color=COLOR_PRIMARY)
            _add_img(_fig_to_png(fig_hist), "Histograma da distribuição de citações")

            fig_box = px.box(df, y=cit_col, title='Box Plot de Citações')
            _add_img(_fig_to_png(fig_box), "Box plot de citações")

            cits_nz = cits[cits > 0]
            if len(cits_nz) > 0:
                cd = cits_nz.value_counts().sort_index().reset_index()
                cd.columns = ['Citações', 'Nº Artigos']
                fig_log = px.scatter(cd, x='Citações', y='Nº Artigos', log_x=True, log_y=True,
                                     title='Distribuição de Citações (Log-Log)')
                fig_log.update_traces(marker=dict(size=6, color=COLOR_PRIMARY))
                _add_img(_fig_to_png(fig_log), "Distribuição log-log de citações")

            cols_show = [c for c in [ti_col, au_col, so_col, year_col, cit_col] if c and c in df.columns]
            if cols_show:
                top_art = df.nlargest(20, cit_col)[cols_show].reset_index(drop=True)
                _add_img(_df_to_png(top_art, "Top 20 Artigos Mais Citados"),
                         "Tabela dos 20 artigos mais citados")

            if dt_col and dt_col in df.columns:
                top_types = df[dt_col].value_counts().head(5).index.tolist()
                df_types = df[df[dt_col].isin(top_types)]
                fig_bdt = px.box(df_types, x=dt_col, y=cit_col, color=dt_col,
                                 title='Citações por Tipo de Documento')
                fig_bdt.update_layout(showlegend=False)
                _add_img(_fig_to_png(fig_bdt), "Box plot de citações por tipo de documento")

        if cr_col and cr_col in df.columns:
            refs = extract_references(df)
            if not refs.empty:
                rc = refs.value_counts().head(15).reset_index()
                rc.columns = ['Referência', 'Frequência']
                fig_refs = bar_chart(rc, 'Referência', 'Frequência',
                                     'Top 15 Referências Mais Citadas', orientation='h',
                                     color=COLOR_SECONDARY, height=500)
                _add_img(_fig_to_png(fig_refs, height=550), "Top 15 referências mais citadas")

                ref_years = []
                for ref in refs:
                    m = re.search(r'\b(19|20)\d{2}\b', str(ref))
                    if m:
                        ref_years.append(int(m.group()))
                if ref_years:
                    rys = pd.Series(ref_years)
                    rys = rys[(rys >= 1900) & (rys <= datetime.now().year)]
                    if len(rys) > 0:
                        fig_ry = px.histogram(rys, nbins=50, title='Anos das Referências Citadas')
                        fig_ry.update_traces(marker_color='#9467bd')
                        _add_img(_fig_to_png(fig_ry), "Distribuição dos anos das referências citadas")

                        median_pub = int(df[year_col].median()) if year_col and year_col in df.columns else None
                        if median_pub:
                            recent = (rys >= median_pub - 5).sum()
                            price_idx = round(recent / len(rys) * 100, 1)
                            _p(f"<b>Índice de Price:</b> {price_idx}% das referências são recentes "
                               f"(últimos 5 anos rel. à mediana {median_pub})", 'Body')
    except Exception:
        pass
    elems.append(PageBreak())

    # ============================================================
    #  SEÇÃO 8 — FINANCIAMENTO
    # ============================================================
    if fu_col and fu_col in df.columns:
        _p("8. Financiamento", 'Section')
        try:
            has_fu = df[fu_col].notna()
            n_fu = has_fu.sum()
            _p(f"<b>Artigos com financiamento:</b> {n_fu:,} ({n_fu/total*100:.1f}%)", 'Body')
            if cit_col and cit_col in df.columns:
                avg_f = df[has_fu][cit_col].mean()
                avg_nf = df[~has_fu][cit_col].mean()
                _p(f"<b>Média citações (financiados):</b> {avg_f:.1f}  |  "
                   f"<b>(não financiados):</b> {avg_nf:.1f}", 'Body')
            agencies = safe_split(df[fu_col], sep='; ')
            if not agencies.empty:
                ag_c = agencies.value_counts().head(20).reset_index()
                ag_c.columns = ['Agência', 'Artigos']
                fig_fu = bar_chart(ag_c, 'Agência', 'Artigos',
                                   'Top 20 Agências Financiadoras', orientation='h',
                                   height=max(400, 20 * 28))
                _add_img(_fig_to_png(fig_fu, height=max(500, 20 * 28)),
                         "Top 20 agências financiadoras")

            if cit_col and cit_col in df.columns:
                dff = df.copy()
                dff['Financiamento'] = dff[fu_col].apply(
                    lambda x: 'Sim' if pd.notna(x) and str(x).strip() else 'Não')
                fig_bfu = px.box(dff, x='Financiamento', y=cit_col,
                                 title='Citações: Financiados vs Não', color='Financiamento')
                _add_img(_fig_to_png(fig_bfu), "Box plot citações — financiados vs não financiados")
        except Exception:
            pass
        elems.append(PageBreak())

    # ============================================================
    #  SEÇÃO 9 — ACESSO ABERTO
    # ============================================================
    if oa_col and oa_col in df.columns:
        _p("9. Acesso Aberto", 'Section')
        try:
            oa_c = df[oa_col].value_counts().reset_index()
            oa_c.columns = ['Tipo OA', 'Artigos']
            oa_total = (df[oa_col].notna()).sum()
            _p(f"<b>Artigos com acesso aberto:</b> {oa_total} ({oa_total/total*100:.1f}%)", 'Body')

            fig_oa = pie_chart(oa_c, 'Tipo OA', 'Artigos', 'Distribuição de Acesso Aberto')
            _add_img(_fig_to_png(fig_oa), "Distribuição dos tipos de acesso aberto")

            fig_oa_b = bar_chart(oa_c, 'Tipo OA', 'Artigos', 'Artigos por Tipo OA', height=350)
            _add_img(_fig_to_png(fig_oa_b), "Barras — artigos por tipo OA")

            if cit_col and cit_col in df.columns:
                fig_boa = px.box(df, x=oa_col, y=cit_col, color=oa_col,
                                 title='Citações por Tipo de Acesso')
                _add_img(_fig_to_png(fig_boa), "Box plot citações por tipo de acesso")
        except Exception:
            pass
        elems.append(PageBreak())

    # ============================================================
    #  SEÇÃO 10 — REDES DE CO-AUTORIA
    # ============================================================
    _p("10. Redes de Colaboração", 'Section')
    try:
        nco, eco = coauthorship_network(df, top_n=50)
        if not nco.empty and not eco.empty:
            _p("10.1 Rede de Co-autoria (Top 50)", 'SubSection')
            _p(f"<b>Nós:</b> {len(nco)}  |  <b>Arestas:</b> {len(eco)}"
               + (f"  |  <b>Comunidades:</b> {nco['Comunidade'].nunique()}" if 'Comunidade' in nco.columns else ""),
               'Body')

            fig_co = network_graph(nco, eco, 'Autor', 'Publicações', 'Comunidade',
                                   'Rede de Co-autoria (Top 50)', height=700)
            _add_img(_fig_to_png(fig_co, width=1400, height=750),
                     "Rede de co-autoria — 50 autores mais produtivos")

            if 'Centralidade Grau' in nco.columns:
                td = nco.nlargest(15, 'Centralidade Grau')
                fig_deg = bar_chart(td, 'Autor', 'Centralidade Grau',
                                    'Centralidade de Grau', orientation='h', color=COLOR_PRIMARY, height=450)
                _add_img(_fig_to_png(fig_deg, height=500), "Top 15 autores — centralidade de grau")

            if 'Centralidade Intermediação' in nco.columns:
                tb = nco.nlargest(15, 'Centralidade Intermediação')
                fig_bet = bar_chart(tb, 'Autor', 'Centralidade Intermediação',
                                    'Centralidade de Intermediação', orientation='h',
                                    color=COLOR_SECONDARY, height=450)
                _add_img(_fig_to_png(fig_bet, height=500), "Top 15 autores — centralidade de intermediação")

            fig_sn = px.scatter(nco, x='Publicações', y='Centralidade Grau',
                                size='Grau', color='Comunidade',
                                title='Publicações vs Centralidade', hover_name='Autor')
            _add_img(_fig_to_png(fig_sn), "Publicações vs centralidade de grau")

            _add_img(_df_to_png(nco.sort_values('Publicações', ascending=False), "Nós da Rede"),
                     "Tabela de métricas da rede de co-autoria")
    except Exception:
        pass
    elems.append(PageBreak())

    # ============================================================
    #  SEÇÃO 11 — CATEGORIAS
    # ============================================================
    _p("11. Categorias e Áreas de Pesquisa", 'Section')
    try:
        top_n = 20
        if wc_col and wc_col in df.columns:
            cats = safe_split(df[wc_col], sep='; ').str.strip()
            if not cats.empty:
                cat_c = cats.value_counts().head(top_n).reset_index()
                cat_c.columns = ['Categoria', 'Artigos']
                _p(f"<b>Total de categorias WoS:</b> {cats.nunique()}", 'Body')
                fig_cat = bar_chart(cat_c, 'Categoria', 'Artigos',
                                    f'Top {top_n} Categorias WoS', orientation='h',
                                    height=max(400, top_n * 28))
                _add_img(_fig_to_png(fig_cat, height=max(500, top_n * 28)),
                         f"Top {top_n} categorias WoS")

                cat_tree = cats.value_counts().head(30).reset_index()
                cat_tree.columns = ['Categoria', 'Artigos']
                fig_tree = px.treemap(cat_tree, path=['Categoria'], values='Artigos',
                                      title='Treemap das Categorias',
                                      color='Artigos', color_continuous_scale='Blues')
                fig_tree.update_layout(height=500)
                _add_img(_fig_to_png(fig_tree, height=550), "Treemap das 30 categorias mais frequentes")

        if sc_col and sc_col in df.columns:
            areas = safe_split(df[sc_col], sep='; ').str.strip()
            if not areas.empty:
                ac = areas.value_counts().head(top_n).reset_index()
                ac.columns = ['Área de Pesquisa', 'Artigos']
                _p(f"<b>Total de áreas:</b> {areas.nunique()}", 'Body')
                fig_ar = bar_chart(ac, 'Área de Pesquisa', 'Artigos',
                                   'Top 20 Áreas de Pesquisa', orientation='h',
                                   color=COLOR_SECONDARY, height=550)
                _add_img(_fig_to_png(fig_ar, height=600), "Top 20 áreas de pesquisa")
    except Exception:
        pass

    # ============================================================
    #  RODAPÉ
    # ============================================================
    _sp(20)
    _p("—" * 60, 'SmallBody')
    _p("Relatório gerado automaticamente pelo <b>BibAnalyze</b> — "
       "ferramenta de análise bibliométrica de exportações Web of Science.", 'SmallBody')

    # ---------- BUILD ----------
    doc.build(elems)
    buf.seek(0)
    return buf.getvalue()


@st.cache_data(show_spinner="Gerando resumo completo...")
def build_full_report(_df: pd.DataFrame) -> str:
    """Gera relatório markdown completo com todas as análises."""
    df = _df
    year_col = get_year_col(df)
    cit_col = get_citations_col(df)
    au_col = get_col(df, 'AU')
    so_col = get_col(df, 'SO')
    ti_col = get_col(df, 'TI')
    de_col = get_col(df, 'DE')
    id_col = get_col(df, 'ID')
    dt_col = get_col(df, 'DT')
    la_col = get_col(df, 'LA')
    fu_col = get_col(df, 'FU')
    oa_col = get_col(df, 'OA')
    cr_col = get_col(df, 'CR')
    doi_col = get_col(df, 'DI')
    wc_col = get_col(df, 'WC')
    sc_col = get_col(df, 'SC')

    total = len(df)
    lines = []
    lines.append("# RELATÓRIO BIBLIOMÉTRICO COMPLETO")
    lines.append(f"*Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')} pelo BibAnalyze*")
    lines.append("")

    # ══════════════════════════════════════════════
    # 1. VISÃO GERAL
    # ══════════════════════════════════════════════
    lines.append("---")
    lines.append("## 1. VISÃO GERAL")
    lines.append("")

    period = "N/A"
    if year_col and year_col in df.columns:
        years = df[year_col].dropna()
        if len(years) > 0:
            period = f"{int(years.min())}–{int(years.max())}"

    total_cit = int(df[cit_col].sum()) if cit_col and cit_col in df.columns else 0
    avg_cit = round(total_cit / total, 1) if total > 0 else 0
    n_authors = safe_split(df[au_col], sep='; ').nunique() if au_col and au_col in df.columns else 0
    n_journals = df[so_col].nunique() if so_col and so_col in df.columns else 0

    lines.append(f"| Indicador | Valor |")
    lines.append(f"|---|---|")
    lines.append(f"| Total de artigos | {total:,} |")
    lines.append(f"| Período coberto | {period} |")
    lines.append(f"| Total de autores únicos | {n_authors:,} |")
    lines.append(f"| Total de periódicos | {n_journals:,} |")
    lines.append(f"| Total de citações | {total_cit:,} |")
    lines.append(f"| Média de citações/artigo | {avg_cit} |")

    if dt_col and dt_col in df.columns:
        dt_counts = df[dt_col].value_counts()
        lines.append(f"| Tipo de documento predominante | {dt_counts.index[0]} ({dt_counts.iloc[0]:,}) |")

    if la_col and la_col in df.columns:
        la_top = df[la_col].value_counts().head(1)
        lines.append(f"| Idioma predominante | {la_top.index[0]} ({la_top.iloc[0]:,}) |")

    lines.append("")

    # ══════════════════════════════════════════════
    # 2. PRODUÇÃO CIENTÍFICA
    # ══════════════════════════════════════════════
    lines.append("---")
    lines.append("## 2. PRODUÇÃO CIENTÍFICA")
    lines.append("")

    stats = yearly_stats(df)
    if not stats.empty:
        # Ano mais produtivo
        best_year = stats.loc[stats['Publicações'].idxmax()]
        lines.append(f"- **Ano mais produtivo:** {int(best_year['Ano'])} ({int(best_year['Publicações'])} publicações)")

        # Crescimento
        if len(stats) >= 2:
            first_5 = stats.head(5)['Publicações'].mean()
            last_5 = stats.tail(5)['Publicações'].mean()
            growth = round((last_5 / max(1, first_5) - 1) * 100, 1)
            lines.append(f"- **Crescimento médio (primeiros 5 vs últimos 5 anos):** {growth:+.1f}%")

        max_growth = stats.loc[stats['Crescimento (%)'].idxmax()] if 'Crescimento (%)' in stats.columns else None
        if max_growth is not None and max_growth['Crescimento (%)'] > 0:
            lines.append(f"- **Maior pico de crescimento:** {int(max_growth['Ano'])} ({max_growth['Crescimento (%)']:.0f}%)")

        lines.append("")
        lines.append("### Publicações por Ano")
        lines.append("")
        lines.append("| Ano | Publicações | Citações | Acumulado |")
        lines.append("|-----|------------|----------|-----------|")
        for _, row in stats.iterrows():
            cit_val = int(row['Citações']) if 'Citações' in stats.columns else '-'
            lines.append(f"| {int(row['Ano'])} | {int(row['Publicações'])} | {cit_val} | {int(row['Acumulado Publicações'])} |")
        lines.append("")

    # Tipo de documento
    if dt_col and dt_col in df.columns:
        lines.append("### Distribuição por Tipo de Documento")
        lines.append("")
        lines.append("| Tipo | Quantidade | % |")
        lines.append("|------|-----------|---|")
        for dtype, count in df[dt_col].value_counts().items():
            lines.append(f"| {dtype} | {count:,} | {count/total*100:.1f}% |")
        lines.append("")

    # ══════════════════════════════════════════════
    # 3. AUTORES
    # ══════════════════════════════════════════════
    lines.append("---")
    lines.append("## 3. ANÁLISE DE AUTORES")
    lines.append("")

    am = author_metrics(df)
    if not am.empty:
        lines.append("### Top 20 Autores por Publicações")
        lines.append("")
        cols = [c for c in ['Autor', 'Publicações', 'Citações', 'Índice h', 'Primeiro Ano', 'Último Ano'] if c in am.columns]
        header = " | ".join(cols)
        sep = " | ".join(["---"] * len(cols))
        lines.append(f"| {header} |")
        lines.append(f"| {sep} |")
        for _, row in am.head(20).iterrows():
            vals = " | ".join(str(int(row[c]) if isinstance(row[c], (int, float)) else row[c]) for c in cols)
            lines.append(f"| {vals} |")
        lines.append("")

    # Lotka
    lotka = lotka_law(df)
    if lotka.get('total_authors', 0) > 0:
        lines.append("### Lei de Lotka")
        lines.append("")
        lines.append(f"- **Autor mais produtivo:** {lotka['n_max']} publicações")
        lines.append(f"- **Limiar para autores-núcleo (M = 0.749 × √Nmax):** {lotka['threshold']}")
        lines.append(f"- **Autores-núcleo:** {lotka['core_count']:,} de {lotka['total_authors']:,} ({lotka['core_count']/lotka['total_authors']*100:.1f}%)")
        lines.append("")
        if not lotka['core_authors'].empty:
            lines.append("**Autores-núcleo:**")
            lines.append("")
            lines.append("| Autor | Publicações |")
            lines.append("|-------|-----------|")
            for _, row in lotka['core_authors'].head(20).iterrows():
                lines.append(f"| {row['Autor']} | {int(row['Publicações'])} |")
            lines.append("")

    # Co-autoria
    if au_col and au_col in df.columns:
        all_au = safe_split(df[au_col], sep='; ')
        n_single = (df[au_col].str.count('; ') == 0).sum()
        avg_coauthors = round(df[au_col].str.count('; ').mean() + 1, 1)
        lines.append(f"- **Média de autores/artigo:** {avg_coauthors}")
        lines.append(f"- **Artigos com autor único:** {n_single} ({n_single/total*100:.1f}%)")
        lines.append("")

    # ══════════════════════════════════════════════
    # 4. PERIÓDICOS
    # ══════════════════════════════════════════════
    lines.append("---")
    lines.append("## 4. ANÁLISE DE PERIÓDICOS")
    lines.append("")

    brad = bradford_law(df)
    if brad.get('total_journals', 0) > 0:
        lines.append("### Lei de Bradford")
        lines.append("")
        lines.append(f"- **Total de periódicos:** {brad['total_journals']}")
        lines.append("")
        if 'zone_summary' in brad and not brad['zone_summary'].empty:
            lines.append("| Zona | Periódicos | Artigos |")
            lines.append("|------|-----------|---------|")
            for _, row in brad['zone_summary'].iterrows():
                lines.append(f"| {row['Zona de Bradford']} | {int(row['Periódicos'])} | {int(row['Artigos'])} |")
            lines.append("")

        if 'journals' in brad and not brad['journals'].empty:
            lines.append("### Top 20 Periódicos por Publicações")
            lines.append("")
            lines.append("| Periódico | Artigos | Zona |")
            lines.append("|-----------|---------|------|")
            for _, row in brad['journals'].head(20).iterrows():
                lines.append(f"| {row['Periódico']} | {int(row['Artigos'])} | {row['Zona de Bradford']} |")
            lines.append("")

    # ══════════════════════════════════════════════
    # 5. PALAVRAS-CHAVE
    # ══════════════════════════════════════════════
    lines.append("---")
    lines.append("## 5. PALAVRAS-CHAVE")
    lines.append("")

    if de_col and de_col in df.columns:
        kw_de = extract_keywords(df, 'DE')
        if not kw_de.empty:
            kw_counts = kw_de.value_counts()
            lines.append(f"- **Total de palavras-chave do autor (DE):** {kw_counts.shape[0]:,}")
            lines.append("")
            lines.append("### Top 30 Palavras-chave do Autor")
            lines.append("")
            lines.append("| # | Palavra-chave | Frequência |")
            lines.append("|---|-------------|-----------|")
            for i, (kw, freq) in enumerate(kw_counts.head(30).items(), 1):
                lines.append(f"| {i} | {kw} | {freq} |")
            lines.append("")

    if id_col and id_col in df.columns:
        kw_id = extract_keywords(df, 'ID')
        if not kw_id.empty:
            id_counts = kw_id.value_counts()
            lines.append(f"- **Total de Keywords Plus (ID):** {id_counts.shape[0]:,}")
            lines.append("")
            lines.append("### Top 20 Keywords Plus")
            lines.append("")
            lines.append("| # | Keyword Plus | Frequência |")
            lines.append("|---|-------------|-----------|")
            for i, (kw, freq) in enumerate(id_counts.head(20).items(), 1):
                lines.append(f"| {i} | {kw} | {freq} |")
            lines.append("")

    # ══════════════════════════════════════════════
    # 6. ANÁLISE GEOGRÁFICA
    # ══════════════════════════════════════════════
    lines.append("---")
    lines.append("## 6. ANÁLISE GEOGRÁFICA")
    lines.append("")

    countries_df = extract_countries(df)
    if not countries_df.empty:
        country_counts = countries_df['País'].value_counts()
        lines.append(f"- **Total de países:** {country_counts.shape[0]}")
        lines.append("")
        lines.append("### Top 20 Países por Publicações")
        lines.append("")
        lines.append("| # | País | Publicações | % |")
        lines.append("|---|------|-----------|---|")
        total_country_entries = country_counts.sum()
        for i, (country, count) in enumerate(country_counts.head(20).items(), 1):
            lines.append(f"| {i} | {country} | {count} | {count/total_country_entries*100:.1f}% |")
        lines.append("")

        # Top por citações
        if cit_col and cit_col in df.columns:
            merged = countries_df.merge(
                df[[cit_col]].reset_index().rename(columns={'index': 'index'}),
                left_on='index', right_on='index', how='left'
            )
            country_cit = merged.groupby('País')[cit_col].sum().sort_values(ascending=False)
            lines.append("### Top 10 Países por Citações")
            lines.append("")
            lines.append("| País | Citações |")
            lines.append("|------|---------|")
            for country, cit in country_cit.head(10).items():
                lines.append(f"| {country} | {int(cit):,} |")
            lines.append("")

    # ══════════════════════════════════════════════
    # 7. INSTITUIÇÕES
    # ══════════════════════════════════════════════
    lines.append("---")
    lines.append("## 7. INSTITUIÇÕES")
    lines.append("")

    insts = extract_institutions(df)
    if not insts.empty:
        inst_counts = insts.value_counts()
        lines.append(f"- **Total de instituições:** {inst_counts.shape[0]}")
        lines.append("")
        lines.append("### Top 20 Instituições por Publicações")
        lines.append("")
        lines.append("| # | Instituição | Publicações |")
        lines.append("|---|-----------|-----------|")
        for i, (inst, count) in enumerate(inst_counts.head(20).items(), 1):
            lines.append(f"| {i} | {inst} | {count} |")
        lines.append("")

    # ══════════════════════════════════════════════
    # 8. CITAÇÕES
    # ══════════════════════════════════════════════
    lines.append("---")
    lines.append("## 8. ANÁLISE DE CITAÇÕES")
    lines.append("")

    if cit_col and cit_col in df.columns:
        citations = df[cit_col].fillna(0)
        lines.append("### Estatísticas de Citações")
        lines.append("")
        lines.append(f"| Indicador | Valor |")
        lines.append(f"|-----------|-------|")
        lines.append(f"| Total de citações | {int(citations.sum()):,} |")
        lines.append(f"| Média | {citations.mean():.1f} |")
        lines.append(f"| Mediana | {citations.median():.0f} |")
        lines.append(f"| Máximo | {int(citations.max()):,} |")
        lines.append(f"| Desvio padrão | {citations.std():.1f} |")
        zero_pct = (citations == 0).mean() * 100
        lines.append(f"| Artigos sem citações | {(citations == 0).sum()} ({zero_pct:.1f}%) |")
        lines.append("")

        # Top 10 artigos mais citados
        cols_show = [c for c in [ti_col, au_col, so_col, year_col, cit_col, doi_col]
                     if c and c in df.columns]
        if cols_show:
            top10 = df.nlargest(10, cit_col)[cols_show]
            lines.append("### Top 10 Artigos Mais Citados")
            lines.append("")
            for rank, (_, row) in enumerate(top10.iterrows(), 1):
                title = row.get(ti_col, 'N/A') if ti_col else 'N/A'
                authors = row.get(au_col, 'N/A') if au_col else 'N/A'
                journal = row.get(so_col, '') if so_col else ''
                year = int(row.get(year_col, 0)) if year_col else ''
                cit = int(row.get(cit_col, 0))
                doi = row.get(doi_col, '') if doi_col else ''
                lines.append(f"**{rank}.** {title}")
                lines.append(f"   - Autores: {authors}")
                info_parts = []
                if journal:
                    info_parts.append(f"Periódico: {journal}")
                if year:
                    info_parts.append(f"Ano: {year}")
                info_parts.append(f"Citações: {cit:,}")
                if doi and pd.notna(doi):
                    info_parts.append(f"DOI: {doi}")
                lines.append(f"   - {' | '.join(info_parts)}")
                lines.append("")

    # Referências mais citadas
    if cr_col and cr_col in df.columns:
        refs = extract_references(df)
        if not refs.empty:
            ref_counts = refs.value_counts().head(15)
            lines.append("### Top 15 Referências Mais Citadas")
            lines.append("")
            lines.append("| # | Referência | Frequência |")
            lines.append("|---|-----------|-----------|")
            for i, (ref, freq) in enumerate(ref_counts.items(), 1):
                ref_clean = ref[:120] + '...' if len(ref) > 120 else ref
                lines.append(f"| {i} | {ref_clean} | {freq} |")
            lines.append("")

        # Price Index
        if year_col and year_col in df.columns:
            ref_years = []
            for ref in refs:
                match = re.search(r'\b(19|20)\d{2}\b', str(ref))
                if match:
                    ref_years.append(int(match.group()))
            if ref_years:
                ref_years_s = pd.Series(ref_years)
                ref_years_s = ref_years_s[(ref_years_s >= 1900) & (ref_years_s <= datetime.now().year)]
                median_pub = int(df[year_col].median())
                recent = (ref_years_s >= median_pub - 5).sum()
                price_idx = round(recent / len(ref_years_s) * 100, 1) if len(ref_years_s) > 0 else 0
                lines.append(f"### Índice de Price")
                lines.append(f"- **Valor:** {price_idx}% das referências são dos últimos 5 anos (relativo à mediana {median_pub})")
                lines.append("")

    # ══════════════════════════════════════════════
    # 9. FINANCIAMENTO
    # ══════════════════════════════════════════════
    if fu_col and fu_col in df.columns:
        lines.append("---")
        lines.append("## 9. FINANCIAMENTO")
        lines.append("")

        has_funding = df[fu_col].notna()
        n_funded = has_funding.sum()
        pct_funded = round(n_funded / total * 100, 1) if total > 0 else 0
        lines.append(f"- **Artigos com financiamento:** {n_funded:,} ({pct_funded}%)")

        if cit_col and cit_col in df.columns:
            avg_funded = df[has_funding][cit_col].mean()
            avg_not = df[~has_funding][cit_col].mean()
            lines.append(f"- **Média citações (financiados):** {avg_funded:.1f}")
            lines.append(f"- **Média citações (não financiados):** {avg_not:.1f}")

        agencies = safe_split(df[fu_col], sep='; ')
        ag_counts = agencies.value_counts()
        lines.append(f"- **Total de agências:** {ag_counts.shape[0]}")
        lines.append("")
        lines.append("### Top 15 Agências de Financiamento")
        lines.append("")
        lines.append("| # | Agência | Artigos |")
        lines.append("|---|---------|---------|")
        for i, (ag, count) in enumerate(ag_counts.head(15).items(), 1):
            lines.append(f"| {i} | {ag} | {count} |")
        lines.append("")

    # ══════════════════════════════════════════════
    # 10. ACESSO ABERTO
    # ══════════════════════════════════════════════
    if oa_col and oa_col in df.columns:
        lines.append("---")
        lines.append("## 10. ACESSO ABERTO")
        lines.append("")

        oa_counts = df[oa_col].fillna('Acesso Restrito').value_counts()
        oa_total = (df[oa_col].notna()).sum()
        lines.append(f"- **Artigos com acesso aberto:** {oa_total} ({oa_total/total*100:.1f}%)")
        lines.append("")
        lines.append("| Tipo OA | Artigos | % |")
        lines.append("|---------|---------|---|")
        for oa_type, count in oa_counts.items():
            lines.append(f"| {oa_type} | {count} | {count/total*100:.1f}% |")
        lines.append("")

        if cit_col and cit_col in df.columns:
            df_oa = df.copy()
            df_oa['_oa'] = df_oa[oa_col].fillna('Acesso Restrito')
            oa_cit = df_oa.groupby('_oa')[cit_col].mean().sort_values(ascending=False)
            lines.append("### Média de Citações por Tipo OA")
            lines.append("")
            lines.append("| Tipo OA | Média Citações |")
            lines.append("|---------|---------------|")
            for oa_type, avg in oa_cit.items():
                lines.append(f"| {oa_type} | {avg:.1f} |")
            lines.append("")

    # ══════════════════════════════════════════════
    # 11. CATEGORIAS E ÁREAS
    # ══════════════════════════════════════════════
    if wc_col and wc_col in df.columns:
        lines.append("---")
        lines.append("## 11. CATEGORIAS WoS E ÁREAS DE PESQUISA")
        lines.append("")

        wc_all = safe_split(df[wc_col], sep='; ')
        wc_counts = wc_all.value_counts()
        lines.append(f"- **Total de categorias WoS:** {wc_counts.shape[0]}")
        lines.append("")
        lines.append("### Top 15 Categorias WoS")
        lines.append("")
        lines.append("| # | Categoria | Artigos |")
        lines.append("|---|----------|---------|")
        for i, (cat, count) in enumerate(wc_counts.head(15).items(), 1):
            lines.append(f"| {i} | {cat} | {count} |")
        lines.append("")

    if sc_col and sc_col in df.columns:
        sc_all = safe_split(df[sc_col], sep='; ')
        sc_counts = sc_all.value_counts()
        lines.append(f"- **Total de áreas de pesquisa:** {sc_counts.shape[0]}")
        lines.append("")
        lines.append("### Top 15 Áreas de Pesquisa")
        lines.append("")
        lines.append("| # | Área | Artigos |")
        lines.append("|---|------|---------|")
        for i, (area, count) in enumerate(sc_counts.head(15).items(), 1):
            lines.append(f"| {i} | {area} | {count} |")
        lines.append("")

    # ══════════════════════════════════════════════
    # 12. REDES DE COLABORAÇÃO (RESUMO)
    # ══════════════════════════════════════════════
    lines.append("---")
    lines.append("## 12. REDES DE COLABORAÇÃO (resumo)")
    lines.append("")

    ca_nodes, ca_edges = coauthorship_network(df, top_n=50)
    if not ca_nodes.empty:
        lines.append("### Rede de Co-autoria (Top 50)")
        lines.append(f"- Nós (autores): {len(ca_nodes)}")
        lines.append(f"- Arestas (colaborações): {len(ca_edges)}")
        if 'Comunidade' in ca_nodes.columns:
            lines.append(f"- Comunidades detectadas: {ca_nodes['Comunidade'].nunique()}")
        top3_degree = ca_nodes.nlargest(3, 'Grau') if 'Grau' in ca_nodes.columns else pd.DataFrame()
        if not top3_degree.empty:
            lines.append("- **Autores mais conectados:**")
            for _, row in top3_degree.iterrows():
                lines.append(f"  - {row['Autor']} (grau: {row['Grau']})")
        lines.append("")

    kw_nodes, kw_edges = keyword_cooccurrence_network(df, 'DE', 3, 50)
    if not kw_nodes.empty:
        lines.append("### Rede de Co-ocorrência de Palavras-chave")
        lines.append(f"- Nós (keywords): {len(kw_nodes)}")
        lines.append(f"- Arestas (co-ocorrências): {len(kw_edges)}")
        if 'Comunidade' in kw_nodes.columns:
            lines.append(f"- Comunidades temáticas: {kw_nodes['Comunidade'].nunique()}")
        lines.append("")

    c_nodes, c_edges = country_collaboration_network(df, top_n=30)
    if not c_nodes.empty:
        lines.append("### Rede de Colaboração Internacional")
        lines.append(f"- Países na rede: {len(c_nodes)}")
        lines.append(f"- Colaborações: {len(c_edges)}")
        lines.append("")

    i_nodes, i_edges = institution_collaboration_network(df, top_n=30)
    if not i_nodes.empty:
        lines.append("### Rede de Colaboração Institucional")
        lines.append(f"- Instituições na rede: {len(i_nodes)}")
        lines.append(f"- Colaborações: {len(i_edges)}")
        lines.append("")

    # ══════════════════════════════════════════════
    # FOOTER
    # ══════════════════════════════════════════════
    lines.append("---")
    lines.append("*Relatório gerado automaticamente pelo BibAnalyze — ferramenta de análise bibliométrica de exportações Web of Science.*")

    return "\n".join(lines)


# ============================
# INTERFACE
# ============================
st.markdown("""
> Esta página gera um **resumo completo** de todas as análises.
> Você pode gerar um **PDF profissional** com todos os gráficos e tabelas,
> ou visualizar/copiar o resumo em Markdown.
""")

# ─── PDF completo ───
st.subheader("📄 Relatório PDF Completo")
st.markdown("Gera um PDF com **todos os gráficos, tabelas e análises** — ideal para entrega ou apresentação.")

if st.button("📄 Gerar PDF Completo com Todas as Análises", type="primary", key="btn_gen_pdf"):
    with st.spinner("Gerando PDF completo… Isso pode levar alguns minutos."):
        try:
            pdf_bytes = _build_pdf(df_f)
            st.session_state['full_pdf'] = pdf_bytes
            st.success("✅ PDF gerado com sucesso!")
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")

pdf_bytes = st.session_state.get('full_pdf')
if pdf_bytes:
    st.download_button(
        "📥 Baixar PDF Completo",
        pdf_bytes,
        f"relatorio_bibliometrico_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
        "application/pdf",
        key="dl_full_pdf",
    )

st.markdown("---")

# ─── Relatório Markdown ───
st.subheader("📝 Relatório Markdown")

if st.button("🔄 Gerar Resumo Markdown", key="btn_gen_md"):
    report = build_full_report(df_f)
    st.session_state['full_report'] = report

report = st.session_state.get('full_report')

if report:
    # Botões de ação
    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(
            "⬇️ Baixar como .txt",
            report.encode('utf-8'),
            "relatorio_bibliometrico_completo.txt",
            "text/plain",
            key="dl_report_txt",
        )
    with col2:
        st.download_button(
            "⬇️ Baixar como .md",
            report.encode('utf-8'),
            "relatorio_bibliometrico_completo.md",
            "text/markdown",
            key="dl_report_md",
        )

    # Botão de copiar via JS
    st.markdown("### 📋 Copiar Resumo")
    st.markdown(
        """<button onclick="
            const el = document.querySelector('[data-testid=\\'stCodeBlock\\'] code');
            if (el) {
                navigator.clipboard.writeText(el.innerText).then(
                    () => alert('Copiado!'),
                    () => alert('Falha ao copiar.')
                );
            }
        " style="
            background-color: #ff4b4b; color: white; border: none;
            padding: 8px 24px; border-radius: 6px; cursor: pointer;
            font-size: 16px; margin-bottom: 12px;
        ">📋 Copiar para Área de Transferência</button>""",
        unsafe_allow_html=True,
    )

    # Visualização Markdown renderizado
    st.markdown("---")
    st.subheader("📖 Visualização Renderizada")
    st.markdown(report)

    # Snippet copiável (código fonte)
    st.markdown("---")
    st.subheader("📝 Código-fonte Markdown (para copiar)")
    st.code(report, language="markdown")
else:
    st.info("Clique no botão acima para gerar o resumo em Markdown.")
