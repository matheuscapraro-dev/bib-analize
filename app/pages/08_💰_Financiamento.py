"""Análise de Financiamento — agências financiadoras, impacto."""
import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.parser import get_col, safe_split
from utils.data_processing import get_year_col, get_citations_col
from components.charts import bar_chart, pie_chart, COLOR_PRIMARY, COLOR_SECONDARY
from components.filters import apply_filters, sidebar_upload
from components.tables import show_dataframe
import plotly.express as px

st.set_page_config(page_title="Financiamento", page_icon="💰", layout="wide")
st.title("💰 Análise de Financiamento")

sidebar_upload()
df = st.session_state.get('df')
if df is None or df.empty:
    st.warning("⚠️ Nenhum dado carregado. Volte à página inicial e faça upload dos arquivos.")
    st.stop()

df_f = apply_filters(df)
fu_col = get_col(df_f, 'FU')
year_col = get_year_col(df_f)
cit_col = get_citations_col(df_f)

if fu_col is None or fu_col not in df_f.columns:
    st.error("Campo de financiamento (FU) não encontrado nos dados. Verifique se a exportação inclui esse campo.")
    st.stop()

# --- KPIs de financiamento ---
has_funding = df_f[fu_col].notna()
n_funded = has_funding.sum()
n_total = len(df_f)
pct_funded = round(n_funded / n_total * 100, 1) if n_total > 0 else 0

c1, c2, c3 = st.columns(3)
c1.metric("📊 Artigos com Financiamento", f"{n_funded:,}")
c2.metric("📊 % com Financiamento", f"{pct_funded}%")
if cit_col and cit_col in df_f.columns:
    avg_funded = df_f[has_funding][cit_col].mean()
    avg_not_funded = df_f[~has_funding][cit_col].mean()
    c3.metric("📈 Média Citações (Financiados)", f"{avg_funded:.1f}",
              delta=f"{avg_funded - avg_not_funded:+.1f} vs não financiados")

st.markdown("---")

# --- Top N agências financiadoras ---
top_n = st.slider("Número de agências (Top N)", 5, 50, 20, key="fund_top_n")
st.subheader(f"Top {top_n} Agências Financiadoras")

agencies = safe_split(df_f[fu_col], sep='; ')
agency_counts = agencies.value_counts().head(top_n).reset_index()
agency_counts.columns = ['Agência', 'Artigos']

fig1 = bar_chart(agency_counts, 'Agência', 'Artigos',
                 f'Top {top_n} Agências Financiadoras', orientation='h',
                 height=max(400, top_n * 28))
st.plotly_chart(fig1, use_container_width=True)

st.markdown("---")

# --- Impacto do financiamento nas citações ---
if cit_col and cit_col in df_f.columns:
    st.subheader("📊 Impacto do Financiamento nas Citações")
    st.markdown("> Comparação da distribuição de citações entre artigos financiados e não financiados.")

    df_funded = df_f.copy()
    df_funded['Financiamento'] = df_funded[fu_col].apply(
        lambda x: 'Com financiamento' if pd.notna(x) else 'Sem financiamento'
    )

    fig_box = px.box(df_funded, x='Financiamento', y=cit_col,
                     color='Financiamento', title='Citações: Financiados vs Não Financiados',
                     labels={cit_col: 'Citações'})
    fig_box.update_layout(showlegend=False)
    st.plotly_chart(fig_box, use_container_width=True)

    # Detalhamento
    summary = df_funded.groupby('Financiamento').agg(
        Artigos=(cit_col, 'count'),
        **{'Média Citações': (cit_col, 'mean')},
        **{'Mediana Citações': (cit_col, 'median')},
        **{'Total Citações': (cit_col, 'sum')},
    ).reset_index()
    summary['Média Citações'] = summary['Média Citações'].round(1)
    st.dataframe(summary, use_container_width=True)

st.markdown("---")

# --- Evolução temporal do financiamento ---
if year_col and year_col in df_f.columns:
    st.subheader("📅 Evolução do Financiamento ao Longo do Tempo")

    yearly_fund = df_f.groupby(year_col).apply(
        lambda g: pd.Series({
            'Total': len(g),
            'Financiados': g[fu_col].notna().sum(),
        })
    ).reset_index()
    yearly_fund.columns = ['Ano', 'Total', 'Financiados']
    yearly_fund['% Financiados'] = (yearly_fund['Financiados'] / yearly_fund['Total'] * 100).round(1)

    fig_trend = px.bar(yearly_fund, x='Ano', y=['Financiados', 'Total'],
                       title='Artigos com Financiamento por Ano', barmode='group')
    st.plotly_chart(fig_trend, use_container_width=True)

    fig_pct = px.line(yearly_fund, x='Ano', y='% Financiados',
                      title='% de Artigos com Financiamento por Ano', markers=True)
    fig_pct.update_traces(line_color=COLOR_PRIMARY)
    st.plotly_chart(fig_pct, use_container_width=True)

st.markdown("---")
# Tabela completa
agency_all = agencies.value_counts().reset_index()
agency_all.columns = ['Agência', 'Artigos']
show_dataframe(agency_all, "Tabela Completa — Agências Financiadoras", key="dl_agencies")
