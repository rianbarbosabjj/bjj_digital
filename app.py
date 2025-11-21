import streamlit as st
import os

from core.db import inicializar_banco
from core.auth import tela_login, verificar_sessao, tela_completar_cadastro

# === PÁGINAS DO SISTEMA ===
from pages.inicio import tela_inicio
from pages.modo_rola import tela_modo_rola
from pages.exame import tela_exame
from pages.ranking import tela_ranking
from pages.professor import painel_professor
from pages.gestao_equipes import gestao_equipes
from pages.gestao_usuarios import gestao_usuarios
from pages.gestao_questoes import gestao_questoes
from pages.gestao_exame import gestao_exames
from pages.admin_dashboard import admin_dashboard

# === NOVAS PÁGINAS ===
from pages.meu_perfil import tela_perfil
from pages.solicitacoes_faixa import tela_solicitacoes_faixa

from api import api_router

# ======================================================================
# CONFIGURAÇÃO DO STREAMLIT
# ======================================================================

st.set_page_config(
    page_title="BJJ Digital",
    page_icon="assets/logo.png",
    layout="wide",
)

# ======================================
# CSS GLOBAL
# ======================================
from core.ui import aplicar_css
aplicar_css()
# CSS opcional
st.markdown("""
<style>
header {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ======================================================================
# INICIALIZAÇÃO DO BANCO
# ======================================================================

inicializar_banco()


# ======================================================================
# MENU PRINCIPAL
# ======================================================================

def menu_lateral(usuario):

    tipo = usuario["tipo"]  # aluno / professor / admin

    with st.sidebar:
        st.image("assets/logo.png", width=180)
        st.markdown(f"### 👋 Olá, **{usuario['nome'].title()}**")
        st.markdown("---")

        # MENU DO ALUNO
        if tipo == "aluno":
            return st.radio("Navegação", [
                "Início",
                "Modo Rola",
                "Exame de Faixa",
                "Ranking",
                "Meu Perfil",
                "Sair"
            ])

        # MENU DO PROFESSOR
        if tipo == "professor":
            return st.radio("Navegação", [
                "Início",
                "Ranking",
                "Painel do Professor",
                "Gestão de Equipes",
                "Aprovar Mudanças de Faixa",
                "Meu Perfil",
                "Sair"
            ])

        # MENU DO ADMIN
        if tipo == "admin":
            return st.radio("Navegação", [
                "Dashboard Administrativo",
                "Gestão de Usuários",
                "Gestão de Equipes",
                "Gestão de Questões",
                "Gestão de Exames",
                "Painel do Professor",
                "Ranking",
                "Aprovar Mudanças de Faixa",
                "Meu Perfil",
                "Sair"
            ])


# ======================================================================
# SISTEMA PRINCIPAL
# ======================================================================

def main():

    # ======================================================
    # 🔥 INTERCEPTAÇÃO DA API
    # ======================================================
    if "api" in st.experimental_get_url():
        api_router()
        return

    # ======================================================
    # SISTEMA NORMAL
    # ======================================================
    usuario = verificar_sessao()

    if not usuario:
        tela_login()
        return

    if not usuario.get("endereco"):
        tela_completar_cadastro(usuario)
        return

    pagina = menu_lateral(usuario)

    # ======================================================
    # ROTEAMENTO DAS PÁGINAS
    # ======================================================

    # ---- ALUNO ----
    if pagina == "Início":
        tela_inicio(usuario)

    elif pagina == "Modo Rola":
        tela_modo_rola(usuario)

    elif pagina == "Exame de Faixa":
        tela_exame(usuario)

    elif pagina == "Ranking":
        tela_ranking()

    elif pagina == "Meu Perfil":
        tela_perfil(usuario)

    # ---- PROFESSOR E ADMIN ----
    elif pagina == "Painel do Professor":
        painel_professor()

    elif pagina == "Gestão de Equipes":
        gestao_equipes()

    elif pagina == "Aprovar Mudanças de Faixa":
        tela_solicitacoes_faixa(usuario)

    # ---- ADMIN ----
    elif pagina == "Dashboard Administrativo":
        admin_dashboard()

    elif pagina == "Gestão de Usuários":
        gestao_usuarios()

    elif pagina == "Gestão de Questões":
        gestao_questoes()

    elif pagina == "Gestão de Exames":
        gestao_exames()

    # ---- SAIR ----
    elif pagina == "Sair":
        st.session_state.clear()
        st.rerun()


# ======================================================================
# EXECUÇÃO
# ======================================================================

if __name__ == "__main__":
    main()
