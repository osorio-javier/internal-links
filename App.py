import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Dashboard de Enlazado Interno",
    page_icon="🔗",
    layout="wide"
)

# --- Título y Cabecera ---
st.title("🔗 Dashboard de Análisis de Enlazado Interno")
st.markdown("""
Sube el archivo `master_file_final.csv` generado previamente para visualizar la estructura de enlaces internos de tu sitio.
Esta herramienta te ayudará a identificar qué páginas reciben y envían más enlaces, y cuáles son los textos ancla más utilizados.
""")

# --- Barra Lateral (Sidebar) ---
st.sidebar.header("Configuración")

# Widget para subir el archivo
uploaded_file = st.sidebar.file_uploader(
    "Carga tu archivo master_file_final.csv",
    type=["csv"]
)

# --- Lógica Principal de la Aplicación ---
if uploaded_file is None:
    st.info("👈 Por favor, carga un archivo CSV para comenzar el análisis.")
    st.stop()

# --- Carga y Cache de Datos ---
# Usamos un decorador de cache para que los datos no se recarguen en cada interacción.
@st.cache_data
def load_data(file):
    try:
        df = pd.read_csv(file)
        # Limpieza básica de datos
        df['URL Destino'] = df['URL Destino'].str.strip()
        df['Anchor text'] = df['Anchor text'].str.strip()
        return df
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        return None

df = load_data(uploaded_file)

if df is None:
    st.stop()

# --- Métricas Principales ---
st.header("Métricas Generales")

total_paginas_origen = df['Dirección'].nunique()
total_enlaces = len(df)
total_paginas_destino = df['URL Destino'].nunique()

col1, col2, col3 = st.columns(3)
col1.metric("Páginas de Origen Únicas", f"{total_paginas_origen}")
col2.metric("Total de Enlaces Analizados", f"{total_enlaces}")
col3.metric("Páginas de Destino Únicas", f"{total_paginas_destino}")

st.markdown("---")

# --- Visualizaciones de Datos ---
st.header("Análisis Gráfico del Enlazado")

# Dividir la sección en dos columnas para los gráficos
col_graf1, col_graf2 = st.columns(2)

# Gráfico 1: Top 20 Páginas con MÁS ENLACES SALIENTES (desde el contenido)
with col_graf1:
    st.subheader("Top 15 Páginas con Más Enlaces Salientes")
    origen_counts = df['Dirección'].value_counts().nlargest(15).sort_values(ascending=True)
    fig_origen = px.bar(
        origen_counts,
        x=origen_counts.values,
        y=origen_counts.index,
        orientation='h',
        title="Páginas que más enlazan a otras",
        labels={'x': 'Cantidad de Enlaces Salientes', 'y': 'URL de Origen'},
        template="plotly_white"
    )
    fig_origen.update_layout(showlegend=False)
    st.plotly_chart(fig_origen, use_container_width=True)

# Gráfico 2: Top 20 Páginas que MÁS ENLACES RECIBEN
with col_graf2:
    st.subheader("Top 15 Páginas que Reciben Más Enlaces")
    destino_counts = df['URL Destino'].value_counts().nlargest(15).sort_values(ascending=True)
    fig_destino = px.bar(
        destino_counts,
        x=destino_counts.values,
        y=destino_counts.index,
        orientation='h',
        title="Páginas más enlazadas internamente",
        labels={'x': 'Cantidad de Enlaces Entrantes', 'y': 'URL de Destino'},
        color_discrete_sequence=['#ff7f0e']
    )
    fig_destino.update_layout(showlegend=False)
    st.plotly_chart(fig_destino, use_container_width=True)

# Gráfico 3: Top 20 Anchor Texts más utilizados
st.subheader("Top 20 Textos Ancla Más Utilizados")
anchor_counts = df['Anchor text'].value_counts().nlargest(20)
fig_anchor = px.bar(
    anchor_counts,
    x=anchor_counts.index,
    y=anchor_counts.values,
    title="Frecuencia de los Textos Ancla",
    labels={'x': 'Texto Ancla', 'y': 'Frecuencia'},
    color_discrete_sequence=px.colors.qualitative.Pastel
)
st.plotly_chart(fig_anchor, use_container_width=True)

st.markdown("---")

# --- Explorador de Enlaces por Página (Diagrama de Sankey) ---
st.header("Explorador de Flujo de Enlaces por Página")
st.markdown("Selecciona una página de origen para ver a dónde enlaza y con qué textos ancla.")

# Selector para la página de origen
lista_paginas = sorted(df['Dirección'].unique())
pagina_seleccionada = st.selectbox(
    "Selecciona una página de Origen:",
    options=lista_paginas
)

if pagina_seleccionada:
    # Filtrar el dataframe por la página seleccionada
    df_filtrado = df[df['Dirección'] == pagina_seleccionada]

    if not df_filtrado.empty:
        # Crear nodos para el diagrama de Sankey
        # Los nodos son: la página de origen, los textos ancla y las páginas de destino
        all_nodes = list(pd.concat([
            df_filtrado['Dirección'],
            df_filtrado['Anchor text'],
            df_filtrado['URL Destino']
        ]).unique())
        
        # Crear un diccionario para mapear nodos a índices numéricos
        node_map = {node: i for i, node in enumerate(all_nodes)}

        # Crear las fuentes (sources), destinos (targets) y valores (values) para el Sankey
        sources = df_filtrado['Dirección'].map(node_map)
        targets_anchor = df_filtrado['Anchor text'].map(node_map)
        
        sources_anchor = df_filtrado['Anchor text'].map(node_map)
        targets_final = df_filtrado['URL Destino'].map(node_map)

        # Combinar los flujos: (Página -> Anchor) y (Anchor -> URL Destino)
        link_sources = pd.concat([sources, sources_anchor])
        link_targets = pd.concat([targets_anchor, targets_final])
        values = [1] * len(link_sources) # Cada enlace cuenta como 1

        # Crear la figura del diagrama de Sankey
        fig_sankey = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=all_nodes,
                color="blue"
            ),
            link=dict(
                source=link_sources,
                target=link_targets,
                value=values
            ))])

        fig_sankey.update_layout(
            title_text=f"Flujo de enlaces desde: {pagina_seleccionada}",
            font_size=10
        )
        st.plotly_chart(fig_sankey, use_container_width=True)
    else:
        st.warning("No se encontraron datos de enlaces para la página seleccionada.")

st.markdown("---")

# --- Tabla de Datos Crudos ---
st.header("Explorar Datos Crudos")
st.markdown("Usa los filtros de las columnas para buscar datos específicos.")
st.dataframe(df)