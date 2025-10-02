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
st.markdown("""
Sube tu archivo CSV. **En el mapa de red:**
1.  **Haz clic en un círculo** para aislarlo y ver solo las páginas a las que enlaza.
2.  **Vuelve a hacer clic** en el mismo círculo para regresar a la vista general.
""")

# --- 3. FUNCIÓN DE PROCESAMIENTO (Sin cambios) ---
def process_data(uploaded_file):
    df = pd.read_csv(uploaded_file, header=0)
    links_list = []
    source_col_name = df.columns[0]
    for _, row in df.iterrows():
        source_url = row[source_col_name]
        for i in range(1, len(df.columns), 2):
            if i + 1 < len(df.columns):
                target_url = row.iloc[i]
                anchor_text = row.iloc[i+1]
                if pd.notna(target_url) and str(target_url).strip() != '':
                    links_list.append({
                        'Source': str(source_url).strip(),
                        'Target': str(target_url).strip(),
                        'Anchor_Text': str(anchor_text).strip()
                    })
    return pd.DataFrame(links_list)

# --- 4. NUEVA FUNCIÓN PARA GENERAR EL MAPA DE RED INTERACTIVO ---
def generate_interactive_network(df_links):
    # Crear el grafo a partir de los datos
    G = nx.from_pandas_edgelist(df_links, 'Source', 'Target', create_using=nx.DiGraph())
    
    # Crear la red con Pyvis
    net = Network(height='800px', width='100%', bgcolor='#222222', font_color='white', notebook=True, directed=True)
    net.from_nx(G)

    # Personalizar tamaño y título de los nodos
    in_degree = dict(G.in_degree)
    for node in net.nodes:
        degree = in_degree.get(node['id'], 0)
        node['value'] = 10 + degree * 3
        node['title'] = f"{node['id']}<br>Enlaces entrantes: {degree}"

    # Ocultar las aristas (enlaces) en la carga inicial
    for edge in net.edges:
        edge['hidden'] = True

    # Generar el HTML base
    html_content = net.generate_html()

    # Preparar los datos para el script de JavaScript
    # Creamos un "mapa" de qué nodos enlaza cada nodo
    adjacency_list = json.dumps({source: list(G.successors(source)) for source in G.nodes()})

    # Inyectar el script de JavaScript para la interactividad
    js_script = f"""
    <script type="text/javascript">
        // Espera a que la red esté lista
        document.addEventListener('DOMContentLoaded', function() {{
            // Mapa de adyacencia (quién enlaza a quién)
            const adjacencyList = {adjacency_list};
            let allNodes = network.body.data.nodes.get({{ return: 'Array' }});
            let allEdges = network.body.data.edges.get({{ return: 'Array' }});
            let selectedNode = null;

            network.on('click', function(params) {{
                const nodeId = params.nodes[0];

                if (nodeId && nodeId === selectedNode) {{
                    // --- SEGUNDO CLIC: Volver a la vista general ---
                    // Muestra todos los nodos y oculta todas las aristas
                    let updates = allNodes.map(n => ({{ id: n.id, hidden: false }}));
                    network.body.data.nodes.update(updates);
                    let edgeUpdates = allEdges.map(e => ({{ id: e.id, hidden: true }}));
                    network.body.data.edges.update(edgeUpdates);
                    selectedNode = null;
                }} else if (nodeId) {{
                    // --- PRIMER CLIC: Aislar el nodo ---
                    selectedNode = nodeId;
                    const neighbors = adjacencyList[nodeId] || [];
                    
                    // Oculta todos los nodos
                    let nodeUpdates = allNodes.map(n => ({{ id: n.id, hidden: true }}));
                    network.body.data.nodes.update(nodeUpdates);
                    
                    // Muestra solo el nodo seleccionado y sus vecinos
                    let nodesToShow = [nodeId, ...neighbors];
                    let showUpdates = nodesToShow.map(n_id => ({{ id: n_id, hidden: false }}));
                    network.body.data.nodes.update(showUpdates);

                    // Muestra solo las aristas que salen del nodo seleccionado
                    let edgeUpdates = allEdges.map(e => ({{ 
                        id: e.id, 
                        hidden: !(e.from === nodeId && nodesToShow.includes(e.to)) 
                    }}));
                    network.body.data.edges.update(edgeUpdates);
                }}
            }});
        }});
    </script>
    """
    
    # Insertar el script justo antes de cerrar el body del HTML
    final_html = html_content.replace('</body>', f'{js_script}</body>')
    return final_html

# --- 5. CARGADOR DE ARCHIVOS Y LÓGICA PRINCIPAL ---
uploaded_file = st.file_uploader("📂 Sube tu archivo CSV aquí", type="csv")

if uploaded_file is not None:
    try:
        df_links = process_data(uploaded_file)

        if df_links.empty:
            st.warning("No se encontraron enlaces válidos en el archivo.")
        else:
            st.success(f"¡Archivo procesado con éxito! Se encontraron **{len(df_links)}** enlaces internos.")
            
            # --- PESTAÑA DEL MAPA DE RED ---
            st.header('🗺️ Mapa de Red Interactivo')
            
            # Genera y muestra el mapa interactivo
            interactive_html = generate_interactive_network(df_links)
            components.html(interactive_html, height=850, scrolling=True)

    except Exception as e:
        st.error(f"❌ Ocurrió un error al procesar el archivo: {e}")
