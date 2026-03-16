"""Funções utilitárias para tabelas formatadas."""
import streamlit as st
import pandas as pd


def show_dataframe(df: pd.DataFrame, title: str = "", key: str = None, height: int = 400):
    """Exibe DataFrame com opção de download CSV."""
    if title:
        st.subheader(title)
    if df.empty:
        st.info("Sem dados disponíveis.")
        return

    st.dataframe(df, use_container_width=True, height=height)

    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        "⬇️ Baixar CSV",
        csv,
        f"{title or 'dados'}.csv",
        "text/csv",
        key=key or f"dl_{title}_{id(df)}",
    )
