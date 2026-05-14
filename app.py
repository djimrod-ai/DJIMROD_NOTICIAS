import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import feedparser
from concurrent.futures import ThreadPoolExecutor
import re

# =============================================================================
# 0. CONFIGURACIÓN PRIVADA
# =============================================================================
MY_SECRET_API_KEY = "PUT_HERE" 

# =============================================================================
# 1. SISTEMA DE DISEÑO Y ESTÉTICA
# =============================================================================
st.set_page_config(page_title="Intelligence Hub Editorial", page_icon="📰", layout="wide")

# Estados globales
if 'bg_color' not in st.session_state:
    st.session_state.bg_color = "#FFFFFF" 
if 'text_color' not in st.session_state:
    st.session_state.text_color = "#1F2937"
if 'accent_color' not in st.session_state:
    st.session_state.accent_color = "#1E3A8A"
if 'bulos_list' not in st.session_state:
    st.session_state.bulos_list = []
if 'show_bulos' not in st.session_state:
    st.session_state.show_bulos = False

# Galería de Estilos
TEMAS_LUJO = {
    "✨ Oro Imperial": ("#FDF5E6", "#4A3F35", "#FFD700"),
    "🥈 Plata Moderna": ("#E5E4E2", "#2C3E50", "#FFD700"),
    "💎 Platino Pure": ("#F5F5F5", "#1A1A1A", "#FFD700"),
    "🍷 Tinto Elegante": ("#F5F5DC", "#2C3E50", "#FFD700"),
    "👑 Azul Real": ("#002366", "#FFFFFF", "#FFD700"),
}
TEMAS_CORPORATIVOS = {
    "☀️ Blanco Puro": ("#FFFFFF", "#1F2937", "#FFD700"),
    "🗞️ Diario Clásico": ("#F4EBD0", "#5D4037", "#C62828"),
    "🏢 Corporativo Azul": ("#FFFFFF", "#333333", "#0056B3"),
    "🌊 Marino Profundo": ("#001F3F", "#FFFFFF", "#3B82F6"),
    "💼 Gris Ejecutivo": ("#E5E7EB", "#111827", "#4B5563"),
}
TEMAS_NOCTURNOS = {
    "🌙 Modo Oscuro": ("#121212", "#FFFFFF", "#00FFC8"),
    "⚡ Cyberpunk": ("#0D0221", "#FF00FF", "#00FFFF"),
    "📟 Matrix": ("#000000", "#00FF41", "#008F11"),
    "🌌 Midnight": ("#000428", "#FFFFFF", "#005C97"),
}
TEMAS_SOFT = {
    "🌸 Sakura": ("#FFF0F5", "#4B0082", "#FF69B4"),
    "🌿 Menta": ("#F0FFF0", "#2F4F4F", "#3CB371"),
    "💜 Lavanda": ("#E6E6FA", "#483D8B", "#9370DB"),
}
TEMAS_VARIADOS = {
    "Dorado": ("#FFB700", "#001DDD", "#FFFFFF"),
    "Sandia": ("#FF0000", "#1BCB00", "#7F5F00"),
    "Cielo": ("#00AEFF", "#FFF0F5", "#FFF0F5"),
    "Atardecer": ("#FF5500", "#FFF200", "#CE3535"),
    "Manzana": ("#91FF00", "#644C25", "#CBFBAF"),
}

def aplicar_tema(bg, txt, acc):
    st.session_state.bg_color = bg
    st.session_state.text_color = txt
    st.session_state.accent_color = acc
    st.rerun()

st.markdown(f"""
    <style>
    html, body, .stApp, .main, .block-container, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
        background-color: {st.session_state.bg_color} !important;
    }}
    p, span, label, .stMarkdown, .stMarkdown p {{
        color: {st.session_state.text_color} !important;
    }}
    .main-title {{
        text-align: center;
        font-size: 3rem;
        font-weight: 800;
        color: {st.session_state.accent_color} !important;
        margin-bottom: 20px;
    }}
    .news-card {{
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid {st.session_state.accent_color};
        margin-bottom: 15px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        color: #1F2937 !important;
    }}
    .date-tag {{
        font-size: 0.75rem;
        color: #C00000;
        font-weight: bold;
    }}
    .bulo-card {{
        background-color: #FFF5F5;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #FF4B4B;
        margin-bottom: 15px;
        color: #7F1D1D !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# =============================================================================
# 2. MOTOR DE BÚSQUEDA E INMEDIATEZ
# =============================================================================
RSS_FEEDS = {
    "El Mundo": "https://www.elmundo.es/rss/estC1.xml",
    "ABC": "https://www.abc.es/rss/noticias.xml",
    "El País": "https://www.elpais.com/rss/0/latest.xml",
    "Diario de Sevilla": "https://www.diariodesevilla.es/rss/noticias.xml",
    "La Vanguardia": "https://www.lavanguardia.com/rss/estatico/todas.xml",
    "El Confidencial": "https://www.elconfidencial.com/rss",
    "RTVE": "https://www.rtve.es/rss/todas-las-noticias.rss",
    "EFE": "https://www.efe.com/rss/estatico/todas.xml",
}

def calcular_score_bulo(titulo, fuente):
    score = 0
    t = titulo.upper()
    if any(p in t for p in ["RAZÓN POR LA QUE", "LO QUE NADIE TE CUENTA", "BOMBA", "SENSACIONAL"]): score += 2
    if any(p in t for p in ["INMEDIATAMENTE", "SÓLO HOY", "URGENTE"]): score += 2
    if "!!!" in t or (len([c for c in t if c.isupper()]) > 10 and len(t) < 50): score += 2
    umbral = 5 if fuente in RSS_FEEDS else 3
    return score >= umbral

def formatear_fecha(fecha_str):
    try:
        dt = pd.to_datetime(fecha_str).replace(tzinfo=None)
        ahora = datetime.now()
        dif = ahora - dt
        if dif.total_seconds() < 3600: return f"⚡ HACE MINUTOS"
        if dt.date() == ahora.date(): return f"🔥 HOY {dt.strftime('%H:%M')}"
        return dt.strftime('%d/%m/%y %H:%M')
    except: return "Reciente"

def fetch_rss(medio, url, keywords):
    resultados = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if any(word.lower() in entry.title.lower() or word.lower() in entry.summary.lower() for word in keywords):
                resultados.append({
                    'title': entry.title, 'url': entry.link, 'source': medio, 
                    'date': formatear_fecha(entry.published if hasattr(entry, 'published') else ""), 
                    'description': entry.summary, 'is_bulo': calcular_score_bulo(entry.title, medio)
                })
    except: pass
    return resultados

def fetch_google_news(keywords):
    resultados = []
    query = ' OR '.join(keywords).replace(' ', '+')
    url = f"https://news.google.com/rss/search?q={query}&hl=es-ES&gl=ES&ceid=ES:es"
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            resultados.append({
                'title': entry.title, 'url': entry.link, 
                'source': entry.source.title if hasattr(entry, 'source') else "Google News", 
                'date': formatear_fecha(entry.published if hasattr(entry, 'published') else ""), 
                'description': "Sincronizado en tiempo real.", 'is_bulo': calcular_score_bulo(entry.title, "Google News")
            })
    except: pass
    return resultados

def obtener_noticias_api(keywords):
    query = ' OR '.join(keywords)
    url = f"https://newsapi.org/v2/everything?q={query}&language=es&sortBy=publishedAt&apiKey={MY_SECRET_API_KEY}"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            art = res.json().get('articles', [])
            return [{'title': a['title'], 'url': a['url'], 'source': a['source'], 'date': formatear_fecha(a['publishedAt']), 'description': a['description'], 'is_bulo': calcular_score_bulo(a['title'], a['source'])} for a in art]
    except: pass
    return []

# =============================================================================
# 3. INTERFAZ DE USUARIO (Súper Organizada)
# =============================================================================
st.sidebar.title("⚙️ Control Hub")

# POSICIÓN 1: ARCHIVO DE BULOS (Uso de key fija para evitar DuplicateElementId)
st.sidebar.markdown("### 🚩 Control de Calidad")
btn_label = f"🗑️ Archivo de Bulos ({len(st.session_state.bulos_list)})"
if st.sidebar.button(btn_label, key="btn_bulos_fixed"):
    st.session_state.show_bulos = not st.session_state.get('show_bulos', False)

st.sidebar.markdown("---")

# POSICIÓN 2: BÚSQUEDA Y TEMAS
st.sidebar.markdown("### 🔍 Temas Maestros")
ALL_THEMES = {
    "🤖 IA Generativa": "ChatGPT\nClaude\nGemini\nSora\nMidjourney\nLLM",
    "🪙 Cripto/Blockchain": "Bitcoin\nEthereum\nSolana\nWeb3\nHalving",
    "📈 Economía Global": "BCE\nInflación\nPIB\nBolsa de Madrid\nS&P500",
    "🌍 Geopolítica": "Rusia\nUcrania\nChina\nOTAN\nIsrael\nGaza",
    "⚽ Fútbol": "LaLiga\nChampions\nFichajes\nReal Madrid\nBarça",
    "🏀 Baloncesto": "NBA\nEuroliga\nACB\nFIBA",
    "🏎️ Motor": "F1\nFerrari\nRed Bull\nMotoGP",
    "🎮 Gaming/Tech": "PlayStation\nXbox\nNvidia\nApple\nQualcomm",
}
search_q = st.sidebar.text_input("Buscar tema")
filtered = {k: v for k, v in ALL_THEMES.items() if search_q.lower() in k.lower()}
preset_list = list(filtered.keys())
if preset_list:
    preset = st.sidebar.selectbox("Sugerencia", preset_list)
    if st.sidebar.button("Cargar Temas"): st.session_state['keywords'] = filtered[preset]

keywords_input = st.sidebar.text_area("Palabras clave", value=st.session_state.get('keywords', "Inteligencia Artificial\nEconomía"))
keywords_list = [k.strip() for k in keywords_input.split('\n') if k.strip()]

# POSICIÓN 3: DISEÑO (SISTEMA DE LLAVES ÚNICAS)
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎨 Estilos")
with st.sidebar.expander("💎 Lujo"):
    for i, (nom, col) in enumerate(TEMAS_LUJO.items()):
        if st.button(nom, key=f"lujo_{i}"): aplicar_tema(*col)
with st.sidebar.expander("🏢 Corporativo"):
    for i, (nom, col) in enumerate(TEMAS_CORPORATIVOS.items()):
        if st.button(nom, key=f"corp_{i}"): aplicar_tema(*col)
with st.sidebar.expander("🌙 Nocturno"):
    for i, (nom, col) in enumerate(TEMAS_NOCTURNOS.items()):
        if st.button(nom, key=f"noct_{i}"): aplicar_tema(*col)
with st.sidebar.expander("🌸 Soft"):
    for i, (nom, col) in enumerate(TEMAS_SOFT.items()):
        if st.button(nom, key=f"soft_{i}"): aplicar_tema(*col)
with st.sidebar.expander("🌈 Variados"):
    for i, (nom, col) in enumerate(TEMAS_VARIADOS.items()):
        if st.button(nom, key=f"var_{i}"): aplicar_tema(*col)

st.sidebar.markdown("---")
st.session_state.bg_color = st.sidebar.color_picker("Fondo Manual", st.session_state.bg_color)
st.session_state.text_color = st.sidebar.color_picker("Letras Manual", st.session_state.text_color)
st.session_state.accent_color = st.sidebar.color_picker("Detalles Manual", st.session_state.accent_color)

# =============================================================================
# 4. CUERPO PRINCIPAL
# =============================================================================
st.markdown("<h1 class='main-title'>📰 Intelligence Hub Editorial</h1>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🌐 Noticias de ÚLTIMA HORA", "🚀 X (Twitter)"])

with tab1:
    col_a, col_b = st.columns([2, 1])
    with col_a:
        modo = st.radio("Fuente:", ["Híbrido (Rápido)", "Solo API Global"], horizontal=True)
    with col_b:
        num_results = st.slider("Cantidad de noticias", 5, 200, 30)
    
    if st.button("🔍 EJECUTAR RASTREO DE INMEDIATEZ"):
        with st.spinner('Sincronizando la red de medios...'):
            final_results = []
            final_results.extend(fetch_google_news(keywords_list))
            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(fetch_rss, medio, url, keywords_list) for medio, url in RSS_FEEDS.items()]
                for future in futures: final_results.extend(future.result())
            if modo == "Híbrido (Rápido)" or modo == "Solo API Global":
                final_results.extend(obtener_noticias_api(keywords_list))
            
            if final_results:
                vistas = set()
                noticias_reales = []
                bulos_detectados = []
                for n in final_results:
                    if n['url'] not in vistas:
                        vistas.add(n['url'])
                        if n.get('is_bulo', False): bulos_detectados.append(n)
                        else: noticias_reales.append(n)
                
                st.session_state.bulos_list = bulos_detectados
                final_list = noticias_reales[:num_results]
                
                if bulos_detectados:
                    st.warning(f"⚠️ {len(bulos_detectados)} noticias fueron archivadas por posible BULO.")

                df = pd.DataFrame(final_list)[['title', 'date', 'source', 'url']]
                df.columns = ['Título', 'Fecha/Hora', 'Fuente', 'Enlace']
                st.subheader("📋 Tabla de Acceso Rápido")
                st.data_editor(df, column_config={"Enlace": st.column_config.LinkColumn("🔗 Abrir Noticia")}, 
                               disabled=True, use_container_width=True, hide_index=True)
                
                st.markdown("---")
                st.subheader("📄 Análisis Detallado")
                for art in final_list:
                    st.markdown(f"""
                        <div class="news-card">
                            <div style='display: flex; justify-content: space-between;'>
                                <span style='color:{st.session_state.accent_color}; font-weight:bold;'>{art['source']}</span>
                                <span class='date-tag'>{art['date']}</span>
                            </div>
                            <h3 style='margin:5px 0;'><a href='{art['url']}' target='_blank' style='text-decoration:none; color:#1F2937;'>👉 {art['title']}</a></h3>
                            <p style='font-size:0.9rem; color:#555;'>{art.get('description', 'Sincronizado en tiempo real.')}</p>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.error("No se detectaron noticias recientes.")

    if st.session_state.get('show_bulos', False):
        st.markdown("---")
        st.markdown(f"<h2 style='color:red;'>🚩 Archivo de Posibles Bulos</h2>", unsafe_allow_html=True)
        for b in st.session_state.bulos_list:
            st.markdown(f"""
                <div class="bulo-card">
                    <span style='font-weight:bold;'>SISTEMA DE ALERTA: Posible Clickbait</span><br>
                    <b>{b['source']}</b> | {b['date']}<br>
                    <a href='{b['url']}' target='_blank' style='color:red; font-weight:bold;'>Ver noticia sospechosa ↗️</a>
                    <p style='font-size:0.8rem;'>{b['description']}</p>
                </div>
                """, unsafe_allow_html=True)

with tab2:
    if keywords_list:
        cols = st.columns(4)
        for idx, word in enumerate(keywords_list):
            col = cols[idx % 4]
            url_x = f"https://twitter.com/search?q={word.replace(' ', '%20')}&f=live"
            col.markdown(f"**{word}**")
            col.markdown(f"[Ver en X ↗️]({url_x})")


