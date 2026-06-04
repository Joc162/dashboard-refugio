import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import tempfile
from supabase import create_client, Client
import datetime

# --- CONFIGURACIÓN DE SUPABASE ---
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="La Manada Feliz", layout="wide", initial_sidebar_state="collapsed")

# --- CSS ---
st.markdown("""
    <style>
    html, body, [class*="st-"] { font-size: 16px !important; }
    .stMarkdown p { font-size: 16px !important; }
    .stCaption { font-size: 14px !important; color: #a0a0a0; }

    input[type="number"]::-webkit-inner-spin-button, 
    input[type="number"]::-webkit-outer-spin-button { 
        -webkit-appearance: none; 
        margin: 0; 
    }
    input[type="number"] {
        -moz-appearance: textfield;
        text-align: center !important;
        font-size: 16px !important;
        padding: 0px !important;
    }

    div.element-container:has(.inventory-marker), 
    div.element-container:has(.dashboard-marker) {
        display: none !important;
    }

    @media (max-width: 768px) {
        #root div[data-testid="stHorizontalBlock"]:has(.inventory-marker):not(:has(div[data-testid="stHorizontalBlock"])),
        #root div[data-testid="stHorizontalBlock"]:has(.dashboard-marker):not(:has(div[data-testid="stHorizontalBlock"])) {
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            width: 100% !important;
            gap: 2px !important;
            padding: 0 !important;
            overflow: hidden !important; 
        }

        #root div[data-testid="stHorizontalBlock"]:has(.inventory-marker):not(:has(div[data-testid="stHorizontalBlock"])) *,
        #root div[data-testid="stHorizontalBlock"]:has(.dashboard-marker):not(:has(div[data-testid="stHorizontalBlock"])) * {
            min-width: 0 !important;
        }

        #root div[data-testid="stHorizontalBlock"]:has(.inventory-marker):not(:has(div[data-testid="stHorizontalBlock"])) > div[data-testid="column"],
        #root div[data-testid="stHorizontalBlock"]:has(.dashboard-marker):not(:has(div[data-testid="stHorizontalBlock"])) > div[data-testid="column"] {
            padding: 0 1px !important; 
        }

        #root div[data-testid="stHorizontalBlock"]:has(.inventory-marker):not(:has(div[data-testid="stHorizontalBlock"])) > div[data-testid="column"]:nth-child(1) { flex: 0 0 46% !important; width: 46% !important; }
        #root div[data-testid="stHorizontalBlock"]:has(.inventory-marker):not(:has(div[data-testid="stHorizontalBlock"])) > div[data-testid="column"]:nth-child(2) { flex: 0 0 12% !important; width: 12% !important; }
        #root div[data-testid="stHorizontalBlock"]:has(.inventory-marker):not(:has(div[data-testid="stHorizontalBlock"])) > div[data-testid="column"]:nth-child(3) { flex: 0 0 12% !important; width: 12% !important; }
        #root div[data-testid="stHorizontalBlock"]:has(.inventory-marker):not(:has(div[data-testid="stHorizontalBlock"])) > div[data-testid="column"]:nth-child(4) { flex: 0 0 18% !important; width: 18% !important; }
        #root div[data-testid="stHorizontalBlock"]:has(.inventory-marker):not(:has(div[data-testid="stHorizontalBlock"])) > div[data-testid="column"]:nth-child(5) { flex: 0 0 12% !important; width: 12% !important; }

        #root div[data-testid="stHorizontalBlock"]:has(.dashboard-marker):not(:has(div[data-testid="stHorizontalBlock"])) > div[data-testid="column"]:nth-child(1) { flex: 0 0 28% !important; width: 28% !important; }
        #root div[data-testid="stHorizontalBlock"]:has(.dashboard-marker):not(:has(div[data-testid="stHorizontalBlock"])) > div[data-testid="column"]:nth-child(2) { flex: 0 0 44% !important; width: 44% !important; }
        #root div[data-testid="stHorizontalBlock"]:has(.dashboard-marker):not(:has(div[data-testid="stHorizontalBlock"])) > div[data-testid="column"]:nth-child(3) { flex: 0 0 28% !important; width: 28% !important; }
    }

    div[data-testid="stNumberInputContainer"] {
        min-height: 2.2rem !important; 
        height: 2.2rem !important;
    }
    .stButton>button {
        min-height: 2.2rem !important;
        height: 2.2rem !important;
        padding: 0px 0px !important; 
        width: 100% !important;      
    }
    </style>
    """, unsafe_allow_html=True)

# 1. ACTUALIZACIÓN DE CATEGORÍAS
CATEGORIAS = ["Alimentación", "Salud", "Limpieza", "Materiales", "Tienda"]

# --- GESTIÓN DE ESTADO ---
if 'df_inventario' not in st.session_state:
    respuesta = supabase.table('inventario').select("*").execute()
    st.session_state.df_inventario = pd.DataFrame(respuesta.data)

if 'cambios_sin_guardar' not in st.session_state:
    st.session_state.cambios_sin_guardar = False


# --- FUNCIONES DE LÓGICA ---
def trigger_cambio():
    st.session_state.cambios_sin_guardar = True


def ajustar_cantidad(id_p, delta, input_key):
    idx = st.session_state.df_inventario[st.session_state.df_inventario['ID'] == id_p].index[0]
    nueva_cant = max(0, int(st.session_state.df_inventario.at[idx, 'Stock_Actual']) + int(delta))
    st.session_state.df_inventario.at[idx, 'Stock_Actual'] = nueva_cant
    st.session_state[input_key] = nueva_cant
    trigger_cambio()


def actualizar_desde_input(id_p, input_key):
    idx = st.session_state.df_inventario[st.session_state.df_inventario['ID'] == id_p].index[0]
    st.session_state.df_inventario.at[idx, 'Stock_Actual'] = int(st.session_state[input_key])
    trigger_cambio()


def agregar_item(nombre, cat, cant, mini, unit, tags_extra):
    df = st.session_state.df_inventario

    # ---> RANGOS DE ID CORREGIDOS (Dice "Materiales") <---
    rangos = {"Alimentación": 100, "Salud": 200, "Limpieza": 300, "Materiales": 500, "Tienda": 600}
    r_base = rangos.get(cat, 700)  # 700 por defecto para cualquier otra cosa

    ids_en_rango = df[(df['ID'] >= r_base) & (df['ID'] < r_base + 100)]['ID']
    nuevo_id = ids_en_rango.max() + 1 if not ids_en_rango.empty else r_base + 1

    # 3. ETIQUETAS BASE AUTOMÁTICAS
    tags_base = {"Alimentación": "comida", "Salud": "medicina", "Limpieza": "higiene", "Materiales": "herramientas", "Tienda": "venta"}.get(cat, "general")
    tag_final = f"{tags_base},{tags_extra}".strip(",").replace(",,", ",") if tags_extra else tags_base

    nuevo = pd.DataFrame([{
        'ID': int(nuevo_id),
        'Producto': nombre,
        'Categoría': cat,
        'Stock_Actual': int(cant),
        'Stock_Mínimo': int(mini),
        'Unidad': unit,
        'Tags': tag_final
    }])
    st.session_state.df_inventario = pd.concat([df, nuevo], ignore_index=True)
    trigger_cambio()

def eliminar_item(id_p):
    st.session_state.df_inventario = st.session_state.df_inventario[st.session_state.df_inventario['ID'] != id_p]
    trigger_cambio()


def crear_grafico_dona(labels, values, colors, texto_centro):
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.7,
                                 marker=dict(colors=colors), sort=False, textinfo='none')])
    fig.update_layout(margin=dict(t=5, b=5, l=5, r=5), height=200, showlegend=False)
    fig.add_annotation(text=texto_centro, x=0.5, y=0.5, showarrow=False, font_size=18)
    return fig

# 4. FUNCIÓN PARA GENERAR PDF
def generar_pdf(dataframe):
    from fpdf import FPDF
    import datetime

    # Generar fecha en formato día/mes/año (ej: 04/jun/2026)
    meses = {"01":"ene", "02":"feb", "03":"mar", "04":"abr", "05":"may", "06":"jun",
             "07":"jul", "08":"ago", "09":"sep", "10":"oct", "11":"nov", "12":"dic"}
    hoy = datetime.datetime.now()
    fecha_texto = f"{hoy.day:02d}/{meses[hoy.strftime('%m')]}/{hoy.year}"

    dataframe = dataframe.sort_values(by='ID')

    pdf = FPDF()
    pdf.add_page()

    # Título y Fecha
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, txt="Inventario - La Manada Feliz", ln=True, align='C')
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(190, 5, txt=f"Fecha de reporte: {fecha_texto}", ln=True, align='C')
    pdf.ln(8)

    # Encabezados de tabla
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(15, 10, "ID", 1, 0, 'C')
    pdf.cell(75, 10, "Producto", 1, 0, 'C')
    pdf.cell(35, 10, "Categoría", 1, 0, 'C')
    pdf.cell(35, 10, "Stock Actual", 1, 0, 'C')
    pdf.cell(30, 10, "Mínimo", 1, 1, 'C')

    # Datos
    pdf.set_font("Arial", '', 10)
    for _, row in dataframe.iterrows():
        prod = str(row['Producto']).encode('latin-1', 'replace').decode('latin-1')[:35]
        cat = str(row['Categoría']).encode('latin-1', 'replace').decode('latin-1')

        pdf.cell(15, 10, str(row['ID']), 1, 0, 'C')
        pdf.cell(75, 10, prod, 1, 0, 'L')
        pdf.cell(35, 10, cat, 1, 0, 'C')
        pdf.cell(35, 10, f"{row['Stock_Actual']} {str(row['Unidad'])[:5]}", 1, 0, 'C')
        pdf.cell(30, 10, str(row['Stock_Mínimo']), 1, 1, 'C')

    # Guardar en memoria y retornar bytes
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        tmp.seek(0)
        pdf_bytes = tmp.read()
    return pdf_bytes


# --- INTERFAZ ---
st.title("🐾 La Manada Feliz")

# --- ALERTAS DINÁMICAS ---
df_actual = st.session_state.df_inventario
criticos = df_actual[df_actual['Stock_Actual'] < df_actual['Stock_Mínimo']]

if not criticos.empty:
    lista_detallada = ""
    for _, row in criticos.iterrows():
        lista_detallada += f"\n* Tienes **{int(row['Stock_Actual'])}** {row['Unidad']} de **{row['Producto']}**, el mínimo es **{int(row['Stock_Mínimo'])}** {row['Unidad']}."
    st.error(f"🚨 **PRODUCTOS BAJOS:** {lista_detallada}")

if st.session_state.cambios_sin_guardar:
    with st.container(border=True):
        st.warning("⚠️ Hay cambios sin guardar.")
        c1, c2 = st.columns(2)
        if c1.button("💾 GUARDAR", use_container_width=True, type="primary"):
            datos_a_guardar = st.session_state.df_inventario.to_dict(orient='records')
            supabase.table('inventario').upsert(datos_a_guardar).execute()

            ids_actuales = st.session_state.df_inventario['ID'].tolist()
            db_items = supabase.table('inventario').select('ID').execute()

            for item in db_items.data:
                id_en_nube = item['ID']
                if id_en_nube not in ids_actuales:
                    supabase.table('inventario').delete().eq('ID', id_en_nube).execute()

            st.session_state.cambios_sin_guardar = False
            st.rerun()

        if c2.button("🔄 DESCARTAR", use_container_width=True):
            respuesta = supabase.table('inventario').select("*").execute()
            st.session_state.df_inventario = pd.DataFrame(respuesta.data)
            st.session_state.cambios_sin_guardar = False
            st.rerun()

# --- DASHBOARD ---
st.subheader("📊 Dashboard")
with st.container(border=True):
    col_inv, col_agua, col_gas = st.columns(3)

    with col_inv:
        st.markdown("<p style='text-align:center; font-weight:bold;'>📦 Estado General</p>", unsafe_allow_html=True)

        df_cats = df_actual[df_actual['Categoría'].isin(CATEGORIAS)]
        total_productos = len(df_cats)

        if total_productos > 0:
            actual_t = int(df_cats['Stock_Actual'].sum())
            min_t = int(df_cats['Stock_Mínimo'].sum())

            # Porcentaje volumétrico total (el que sale en el centro de la dona)
            porc = int((actual_t / min_t * 100)) if min_t > 0 else 0

            # Contar cuántos productos diferentes están por debajo de su mínimo
            criticos_count = len(df_cats[df_cats['Stock_Actual'] < df_cats['Stock_Mínimo']])

            # Calcular qué porcentaje del catálogo total está en crisis
            tasa_criticos = (criticos_count / total_productos) * 100

            # --- NUEVO ALGORITMO BALANCEADO ---
            if tasa_criticos >= 20:
                # Más del 20% del inventario tiene problemas
                color_grafico = "#e74c3c"  # Rojo
                mensaje = f"🔴 Crítico ({criticos_count} alertas)"
                color_texto = "red"
            elif tasa_criticos > 0:
                # Hay faltantes, pero son incidentes aislados (menos del 20%)
                color_grafico = "#f1c40f"  # Amarillo
                mensaje = f"🟡 Atención ({criticos_count} alertas)"
                color_texto = "#d4ac0d"
            elif porc > 120:
                # Todo cubierto y con bastante extra
                color_grafico = "#3498db"  # Azul
                mensaje = "🔵 Sobreabasto"
                color_texto = "#2980b9"
            else:
                # Todo cubierto en niveles normales
                color_grafico = "#2ecc71"  # Verde
                mensaje = "🟢 Abasto Justo"
                color_texto = "green"

            # Adaptación visual de la Dona
            if porc >= 100:
                labels_dona = ["Cubierto"]
                valores_dona = [1]
                colores_dona = [color_grafico]
            else:
                labels_dona = ["Actual", "Faltante global"]
                valores_dona = [actual_t, min_t - actual_t]
                colores_dona = [color_grafico, '#f0f0f0']

            st.plotly_chart(
                crear_grafico_dona(
                    labels_dona,
                    valores_dona,
                    colores_dona,
                    f"<b>{porc}%</b>"
                ),
                use_container_width=True
            )

            st.markdown(
                f"<p style='text-align:center; font-size:15px; font-weight:bold; color:{color_texto}; margin-top:-20px;'>{mensaje}</p>",
                unsafe_allow_html=True)

        else:
            st.info("Sin datos registrados.")

    with col_agua:
        c_t, c_b = st.columns([4, 1])
        c_t.markdown("<p style='text-align:center; font-weight:bold;'>💧 Agua</p>", unsafe_allow_html=True)
        try:
            idx_a = df_actual[df_actual['Producto'].str.contains("Agua", case=False)].index[0]
            id_a, act_a, min_a = int(df_actual.at[idx_a, 'ID']), int(df_actual.at[idx_a, 'Stock_Actual']), int(
                df_actual.at[idx_a, 'Stock_Mínimo'])

            with c_b:
                with st.popover("⚙️"):
                    def upd_min_agua():
                        st.session_state.df_inventario.at[idx_a, 'Stock_Mínimo'] = int(st.session_state.m_agua_val)
                        trigger_cambio()


                    st.number_input("Mínimo Agua", value=min_a, key="m_agua_val", on_change=upd_min_agua, step=1)

            porc_a = int((act_a / min_a * 100)) if min_a > 0 else 0
            st.plotly_chart(
                crear_grafico_dona(["Lleno", "Vacío"], [act_a, max(0, min_a - act_a)], ['#3498db', '#f0f0f0'],
                                   f"<b>{porc_a}%</b><br><span style='font-size:12px;'>{act_a} Tinacos</span>"),
                use_container_width=True)

            if "dash_agua" not in st.session_state: st.session_state["dash_agua"] = act_a

            c_m, c_i, c_p = st.columns([1, 1.5, 1], vertical_alignment="center")
            c_m.markdown("<span class='dashboard-marker'></span>", unsafe_allow_html=True)
            c_m.button("➖", key="btn_m_agua", on_click=ajustar_cantidad, args=(id_a, -1, "dash_agua"),
                       use_container_width=True)
            with c_i:
                st.number_input("Cant Agua", value=act_a, step=1, key="dash_agua", on_change=actualizar_desde_input,
                                args=(id_a, "dash_agua"), label_visibility="collapsed")
            c_p.button("➕", key="btn_p_agua", on_click=ajustar_cantidad, args=(id_a, 1, "dash_agua"),
                       use_container_width=True)
        except IndexError:
            st.write("Falta registrar 'Agua'")

    with col_gas:
        c_t, c_b = st.columns([4, 1])
        c_t.markdown("<p style='text-align:center; font-weight:bold;'>⛽ Gasolina</p>", unsafe_allow_html=True)
        try:
            idx_g = df_actual[df_actual['Producto'].str.contains("Gasolina", case=False)].index[0]
            id_g, act_g, min_g = int(df_actual.at[idx_g, 'ID']), int(df_actual.at[idx_g, 'Stock_Actual']), int(
                df_actual.at[idx_g, 'Stock_Mínimo'])

            with c_b:
                with st.popover("⚙️"):
                    def upd_min_gas():
                        st.session_state.df_inventario.at[idx_g, 'Stock_Mínimo'] = int(st.session_state.m_gas_val)
                        trigger_cambio()


                    st.number_input("Mínimo Gas", value=min_g, key="m_gas_val", on_change=upd_min_gas, step=1)

            porc_g = int((act_g / min_g * 100)) if min_g > 0 else 0
            st.plotly_chart(
                crear_grafico_dona(["Lleno", "Vacío"], [act_g, max(0, min_g - act_g)], ['#f1c40f', '#f0f0f0'],
                                   f"<b>{porc_g}%</b><br><span style='font-size:12px;'>{act_g} Bidones</span>"),
                use_container_width=True)

            if "dash_gas" not in st.session_state: st.session_state["dash_gas"] = act_g

            c_m, c_i, c_p = st.columns([1, 1.5, 1], vertical_alignment="center")
            c_m.markdown("<span class='dashboard-marker'></span>", unsafe_allow_html=True)
            c_m.button("➖", key="btn_m_gas", on_click=ajustar_cantidad, args=(id_g, -1, "dash_gas"),
                       use_container_width=True)
            with c_i:
                st.number_input("Cant Gas", value=act_g, step=1, key="dash_gas", on_change=actualizar_desde_input,
                                args=(id_g, "dash_gas"), label_visibility="collapsed")
            c_p.button("➕", key="btn_p_gas", on_click=ajustar_cantidad, args=(id_g, 1, "dash_gas"),
                       use_container_width=True)
        except IndexError:
            st.write("Falta registrar 'Gasolina'")

# --- GESTIÓN DE INVENTARIO ---
st.markdown("---")
st.subheader("📋 Gestión de Inventario")

# 5. ACTUALIZACIÓN DE PESTAÑAS (TABS)
tab_names = ["🍎 Alimentación", "💊 Salud", "🧼 Limpieza", "🛠️ Materiales", "🏪 Tienda", "📋 Todo"]

if "pestana_activa" not in st.session_state:
    st.session_state.pestana_activa = 0


def sincronizar_pestana():
    st.session_state.pestana_activa = tab_names.index(st.session_state.selector_tabs)


st.radio("Secciones", tab_names, horizontal=True, key="selector_tabs", index=st.session_state.pestana_activa,
         on_change=sincronizar_pestana, label_visibility="collapsed")


def render_row(row, pref):
    id_p = int(row['ID'])
    input_key = f"{pref}_in_{id_p}"

    critico = row['Stock_Actual'] < row['Stock_Mínimo']
    if input_key not in st.session_state: st.session_state[input_key] = int(row['Stock_Actual'])

    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns([4, 1, 0.8, 1.2, 0.8], vertical_alignment="center")

        c1.markdown("<span class='inventory-marker'></span>", unsafe_allow_html=True)

        with c1:
            st.markdown(
                f"<span style='color:{'#ff4b4b' if critico else 'inherit'}; font-weight:bold;'>{'🚨' if critico else '✅'} {row['Producto']}</span>",
                unsafe_allow_html=True)
            st.caption(f"Stock: {int(row['Stock_Actual'])} / Mín: {int(row['Stock_Mínimo'])} {row['Unidad']}")

        with c2:
            with st.popover("⚙️"):
                def upd_m(id_p=id_p, pr=pref):
                    st.session_state.df_inventario.loc[
                        st.session_state.df_inventario['ID'] == id_p, 'Stock_Mínimo'] = int(
                        st.session_state[f"{pr}_m_ed_{id_p}"])
                    trigger_cambio()

                st.number_input("Editar Mínimo", value=int(row['Stock_Mínimo']), key=f"{pref}_m_ed_{id_p}",
                                on_change=upd_m, step=1)
                if row['Categoría'] != 'Recursos':
                    st.divider()
                    if st.button(f"🗑️ Borrar", key=f"del_{pref}_{id_p}", use_container_width=True):
                        eliminar_item(id_p)
                        st.rerun()

        c3.button("➖", key=f"{pref}_b_m_{id_p}", on_click=ajustar_cantidad, args=(id_p, -1, input_key),
                  use_container_width=True)
        with c4:
            st.number_input("Cant", value=int(row['Stock_Actual']), key=input_key, label_visibility="collapsed", step=1,
                            on_change=actualizar_desde_input, args=(id_p, input_key))
        c5.button("➕", key=f"{pref}_b_p_{id_p}", on_click=ajustar_cantidad, args=(id_p, 1, input_key),
                  use_container_width=True)


idx_tab = st.session_state.pestana_activa
# Ajustar el índice para detectar "Todo" (ahora es el índice 5)
cat_actual = "Todo" if idx_tab == 5 else CATEGORIAS[idx_tab]
pfx = "gen" if cat_actual == "Todo" else cat_actual[:3].lower()

# 6. BOTÓN DE DESCARGA PDF SI ESTAMOS EN LA PESTAÑA "TODO"
if cat_actual == "Todo":
    import datetime
    meses = {"01":"ene", "02":"feb", "03":"mar", "04":"abr", "05":"may", "06":"jun",
             "07":"jul", "08":"ago", "09":"sep", "10":"oct", "11":"nov", "12":"dic"}
    hoy = datetime.datetime.now()
    fecha_archivo = f"{hoy.day:02d}-{meses[hoy.strftime('%m')]}-{hoy.year}"

    st.markdown("<br>", unsafe_allow_html=True)
    pdf_bytes = generar_pdf(df_actual)
    st.download_button(
        label="📥 Descargar Inventario en PDF",
        data=pdf_bytes,
        file_name=f"inventario_{fecha_archivo}.pdf",
        mime="application/pdf",
        use_container_width=True,
        type="primary"
    )
    st.markdown("<hr>", unsafe_allow_html=True)

items = df_actual[~df_actual['Categoría'].isin(['Recursos'])] if cat_actual == "Todo" else df_actual[
    df_actual['Categoría'] == cat_actual]

for _, row in items.iterrows():
    render_row(row, pfx)

if cat_actual != "Todo":
    with st.expander(f"✨ Agregar a {cat_actual}"):
        with st.form(f"f_{cat_actual}"):
            n_nom = st.text_input("Nombre del Producto")
            c1, c2 = st.columns(2)
            n_can = c1.number_input("Cantidad Inicial", min_value=0, step=1)
            n_min = c2.number_input("Mínimo Requerido", min_value=0, step=1)

            c3, c4 = st.columns(2)
            n_uni = c3.text_input("Unidad (ej: litros, kg, piezas)")
            n_tags = c4.text_input("(Opcional)Etiquetas extra (ej: caballos, urgente)")

            if st.form_submit_button("Añadir al Sistema"):
                if n_nom:
                    agregar_item(n_nom, cat_actual, n_can, n_min, n_uni, n_tags)
                    st.rerun()