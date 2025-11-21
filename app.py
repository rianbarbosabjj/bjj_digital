import streamlit as st
import os

from core.db import inicializar_banco
from core.auth import tela_login, verificar_sessao, tela_completar_cadastro

# PÁGINAS DO SISTEMA
from pages.inicio import tela_inicio
from pages.modo_rola import tela_modo_rola
from pages.exame import tela_exame
from pages.ranking import tela_ranking
from pages.professor import painel_professor
from pages.gestao_equipes import gestao_equipes
from pages.gestao_usuarios import gestao_usuarios
from pages.gestao_questoes import gestao_questoes
from pages.gestao_exames import gestao_exames
from pages.admin_dashboard import admin_dashboard


# ======================================================================
# CONFIGURAÇÃO DO STREAMLIT
# ======================================================================

st.set_page_config(
    page_title="BJJ Digital",
    page_icon="🥋",
    layout="wide",
)

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
                "Sair"
            ])

        # MENU DO PROFESSOR
        if tipo == "professor":
            return st.radio("Navegação", [
                "Início",
                "Ranking",
                "Painel do Professor",
                "Gestão de Equipes",
                "Sair"
            ])

        # MENU DO ADMIN
        if tipo == "admin":
            return st.radio("Navegação", [
                "Dashboard Administrativo",
                "Gestão de Usuários",
                "Gestão de Equipes",
                "
