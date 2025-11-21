import streamlit as st

# ============================================
# 🎨 CORES DO SISTEMA (ORIGINAIS DO SEU APP)
# ============================================
COR_FUNDO = "#0e2d26"
COR_TEXTO = "#FFFFFF"
COR_DESTAQUE = "#FFD770"
COR_BOTAO = "#078B6C"
COR_HOVER = "#FFD770"

# ============================================
# 💅 CSS GLOBAL
# ============================================
def aplicar_css():
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;700&display=swap');

        body {{
            background-color: {COR_FUNDO} !important;
            color: {COR_TEXTO} !important;
            font-family: 'Poppins', sans-serif !important;
        }}

        header {{visibility: hidden;}}
        footer {{visibility: hidden;}}

        .stButton>button {{
            background: linear-gradient(90deg, {COR_BOTAO}, #056853);
            color: white;
            font-weight: bold;
            border-radius: 8px;
            padding: 0.6rem 1.2rem;
            border: none;
        }}

        .stButton>button:hover {{
            background: {COR_HOVER};
            color: black;
        }}

        .card {{
            border: 2px solid {COR_DESTAQUE};
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            background-color: #133c33;
        }}

    </style>
    """, unsafe_allow_html=True)
