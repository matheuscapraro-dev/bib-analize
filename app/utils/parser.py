"""
Parser de arquivos de exportação do Web of Science.
Suporta formato tagged (FN/VR/PT...) e tab-delimited (.txt), além de CSV.
"""
import pandas as pd
import numpy as np
import io
import re
from unidecode import unidecode

# Mapeamento completo dos campos WoS para nomes legíveis em português
FIELD_MAP = {
    'PT': 'Tipo de Publicação',
    'AU': 'Autores',
    'BA': 'Autor do Livro',
    'BE': 'Editor do Livro',
    'GP': 'Grupo Autor do Livro',
    'AF': 'Autores (Nome Completo)',
    'BF': 'Autores Livro (Nome Completo)',
    'CA': 'Autor Corporativo',
    'TI': 'Título',
    'SO': 'Periódico',
    'SE': 'Série',
    'BS': 'Subtítulo Série Livro',
    'LA': 'Idioma',
    'DT': 'Tipo de Documento',
    'CT': 'Título da Conferência',
    'CY': 'País da Conferência',
    'CL': 'Local da Conferência',
    'SP': 'Patrocinador da Conferência',
    'HO': 'Organização Anfitriã',
    'DE': 'Palavras-chave do Autor',
    'ID': 'Keywords Plus',
    'AB': 'Resumo',
    'C1': 'Endereços',
    'C3': 'Afiliações',
    'RP': 'Endereço de Reimpressão',
    'EM': 'Email',
    'RI': 'ResearcherID',
    'OI': 'ORCID',
    'FU': 'Agência Financiadora',
    'FP': 'Programa de Financiamento',
    'FX': 'Texto de Financiamento',
    'CR': 'Referências Citadas',
    'NR': 'Nº de Referências Citadas',
    'TC': 'Citações WoS Core',
    'Z9': 'Citações Total',
    'U1': 'Uso (180 dias)',
    'U2': 'Uso (desde 2013)',
    'PU': 'Editora',
    'PI': 'Cidade da Editora',
    'PA': 'Endereço da Editora',
    'SN': 'ISSN',
    'EI': 'eISSN',
    'BN': 'ISBN',
    'J9': 'Abreviação do Periódico',
    'JI': 'ISO do Periódico',
    'PD': 'Data de Publicação',
    'PY': 'Ano de Publicação',
    'VL': 'Volume',
    'IS': 'Fascículo',
    'PN': 'Número da Parte',
    'SU': 'Suplemento',
    'SI': 'Edição Especial',
    'MA': 'Endereço da Reunião',
    'BP': 'Página Inicial',
    'EP': 'Página Final',
    'AR': 'Número do Artigo',
    'DI': 'DOI',
    'DL': 'Entrega de Documento',
    'D2': 'DOI do Livro',
    'EA': 'Acesso Antecipado',
    'PG': 'Contagem de Páginas',
    'WC': 'Categorias WoS',
    'WE': 'Índice WoS',
    'SC': 'Áreas de Pesquisa',
    'GA': 'Categoria Geral',
    'PM': 'PubMed ID',
    'OA': 'Acesso Aberto',
    'HC': 'Altamente Citado',
    'DA': 'Data de Atualização',
    'UT': 'ID Único WoS',
}

# Campos numéricos
NUMERIC_FIELDS = ['NR', 'TC', 'Z9', 'U1', 'U2', 'PY', 'PG']
NUMERIC_FIELDS_PT = [FIELD_MAP.get(f, f) for f in NUMERIC_FIELDS]

# Tags que usam "; " como separador no formato tagged (listas multi-valor)
_MULTILINE_JOIN_NEWLINE = {'CR'}  # referências: cada linha é uma referência separada
_MULTILINE_JOIN_SEMI = {'AU', 'AF', 'BA', 'BF', 'BE', 'C1', 'C3'}  # autores/endereços


def _detect_format(text: str) -> str:
    """Detecta se o arquivo é tagged (FN/VR) ou tab-delimited."""
    first_line = text.split('\n', 1)[0].strip()
    if first_line.startswith('FN ') or first_line.startswith('FN\t'):
        # Poderia ser tagged com FN na primeira linha
        # Mas tab-delimited também começa com FN se...
        # Verificar se segunda linha tem tag de 2 letras
        lines = text.split('\n', 5)
        for line in lines[1:4]:
            stripped = line.strip()
            if stripped and len(stripped) >= 2:
                tag_part = stripped[:2]
                rest = stripped[2:3] if len(stripped) > 2 else ''
                if tag_part.isalpha() and tag_part.isupper() and (rest == ' ' or rest == '' or stripped == 'ER'):
                    return 'tagged'
        # Se a primeira linha tem muitos tabs, é tab-delimited
        if first_line.count('\t') > 5:
            return 'tab-delimited'
        return 'tagged'
    elif '\t' in first_line and first_line.count('\t') > 3:
        return 'tab-delimited'
    return 'tagged'


def parse_wos_tagged(text: str) -> pd.DataFrame:
    """
    Parseia arquivo WoS no formato tagged (FN Clarivate...).
    Cada registro começa com PT e termina com ER.
    Linhas de continuação começam com 3 espaços.
    """
    records = []
    current_record = {}
    current_tag = None

    for line in text.split('\n'):
        # Pular linhas de cabeçalho/rodapé
        if line.startswith('FN ') or line.startswith('VR ') or line.startswith('EF'):
            continue

        stripped = line.rstrip()

        if stripped == 'ER':
            # Fim do registro
            if current_record:
                records.append(current_record)
            current_record = {}
            current_tag = None
            continue

        if len(stripped) >= 3 and stripped[:2].isalpha() and stripped[:2].isupper() and stripped[2] == ' ':
            # Nova tag (ex: "AU Smith, J")
            current_tag = stripped[:2]
            value = stripped[3:]
            if current_tag in current_record:
                # Tag repetida — concatenar
                if current_tag in _MULTILINE_JOIN_NEWLINE:
                    current_record[current_tag] += '; ' + value
                elif current_tag in _MULTILINE_JOIN_SEMI:
                    current_record[current_tag] += '; ' + value
                else:
                    current_record[current_tag] += ' ' + value
            else:
                current_record[current_tag] = value

        elif stripped.startswith('   ') and current_tag:
            # Linha de continuação (3 espaços)
            value = stripped.strip()
            if current_tag in _MULTILINE_JOIN_NEWLINE:
                current_record[current_tag] += '; ' + value
            elif current_tag in _MULTILINE_JOIN_SEMI:
                current_record[current_tag] += '; ' + value
            else:
                current_record[current_tag] += ' ' + value

    # Último registro se não terminou com ER
    if current_record:
        records.append(current_record)

    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records)


def parse_wos_tabdelimited(text: str) -> pd.DataFrame:
    """Parseia arquivo WoS no formato tab-delimited."""
    df = pd.read_csv(io.StringIO(text), sep='\t', dtype=str, on_bad_lines='skip')
    df.columns = [c.strip().replace('\ufeff', '') for c in df.columns]
    return df


def parse_wos_file(file_content: bytes, filename: str = "") -> pd.DataFrame:
    """Parseia um arquivo de exportação WoS, detectando automaticamente o formato."""
    try:
        text = file_content.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = file_content.decode('latin-1')

    fmt = _detect_format(text)
    if fmt == 'tagged':
        return parse_wos_tagged(text)
    else:
        return parse_wos_tabdelimited(text)


def consolidate_files(uploaded_files: list) -> pd.DataFrame:
    """
    Consolida múltiplos arquivos WoS em um único DataFrame.
    Remove duplicatas baseado no campo UT (ID único WoS).
    """
    dfs = []
    for f in uploaded_files:
        content = f.read()
        f.seek(0)
        name = f.name if hasattr(f, 'name') else ''
        if name.lower().endswith('.csv'):
            try:
                text = content.decode('utf-8-sig')
            except UnicodeDecodeError:
                text = content.decode('latin-1')
            df = pd.read_csv(io.StringIO(text), dtype=str)
        else:
            df = parse_wos_file(content, name)
        if not df.empty:
            dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    combined = pd.concat(dfs, ignore_index=True)

    # Remover duplicatas pelo UT (ID único)
    if 'UT' in combined.columns:
        combined = combined.drop_duplicates(subset='UT', keep='first')
    elif FIELD_MAP.get('UT', '') in combined.columns:
        combined = combined.drop_duplicates(subset=FIELD_MAP['UT'], keep='first')

    return combined


def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Renomeia colunas WoS abreviadas para nomes legíveis em português."""
    rename_map = {}
    for col in df.columns:
        col_clean = col.strip()
        if col_clean in FIELD_MAP:
            rename_map[col] = FIELD_MAP[col_clean]
    return df.rename(columns=rename_map)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Limpa e converte tipos dos dados."""
    df = df.copy()

    # Converter campos numéricos
    for field in NUMERIC_FIELDS_PT:
        if field in df.columns:
            df[field] = pd.to_numeric(df[field], errors='coerce')

    for field in NUMERIC_FIELDS:
        if field in df.columns:
            df[field] = pd.to_numeric(df[field], errors='coerce')

    # Preencher citações NaN com 0
    for col in ['Citações Total', 'Citações WoS Core', 'Z9', 'TC']:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(int)

    # Preencher ano NaN
    year_col = 'Ano de Publicação' if 'Ano de Publicação' in df.columns else 'PY'
    if year_col in df.columns:
        df[year_col] = pd.to_numeric(df[year_col], errors='coerce')
        df = df.dropna(subset=[year_col])
        df[year_col] = df[year_col].astype(int)

    return df


def process_upload(uploaded_files: list) -> pd.DataFrame:
    """Pipeline completo: consolidar, renomear, limpar."""
    df = consolidate_files(uploaded_files)
    if df.empty:
        return df
    df = rename_columns(df)
    df = clean_data(df)
    return df.reset_index(drop=True)


def get_col(df: pd.DataFrame, wos_code: str) -> str:
    """Retorna o nome da coluna no DataFrame (português ou abreviado)."""
    pt_name = FIELD_MAP.get(wos_code, wos_code)
    if pt_name in df.columns:
        return pt_name
    if wos_code in df.columns:
        return wos_code
    return None


def safe_split(series: pd.Series, sep: str = '; ') -> pd.Series:
    """Split seguro de uma coluna string por separador, retornando Series explodida."""
    return series.dropna().str.split(sep).explode().str.strip()
