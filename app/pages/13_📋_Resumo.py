"""Resumo Geral — visão consolidada de todas as análises com botão de copiar."""
import streamlit as st
import pandas as pd
import re
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
from components.filters import apply_filters, sidebar_upload

st.set_page_config(page_title="Resumo Geral", page_icon="📋", layout="wide")
st.title("📋 Resumo Geral — Relatório Completo")

sidebar_upload()
df = st.session_state.get('df')
if df is None or df.empty:
    st.warning("⚠️ Nenhum dado carregado. Volte à página inicial e faça upload dos arquivos.")
    st.stop()

df_f = apply_filters(df)


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
> Esta página gera um **resumo completo** de todas as análises em formato Markdown.
> Você pode visualizar, copiar para a área de transferência ou baixar como arquivo `.txt`.
""")

if st.button("🔄 Gerar Resumo Completo", type="primary"):
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
    st.info("Clique no botão acima para gerar o resumo.")
