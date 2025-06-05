import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import os
from plotly.subplots import make_subplots
import gdown
import requests

# =============================================
# CONFIGURACIÓN INICIAL
# =============================================
st.set_page_config(
    page_title="Panel de Ventas SPV",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================
# FUNCIÓN PARA CARGAR DATOS (VERSIÓN PARA DEPLOY)
# =============================================
@st.cache_data(ttl=3600)
def load_data():
    import tempfile
    import time
    
    file_urls = [
        "https://drive.google.com/uc?id=10NLcCVPLe3q9kpqFyOeCrOSY9d5U-WSA",
        "https://docs.google.com/spreadsheets/d/10NLcCVPLe3q9kpqFyOeCrOSY9d5U-WSA/export?format=xlsx"
    ]
    
    for i, file_url in enumerate(file_urls):
        try:
            # Crear archivo temporal con nombre único
            temp_file = os.path.join(tempfile.gettempdir(), f"ventas_spv_temp_{int(time.time())}_{i}.xlsx")
            
            with st.spinner(f"Descargando desde fuente {i+1}..."):
                # Método de descarga alternativo
                if "drive.google.com" in file_url:
                    import gdown
                    gdown.download(file_url, temp_file, quiet=True, fuzzy=True)
                else:
                    import requests
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    response = requests.get(file_url, headers=headers, stream=True, timeout=30)
                    response.raise_for_status()
                    
                    with open(temp_file, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
            
            # Verificar que el archivo se descargó correctamente
            if os.path.getsize(temp_file) == 0:
                raise ValueError("El archivo descargado está vacío")
            
            # Leer con openpyxl para mejor compatibilidad
            df = pd.read_excel(temp_file, engine='openpyxl')
            
            # Validación de columnas
            required_columns = ['Vendedor', 'Fecha Pedido', 'Nombre Cliente', 'Codigo Cliente',
                              'Pedido', 'Codigo Producto', 'Nombre Producto', 'Cantidad',
                              'Precio', 'Monto Total', 'Caja', 'Centro']
            
            if not all(col in df.columns for col in required_columns):
                missing = [col for col in required_columns if col not in df.columns]
                st.warning(f"Fuente {i+1}: Faltan columnas: {', '.join(missing)}")
                continue
                
            # Procesamiento exitoso
            return df
            
        except Exception as e:
            st.warning(f"Intento {i+1} fallido: {str(e)}")
            continue
            
        finally:
            # Limpieza garantizada del archivo temporal
            if 'temp_file' in locals() and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
    
    st.error("❌ No se pudo cargar el archivo desde ninguna fuente disponible")
    return None

# =============================================
# CARGA Y VALIDACIÓN DE DATOS
# =============================================
with st.spinner("🔍 Cargando y validando datos..."):
    df = load_data()

# Validación de datos cargados
if df is None:
    st.error("🚨 No se pudieron cargar los datos. La aplicación se detendrá.")
    st.stop()

if not isinstance(df, pd.DataFrame) or df.empty:
    st.error("⚠️ Los datos cargados no son válidos o están vacíos.")
    st.stop()

# =============================================
# PROCESAMIENTO DE DATOS
# =============================================
try:
    # Extraer componentes de fecha
    df['Mes'] = df['Fecha Pedido'].dt.month
    df['Ano'] = df['Fecha Pedido'].dt.year
    df['Dia'] = df['Fecha Pedido'].dt.day
    df['Dia Semana'] = df['Fecha Pedido'].dt.day_name()
    df['Semana'] = df['Fecha Pedido'].dt.isocalendar().week
    df['Hora'] = df['Fecha Pedido'].dt.hour
    
    # Ordenar días de la semana
    dias_semana = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    df['Dia Semana'] = pd.Categorical(df['Dia Semana'], categories=dias_semana, ordered=True)
    
    # Calcular días hábiles
    df['Es Dia Habitl'] = df['Dia Semana'].isin(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'])
    
    # Definir variables globales para fechas
    global fecha_min, fecha_max
    fecha_min = df['Fecha Pedido'].min().strftime('%d/%m/%Y')
    fecha_max = df['Fecha Pedido'].max().strftime('%d/%m/%Y')

except Exception as e:
    st.error(f"❌ Error al procesar fechas: {str(e)}")
    st.stop()

# =============================================
# BARRA LATERAL (FILTROS)
# =============================================
st.sidebar.title("🔍 Filtros Principales")
st.sidebar.markdown("---")

# Selector de Año
try:
    años_disponibles = sorted(df['Ano'].unique())
    año_seleccionado = st.sidebar.selectbox(
        "**Seleccione el Año**",
        options=años_disponibles,
        index=len(años_disponibles)-1
    )

    # Selector de Mes (filtrado por año seleccionado)
    meses_disponibles = sorted(df[df['Ano'] == año_seleccionado]['Mes'].unique())
    mes_seleccionado = st.sidebar.selectbox(
        "**Seleccione el Mes**", 
        options=meses_disponibles,
        index=len(meses_disponibles)-1 if meses_disponibles else 0
    )
except Exception as e:
    st.error(f"❌ Error en los filtros de fecha: {str(e)}")
    st.stop()

# Filtros adicionales
try:
    centros_disponibles = df['Centro'].unique()
    centros_seleccionados = st.sidebar.multiselect(
        "**Filtrar por Centro**",
        options=centros_disponibles,
        default=centros_disponibles
    )

    vendedores_disponibles = df['Vendedor'].unique()
    vendedores_seleccionados = st.sidebar.multiselect(
        "**Filtrar por Vendedor**",
        options=vendedores_disponibles,
        default=vendedores_disponibles
    )
except Exception as e:
    st.error(f"❌ Error en los filtros adicionales: {str(e)}")
    st.stop()

# Aplicar filtros
try:
    df_filtrado = df[
        (df['Ano'] == año_seleccionado) &
        (df['Mes'] == mes_seleccionado) &
        (df['Centro'].isin(centros_seleccionados)) &
        (df['Vendedor'].isin(vendedores_seleccionados))
    ].copy()
    
    if df_filtrado.empty:
        st.warning("⚠️ No hay datos con los filtros seleccionados. Mostrando todos los datos.")
        df_filtrado = df.copy()
except Exception as e:
    st.error(f"❌ Error al aplicar filtros: {str(e)}")
    st.stop()

# =============================================
# PESTAÑAS PRINCIPALES
# =============================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Resumen Ventas", 
    "📋 Pedidos por Vendedor", 
    "🏢 Ventas por Cliente", 
    "🔎 Búsqueda de Productos"
])

# --- Pestaña 1: Resumen de Ventas ---
with tab1:
    try:
        st.header("📊 Resumen General de Ventas")
        
        # KPIs principales
        ventas_totales = df_filtrado['Monto Total'].sum()
        cajas_totales = df_filtrado['Caja'].sum()
        pedidos_totales = df_filtrado['Pedido'].nunique()
        ticket_promedio = ventas_totales / pedidos_totales if pedidos_totales > 0 else 0
        clientes_unicos = df_filtrado['Codigo Cliente'].nunique()
        
        # Mostrar KPIs
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("**Ventas Totales**", f"${ventas_totales:,.0f}")
        col2.metric("**Cajas Vendidas**", f"{cajas_totales:,.0f}")
        col3.metric("**Pedidos Realizados**", f"{pedidos_totales:,.0f}")
        col4.metric("**Ticket Promedio**", f"${ticket_promedio:,.0f}")
        col5.metric("**Clientes Atendidos**", f"{clientes_unicos:,.0f}")
        
        st.markdown("---")
        
        # Comparación con mes anterior
        st.subheader("📅 Comparación Mensual")
        
        mes_anterior = mes_seleccionado - 1 if mes_seleccionado > 1 else 12
        año_mes_anterior = año_seleccionado if mes_seleccionado > 1 else año_seleccionado - 1
        
        df_mes_anterior = df[
            (df['Ano'] == año_mes_anterior) & 
            (df['Mes'] == mes_anterior) &
            (df['Centro'].isin(centros_seleccionados)) &
            (df['Vendedor'].isin(vendedores_seleccionados))
        ]
        
        ventas_mes_anterior = df_mes_anterior['Monto Total'].sum()
        variacion = ((ventas_totales - ventas_mes_anterior) / ventas_mes_anterior * 100) if ventas_mes_anterior != 0 else 0
        
        col1, col2 = st.columns(2)
        col1.metric(
            f"**Ventas {mes_seleccionado}/{año_seleccionado}**",
            f"${ventas_totales:,.0f}",
            f"{variacion:.1f}% vs mes anterior",
            delta_color="inverse" if variacion < 0 else "normal"
        )
        col2.metric(
            f"**Ventas {mes_anterior}/{año_mes_anterior}**",
            f"${ventas_mes_anterior:,.0f}"
        )
        
        st.markdown("---")
        
        # Gráficos de análisis
        st.subheader("📊 Análisis por Dimensiones")
        
        # Ventas por vendedor
        ventas_vendedor = df_filtrado.groupby('Vendedor').agg({
            'Monto Total': 'sum',
            'Pedido': 'nunique',
            'Caja': 'sum'
        }).reset_index().sort_values('Monto Total', ascending=False)
        
        fig1 = px.bar(
            ventas_vendedor,
            x='Vendedor',
            y='Monto Total',
            title='**Ventas Totales por Vendedor**',
            color='Pedido',
            labels={'Monto Total': 'Ventas ($)', 'Pedido': 'N° Pedidos'},
            hover_data=['Caja']
        )
        st.plotly_chart(fig1, use_container_width=True)
        
        # Ventas por centro
        ventas_centro = df_filtrado.groupby('Centro').agg({
            'Monto Total': 'sum',
            'Caja': 'sum'
        }).reset_index().sort_values('Monto Total', ascending=False)
        
        fig2 = px.pie(
            ventas_centro,
            names='Centro',
            values='Monto Total',
            title='**Distribución de Ventas por Centro**',
            hole=0.3,
            hover_data=['Caja']
        )
        st.plotly_chart(fig2, use_container_width=True)
        
    except Exception as e:
        st.error(f"❌ Error en la pestaña de Resumen: {str(e)}")

# --- Pestaña 2: Pedidos por Vendedor ---
with tab2:
    try:
        st.header("📋 Análisis de Pedidos por Vendedor")
        
        # Configuración de objetivos
        st.subheader("🎯 Configuración de Objetivos")
        objetivo_default = 45
        objetivo = st.number_input(
            "**Establezca el objetivo diario de pedidos por vendedor**",
            min_value=1,
            value=objetivo_default,
            step=1
        )
        
        st.markdown("---")
        
        # Cálculo de métricas
        dias_habiles = df_filtrado['Dia'].nunique()
        objetivo_mensual = objetivo * dias_habiles
        
        pedidos_vendedor = df_filtrado.groupby('Vendedor').agg({
            'Pedido': 'nunique',
            'Dia': 'nunique',
            'Monto Total': 'sum'
        }).reset_index()
        
        pedidos_vendedor['Pedidos/Día'] = pedidos_vendedor['Pedido'] / pedidos_vendedor['Dia']
        pedidos_vendedor['Cumplimiento %'] = (pedidos_vendedor['Pedidos/Día'] / objetivo) * 100
        pedidos_vendedor['Desviación'] = pedidos_vendedor['Pedido'] - objetivo_mensual
        
        # Mostrar tabla resumen
        st.subheader("📊 Cumplimiento por Vendedor")
        
        st.dataframe(
            pedidos_vendedor.sort_values('Cumplimiento %', ascending=False),
            column_config={
                "Vendedor": "Vendedor",
                "Pedido": st.column_config.NumberColumn("Total Pedidos", format="%d"),
                "Dia": st.column_config.NumberColumn("Días Trabajados", format="%d"),
                "Pedidos/Día": st.column_config.NumberColumn("Pedidos/Día", format="%.1f"),
                "Cumplimiento %": st.column_config.ProgressColumn(
                    "Cumplimiento %",
                    format="%.1f%%",
                    min_value=0,
                    max_value=150
                ),
                "Desviación": st.column_config.NumberColumn("Desviación vs Objetivo", format="%+d"),
                "Monto Total": st.column_config.NumberColumn("Ventas Generadas", format="$%.0f")
            },
            hide_index=True,
            use_container_width=True
        )
        
        st.markdown("---")
        
        # Gráfico de tendencia de pedidos
        st.subheader("📈 Tendencia de Pedidos")
        
        pedidos_dia_semana = df_filtrado.groupby(['Dia Semana', 'Vendedor'])['Pedido'].nunique().reset_index()
        
        fig3 = px.bar(
            pedidos_dia_semana,
            x='Dia Semana',
            y='Pedido',
            color='Vendedor',
            title='**Pedidos por Día de la Semana**',
            labels={'Pedido': 'N° de Pedidos', 'Dia Semana': 'Día'},
            barmode='group'
        )
        fig3.add_hline(y=objetivo, line_dash="dash", line_color="red", annotation_text="Objetivo Diario")
        st.plotly_chart(fig3, use_container_width=True)
        
    except Exception as e:
        st.error(f"❌ Error en la pestaña de Pedidos: {str(e)}")

# --- Pestaña 3: Ventas por Cliente ---
with tab3:
    try:
        st.header("🏢 Análisis de Ventas por Cliente")
        
        # Selector de clientes
        clientes_seleccionados = st.multiselect(
            "**Seleccione clientes para analizar**",
            options=df_filtrado['Nombre Cliente'].unique(),
            default=df_filtrado['Nombre Cliente'].unique()[:3] if len(df_filtrado['Nombre Cliente'].unique()) > 0 else []
        )
        
        if not clientes_seleccionados:
            st.warning("⚠️ Por favor seleccione al menos un cliente.")
            st.stop()
        
        df_clientes = df_filtrado[df_filtrado['Nombre Cliente'].isin(clientes_seleccionados)]
        
        # Resumen por cliente
        st.subheader("📋 Resumen por Cliente")
        
        resumen_clientes = df_clientes.groupby(['Codigo Cliente', 'Nombre Cliente']).agg({
            'Pedido': 'nunique',
            'Monto Total': 'sum',
            'Caja': 'sum',
            'Fecha Pedido': ['min', 'max']
        }).reset_index()
        
        resumen_clientes.columns = [' '.join(col).strip() for col in resumen_clientes.columns.values]
        
        st.dataframe(
            resumen_clientes.sort_values('Monto Total sum', ascending=False),
            column_config={
                "Codigo Cliente": "Código",
                "Nombre Cliente": "Cliente",
                "Pedido nunique": st.column_config.NumberColumn("Pedidos", format="%d"),
                "Monto Total sum": st.column_config.NumberColumn("Total Vendido", format="$%.0f"),
                "Caja sum": st.column_config.NumberColumn("Cajas Vendidas", format="%d"),
                "Fecha Pedido min": st.column_config.DateColumn("Primer Pedido"),
                "Fecha Pedido max": st.column_config.DateColumn("Último Pedido")
            },
            hide_index=True,
            use_container_width=True
        )
        
        st.markdown("---")
        
        # Detalle por cliente seleccionado
        st.subheader("🔍 Detalle por Cliente")
        
        cliente_seleccionado = st.selectbox(
            "**Seleccione un cliente para ver detalle**",
            options=df_clientes['Nombre Cliente'].unique()
        )
        
        df_cliente = df_clientes[df_clientes['Nombre Cliente'] == cliente_seleccionado]
        
        # Productos más comprados por el cliente
        st.markdown(f"#### 🛍️ Productos más comprados por {cliente_seleccionado}")
        
        productos_cliente = df_cliente.groupby(['Codigo Producto', 'Nombre Producto']).agg({
            'Cantidad': 'sum',
            'Monto Total': 'sum',
            'Caja': 'sum',
            'Pedido': 'nunique'
        }).reset_index().sort_values('Monto Total', ascending=False)
        
        st.dataframe(
            productos_cliente,
            column_config={
                "Codigo Producto": "Código",
                "Nombre Producto": "Producto",
                "Cantidad": st.column_config.NumberColumn("Cantidad Total", format="%d"),
                "Monto Total": st.column_config.NumberColumn("Total Vendido", format="$%.0f"),
                "Caja": st.column_config.NumberColumn("Cajas Vendidas", format="%d"),
                "Pedido": st.column_config.NumberColumn("Veces Pedido", format="%d")
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Evolución temporal de compras
        st.markdown(f"#### 📅 Evolución Temporal de Compras - {cliente_seleccionado}")
        
        evolucion = df_cliente.groupby(df_cliente['Fecha Pedido'].dt.date).agg({
            'Monto Total': 'sum',
            'Pedido': 'nunique'
        }).reset_index()
        
        fig4 = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig4.add_trace(
            px.line(evolucion, x='Fecha Pedido', y='Monto Total', markers=True).data[0],
            secondary_y=False
        )
        
        fig4.add_trace(
            px.bar(evolucion, x='Fecha Pedido', y='Pedido', opacity=0.3).data[0],
            secondary_y=True
        )
        
        fig4.update_layout(
            title=f"Ventas a {cliente_seleccionado} por Fecha",
            xaxis_title="Fecha",
            yaxis_title="Ventas ($)",
            yaxis2_title="N° Pedidos",
            showlegend=True
        )
        
        st.plotly_chart(fig4, use_container_width=True)
        
    except Exception as e:
        st.error(f"❌ Error en la pestaña de Clientes: {str(e)}")

# --- Pestaña 4: Búsqueda de Productos ---
with tab4:
    try:
        st.header("🔎 Búsqueda Avanzada de Productos")
        
        # Selector de productos
        productos_buscar = st.multiselect(
            "**Seleccione productos a analizar**",
            options=df['Nombre Producto'].unique(),
            default=df['Nombre Producto'].unique()[:2] if len(df['Nombre Producto'].unique()) > 0 else []
        )
        
        if not productos_buscar:
            st.info("ℹ️ Seleccione al menos un producto para realizar la búsqueda.")
            st.stop()
        
        df_productos = df[df['Nombre Producto'].isin(productos_buscar)]
        
        # Resumen de productos seleccionados
        st.subheader("📋 Resumen de Productos Seleccionados")
        
        resumen_productos = df_productos.groupby(['Codigo Producto', 'Nombre Producto']).agg({
            'Pedido': 'nunique',
            'Cantidad': 'sum',
            'Monto Total': 'sum',
            'Caja': 'sum',
            'Nombre Cliente': 'nunique',
            'Fecha Pedido': ['min', 'max']
        }).reset_index()
        
        resumen_productos.columns = [' '.join(col).strip() for col in resumen_productos.columns.values]
        
        st.dataframe(
            resumen_productos,
            column_config={
                "Codigo Producto": "Código",
                "Nombre Producto": "Producto",
                "Pedido nunique": st.column_config.NumberColumn("Pedidos", format="%d"),
                "Cantidad sum": st.column_config.NumberColumn("Cantidad Total", format="%d"),
                "Monto Total sum": st.column_config.NumberColumn("Ventas Totales", format="$%.0f"),
                "Caja sum": st.column_config.NumberColumn("Cajas Vendidas", format="%d"),
                "Nombre Cliente nunique": st.column_config.NumberColumn("Clientes Únicos", format="%d"),
                "Fecha Pedido min": st.column_config.DateColumn("Primera Venta"),
                "Fecha Pedido max": st.column_config.DateColumn("Última Venta")
            },
            hide_index=True,
            use_container_width=True
        )
        
        st.markdown("---")
        
        # Detalle por producto seleccionado
        st.subheader("🔍 Detalle por Producto")
        
        producto_seleccionado = st.selectbox(
            "**Seleccione un producto para ver detalle**",
            options=productos_buscar
        )
        
        df_producto = df_productos[df_productos['Nombre Producto'] == producto_seleccionado]
        
        # Clientes que compraron este producto
        st.markdown(f"#### 🧑‍💼 Clientes que compraron {producto_seleccionado}")
        
        clientes_producto = df_producto.groupby(['Codigo Cliente', 'Nombre Cliente']).agg({
            'Pedido': 'nunique',
            'Cantidad': 'sum',
            'Monto Total': 'sum',
            'Caja': 'sum',
            'Fecha Pedido': 'max'
        }).reset_index().sort_values('Monto Total', ascending=False)
        
        st.dataframe(
            clientes_producto,
            column_config={
                "Codigo Cliente": "Código",
                "Nombre Cliente": "Cliente",
                "Pedido": st.column_config.NumberColumn("Veces Comprado", format="%d"),
                "Cantidad": st.column_config.NumberColumn("Cantidad Total", format="%d"),
                "Monto Total": st.column_config.NumberColumn("Total Gastado", format="$%.0f"),
                "Caja": st.column_config.NumberColumn("Cajas Compradas", format="%d"),
                "Fecha Pedido": st.column_config.DateColumn("Última Compra")
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Evolución temporal de ventas del producto
        st.markdown(f"#### 📈 Evolución de Ventas - {producto_seleccionado}")
        
        evolucion_producto = df_producto.groupby(df_producto['Fecha Pedido'].dt.to_period('M')).agg({
            'Monto Total': 'sum',
            'Pedido': 'nunique',
            'Cantidad': 'sum'
        }).reset_index()
        evolucion_producto['Fecha Pedido'] = evolucion_producto['Fecha Pedido'].dt.to_timestamp()
        
        fig5 = px.line(
            evolucion_producto,
            x='Fecha Pedido',
            y='Monto Total',
            title=f"Ventas Mensuales de {producto_seleccionado}",
            markers=True,
            labels={'Monto Total': 'Ventas ($)', 'Fecha Pedido': 'Mes'}
        )
        fig5.add_bar(x=evolucion_producto['Fecha Pedido'], y=evolucion_producto['Pedido'], name="N° Pedidos")
        st.plotly_chart(fig5, use_container_width=True)
        
    except Exception as e:
        st.error(f"❌ Error en la pestaña de Productos: {str(e)}")

# =============================================
# BARRA LATERAL (INFORMACIÓN ADICIONAL)
# =============================================
st.sidebar.markdown("---")
st.sidebar.markdown("**📌 Notas:**")
st.sidebar.markdown("- Los datos se actualizan automáticamente al cambiar los filtros")
st.sidebar.markdown("- Use los controles de los gráficos para zoom y detalles")
st.sidebar.markdown("- Exporte datos con el menú de los gráficos (ícono de cámara)")

st.sidebar.markdown("---")

# Agregar botón de actualización
if st.sidebar.button("🔄 Actualizar Datos", help="Haz clic para forzar la actualización de los datos"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown(f"📅 **Datos desde:** {fecha_min} **hasta** {fecha_max}")
st.sidebar.markdown(f"🔄 **Última actualización:** {datetime.now().strftime('%d/%m/%Y %H:%M')}")
