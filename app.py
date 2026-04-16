import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import os

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Gestor Torneos Básquet", layout="wide", page_icon="🏀")

DB_NAME = "basquet_completo.db"

# --- FUNCIONES DE BASE DE DATOS ---
def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Activar claves foráneas
    c.execute("PRAGMA foreign_keys = ON;")

    # 1. Tabla de Torneos/Categorías
    c.execute('''CREATE TABLE IF NOT EXISTS torneos 
                 (id INTEGER PRIMARY KEY, nombre TEXT UNIQUE NOT NULL)''')
    
    # 2. Tabla de Equipos
    c.execute('''CREATE TABLE IF NOT EXISTS equipos 
                 (id INTEGER PRIMARY KEY, nombre TEXT UNIQUE NOT NULL)''')

    # 3. Tabla de Jugadores
    c.execute('''CREATE TABLE IF NOT EXISTS jugadores 
                 (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, 
                  equipo_id INTEGER,
                  FOREIGN KEY(equipo_id) REFERENCES equipos(id))''')

    # 4. Tabla de Partidos
    c.execute('''CREATE TABLE IF NOT EXISTS partidos 
                 (id INTEGER PRIMARY KEY, 
                  torneo_id INTEGER,
                  fecha DATE,
                  equipo_local_id INTEGER,
                  equipo_visitante_id INTEGER,
                  puntos_local INTEGER,
                  puntos_visitante INTEGER,
                  FOREIGN KEY(torneo_id) REFERENCES torneos(id),
                  FOREIGN KEY(equipo_local_id) REFERENCES equipos(id),
                  FOREIGN KEY(equipo_visitante_id) REFERENCES equipos(id))''')

    # 5. Tabla de Estadísticas Individuales por Partido
    c.execute('''CREATE TABLE IF NOT EXISTS estadisticas_jugador 
                 (id INTEGER PRIMARY KEY,
                  partido_id INTEGER,
                  jugador_id INTEGER,
                  puntos INTEGER DEFAULT 0,
                  rebotes INTEGER DEFAULT 0,
                  asistencias INTEGER DEFAULT 0,
                  faltas INTEGER DEFAULT 0,
                  FOREIGN KEY(partido_id) REFERENCES partidos(id),
                  FOREIGN KEY(jugador_id) REFERENCES jugadores(id))''')
    
    # Insertar categorías por defecto si no existen
    c.execute("SELECT count(*) FROM torneos")
    if c.fetchone()[0] == 0:
        categorias = [("Primera División"), ("U19 Masculino"), ("U17 Femenino"), ("Mini Básquet")]
        c.executemany("INSERT INTO torneos (nombre) VALUES (?)", categorias)

    conn.commit()
    conn.close()

# Funciones Auxiliares de Datos
def run_query(query, params=()):
    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)

def run_action(query, params=()):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()

# --- INICIALIZAR ---
init_db()

# --- SIDEBAR Y LOGO ---
with st.sidebar:
    # Intentar cargar el logo
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.error("Archivo 'logo.png' no encontrado. Por favor súbelo.")
    
    st.title("Administración")
    menu = ["🏆 Panel General", "📝 Cargar Datos", "🏀 Estadísticas Jugadores"]
    choice = st.radio("Ir a:", menu)
    st.markdown("---")
    st.caption("Club Escuela de Básquet - Gestión Interna")

# --- LÓGICA DE LA APP ---

# ==========================================
# 🏆 PANEL GENERAL (VISUALIZACIÓN)
# ==========================================
if choice == "🏆 Panel General":
    st.title("Panel General del Torneo")
    
    # 1. Selector de Categoría (Torneo)
    df_torneos = run_query("SELECT * FROM torneos")
    if not df_torneos.empty:
        cat_nombres = df_torneos['nombre'].tolist()
        t_seleccionado = st.selectbox("Selecciona la Categoría a visualizar:", cat_nombres)
        t_id = df_torneos[df_torneos['nombre'] == t_seleccionado]['id'].values[0]
        
        st.markdown(f"### Clasificación: {t_seleccionado}")

        # 2. Lógica de Tabla de Posiciones (Simplificada para el ejemplo)
        # Obtenemos partidos de este torneo
        query_partidos = """
            SELECT p.*, el.nombre as local, ev.nombre as visitante
            FROM partidos p
            JOIN equipos el ON p.equipo_local_id = el.id
            JOIN equipos ev ON p.equipo_visitante_id = ev.id
            WHERE p.torneo_id = ?
        """
        df_p = run_query(query_partidos, (int(t_id),))

        if not df_p.empty:
            # Calcular Stats de Equipo
            equipos_ids = pd.concat([df_p['equipo_local_id'], df_p['equipo_visitante_id']]).unique()
            df_equipos_all = run_query("SELECT * FROM equipos")
            
            stats_list = []
            for eq_id in equipos_ids:
                eq_nombre = df_equipos_all[df_equipos_all['id'] == eq_id]['nombre'].values[0]
                
                # Partidos como local y visitante
                p_local = df_p[df_p['equipo_local_id'] == eq_id]
                p_visit = df_p[df_p['equipo_visitante_id'] == eq_id]
                
                pj = len(p_local) + len(p_visit)
                
                # Victorias
                ganados = len(p_local[p_local['puntos_local'] > p_local['puntos_visitante']]) + \
                          len(p_visit[p_visit['puntos_visitante'] > p_visit['puntos_local']])
                
                perdidos = pj - ganados
                
                # Puntos
                favor = p_local['puntos_local'].sum() + p_visit['puntos_visitante'].sum()
                contra = p_local['puntos_visitante'].sum() + p_visit['puntos_local'].sum()
                
                # Puntos Campeonato (2 por ganar, 1 por perder)
                pts_camp = (ganados * 2) + (perdidos * 1)
                
                stats_list.append({
                    "Equipo": eq_nombre,
                    "PJ": pj,
                    "PG": ganados,
                    "PP": perdidos,
                    "PF": favor,
                    "PC": contra,
                    "Dif": favor - contra,
                    "PTS": pts_camp
                })
            
            df_tabla = pd.DataFrame(stats_list).sort_values(by=["PTS", "Dif"], ascending=[False, False])
            
            # Estilar tabla
            st.dataframe(df_tabla.style.highlight_max(axis=0, subset=['PTS'], color='#2e7d32'), use_container_width=True)

            # Últimos Resultados
            st.markdown("#### Últimos Resultados Registrados")
            df_p_show = df_p[['fecha', 'local', 'puntos_local', 'puntos_visitante', 'visitante']].sort_values(by='fecha', ascending=False)
            st.table(df_p_show.head(5))

        else:
            st.info("No hay partidos registrados en esta categoría aún.")
    else:
        st.warning("No hay categorías definidas en la base de datos.")

# ==========================================
# 📝 CARGAR DATOS (SIMPLE)
# ==========================================
elif choice == "📝 Cargar Datos":
    st.title("Centro de Carga de Datos")
    
    tipo_carga = st.tabs(["🏗️ Crear Equipos/Jugadores", "🏀 Registrar Partido y Stats"])
    
    # --- TABA 1: ESTRUCTURA ---
    with tipo_carga[0]:
        col_eq, col_jug = st.columns(2)
        
        with col_eq:
            st.subheader("Añadir Nuevo Equipo")
            nuevo_eq = st.text_input("Nombre del Equipo", key="in_eq")
            if st.button("Guardar Equipo"):
                if nuevo_eq:
                    try:
                        run_action("INSERT INTO equipos (nombre) VALUES (?)", (nuevo_eq,))
                        st.success(f"Equipo '{nuevo_eq}' creado.")
                        st.rerun()
                    except:
                        st.error("El equipo ya existe o hubo un error.")
        
        with col_jug:
            st.subheader("Añadir Jugador a Equipo")
            df_eq_existentes = run_query("SELECT * FROM equipos")
            if not df_eq_existentes.empty:
                eq_dest = st.selectbox("Seleccionar Equipo", df_eq_existentes['nombre'].tolist())
                eq_dest_id = df_eq_existentes[df_eq_existentes['nombre'] == eq_dest]['id'].values[0]
                nuevo_jug = st.text_input("Nombre del Jugador")
                
                if st.button("Guardar Jugador"):
                    if nuevo_jug:
                        run_action("INSERT INTO jugadores (nombre, equipo_id) VALUES (?, ?)", (nuevo_jug, int(eq_dest_id)))
                        st.success(f"Jugador '{nuevo_jug}' añadido a {eq_dest}.")
            else:
                st.info("Primero crea un equipo.")

    # --- TABA 2: PARTIDO (LA PARTE COMPLEJA PERO SIMPLE VISUALMENTE) ---
    with tipo_carga[1]:
        st.subheader("Registrar Resultado de Partido")
        
        # 1. Selección Básica
        df_t = run_query("SELECT * FROM torneos")
        df_e = run_query("SELECT * FROM equipos")
        
        if len(df_e) < 2:
            st.warning("Necesitas al menos dos equipos creados.")
        else:
            col_p1, col_p2, col_p3 = st.columns([2,1,2])
            
            with col_p1:
                cat_partido = st.selectbox("Categoría/Torneo", df_t['nombre'].tolist(), key="p_cat")
                eq_loc = st.selectbox("Equipo Local", df_e['nombre'].tolist(), key="p_loc")
            
            with col_p2:
                fecha_p = st.date_input("Fecha", date.today())
                st.markdown("<h2 style='text-align: center;'>VS</h2>", unsafe_allow_html=True)
            
            with col_p3:
                # Evitar que sea el mismo equipo
                opciones_vis = df_e[df_e['nombre'] != eq_loc]['nombre'].tolist()
                eq_vis = st.selectbox("Equipo Visitante", opciones_vis, key="p_vis")

            st.markdown("---")
            col_sc1, col_sc2 = st.columns(2)
            with col_sc1:
                sc_loc = st.number_input(f"Puntos Finales {eq_loc}", min_value=0, step=1)
            with col_sc2:
                sc_vis = st.number_input(f"Puntos Finales {eq_vis}", min_value=0, step=1)

            # 2. CARGA DE ESTADÍSTICAS INDIVIDUALES (Dianmico)
            st.markdown("#### 📊 Estadísticas Individuales de Jugadores")
            st.caption("Introduce los datos de los jugadores que participaron.")
            
            id_t = df_t[df_t['nombre'] == cat_partido]['id'].values[0]
            id_loc = df_e[df_e['nombre'] == eq_loc]['id'].values[0]
            id_vis = df_e[df_e['nombre'] == eq_vis]['id'].values[0]
            
            # Obtener Jugadores
            jug_loc = run_query("SELECT id, nombre FROM jugadores WHERE equipo_id = ?", (int(id_loc),))
            jug_vis = run_query("SELECT id, nombre FROM jugadores WHERE equipo_id = ?", (int(id_vis),))
            
            # Contenedores para guardar lo que se escriba en los inputs dinámicos
            stats_a_guardar = []

            # Función para generar inputs de equipo
            def generar_inputs_jugadores(df_jugadores, nombre_equipo):
                st.markdown(f"**Jugadores de {nombre_equipo}**")
                if df_jugadores.empty:
                    st.caption("No hay jugadores registrados en este equipo.")
                    return
                
                # Cabecera de la "tabla" de inputs
                c0, c1, c2, c3, c4 = st.columns([3, 1, 1, 1, 1])
                c0.caption("Nombre")
                c1.caption("Pts")
                c2.caption("Reb")
                c3.caption("Asis")
                c4.caption("Faltas")

                for _, jug in df_jugadores.iterrows():
                    col0, col1, col2, col3, col4 = st.columns([3, 1, 1, 1, 1])
                    col0.markdown(f"**{jug['nombre']}**")
                    
                    # Keys únicas para streamlit
                    k = f"j_{jug['id']}_p{id_t}" 
                    
                    pts = col1.number_input("", min_value=0, step=1, key=f"{k}_pts", label_visibility="collapsed")
                    reb = col2.number_input("", min_value=0, step=1, key=f"{k}_reb", label_visibility="collapsed")
                    asi = col3.number_input("", min_value=0, step=1, key=f"{k}_asi", label_visibility="collapsed")
                    fal = col4.number_input("", min_value=0, step=1, key=f"{k}_fal", label_visibility="collapsed")
                    
                    # Solo guardar si jugo (hizo algo) para no llenar la DB de ceros innecesarios
                    if pts > 0 or reb > 0 or asi > 0 or fal > 0:
                        stats_a_guardar.append((jug['id'], pts, reb, asi, fal))

            col_input_loc, col_input_vis = st.columns(2)
            with col_input_loc:
                generar_inputs_jugadores(jug_loc, eq_loc)
            with col_input_vis:
                generar_inputs_jugadores(jug_vis, eq_vis)

            st.markdown("---")
            # BOTÓN FINAL DE GUARDADO TOTAL
            if st.button("💾 GUARDAR PARTIDO COMPLETO Y ESTADÍSTICAS", type="primary"):
                conn = get_connection()
                c = conn.cursor()
                try:
                    # 1. Guardar Partido
                    c.execute("""INSERT INTO partidos 
                                (torneo_id, fecha, equipo_local_id, equipo_visitante_id, puntos_local, puntos_visitante) 
                                VALUES (?,?,?,?,?,?)""",
                             (int(id_t), fecha_p, int(id_loc), int(id_vis), sc_loc, sc_vis))
                    
                    partido_id = c.lastrowid # Obtener ID del partido recién creado
                    
                    # 2. Guardar Stats de jugadores
                    if stats_a_guardar:
                        # Preparamos los datos añadiendo el partido_id
                        datos_finales_stats = []
                        for s in stats_a_guardar:
                            datos_finales_stats.append((partido_id, s[0], s[1], s[2], s[3], s[4]))
                        
                        c.executemany("""INSERT INTO estadisticas_jugador 
                                       (partido_id, jugador_id, puntos, rebotes, asistencias, faltas) 
                                       VALUES (?,?,?,?,?,?)""", datos_finales_stats)
                    
                    conn.commit()
                    st.success(f"Partido y {len(stats_a_guardar)} registros de estadísticas individuales guardados correctamente.")
                    # Limpiar inputs (opcional, requiere manejo de state complejo, rerun suele servir)
                    # st.rerun() 
                except Exception as e:
                    conn.rollback()
                    st.error(f"Error al guardar: {e}")
                finally:
                    conn.close()

# ==========================================
# 🏀 ESTADÍSTICAS JUGADORES (RESUMEN COMPLETO)
# ==========================================
elif choice == "🏀 Estadísticas Jugadores":
    st.title("Líderes y Resumen Completo de Jugadores")
    
    # Selector de Categoría para filtrar jugadores
    df_torneos = run_query("SELECT * FROM torneos")
    cat_nombres = ["Todos"] + df_torneos['nombre'].tolist()
    t_seleccionado = st.selectbox("Filtrar por Categoría:", cat_nombres)
    
    # Query Compleja para promedios y totales
    query_base = """
        SELECT 
            j.nombre as Jugador,
            e.nombre as Equipo,
            t.nombre as Categoria,
            COUNT(ej.partido_id) as PJ,
            SUM(ej.puntos) as Pts_Total,
            ROUND(AVG(ej.puntos), 1) as Ppp,
            SUM(ej.rebotes) as Reb_Total,
            ROUND(AVG(ej.rebotes), 1) as Rpp,
            SUM(ej.asistencias) as Ast_Total,
            ROUND(AVG(ej.asistencias), 1) as App,
            SUM(ej.faltas) as Fal_Total,
            ROUND(AVG(ej.faltas), 1) as Fpp
        FROM jugadores j
        JOIN equipos e ON j.equipo_id = e.id
        JOIN estadisticas_jugador ej ON j.id = ej.jugador_id
        JOIN partidos p ON ej.partido_id = p.id
        JOIN torneos t ON p.torneo_id = t.id
    """
    
    if t_seleccionado == "Todos":
        query_final = query_base + " GROUP BY j.id ORDER BY Pts_Total DESC"
        df_stats_jug = run_query(query_final)
    else:
        query_final = query_base + " WHERE t.nombre = ? GROUP BY j.id ORDER BY Pts_Total DESC"
        df_stats_jug = run_query(query_final, (t_seleccionado,))

    if not df_stats_jug.empty:
        # Renombrar columnas para que queden bonitas
        cols_renombrar = {
            'PJ': 'PJ', 'Pts_Total': 'PTS Totales', 'Ppp': 'PPP',
            'Reb_Total': 'REB Totales', 'Rpp': 'RPP',
            'Ast_Total': 'AST Totales', 'App': 'APP',
            'Fal_Total': 'Faltas Totales', 'Fpp': 'FPP'
        }
        df_mostrar = df_stats_jug.rename(columns=cols_renombrar)
        
        # Visualización de Líderes destacada
        st.subheader(f"Top Anotadores - {t_seleccionado}")
        col_l1, col_l2, col_l3 = st.columns(3)
        
        top_anotador = df_mostrar.iloc[0]
        col_l1.metric("Máximo Anotador (Total)", top_anotador['Jugador'], f"{top_anotador['PTS Totales']} pts")
        
        # Ordenar por promedio para el segundo metric
        top_ppp = df_mostrar.sort_values(by='PPP', ascending=False).iloc[0]
        col_l2.metric("Mejor Promedio (PPP)", top_ppp['Jugador'], f"{top_ppp['PPP']}")

        top_asist = df_mostrar.sort_values(by='APP', ascending=False).iloc[0]
        col_l3.metric("Líder Asistencias (APP)", top_asist['Jugador'], f"{top_asist['APP']}")

        st.markdown("---")
        st.subheader("Tabla Completa de Estadísticas (Promedios y Totales)")
        st.caption("PPP: Puntos por partido | RPP: Rebotes por partido | APP: Asistencias por partido | FPP: Faltas por partido")
        
        # Mostramos la tabla completa interactiva
        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
        
    else:
        st.info("No hay datos estadísticos individuales registrados aún.")
