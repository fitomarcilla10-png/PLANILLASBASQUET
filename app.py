import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Configuración estética
st.set_page_config(page_title="Torneo Basket Truncado", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    h1, h2, h3 { color: #f39c12; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏀 Gestión de Torneo Pico Truncado")

# URL de tu Google Sheet (la que me pasaste)
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1k4N4fh99qmAcueIlx4FcreL0MNrwHrCxDxfzkWeSUEM/edit?usp=sharing"

# Establecer conexión
conn = st.connection("gsheets", type=GSheetsConnection)

# --- SIDEBAR DE SELECCIÓN ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/889/889500.png", width=100)
st.sidebar.header("Filtros del Torneo")
rama = st.sidebar.selectbox("Rama", ["Masculino", "Femenino"])
categoria = st.sidebar.selectbox("Categoría", ["Infantil", "Cadete", "Juvenil", "Mayores"])

tab1, tab2 = st.tabs(["📊 Tabla de Posiciones", "📝 Carga de Planilla"])

with tab2:
    st.subheader(f"Nueva Entrada: {rama} - {categoria}")
    with st.form("registro_partido"):
        col1, col2 = st.columns(2)
        eq_local = col1.text_input("Equipo Local")
        eq_visitante = col2.text_input("Equipo Visitante")
        pts_l = col1.number_input("Puntos Local", min_value=0, step=1)
        pts_v = col2.number_input("Puntos Visitante", min_value=0, step=1)
        
        btn_guardar = st.form_submit_button("Guardar Resultado")
        
        if btn_guardar:
            if eq_local and eq_visitante:
                try:
                    # Leer datos existentes
                    existing_data = conn.read(spreadsheet=spreadsheet_url)
                    
                    # Crear nueva fila (asegúrate de que los nombres coincidan con tu Excel)
                    new_row = pd.DataFrame([{
                        "rama": rama,
                        "categoria": categoria,
                        "local": eq_local,
                        "visitante": eq_visitante,
                        "pts_l": pts_l,
                        "pts_v": pts_v
                    }])
                    
                    # Combinar y subir
                    updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                    conn.update(spreadsheet=spreadsheet_url, data=updated_df)
                    st.success("✅ ¡Partido guardado y sincronizado con Google Sheets!")
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
            else:
                st.warning("Por favor, completa los nombres de los equipos.")

with tab1:
    st.subheader(f"Estadísticas: {rama} - {categoria}")
    try:
        df = conn.read(spreadsheet=spreadsheet_url)
        if not df.empty:
            # Filtrar por los selectores del sidebar
            mask = (df['rama'] == rama) & (df['categoria'] == categoria)
            df_filtro = df[mask]
            
            if not df_filtro.empty:
                st.table(df_filtro[['local', 'pts_l', 'pts_v', 'visitante']])
            else:
                st.info("Aún no hay partidos registrados para esta categoría.")
        else:
            st.info("La base de datos está vacía.")
    except Exception as e:
        st.error("Asegúrate de que la primera fila de tu Excel tenga estos encabezados: rama, categoria, local, visitante, pts_l, pts_v")
