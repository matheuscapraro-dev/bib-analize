"""Filtros de sidebar reutilizáveis."""
import streamlit as st
import pandas as pd
from utils.parser import get_col, process_upload


def sidebar_upload():
    """Renderiza o widget de upload na sidebar. Retorna o df do session_state."""
    if 'df' not in st.session_state:
        st.session_state.df = None
        st.session_state.df_filtered = None

    st.sidebar.header("📁 Carregar Dados")
    uploaded_files = st.sidebar.file_uploader(
        "Upload de arquivos WoS (.txt ou .csv)",
        type=['txt', 'csv'],
        accept_multiple_files=True,
        key="file_uploader",
    )

    if uploaded_files:
        if st.sidebar.button("🔄 Processar Dados", type="primary"):
            with st.spinner("Processando arquivos..."):
                df = process_upload(uploaded_files)
                if not df.empty:
                    st.session_state.df = df
                    st.session_state.df_filtered = df
                    st.sidebar.success(f"✅ {len(df):,} registros carregados de {len(uploaded_files)} arquivo(s)")
                else:
                    st.sidebar.error("❌ Nenhum dado encontrado nos arquivos.")

    return st.session_state.get('df')


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica filtros na sidebar e retorna DataFrame filtrado."""
    if df.empty:
        return df

    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filtros")

    filtered = df.copy()

    # Filtro por ano
    year_col = get_col(df, 'PY')
    if year_col and year_col in df.columns:
        years = df[year_col].dropna().astype(int)
        if len(years) > 0:
            min_y, max_y = int(years.min()), int(years.max())
            if min_y < max_y:
                year_range = st.sidebar.slider(
                    "Período (Ano)", min_y, max_y, (min_y, max_y), key="filter_year"
                )
                filtered = filtered[
                    (filtered[year_col] >= year_range[0]) &
                    (filtered[year_col] <= year_range[1])
                ]

    # Filtro por tipo de documento
    dt_col = get_col(df, 'DT')
    if dt_col and dt_col in df.columns:
        doc_types = sorted(df[dt_col].dropna().unique())
        if len(doc_types) > 1:
            selected_types = st.sidebar.multiselect(
                "Tipo de Documento", doc_types, default=doc_types, key="filter_dt"
            )
            if selected_types:
                filtered = filtered[filtered[dt_col].isin(selected_types)]

    # Filtro por idioma
    la_col = get_col(df, 'LA')
    if la_col and la_col in df.columns:
        languages = sorted(df[la_col].dropna().unique())
        if len(languages) > 1:
            selected_langs = st.sidebar.multiselect(
                "Idioma", languages, default=languages, key="filter_la"
            )
            if selected_langs:
                filtered = filtered[filtered[la_col].isin(selected_langs)]

    # Filtro por acesso aberto
    oa_col = get_col(df, 'OA')
    if oa_col and oa_col in df.columns:
        oa_types = sorted(df[oa_col].dropna().unique())
        if len(oa_types) > 1:
            selected_oa = st.sidebar.multiselect(
                "Acesso Aberto", oa_types, default=oa_types, key="filter_oa"
            )
            if selected_oa:
                filtered = filtered[filtered[oa_col].isin(selected_oa)]

    n_removed = len(df) - len(filtered)
    if n_removed > 0:
        st.sidebar.info(f"📊 {len(filtered):,} de {len(df):,} registros ({n_removed:,} filtrados)")
    else:
        st.sidebar.info(f"📊 {len(filtered):,} registros")

    return filtered
