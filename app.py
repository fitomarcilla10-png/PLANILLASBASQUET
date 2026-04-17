import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Configuración visual deportiva
st.set_page_config(page_title="Gestión Basket Truncado", layout="wide")

st.title("🏀 Sistema de Gestión de Torneos")
st.markdown("### Ramas Masculina y Femenina | Todas las Categorías")

# 1. Conexión con Google Sheets
url = "TU_URL_DE_GOOGLE_SHEETS_AQUÍ" # <--- PEGA TU URL AQUÍ
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Sidebar para filtros
st.sidebar.header("Configuración del Torneo")
rama = st.sidebar.selectbox("Rama", ["Masculino", "Femenino"])
categoria = st.sidebar.selectbox("Categoría", ["Infantil", "Cadete", "Juvenil", "Mayores"])

tab1, tab2 = st.tabs(["📊 Tabla de Posiciones", "📝 Carga de Resultados"])

with tab2:
    st.subheader(f"Carga de Planilla: {rama} - {categoria}")
    with st.form("planilla_form"):
        col1, col2 = st.columns(2)
        local = col1.text_input("Equipo Local")
        visitante = col2.text_input("Equipo Visitante")
        p_l = col1.number_input("Puntos Local", min_value=0, step=1)
        p_v = col2.number_input("Puntos Visitante", min_value=0, step=1)
        
        if st.form_submit_button("Guardar en Google Sheets"):
            # Leer datos actuales
            data = conn.read(spreadsheet=url)
            # Crear nueva fila
            nueva_fila = pd.DataFrame([{
                "rama": rama, "categoria": categoria,
                "local": local, "visitante": visitante,
                "pts_l": p_l, "pts_v": p_v
            }])
            # Concatenar y actualizar
            updated_df = pd.concat([data, nueva_fila], ignore_index=True)
            conn.update(spreadsheet=url, data=updated_df)
            st.success("¡Resultado sincronizado exitosamente!")

with tab1:
    st.subheader(f"Resultados registrados en {categoria} ({rama})")
    df_full = conn.read(spreadsheet=url)
    # Filtrar por la selección actual
    df_filtrado = df_full[(df_full['rama'] == rama) & (df_full['categoria'] == categoria)]
    
    if not df_filtrado.empty:
        st.dataframe(df_filtrado, use_container_width=True)
    else:
        st.info("No hay partidos registrados para esta selección.")
