import streamlit as st
import os, base64
from core.ui import aplicar_css, COR_DESTAQUE

def tela_inicio(usuario):

    aplicar_css()

    st.markdown("<h1 style='text-align:center; color:#FFD770;'>👋 Bem-vindo ao BJJ Digital</h1>", unsafe_allow_html=True)

    # ============================
    # Logo centralizado
    # ============================
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode()
        st.markdown(
            f"<div style='text-align:center;'><img src='data:image/png;base64,{logo_base64}' style='width:160px; margin-top:10px;'></div>",
            unsafe_allow_html=True
        )

    st.write("")
    st.markdown("<h3 style='text-align:center;'>Escolha uma opção abaixo para continuar:</h3>", unsafe_allow_html=True)
    st.write("")

    # ============================
    # Cards principais
    # ============================
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center;'>🥋 Modo Rola</h3>", unsafe_allow_html=True)
        if st.button("Acessar Modo Rola"):
            st.session_state.menu_selection = "Modo Rola"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown(f"<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center;'>📘 Exame de Faixa</h3>", unsafe_allow_html=True)
        if st.button("Fazer Exame"):
            st.session_state.menu_selection = "Exame de Faixa"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col3:
        st.markdown(f"<div class='card'>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center;'>🏆 Ranking</h3>", unsafe_allow_html=True)
        if st.button("Ver Ranking"):
            st.session_state.menu_selection = "Ranking"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
