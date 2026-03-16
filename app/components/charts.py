"""Gráficos Plotly padronizados para o dashboard bibliométrico."""
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# Paleta de cores padrão
COLORS = px.colors.qualitative.Set2
COLORS_SEQ = px.colors.sequential.Blues
COLOR_PRIMARY = '#1f77b4'
COLOR_SECONDARY = '#ff7f0e'
COLOR_THIRD = '#2ca02c'

LAYOUT_DEFAULTS = dict(
    font=dict(family="Arial, sans-serif", size=12),
    plot_bgcolor='rgba(0,0,0,0)',
    paper_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=20, r=20, t=40, b=20),
    hoverlabel=dict(bgcolor="white", font_size=12),
)


def _apply_defaults(fig, height=None):
    fig.update_layout(**LAYOUT_DEFAULTS)
    if height:
        fig.update_layout(height=height)
    fig.update_xaxes(gridcolor='#eee')
    fig.update_yaxes(gridcolor='#eee')
    return fig


def bar_chart(df, x, y, title="", orientation='v', color=COLOR_PRIMARY, height=400, text_auto=True):
    """Gráfico de barras simples."""
    if orientation == 'h':
        fig = px.bar(df, x=y, y=x, orientation='h', title=title, text=y if text_auto else None)
        fig.update_traces(marker_color=color)
        fig.update_layout(yaxis=dict(autorange='reversed'))
    else:
        fig = px.bar(df, x=x, y=y, title=title, text=y if text_auto else None)
        fig.update_traces(marker_color=color)
    if text_auto:
        fig.update_traces(textposition='outside', texttemplate='%{text:,.0f}')
    return _apply_defaults(fig, height)


def bar_chart_colored(df, x, y, color_col, title="", height=400):
    """Gráfico de barras com cores por categoria."""
    fig = px.bar(df, x=x, y=y, color=color_col, title=title, color_discrete_sequence=COLORS)
    return _apply_defaults(fig, height)


def line_chart(df, x, y, title="", color=COLOR_PRIMARY, height=400, markers=True):
    """Gráfico de linha simples."""
    fig = px.line(df, x=x, y=y, title=title, markers=markers)
    fig.update_traces(line_color=color)
    return _apply_defaults(fig, height)


def dual_axis_chart(df, x, y1, y2, name1="", name2="", title="", height=450):
    """Gráfico com dois eixos Y (publicações + citações)."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(x=df[x], y=df[y1], name=name1 or y1, marker_color=COLOR_PRIMARY, opacity=0.7),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=df[x], y=df[y2], name=name2 or y2, mode='lines+markers',
                   line=dict(color=COLOR_SECONDARY, width=2)),
        secondary_y=True,
    )
    fig.update_yaxes(title_text=name1 or y1, secondary_y=False)
    fig.update_yaxes(title_text=name2 or y2, secondary_y=True)
    fig.update_layout(title=title)
    return _apply_defaults(fig, height)


def pie_chart(df, names, values, title="", height=400):
    """Gráfico de pizza/rosca."""
    fig = px.pie(df, names=names, values=values, title=title,
                 color_discrete_sequence=COLORS, hole=0.3)
    fig.update_traces(textposition='inside', textinfo='percent+label')
    return _apply_defaults(fig, height)


def treemap_chart(df, path, values, title="", color_col=None, height=500):
    """Treemap."""
    fig = px.treemap(df, path=path, values=values, title=title,
                     color=color_col, color_discrete_sequence=COLORS)
    return _apply_defaults(fig, height)


def histogram(series, title="", nbins=50, height=400):
    """Histograma."""
    fig = px.histogram(series, nbins=nbins, title=title)
    fig.update_traces(marker_color=COLOR_PRIMARY)
    return _apply_defaults(fig, height)


def box_plot(df, x, y, title="", height=400):
    """Box plot."""
    fig = px.box(df, x=x, y=y, title=title, color_discrete_sequence=COLORS)
    return _apply_defaults(fig, height)


def heatmap(df, x, y, z, title="", height=500):
    """Heatmap."""
    pivot = df.pivot_table(index=y, columns=x, values=z, fill_value=0)
    fig = px.imshow(pivot, title=title, aspect='auto',
                    color_continuous_scale='Blues', text_auto=True)
    return _apply_defaults(fig, height)


def choropleth_map(df, locations, values, title="", height=500, color_scale='Blues'):
    """Mapa mundi choropleth."""
    fig = px.choropleth(
        df, locations=locations, color=values, title=title,
        color_continuous_scale=color_scale,
        projection='natural earth',
    )
    fig.update_layout(geo=dict(showframe=False, showcoastlines=True))
    return _apply_defaults(fig, height)


def network_graph(nodes_df, edges_df, node_label, node_size_col, node_color_col,
                  title="", height=600):
    """Grafo de rede usando NetworkX layout + Plotly."""
    import networkx as nx

    if nodes_df.empty or edges_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Dados insuficientes para gerar a rede.",
                           showarrow=False, font=dict(size=16))
        return _apply_defaults(fig, height)

    G = nx.Graph()
    for _, row in nodes_df.iterrows():
        G.add_node(row[node_label])
    for _, row in edges_df.iterrows():
        G.add_edge(row['Origem'], row['Destino'], weight=row.get('Peso', 1))

    pos = nx.spring_layout(G, k=2/np.sqrt(len(G.nodes)), iterations=50, seed=42)

    # Arestas
    edge_traces = []
    max_weight = edges_df['Peso'].max() if 'Peso' in edges_df.columns else 1
    for _, row in edges_df.iterrows():
        x0, y0 = pos.get(row['Origem'], (0, 0))
        x1, y1 = pos.get(row['Destino'], (0, 0))
        weight = row.get('Peso', 1)
        edge_traces.append(
            go.Scatter(x=[x0, x1, None], y=[y0, y1, None],
                       mode='lines', line=dict(width=max(0.5, weight / max_weight * 3), color='#ccc'),
                       hoverinfo='none', showlegend=False)
        )

    # Nós — mapear comunidades para cores discretas
    community_colors = COLORS  # px.colors.qualitative.Set2
    node_x, node_y, node_text, node_sizes, node_color_list = [], [], [], [], []
    for _, row in nodes_df.iterrows():
        label = row[node_label]
        x, y = pos.get(label, (0, 0))
        node_x.append(x)
        node_y.append(y)
        node_text.append(f"{label}<br>{node_size_col}: {row[node_size_col]}")
        node_sizes.append(max(10, min(50, row[node_size_col] * 2)))
        comm = int(row.get(node_color_col, 0))
        node_color_list.append(community_colors[comm % len(community_colors)])

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode='markers+text', text=[r[node_label] for _, r in nodes_df.iterrows()],
        textposition='top center', textfont=dict(size=8),
        marker=dict(size=node_sizes, color=node_color_list,
                    line=dict(width=1, color='white')),
        hovertext=node_text, hoverinfo='text', showlegend=False,
    )

    fig = go.Figure(data=edge_traces + [node_trace])
    fig.update_layout(title=title, showlegend=False,
                      xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                      yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    return _apply_defaults(fig, height)


def wordcloud_to_fig(word_freq: dict, title="", height=400):
    """Gera imagem de word cloud e retorna como figura Plotly."""
    from wordcloud import WordCloud
    import io
    from PIL import Image

    if not word_freq:
        fig = go.Figure()
        fig.add_annotation(text="Sem dados para gerar nuvem de palavras.",
                           showarrow=False, font=dict(size=16))
        return _apply_defaults(fig, height)

    wc = WordCloud(width=800, height=400, background_color='white',
                   colormap='tab20', max_words=100, prefer_horizontal=0.7)
    wc.generate_from_frequencies(word_freq)

    img = wc.to_image()
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    fig = go.Figure()
    fig.add_layout_image(
        dict(source=Image.open(img_bytes), xref="x", yref="y",
             x=0, y=1, sizex=1, sizey=1,
             xanchor="left", yanchor="top", layer="below")
    )
    fig.update_xaxes(range=[0, 1], showticklabels=False, showgrid=False)
    fig.update_yaxes(range=[0, 1], showticklabels=False, showgrid=False)
    fig.update_layout(title=title, height=height, margin=dict(l=0, r=0, t=40, b=0))
    return fig


def stacked_area(df, x, y_cols, title="", height=450):
    """Gráfico de área empilhada."""
    fig = go.Figure()
    for i, col in enumerate(y_cols):
        fig.add_trace(go.Scatter(
            x=df[x], y=df[col], name=col, mode='lines',
            stackgroup='one', fill='tonexty',
            line=dict(color=COLORS[i % len(COLORS)])
        ))
    fig.update_layout(title=title)
    return _apply_defaults(fig, height)
