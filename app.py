import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import json

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Visualizador de Enlazado Interno", page_icon="🔗", layout="wide")

# --- 2. TÍTULO Y DESCRIPCIÓN ---
st.title('🔗 Visualizador de Enlazado Interno (Interactivo)')
st.markdown("Sube tu archivo CSV para analizar la estructura de enlaces.")

# --- 3. FUNCIÓN DE PROCESAMIENTO (CORREGIDA PARA EL FORMATO REAL DEL CSV)---
def process_data(uploaded_file):
    """
    Procesa el CSV con formato de bloques (todas las URLs primero, luego todos los anclas).
    """
    df = pd.read_csv(uploaded_file)
    
    # Identifica las columnas de URL y de Texto Ancla por separado
    url_cols = [col for col in df.columns if 'URL_Destino_Contenido' in col]
    texto_cols = [col for col in df.columns if 'Texto_Ancla_Contenido' in col]

    # Transforma ambos bloques de datos a un formato largo
    melted_urls = df.melt(id_vars='Dirección', value_vars=url_cols, value_name='Target')
    melted_textos = df.melt(id_vars='Dirección', value_vars=texto_cols, value_name='Anchor_Text')

    # Extrae el número de cada columna para poder unirlas correctamente
    melted_urls['link_num'] = melted_urls['variable'].str.extract(r'(\d+)').astype(int)
    melted_textos['link_num'] = melted_textos['variable'].str.extract(r'(\d+)').astype(int)

    # Une las URLs con sus textos ancla correspondientes
    df_long = pd.merge(melted_urls, melted_textos, on=['Dirección', 'link_num'])

    # Limpieza final
    df_links = df_long[['Dirección', 'Target', 'Anchor_Text']].copy()
    df_links.dropna(subset=['Target'], inplace=True)
    df_links.rename(columns={'Dirección': 'Source'}, inplace=True)
    
    df_links['Source'] = df_links['Source'].astype(str).str.strip()
    df_links['Target'] = df_links['Target'].astype(str).str.strip()

    return df_links

# --- 4. FUNCIÓN PARA GENERAR EL MAPA DE RED ---
def generate_interactive_network(df_links):
    G = nx.from_pandas_edgelist(df_links, 'Source', 'Target', create_using=nx.DiGraph())
    net = Network(height='800px', width='100%', bgcolor='#222222', font_color='white', notebook=True, directed=True)
    net.from_nx(G)

    in_degree = dict(G.in_degree)
    for node in net.nodes:
        degree = in_degree.get(node['id'], 0)
        node['size'] = 10 + degree * 3
        node['title'] = f"{node['id']}<br>Enlaces entrantes: {degree}"

    for edge in net.edges:
        edge['hidden'] = True

    html_content = net.generate_html()
    adjacency_list = json.dumps({source: list(G.successors(source)) for source in G.nodes()})

    js_script = f"""
    <script type="text/javascript">
        document.addEventListener('DOMContentLoaded', function() {{
            const adjacencyList = {adjacency_list};
            if (typeof network !== 'undefined') {{
                let allNodes = network.body.data.nodes.get({{ return: 'Array' }});
                let allEdges = network.body.data.edges.get({{ return: 'Array' }});
                let selectedNode = null;
                network.on('click', function(params) {{
                    const nodeId = params.nodes[0];
                    if (nodeId && nodeId === selectedNode) {{
                        let updates = allNodes.map(n => ({{ id: n.id, hidden: false }}));
                        network.body.data.nodes.update(updates);
                        let edgeUpdates = allEdges.map(e => ({{ id: e.id, hidden: true }}));
                        network.body.data.edges.update(edgeUpdates);
                        selectedNode = null;
                    }} else if (nodeId) {{
                        selectedNode = nodeId;
                        const neighbors = adjacencyList[nodeId] || [];
                        let nodeUpdates = allNodes.map(n => ({{ id: n.id, hidden: true }}));
                        network.body.data.nodes.update(nodeUpdates);
                        let nodesToShow = [nodeId, ...neighbors];
                        let showUpdates = nodesToShow.map(n_id => ({{ id: n_id, hidden: false }}));
                        network.body.data.nodes.update(showUpdates);
                        let edgeUpdates = allEdges.map(e => ({{ id: e.id, hidden: !(e.from === nodeId && nodesToShow.includes(e.to)) }}));
                        network.body.data.edges.update(edgeUpdates);
                    }}
                }});
            }}
        }});
    </script>
    """
    
    final_html = html_content.replace('</body>', f'{js_script}</body>')
    return final_html

# --- 5. LÓGICA PRINCIPAL DE LA APLICACIÓN ---
uploaded_file = st.file_uploader("📂 Sube tu archivo CSV aquí", type="csv")

if uploaded_file is not None:
    try:
        df_links = process_data(uploaded_file)
        if df_links.empty:
            st.warning("No se encontraron enlaces válidos en el archivo.")
        else:
            st.success(f"¡Archivo procesado con éxito! Se encontraron **{len(df_links)}** enlaces internos.")
            st.header('🗺️ Mapa de Red Interactivo')
            interactive_html = generate_interactive_network(df_links)
            components.html(interactive_html, height=850, scrolling=True)
    except Exception as e:
        st.error(f"❌ Ocurrió un error al procesar el archivo: {e}")
