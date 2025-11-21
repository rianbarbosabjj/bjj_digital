import streamlit as st
from streamlit_option_menu import option_menu
from core.auth import tela_login, verificar_sessao
from core.db import inicializar_banco
from pages.inicio import tela_inicio
from pages.modo_rola import tela_modo_rola
from pages.exame import tela_exame
from pages.ranking import tela_ranking
from pages.professor import painel_professor
from pages.gestao_equipe import gestao_equipes
from pages.gestao_usuarios import gestao_usuarios
from pages.gestao_questoes import gestao_questoes
from pages.gestao_exame import gestao_exame_de_faixa
from pages.meu_perfil import tela_meu_perfil

# ================================
# CONFIGURAÇÕES GERAIS
# ================================
st.set_page_config(
    page_title="BJJ Digital",
    page_icon="assets/logo.png",
    layout="wide"
)

# Inicializa Banco
inicializar_banco()

# Verifica login e cadastro pendente
user = verificar_sessao()
if user is None:
    tela_login()
    st.stop()

usuario_logado = st.session_state.usuario
tipo = usuario_logado["tipo"]

# ================================
# SIDEBAR
# ================================
st.sidebar.image("assets/logo.png", use_container_width=True)
st.sidebar.markdown(f"### {usuario_logado['nome'].title()}")
st.sidebar.markdown(f"<small>Perfil: {tipo.capitalize()}</small>", unsafe_allow_html=True)

# Botões da sidebar
if st.sidebar.button("👤 Meu Perfil", use_container_width=True):
    st.session_state.menu = "Meu Perfil"

if tipo in ["admin", "professor"]:
    if st.sidebar.button("👩‍🏫 Painel do Professor", use_container_width=True):
        st.session_state.menu = "Painel Professor"

if tipo == "admin":
    if st.sidebar.button("🔑 Gestão de Usuários", use_container_width=True):
        st.session_state.menu = "Gestão Usuários"

if st.sidebar.button("🚪 Sair", use_container_width=True):
    st.session_state.clear()
    st.rerun()

# Valor padrão
if "menu" not in st.session_state:
    st.session_state.menu = "Início"

# ================================
# MENU SUPERIOR (HORIZONTAL)
# ================================
if tipo in ["admin", "professor"]:
    opcoes = [
        "Início", "Modo Rola", "Exame", "Ranking",
        "Gestão Questões", "Gestão Equipes", "Gestão Exame"
    ]
    icons = [
        "house-fill", "people-fill", "journal-check", "trophy-fill",
        "cpu-fill", "building-fill", "file-earmark-check-fill"
    ]
else:
    opcoes = ["Início", "Modo Rola", "Ranking", "Meus Certificados"]
    icons = ["house-fill", "people-fill", "trophy-fill", "patch-check-fill"]

menu_sel = option_menu(
    None,
    opcoes,
    icons=icons,
    orientation="horizontal",
    key="menu",
)

# ================================
# ROTEAMENTO
# ================================
if menu_sel == "Início":
    tela_inicio(usuario_logado)

elif menu_sel == "Modo Rola":
    tela_modo_rola(usuario_logado)

elif menu_sel == "Exame":
    tela_exame(usuario_logado)

elif menu_sel == "Ranking":
    tela_ranking()

elif menu_sel == "Gestão Equipes":
    gestao_equipes()

elif menu_sel == "Gestão Questões":
    gestao_questoes()

elif menu_sel == "Gestão Exame":
    gestao_exame_de_faixa()

elif st.session_state.menu == "Painel Professor":
    painel_professor()

elif st.session_state.menu == "Gestão Usuários":
    gestao_usuarios(usuario_logado)

elif st.session_state.menu == "Meu Perfil":
    tela_meu_perfil(usuario_logado)

