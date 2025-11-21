import streamlit as st

# ============================================================
#  UI GLOBAL – CSS COMPLETO E OTIMIZADO
# ============================================================

def aplicar_css():
    st.markdown("""
    <style>

    /* ===============================
       FONTE GLOBAL
    =============================== */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif !important;
        background-color: #0e2d26 !important;
        color: #FFFFFF !important;
    }

    /* ===============================
       OCULTAR CABEÇALHO E RODAPÉ
    =============================== */
    header { visibility: hidden; }
    footer { visibility: hidden; }

    /* ===============================
       TÍTULOS
    =============================== */
    h1, h2, h3, h4, h5, h6 {
        color: #FFD770 !important;
        font-weight: 700 !important;
    }

    p, label, span, div {
        color: #FFFFFF !important;
    }

    /* ===============================
       BOTÕES PERSONALIZADOS
    =============================== */
    .stButton>button {
        background: linear-gradient(90deg, #078B6C, #056853);
        color: white;
        border: none;
        padding: 0.6rem 1.2rem;
        border-radius: 10px;
        font-weight: bold;
        transition: 0.2s ease-in-out;
        font-size: 16px;
    }

    .stButton>button:hover {
        background-color: #FFD770;
        color: #0e2d26;
        transform: scale(1.03);
        transition: 0.2s;
    }

    /* ===============================
       CAIXAS DE TEXTO, INPUTS, SELECTS
    =============================== */
    .stTextInput>div>input,
    select,
    textarea {
        background-color: #113830 !important;
        color: #FFFFFF !important;
        border: 1px solid #FFD770 !important;
        border-radius: 8px !important;
    }

    /* ===============================
       RADIO BUTTONS
    =============================== */
    .stRadio>div>label {
        color: #FFFFFF !important;
        font-weight: 500 !important;
    }

    /* ===============================
       CARDS (BLOCOS)
    =============================== */
    .card {
        background-color: #113830;
        padding: 20px;
        border-radius: 15px;
        border: 2px solid #FFD770;
        text-align: center;
        transition: 0.25s;
    }

    .card:hover {
        background-color: #FFD770;
        color: #0e2d26 !important;
        transform: scale(1.03);
        cursor: pointer;
    }

    /* ===============================
       SEÇÕES E LINHAS
    =============================== */
    hr {
        border: 1px solid #FFD770 !important;
    }

    /* ===============================
       TABELAS
    =============================== */
    table {
        background-color: #113830 !important;
        border-radius: 12px !important;
        overflow: hidden !important;
    }

    thead tr th {
        background-color: #FFD770 !important;
        color: #0e2d26 !important;
        font-weight: bold !important;
        padding: 10px !important;
    }

    tbody tr td {
        background-color: #0e2d26 !important;
        color: #FFFFFF !important;
        padding: 8px !important;
    }

    /* ===============================
       ALERTAS (success, warning, info)
    =============================== */
    .stAlert {
        border-radius: 12px !important;
    }

    .stAlert>div {
        background-color: #113830 !important;
        border-left: 6px solid #FFD770 !important;
    }

    /* ===============================
       SCROLLBAR
    =============================== */
    ::-webkit-scrollbar {
        width: 10px;
    }
    ::-webkit-scrollbar-track {
        background: #0e2d26;
    }
    ::-webkit-scrollbar-thumb {
        background: #FFD770;
        border-radius: 10px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #e6c462;
    }

    </style>
    """, unsafe_allow_html=True)
