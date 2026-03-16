"""
Funções de transformação e processamento de dados bibliométricos.
"""
import streamlit as st
import pandas as pd
import numpy as np
import re
from collections import Counter
from .parser import get_col, safe_split

# --- Mapeamento de países (normalização) ---
COUNTRY_NORMALIZE = {
    'PEOPLES R CHINA': 'China',
    'P.R. CHINA': 'China',
    'PR CHINA': 'China',
    'USA': 'Estados Unidos',
    'UNITED STATES': 'Estados Unidos',
    'U.S.A.': 'Estados Unidos',
    'ENGLAND': 'Reino Unido',
    'SCOTLAND': 'Reino Unido',
    'WALES': 'Reino Unido',
    'NORTH IRELAND': 'Reino Unido',
    'SOUTH KOREA': 'Coreia do Sul',
    'NORTH KOREA': 'Coreia do Norte',
    'TAIWAN': 'Taiwan',
    'RUSSIA': 'Rússia',
    'GERMANY': 'Alemanha',
    'FRANCE': 'França',
    'SPAIN': 'Espanha',
    'ITALY': 'Itália',
    'JAPAN': 'Japão',
    'BRAZIL': 'Brasil',
    'CANADA': 'Canadá',
    'INDIA': 'Índia',
    'AUSTRALIA': 'Austrália',
    'NETHERLANDS': 'Países Baixos',
    'SWEDEN': 'Suécia',
    'SWITZERLAND': 'Suíça',
    'BELGIUM': 'Bélgica',
    'NORWAY': 'Noruega',
    'DENMARK': 'Dinamarca',
    'FINLAND': 'Finlândia',
    'PORTUGAL': 'Portugal',
    'AUSTRIA': 'Áustria',
    'POLAND': 'Polônia',
    'TURKEY': 'Turquia',
    'IRAN': 'Irã',
    'ISRAEL': 'Israel',
    'MEXICO': 'México',
    'SINGAPORE': 'Singapura',
    'MALAYSIA': 'Malásia',
    'THAILAND': 'Tailândia',
    'PAKISTAN': 'Paquistão',
    'SAUDI ARABIA': 'Arábia Saudita',
    'EGYPT': 'Egito',
    'SOUTH AFRICA': 'África do Sul',
    'CHILE': 'Chile',
    'COLOMBIA': 'Colômbia',
    'ARGENTINA': 'Argentina',
    'GREECE': 'Grécia',
    'CZECH REPUBLIC': 'República Tcheca',
    'ROMANIA': 'Romênia',
    'HUNGARY': 'Hungria',
    'IRELAND': 'Irlanda',
    'NEW ZEALAND': 'Nova Zelândia',
    'UNITED ARAB EMIRATES': 'Emirados Árabes',
    'QATAR': 'Catar',
    'NIGERIA': 'Nigéria',
    'VIETNAM': 'Vietnã',
    'INDONESIA': 'Indonésia',
    'PHILIPPINES': 'Filipinas',
    'BANGLADESH': 'Bangladesh',
    'SRI LANKA': 'Sri Lanka',
    'MOROCCO': 'Marrocos',
    'TUNISIA': 'Tunísia',
    'ALGERIA': 'Argélia',
    'IRAQ': 'Iraque',
    'JORDAN': 'Jordânia',
    'LEBANON': 'Líbano',
    'OMAN': 'Omã',
    'KUWAIT': 'Kuwait',
    'CROATIA': 'Croácia',
    'SERBIA': 'Sérvia',
    'SLOVENIA': 'Eslovênia',
    'SLOVAKIA': 'Eslováquia',
    'BULGARIA': 'Bulgária',
    'UKRAINE': 'Ucrânia',
    'LITHUANIA': 'Lituânia',
    'LATVIA': 'Letônia',
    'ESTONIA': 'Estônia',
    'LUXEMBOURG': 'Luxemburgo',
    'ICELAND': 'Islândia',
    'CYPRUS': 'Chipre',
    'MALTA': 'Malta',
}

# Mapeamento de países para código ISO (para Plotly choropleth)
COUNTRY_ISO = {
    'China': 'CHN', 'Estados Unidos': 'USA', 'Reino Unido': 'GBR',
    'Coreia do Sul': 'KOR', 'Taiwan': 'TWN', 'Rússia': 'RUS',
    'Alemanha': 'DEU', 'França': 'FRA', 'Espanha': 'ESP',
    'Itália': 'ITA', 'Japão': 'JPN', 'Brasil': 'BRA',
    'Canadá': 'CAN', 'Índia': 'IND', 'Austrália': 'AUS',
    'Países Baixos': 'NLD', 'Suécia': 'SWE', 'Suíça': 'CHE',
    'Bélgica': 'BEL', 'Noruega': 'NOR', 'Dinamarca': 'DNK',
    'Finlândia': 'FIN', 'Portugal': 'PRT', 'Áustria': 'AUT',
    'Polônia': 'POL', 'Turquia': 'TUR', 'Irã': 'IRN',
    'Israel': 'ISR', 'México': 'MEX', 'Singapura': 'SGP',
    'Malásia': 'MYS', 'Tailândia': 'THA', 'Paquistão': 'PAK',
    'Arábia Saudita': 'SAU', 'Egito': 'EGY', 'África do Sul': 'ZAF',
    'Chile': 'CHL', 'Colômbia': 'COL', 'Argentina': 'ARG',
    'Grécia': 'GRC', 'República Tcheca': 'CZE', 'Romênia': 'ROU',
    'Hungria': 'HUN', 'Irlanda': 'IRL', 'Nova Zelândia': 'NZL',
    'Emirados Árabes': 'ARE', 'Catar': 'QAT', 'Nigéria': 'NGA',
    'Vietnã': 'VNM', 'Indonésia': 'IDN', 'Filipinas': 'PHL',
    'Bangladesh': 'BGD', 'Sri Lanka': 'LKA', 'Marrocos': 'MAR',
    'Tunísia': 'TUN', 'Argélia': 'DZA', 'Iraque': 'IRQ',
    'Jordânia': 'JOR', 'Líbano': 'LBN', 'Omã': 'OMN',
    'Kuwait': 'KWT', 'Croácia': 'HRV', 'Sérvia': 'SRB',
    'Eslovênia': 'SVN', 'Eslováquia': 'SVK', 'Bulgária': 'BGR',
    'Ucrânia': 'UKR', 'Lituânia': 'LTU', 'Letônia': 'LVA',
    'Estônia': 'EST', 'Luxemburgo': 'LUX', 'Islândia': 'ISL',
    'Chipre': 'CYP', 'Malta': 'MLT', 'Coreia do Norte': 'PRK',
}


def normalize_country(country_str: str) -> str:
    """Normaliza nome de país."""
    c = country_str.strip().upper()
    if c in COUNTRY_NORMALIZE:
        return COUNTRY_NORMALIZE[c]
    return country_str.strip().title()


def extract_countries(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extrai países a partir do campo de endereços (C1), ou RP como fallback.
    Retorna DataFrame com colunas ['index', 'País'].
    """
    col = get_col(df, 'C1')
    if col is None:
        col = get_col(df, 'RP')
    if col is None:
        return pd.DataFrame(columns=['index', 'País'])

    countries = []
    for idx, addr in df[col].dropna().items():
        seen = set()
        for part in str(addr).split('; '):
            # O país geralmente é o último elemento após a última vírgula
            # Padrão: "[Autor] Universidade, Cidade, Estado, País"
            # No RP: "Autor (corresponding author), Univ, Cidade, País."
            elements = part.split(', ')
            if elements:
                country = elements[-1].strip().rstrip('.')
                # Ignorar valores claramente não-país
                if len(country) > 2 and not country.isdigit() and '@' not in country:
                    country = normalize_country(country)
                    if country and country not in seen and len(country) < 50:
                        seen.add(country)
                        countries.append({'index': idx, 'País': country})

    return pd.DataFrame(countries) if countries else pd.DataFrame(columns=['index', 'País'])


def extract_institutions(df: pd.DataFrame) -> pd.Series:
    """Extrai instituições do campo C3 (Affiliations), ou RP como fallback."""
    col = get_col(df, 'C3')
    if col is None:
        # Fallback: extrair instituição do RP
        col = get_col(df, 'RP')
        if col is None:
            return pd.Series(dtype=str)
        # Do RP, extrair a parte após "(corresponding author), " e antes da primeira vírgula
        insts = []
        for val in df[col].dropna():
            parts = str(val).split('), ')
            if len(parts) > 1:
                inst_part = parts[1].split(', ')
                if inst_part:
                    insts.append(inst_part[0].strip())
            else:
                inst_part = str(val).split(', ')
                if len(inst_part) > 1:
                    insts.append(inst_part[0].strip())
        return pd.Series(insts).str.strip() if insts else pd.Series(dtype=str)
    return safe_split(df[col], sep='; ')


def extract_authors(df: pd.DataFrame, use_full_names: bool = False) -> pd.Series:
    """Extrai lista de autores individuais."""
    col = get_col(df, 'AF' if use_full_names else 'AU')
    if col is None:
        col = get_col(df, 'AU')
    if col is None:
        return pd.Series(dtype=str)
    return safe_split(df[col], sep='; ')


def extract_keywords(df: pd.DataFrame, field: str = 'DE') -> pd.Series:
    """Extrai palavras-chave (DE = autor, ID = Keywords Plus)."""
    col = get_col(df, field)
    if col is None:
        return pd.Series(dtype=str)
    return safe_split(df[col], sep='; ').str.lower().str.strip()


def extract_references(df: pd.DataFrame) -> pd.Series:
    """Extrai referências citadas individuais do campo CR."""
    col = get_col(df, 'CR')
    if col is None:
        return pd.Series(dtype=str)
    return safe_split(df[col], sep='; ')


def get_year_col(df: pd.DataFrame) -> str:
    """Retorna o nome da coluna de ano."""
    return get_col(df, 'PY') or 'Ano de Publicação'


def get_citations_col(df: pd.DataFrame) -> str:
    """Retorna o nome da coluna de citações total."""
    col = get_col(df, 'Z9')
    if col is None:
        col = get_col(df, 'TC')
    return col


@st.cache_data(show_spinner="Calculando Lei de Lotka...")
def lotka_law(df: pd.DataFrame) -> dict:
    """
    Aplica a Lei de Lotka para identificar autores-núcleo.
    M = 0.749 × √(Nmax), onde Nmax = máximo de publicações de um autor.
    Autores com publicações >= M são considerados núcleo.
    """
    authors = extract_authors(df)
    if authors.empty:
        return {'threshold': 0, 'core_authors': pd.DataFrame(), 'distribution': pd.DataFrame()}

    author_counts = authors.value_counts()
    n_max = author_counts.max()
    m = 0.749 * np.sqrt(n_max)

    core = author_counts[author_counts >= m].reset_index()
    core.columns = ['Autor', 'Publicações']

    # Distribuição de produtividade (para gráfico log-log)
    freq = author_counts.rename('pubs').value_counts().sort_index()
    dist = pd.DataFrame({'Nº Publicações': freq.index, 'Nº Autores': freq.values})

    return {
        'threshold': round(m, 2),
        'n_max': n_max,
        'core_authors': core,
        'distribution': dist,
        'total_authors': len(author_counts),
        'core_count': len(core),
    }


@st.cache_data(show_spinner="Calculando Lei de Bradford...")
def bradford_law(df: pd.DataFrame) -> dict:
    """
    Aplica a Lei de Bradford para identificar periódicos-núcleo.
    Divide periódicos em 3 zonas com aproximadamente o mesmo número de artigos.
    """
    col = get_col(df, 'SO')
    if col is None:
        return {'zones': pd.DataFrame()}

    journal_counts = df[col].value_counts().reset_index()
    journal_counts.columns = ['Periódico', 'Artigos']
    journal_counts = journal_counts.sort_values('Artigos', ascending=False)
    journal_counts['Acumulado'] = journal_counts['Artigos'].cumsum()

    total = journal_counts['Artigos'].sum()
    third = total / 3

    zones = []
    for _, row in journal_counts.iterrows():
        if row['Acumulado'] <= third:
            zones.append('Zona 1 (Núcleo)')
        elif row['Acumulado'] <= 2 * third:
            zones.append('Zona 2 (Semi-produtivo)')
        else:
            zones.append('Zona 3 (Periférico)')

    journal_counts['Zona de Bradford'] = zones

    zone_summary = journal_counts.groupby('Zona de Bradford').agg(
        Periódicos=('Periódico', 'count'),
        Artigos=('Artigos', 'sum')
    ).reset_index()

    return {
        'journals': journal_counts,
        'zone_summary': zone_summary,
        'total_journals': len(journal_counts),
    }


def calculate_h_index(citations: list) -> int:
    """Calcula o índice h a partir de uma lista de citações."""
    citations_sorted = sorted(citations, reverse=True)
    h = 0
    for i, c in enumerate(citations_sorted, 1):
        if c >= i:
            h = i
        else:
            break
    return h


@st.cache_data(show_spinner="Calculando métricas de autores...")
def author_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula métricas detalhadas por autor: publicações, citações, h-index, etc.
    """
    au_col = get_col(df, 'AU')
    cit_col = get_citations_col(df)
    year_col = get_year_col(df)

    if au_col is None or cit_col is None:
        return pd.DataFrame()

    records = []
    for idx, row in df.iterrows():
        if pd.isna(row.get(au_col)):
            continue
        authors = [a.strip() for a in str(row[au_col]).split('; ')]
        cit = int(row.get(cit_col, 0) or 0)
        year = int(row.get(year_col, 0) or 0)
        for author in authors:
            if author:
                records.append({'Autor': author, 'Citações': cit, 'Ano': year})

    if not records:
        return pd.DataFrame()

    adf = pd.DataFrame(records)
    grouped = adf.groupby('Autor').agg(
        Publicações=('Citações', 'count'),
        **{'Citações Total': ('Citações', 'sum')},
        **{'Média Citações': ('Citações', 'mean')},
        **{'Primeiro Ano': ('Ano', 'min')},
        **{'Último Ano': ('Ano', 'max')},
    ).reset_index()

    # H-index por autor
    h_indices = []
    for author in grouped['Autor']:
        cits = adf[adf['Autor'] == author]['Citações'].tolist()
        h_indices.append(calculate_h_index(cits))
    grouped['Índice h'] = h_indices

    grouped['Média Citações'] = grouped['Média Citações'].round(1)
    return grouped.sort_values('Publicações', ascending=False).reset_index(drop=True)


@st.cache_data(show_spinner="Calculando estatísticas anuais...")
def yearly_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Estatísticas por ano: publicações, citações, acumulado."""
    year_col = get_year_col(df)
    cit_col = get_citations_col(df)
    if year_col is None or year_col not in df.columns:
        return pd.DataFrame()

    agg_dict = {}
    if cit_col and cit_col in df.columns:
        agg_dict['Citações'] = (cit_col, 'sum')

    stats = df.groupby(year_col).agg(
        Publicações=(year_col, 'count'),
        **agg_dict,
    ).reset_index()
    stats.columns = ['Ano', 'Publicações'] + (['Citações'] if cit_col else [])
    stats = stats.sort_values('Ano')
    stats['Acumulado Publicações'] = stats['Publicações'].cumsum()
    if 'Citações' in stats.columns:
        stats['Acumulado Citações'] = stats['Citações'].cumsum()
    # Taxa de crescimento
    stats['Crescimento (%)'] = stats['Publicações'].pct_change().fillna(0) * 100
    stats['Crescimento (%)'] = stats['Crescimento (%)'].replace([np.inf, -np.inf], 0).round(1)
    return stats


@st.cache_data(show_spinner="Construindo rede de co-autoria...")
def coauthorship_network(df: pd.DataFrame, top_n: int = 50) -> tuple:
    """
    Constrói rede de co-autoria dos top N autores.
    Retorna (nodes_df, edges_df) para visualização.
    """
    import networkx as nx
    try:
        from community import community_louvain
        has_louvain = True
    except ImportError:
        has_louvain = False

    au_col = get_col(df, 'AU')
    cit_col = get_citations_col(df)
    if au_col is None:
        return pd.DataFrame(), pd.DataFrame()

    # Encontrar top N autores
    all_authors = safe_split(df[au_col], sep='; ')
    top_authors = set(all_authors.value_counts().head(top_n).index)

    # Construir grafo
    G = nx.Graph()
    for _, row in df.iterrows():
        if pd.isna(row.get(au_col)):
            continue
        authors = [a.strip() for a in str(row[au_col]).split('; ')]
        relevant = [a for a in authors if a in top_authors]
        for i, a1 in enumerate(relevant):
            for a2 in relevant[i+1:]:
                if G.has_edge(a1, a2):
                    G[a1][a2]['weight'] += 1
                else:
                    G.add_edge(a1, a2, weight=1)

    if len(G.nodes) == 0:
        return pd.DataFrame(), pd.DataFrame()

    # Detectar comunidades
    if has_louvain and len(G.nodes) > 1:
        partition = community_louvain.best_partition(G)
    else:
        partition = {n: 0 for n in G.nodes}

    # Métricas de centralidade
    degree_cent = nx.degree_centrality(G)
    betweenness = nx.betweenness_centrality(G)

    pub_counts = all_authors.value_counts()
    nodes = []
    for node in G.nodes:
        nodes.append({
            'Autor': node,
            'Publicações': int(pub_counts.get(node, 0)),
            'Comunidade': partition.get(node, 0),
            'Grau': G.degree(node),
            'Centralidade Grau': round(degree_cent.get(node, 0), 4),
            'Centralidade Intermediação': round(betweenness.get(node, 0), 4),
        })

    edges = []
    for u, v, d in G.edges(data=True):
        edges.append({'Origem': u, 'Destino': v, 'Peso': d['weight']})

    return pd.DataFrame(nodes), pd.DataFrame(edges)


@st.cache_data(show_spinner="Construindo rede de co-ocorrência...")
def keyword_cooccurrence_network(df: pd.DataFrame, field: str = 'DE', min_freq: int = 5, top_n: int = 50) -> tuple:
    """
    Constrói rede de co-ocorrência de palavras-chave.
    Retorna (nodes_df, edges_df) para visualização.
    """
    import networkx as nx
    try:
        from community import community_louvain
        has_louvain = True
    except ImportError:
        has_louvain = False

    col = get_col(df, field)
    if col is None:
        return pd.DataFrame(), pd.DataFrame()

    # Contar frequências e filtrar top N
    all_kw = safe_split(df[col], sep='; ').str.lower().str.strip()
    kw_counts = all_kw.value_counts()
    top_kw = set(kw_counts[kw_counts >= min_freq].head(top_n).index)

    # Construir grafo de co-ocorrência
    G = nx.Graph()
    for _, row in df.iterrows():
        if pd.isna(row.get(col)):
            continue
        kws = [k.strip().lower() for k in str(row[col]).split('; ')]
        relevant = [k for k in kws if k in top_kw]
        for i, k1 in enumerate(relevant):
            for k2 in relevant[i+1:]:
                if k1 != k2:
                    if G.has_edge(k1, k2):
                        G[k1][k2]['weight'] += 1
                    else:
                        G.add_edge(k1, k2, weight=1)

    if len(G.nodes) == 0:
        return pd.DataFrame(), pd.DataFrame()

    if has_louvain and len(G.nodes) > 1:
        partition = community_louvain.best_partition(G)
    else:
        partition = {n: 0 for n in G.nodes}

    nodes = []
    for node in G.nodes:
        nodes.append({
            'Palavra-chave': node,
            'Frequência': int(kw_counts.get(node, 0)),
            'Cluster': partition.get(node, 0),
            'Grau': G.degree(node),
        })

    edges = []
    for u, v, d in G.edges(data=True):
        edges.append({'Origem': u, 'Destino': v, 'Peso': d['weight']})

    return pd.DataFrame(nodes), pd.DataFrame(edges)


@st.cache_data(show_spinner="Construindo rede de colaboração...")
def country_collaboration_network(df: pd.DataFrame, top_n: int = 30) -> tuple:
    """Constrói rede de colaboração internacional."""
    import networkx as nx
    try:
        from community import community_louvain
        has_louvain = True
    except ImportError:
        has_louvain = False

    col = get_col(df, 'C1')
    if col is None:
        col = get_col(df, 'RP')
    if col is None:
        return pd.DataFrame(), pd.DataFrame()

    # Extrair países por artigo e contar
    country_list = []
    for _, row in df.iterrows():
        if pd.isna(row.get(col)):
            continue
        countries = set()
        for part in str(row[col]).split('; '):
            elements = part.split(', ')
            if elements:
                c = elements[-1].strip().rstrip('.')
                if len(c) > 2 and not c.isdigit() and '@' not in c and len(c) < 50:
                    c = normalize_country(c)
                    if c:
                        countries.add(c)
        if len(countries) > 1:
            country_list.append(list(countries))

    # Top N países por frequência
    flat = [c for group in country_list for c in group]
    top_countries = set(pd.Series(flat).value_counts().head(top_n).index)

    G = nx.Graph()
    for countries in country_list:
        relevant = [c for c in countries if c in top_countries]
        for i, c1 in enumerate(relevant):
            for c2 in relevant[i+1:]:
                if G.has_edge(c1, c2):
                    G[c1][c2]['weight'] += 1
                else:
                    G.add_edge(c1, c2, weight=1)

    if len(G.nodes) == 0:
        return pd.DataFrame(), pd.DataFrame()

    if has_louvain and len(G.nodes) > 1:
        partition = community_louvain.best_partition(G)
    else:
        partition = {n: 0 for n in G.nodes}

    pub_counts = pd.Series(flat).value_counts()
    nodes = []
    for node in G.nodes:
        nodes.append({
            'País': node,
            'Publicações': int(pub_counts.get(node, 0)),
            'Comunidade': partition.get(node, 0),
            'Colaborações': G.degree(node),
        })

    edges = []
    for u, v, d in G.edges(data=True):
        edges.append({'Origem': u, 'Destino': v, 'Peso': d['weight']})

    return pd.DataFrame(nodes), pd.DataFrame(edges)


@st.cache_data(show_spinner="Construindo rede institucional...")
def institution_collaboration_network(df: pd.DataFrame, top_n: int = 30) -> tuple:
    """Constrói rede de colaboração institucional."""
    import networkx as nx
    try:
        from community import community_louvain
        has_louvain = True
    except ImportError:
        has_louvain = False

    col = get_col(df, 'C3')
    if col is None:
        col = get_col(df, 'C1')
    if col is None:
        col = get_col(df, 'RP')
    if col is None:
        return pd.DataFrame(), pd.DataFrame()

    # Extrair instituições por artigo
    inst_list = []
    for _, row in df.iterrows():
        if pd.isna(row.get(col)):
            continue
        insts = [i.strip() for i in str(row[col]).split('; ') if i.strip()]
        if len(insts) > 1:
            inst_list.append(insts)

    flat = [i for group in inst_list for i in group]
    top_insts = set(pd.Series(flat).value_counts().head(top_n).index)

    G = nx.Graph()
    for insts in inst_list:
        relevant = [i for i in insts if i in top_insts]
        for i, i1 in enumerate(relevant):
            for i2 in relevant[i+1:]:
                if i1 != i2:
                    if G.has_edge(i1, i2):
                        G[i1][i2]['weight'] += 1
                    else:
                        G.add_edge(i1, i2, weight=1)

    if len(G.nodes) == 0:
        return pd.DataFrame(), pd.DataFrame()

    if has_louvain and len(G.nodes) > 1:
        partition = community_louvain.best_partition(G)
    else:
        partition = {n: 0 for n in G.nodes}

    pub_counts = pd.Series(flat).value_counts()
    nodes = []
    for node in G.nodes:
        nodes.append({
            'Instituição': node, 'Publicações': int(pub_counts.get(node, 0)),
            'Comunidade': partition.get(node, 0), 'Colaborações': G.degree(node),
        })

    edges = []
    for u, v, d in G.edges(data=True):
        edges.append({'Origem': u, 'Destino': v, 'Peso': d['weight']})

    return pd.DataFrame(nodes), pd.DataFrame(edges)
