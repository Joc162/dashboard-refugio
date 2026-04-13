import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="La Manada Feliz", layout="wide", initial_sidebar_state="collapsed")

# --- CSS PARA VISIBILIDAD COMPACTA Y BOTONES EN LÍNEA ---
st.markdown("""
    <style>
    /* Ajustes generales de texto para móvil */
    html, body, [class*="st-"] { font-size: 16px !important; }
    .stMarkdown p { font-size: 16px !important; }
    .stCaption { font-size: 14px !important; color: #a0a0a0; }

    /* 1. OCULTAR LAS FLECHITAS NATIVAS DEL NUMBER INPUT PARA AHORRAR ESPACIO */
    input[type="number"]::-webkit-inner-spin-button, 
    input[type="number"]::-webkit-outer-spin-button { 
        -webkit-appearance: none; 
        margin: 0; 
    }
    input[type="number"] {
        -moz-appearance: textfield;
        text-align: center !important; /* Centrar el número */
        font-size: 16px !important;
        padding: 0px !important;
    }

    /* 2. FORZAR QUE NO SE APILEN LAS COLUMNAS EN MÓVIL */
    @media (max-width: 600px) {
        div[data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap !important;
            gap: 2px !important; /* Espacio mínimo entre elementos */
        }
        div[data-testid="column"] {
            min-width: 0 !important; /* Permite que las columnas se hagan delgadas */
        }
    }

    /* 3. Hacer las cajas y botones más compactos */
    div[data-testid="stNumberInputContainer"] {
        min-height: 2.2rem !important; 
        height: 2.2rem !important;
    }
    .stButton>button {
        min-height: 2.2rem !important;
        height: 2.2rem !important;
        padding: 0px 5px !important;
    }
    </style>
    """, unsafe_allow_html=True)

DB_FILE = 'inventario_santuario.csv'
CATEGORIAS = ["Alimentación", "Salud", "Limpieza"]

# --- GESTIÓN DE ESTADO ---
if 'df_inventario' not in st.session_state:
    if os.path.exists(DB_FILE):
        st.session_state.df_inventario = pd.read_csv(DB_FILE)
    else:
        # Datos iniciales
        data = {
            'ID': [101, 201, 301, 401, 402],
            'Producto': ['Croquetas', 'Bravecto', 'Jabón Líquido', 'Agua (Tanque)', 'Gasolina'],
            'Categoría': ['Alimentación', 'Salud', 'Limpieza', 'Recursos', 'Recursos'],
            'Stock_Actual': [10, 60, 40, 1, 5],
            'Stock_Mínimo': [4, 45, 20, 1, 2],
            'Unidad': ['costales', 'piezas', 'litros', 'tinacos', 'bidones'],
            'Tags': ['comida,perros', 'medicina', 'higiene', 'recursos', 'recursos']
        }
        st.session_state.df_inventario = pd.DataFrame(data)

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
    rangos = {"Alimentación": 100, "Salud": 200, "Limpieza": 300}
    r_base = rangos.get(cat, 500)

    ids_en_rango = df[(df['ID'] >= r_base) & (df['ID'] < r_base + 100)]['ID']
    nuevo_id = ids_en_rango.max() + 1 if not ids_en_rango.empty else r_base + 1

    tags_base = {"Alimentación": "comida", "Salud": "medicina", "Limpieza": "higiene"}.get(cat, "general")
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


# --- INTERFAZ ---
st.title("🐾 La Manada Feliz")

# 1. ALERTAS DINÁMICAS
df_actual = st.session_state.df_inventario
criticos = df_actual[df_actual['Stock_Actual'] < df_actual['Stock_Mínimo']]

if not criticos.empty:
    lista_detallada = ""
    for _, row in criticos.iterrows():
        lista_detallada += f"\n* Tienes **{int(row['Stock_Actual'])}** {row['Unidad']} de **{row['Producto']}**, el mínimo es **{int(row['Stock_Mínimo'])}** {row['Unidad']}."
    st.error(f"🚨 **PRODUCTOS BAJOS:** {lista_detallada}")

# Guardado
if st.session_state.cambios_sin_guardar:
    with st.container(border=True):
        st.warning("⚠️ Hay cambios sin guardar.")
        c1, c2 = st.columns(2)
        if c1.button("💾 GUARDAR", use_container_width=True, type="primary"):
            st.session_state.df_inventario.to_csv(DB_FILE, index=False)
            st.session_state.cambios_sin_guardar = False
            st.rerun()
        if c2.button("🔄 DESCARTAR", use_container_width=True):
            if os.path.exists(DB_FILE): st.session_state.df_inventario = pd.read_csv(DB_FILE)
            st.session_state.cambios_sin_guardar = False
            st.rerun()

# 2. DASHBOARD
st.subheader("📊 Dashboard")
with st.container(border=True):
    col_inv, col_agua, col_gas = st.columns(3)

    with col_inv:
        st.markdown("<p style='text-align:center; font-weight:bold;'>📦 Suministros</p>", unsafe_allow_html=True)
        stock_cat = df_actual[df_actual['Categoría'].isin(CATEGORIAS)].groupby('Categoría')['Stock_Actual'].sum()
        actual_t = int(stock_cat.sum())
        min_t = int(df_actual[df_actual['Categoría'].isin(CATEGORIAS)]['Stock_Mínimo'].sum())
        porc = int((actual_t / min_t * 100)) if min_t > 0 else 0
        st.plotly_chart(crear_grafico_dona(stock_cat.index.tolist() + ["Faltante"],
                                           list(stock_cat.values) + [max(0, min_t - actual_t)],
                                           ['#ff9f9f', '#9eff9e', '#9fe2ff', '#f0f0f0'], f"<b>{porc}%</b>"),
                        use_container_width=True)

    with col_agua:
        c_t, c_b = st.columns([4, 1])
        c_t.markdown("<p style='text-align:center; font-weight:bold;'>💧 Agua</p>", unsafe_allow_html=True)
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
        st.plotly_chart(crear_grafico_dona(["Lleno", "Vacío"], [act_a, max(0, min_a - act_a)], ['#3498db', '#f0f0f0'],
                                           f"<b>{porc_a}%</b><br><span style='font-size:12px;'>{act_a} Tinacos</span>"),
                        use_container_width=True)

        if "dash_agua" not in st.session_state: st.session_state["dash_agua"] = act_a

        # Dashboard: Restaurados los botones con barra delgada
        c_m, c_i, c_p = st.columns([1, 1.5, 1], vertical_alignment="center")
        c_m.button("➖", key="btn_m_agua", on_click=ajustar_cantidad, args=(id_a, -1, "dash_agua"),
                   use_container_width=True)
        with c_i: st.number_input("Cant Agua", value=act_a, step=1, key="dash_agua", on_change=actualizar_desde_input,
                                  args=(id_a, "dash_agua"), label_visibility="collapsed")
        c_p.button("➕", key="btn_p_agua", on_click=ajustar_cantidad, args=(id_a, 1, "dash_agua"),
                   use_container_width=True)

    with col_gas:
        c_t, c_b = st.columns([4, 1])
        c_t.markdown("<p style='text-align:center; font-weight:bold;'>⛽ Gasolina</p>", unsafe_allow_html=True)
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
        st.plotly_chart(crear_grafico_dona(["Lleno", "Vacío"], [act_g, max(0, min_g - act_g)], ['#f1c40f', '#f0f0f0'],
                                           f"<b>{porc_g}%</b><br><span style='font-size:12px;'>{act_g} Bidones</span>"),
                        use_container_width=True)

        if "dash_gas" not in st.session_state: st.session_state["dash_gas"] = act_g

        # Dashboard: Restaurados los botones con barra delgada
        c_m, c_i, c_p = st.columns([1, 1.5, 1], vertical_alignment="center")
        c_m.button("➖", key="btn_m_gas", on_click=ajustar_cantidad, args=(id_g, -1, "dash_gas"),
                   use_container_width=True)
        with c_i: st.number_input("Cant Gas", value=act_g, step=1, key="dash_gas", on_change=actualizar_desde_input,
                                  args=(id_g, "dash_gas"), label_visibility="collapsed")
        c_p.button("➕", key="btn_p_gas", on_click=ajustar_cantidad, args=(id_g, 1, "dash_gas"),
                   use_container_width=True)

# 3. GESTIÓN DE INVENTARIO
st.markdown("---")
st.subheader("📋 Gestión de Inventario")

tab_names = ["🍎 Alimentación", "💊 Salud", "🧼 Limpieza", "📋 Todo"]

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
        # Columnas ajustadas para acomodar los botones a los lados de la barra
        c1, c2, c3, c4, c5 = st.columns([4, 1, 0.8, 1.2, 0.8], vertical_alignment="center")

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

        # AQUÍ ESTÁN TUS BOTONES DE VUELTA [-] [  numero  ] [+]
        c3.button("➖", key=f"{pref}_b_m_{id_p}", on_click=ajustar_cantidad, args=(id_p, -1, input_key),
                  use_container_width=True)
        with c4:
            st.number_input("Cant", value=int(row['Stock_Actual']), key=input_key, label_visibility="collapsed", step=1,
                            on_change=actualizar_desde_input, args=(id_p, input_key))
        c5.button("➕", key=f"{pref}_b_p_{id_p}", on_click=ajustar_cantidad, args=(id_p, 1, input_key),
                  use_container_width=True)


idx_tab = st.session_state.pestana_activa
cat_actual = "Todo" if idx_tab == 3 else CATEGORIAS[idx_tab]
pfx = "gen" if cat_actual == "Todo" else cat_actual[:3].lower()

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
                if n_nom: agregar_item(n_nom, cat_actual, n_can, n_min, n_uni, n_tags); st.rerun()