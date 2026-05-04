import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from supabase import create_client, Client

# --- CONFIGURACIÓN DE SUPABASE ---
# Streamlit leerá esto de tus variables de entorno locales (secrets.toml) o de la nube
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

CATEGORIAS = ["Alimentación", "Salud", "Limpieza"]

# --- GESTIÓN DE ESTADO ---
if 'df_inventario' not in st.session_state:
    # 1. Leer datos directamente desde Supabase
    respuesta = supabase.table('inventario').select("*").execute()
    # 2. Convertir la respuesta de Supabase a un DataFrame de Pandas
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
            # 1. Guardar/Actualizar los datos actuales
            datos_a_guardar = st.session_state.df_inventario.to_dict(orient='records')
            supabase.table('inventario').upsert(datos_a_guardar).execute()

            # 2. Borrar de la nube los que eliminaste en el programa (CÓDIGO CORREGIDO)
            ids_actuales = st.session_state.df_inventario['ID'].tolist()
            db_items = supabase.table('inventario').select('ID').execute()

            for item in db_items.data:
                id_en_nube = item['ID']
                if id_en_nube not in ids_actuales:
                    supabase.table('inventario').delete().eq('ID', id_en_nube).execute()

            st.session_state.cambios_sin_guardar = False
            st.rerun()

        if c2.button("🔄 DESCARTAR", use_container_width=True):
            # Si se descarta, volvemos a descargar lo que hay en la nube
            respuesta = supabase.table('inventario').select("*").execute()
            st.session_state.df_inventario = pd.DataFrame(respuesta.data)
            st.session_state.cambios_sin_guardar = False
            st.rerun()

# --- DASHBOARD ---
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

        c_m, c_i, c_p = st.columns([1, 1.5, 1], vertical_alignment="center")
        c_m.markdown("<span class='dashboard-marker'></span>", unsafe_allow_html=True)
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

        c_m, c_i, c_p = st.columns([1, 1.5, 1], vertical_alignment="center")
        c_m.markdown("<span class='dashboard-marker'></span>", unsafe_allow_html=True)
        c_m.button("➖", key="btn_m_gas", on_click=ajustar_cantidad, args=(id_g, -1, "dash_gas"),
                   use_container_width=True)
        with c_i: st.number_input("Cant Gas", value=act_g, step=1, key="dash_gas", on_change=actualizar_desde_input,
                                  args=(id_g, "dash_gas"), label_visibility="collapsed")
        c_p.button("➕", key="btn_p_gas", on_click=ajustar_cantidad, args=(id_g, 1, "dash_gas"),
                   use_container_width=True)

# --- GESTIÓN DE INVENTARIO ---
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