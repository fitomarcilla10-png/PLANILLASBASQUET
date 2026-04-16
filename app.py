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
    c.execute("PRAGMA foreign_keys = ON;")

    # 1. Tabla de Torneos/Categorías
    c.execute('''CREATE TABLE IF NOT EXISTS torneos 
                 (id INTEGER PRIMARY KEY, nombre TEXT UNIQUE NOT NULL)''')
    
    # 2. Tabla de Equipos
    c.execute('''CREATE TABLE IF NOT EXISTS equipos 
                 (id INTEGER PRIMARY KEY, nombre TEXT UNIQUE NOT NULL)''')

    # 3. Tabla de Jugadores
    c.execute('''CREATE TABLE IF NOT EXISTS jugadores 
                 (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, equipo_id INTEGER,
                  FOREIGN KEY(equipo_id) REFERENCES equipos(id))''')

    # 4. Tabla de Partidos
    c.execute('''CREATE TABLE IF NOT EXISTS partidos 
                 (id INTEGER PRIMARY KEY, torneo_id INTEGER, fecha DATE,
                  equipo_local_id INTEGER, equipo_visitante_id INTEGER,
                  puntos_local INTEGER, puntos_visitante INTEGER,
                  FOREIGN KEY(torneo_id) REFERENCES torneos(id),
                  FOREIGN KEY(equipo_local_id) REFERENCES equipos(id),
                  FOREIGN KEY(equipo_visitante_id) REFERENCES equipos(id))''')

    # 5. Tabla de Estadísticas Individuales
    c.execute('''CREATE TABLE IF NOT EXISTS estadisticas_jugador 
                 (id INTEGER PRIMARY KEY, partido_id INTEGER, jugador_id INTEGER,
                  puntos INTEGER DEFAULT 0, rebotes INTEGER DEFAULT 0,
                  asistencias INTEGER DEFAULT 0, faltas INTEGER DEFAULT 0,
                  FOREIGN KEY(partido_id) REFERENCES partidos(id),
                  FOREIGN KEY(jugador_id) REFERENCES jugadores(id))''')
    
    # --- ACTUALIZACIÓN DE CATEGORÍAS ---
    c.execute("SELECT count(*) FROM torneos")
    if c.fetchone()[0] == 0:
        categorias = [
            ("Masculino Infantil",), ("Masculino Cadete",), ("Masculino Juvenil",), ("Masculino Mayores",),
            ("Femenino Infantil",), ("Femenino Cadete",), ("Femenino Juvenil",), ("Femenino Mayores",)
        ]
        c.executemany("INSERT INTO torneos (nombre) VALUES (?)", categorias)

    conn.commit()
    conn.close()

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
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.info("Sube 'logo.png' para verlo aquí.")
    
    st.title("🏀 Administración")
    menu = ["🏆 Panel General", "📝 Cargar Datos", "📊 Estadísticas Jugadores"]
    choice = st.radio("Ir a:", menu)
    st.markdown("---")
    st.caption("Pico Truncado - Gestión de Básquet")

# ==========================================
# 🏆 PANEL GENERAL
# ==========================================
if choice == "🏆 Panel General":
    st.title("Resultados y Posiciones")
    
    df_torneos = run_query("SELECT * FROM torneos")
    cat_nombres = df_torneos['nombre'].tolist()
    t_seleccionado = st.selectbox("Selecciona Categoría:", cat_nombres)
    t_id = df_torneos[df_torneos['nombre'] == t_seleccionado]['id'].values[0]
    
    st.header(f"Torneo: {t_seleccionado}")

    query_partidos = """
        SELECT p.*, el.nombre as local, ev.nombre as visitante
        FROM partidos p
        JOIN equipos el ON p.equipo_local_id = el.id
        JOIN equipos ev ON p.equipo_visitante_id = ev.id
        WHERE p.torneo_id = ?
    """
    df_p = run_query(query_partidos, (int(t_id),))

    if not df_p.empty:
        # Lógica de Tabla de Posiciones
        equipos_ids = pd.concat([df_p['equipo_local_id'], df_p['equipo_visitante_id']]).unique()
        df_equipos_all = run_query("SELECT * FROM equipos")
        
        stats_list = []
        for eq_id in equipos_ids:
            eq_nombre = df_equipos_all[df_equipos_all['id'] == eq_id]['nombre'].values[0]
            p_local = df_p[df_p['equipo_local_id'] == eq_id]
            p_visit = df_p[df_p['equipo_visitante_id'] == eq_id]
            pj = len(p_local) + len(p_visit)
            ganados = len(p_local[p_local['puntos_local'] > p_local['puntos_visitante']]) + \
                      len(p_visit[p_visit['puntos_visitante'] > p_visit['puntos_local']])
            perdidos = pj - ganados
            favor = p_local['puntos_local'].sum() + p_visit['puntos_visitante'].sum()
            contra = p_local['puntos_visitante'].sum() + p_visit['puntos_local'].sum()
            stats_list.append({
                "Equipo": eq_nombre, "PJ": pj, "PG": ganados, "PP": perdidos, 
                "PF": favor, "PC": contra, "Dif": favor - contra, "PTS": (ganados * 2 + perdidos)
            })
        
        df_tabla = pd.DataFrame(stats_list).sort_values(by=["PTS", "Dif"], ascending=[False, False])
        st.subheader("Tabla de Clasificación")
        st.dataframe(df_tabla, use_container_width=True, hide_index=True)

        st.subheader("Últimos Encuentros")
        st.table(df_p[['fecha', 'local', 'puntos_local', 'puntos_visitante', 'visitante']].sort_values(by='fecha', ascending=False))
    else:
        st.info("No hay datos para esta categoría.")

# ==========================================
# 📝 CARGAR DATOS
# ==========================================
elif choice == "📝 Cargar Datos":
    st.title("Carga de Información")
    tab1, tab2 = st.tabs(["🏗️ Estructura (Equipos/Jugadores)", "🏀 Resultados de Partidos"])
    
    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Nuevo Equipo")
            nuevo_eq = st.text_input("Nombre del Equipo")
            if st.button("Guardar Equipo"):
                if nuevo_eq:
                    run_action("INSERT INTO equipos (nombre) VALUES (?)", (nuevo_eq,))
                    st.success("Equipo creado.")
                    st.rerun()
        with c2:
            st.subheader("Nuevo Jugador")
            df_e = run_query("SELECT * FROM equipos")
            if not df_e.empty:
                eq_sel = st.selectbox("Equipo", df_e['nombre'].tolist())
                eq_id = df_e[df_e['nombre'] == eq_sel]['id'].values[0]
                nom_jug = st.text_input("Nombre del Jugador")
                if st.button("Guardar Jugador"):
                    run_action("INSERT INTO jugadores (nombre, equipo_id) VALUES (?, ?)", (nom_jug, int(eq_id)))
                    st.success(f"{nom_jug} añadido a {eq_sel}")
            else:
                st.warning("Crea un equipo primero.")

    with tab2:
        st.subheader("Planilla de Partido")
        df_t = run_query("SELECT * FROM torneos")
        df_e = run_query("SELECT * FROM equipos")
        
        if len(df_e) >= 2:
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                cat_p = st.selectbox("Categoría", df_t['nombre'].tolist())
                e_loc = st.selectbox("Local", df_e['nombre'].tolist())
            with col_b:
                f_p = st.date_input("Fecha", date.today())
                p_l = st.number_input("Pts Local", min_value=0, step=1)
            with col_c:
                e_vis = st.selectbox("Visitante", df_e[df_e['nombre'] != e_loc]['nombre'].tolist())
                p_v = st.number_input("Pts Visitante", min_value=0, step=1)
            
            st.markdown("---")
            st.write("📊 **Estadísticas Individuales**")
            
            id_t = df_t[df_t['nombre'] == cat_p]['id'].values[0]
            id_l = df_e[df_e['nombre'] == e_loc]['id'].values[0]
            id_v = df_e[df_e['nombre'] == e_vis]['id'].values[0]
            
            j_l = run_query("SELECT id, nombre FROM jugadores WHERE equipo_id = ?", (int(id_l),))
            j_v = run_query("SELECT id, nombre FROM jugadores WHERE equipo_id = ?", (int(id_v),))
            
            stats_data = []
            
            def render_inputs(df, titulo):
                st.write(f"**{titulo}**")
                if df.empty: st.caption("Sin jugadores")
                else:
                    for _, r in df.iterrows():
                        c_nom, c_p, c_r, c_a, c_f = st.columns([3,1,1,1,1])
                        c_nom.write(r['nombre'])
                        pts = c_p.number_input("P", 0, 200, 0, key=f"p_{r['id']}_{id_t}")
                        reb = c_r.number_input("R", 0, 100, 0, key=f"r_{r['id']}_{id_t}")
                        ast = c_a.number_input("A", 0, 100, 0, key=f"a_{r['id']}_{id_t}")
                        fal = c_f.number_input("F", 0, 5, 0, key=f"f_{r['id']}_{id_t}")
                        if any([pts, reb, ast, fal]):
                            stats_data.append((r['id'], pts, reb, ast, fal))

            c_inp_l, c_inp_v = st.columns(2)
            with c_inp_l: render_inputs(j_l, e_loc)
            with c_inp_v: render_inputs(j_v, e_vis)
            
            if st.button("💾 Guardar Todo", type="primary"):
                conn = get_connection()
                c = conn.cursor()
                try:
                    c.execute("INSERT INTO partidos (torneo_id, fecha, equipo_local_id, equipo_visitante_id, puntos_local, puntos_visitante) VALUES (?,?,?,?,?,?)",
                             (int(id_t), f_p, int(id_l), int(id_v), p_l, p_v))
                    pid = c.lastrowid
                    if stats_data:
                        final_stats = [(pid, s[0], s[1], s[2], s[3], s[4]) for s in stats_data]
                        c.executemany("INSERT INTO estadisticas_jugador (partido_id, jugador_id, puntos, rebotes, asistencias, faltas) VALUES (?,?,?,?,?,?)", final_stats)
                    conn.commit()
                    st.success("¡Datos guardados!")
                except Exception as e:
                    st.error(f"Error: {e}")
                finally: conn.close()
        else:
            st.info("Crea al menos 2 equipos.")

# ==========================================
# 📊 ESTADÍSTICAS JUGADORES
# ==========================================
elif choice == "📊 Estadísticas Jugadores":
    st.title("Estadísticas Individuales")
    df_t = run_query("SELECT * FROM torneos")
    cat = st.selectbox("Categoría:", ["Todas"] + df_t['nombre'].tolist())
    
    query = """
        SELECT j.nombre as Jugador, e.nombre as Equipo, t.nombre as Categoria,
        COUNT(ej.id) as PJ, SUM(ej.puntos) as T_PTS, AVG(ej.puntos) as PPP,
        SUM(ej.rebotes) as T_REB, SUM(ej.asistencias) as T_AST, SUM(ej.faltas) as T_FAL
        FROM jugadores j
        JOIN equipos e ON j.equipo_id = e.id
        JOIN estadisticas_jugador ej ON j.id = ej.jugador_id
        JOIN partidos p ON ej.partido_id = p.id
        JOIN torneos t ON p.torneo_id = t.id
    """
    if cat == "Todas":
        df_res = run_query(query + " GROUP BY j.id ORDER BY T_PTS DESC")
    else:
        df_res = run_query(query + " WHERE t.nombre = ? GROUP BY j.id ORDER BY T_PTS DESC", (cat,))

    if not df_res.empty:
        st.dataframe(df_res.round(1), use_container_width=True, hide_index=True)
    else:
        st.info("No hay estadísticas registradas.")
