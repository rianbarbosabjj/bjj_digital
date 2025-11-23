import streamlit as st
from streamlit_option_menu import option_menu
import os

# Importações dos Módulos
from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
from database import criar_banco, criar_usuarios_teste
from views import login, geral, aluno, professor, admin

# =========================================
# CONFIGURAÇÕES GERAIS
# =========================================
st.set_page_config(page_title="BJJ Digital", page_icon="assets/logo.png", layout="wide")

# [CSS] - Pode manter aqui ou mover para um arquivo styles.css e ler ele
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;700&display=swap');
.stButton>button {{ background: linear-gradient(90deg, {COR_BOTAO}, #056853); color: white; font-weight: bold; border: none; padding: 0.6em 1.2em; border-radius: 10px; transition: 0.3s; }}
.stButton>button:hover {{ background: {COR_HOVER}; color: {COR_FUNDO}; transform: scale(1.02); }}
h1, h2, h3 {{ color: {COR_DESTAQUE}; text-align: center; font-weight: 700; }}
/* ... COPIE O RESTANTE DO SEU CSS AQUI ... */
</style>
""", unsafe_allow_html=True)

# Inicialização do Banco
if not os.path.exists(os.path.expanduser("~/bjj_digital.db")):
    criar_banco()
    criar_usuarios_teste()

# =========================================
# EXECUÇÃO PRINCIPAL (ROTEADOR)
# =========================================
def app_principal():
    usuario_logado = st.session_state.usuario
    if not usuario_logado:
        st.error("Sessão expirada. Faça login novamente.")
        st.session_state.usuario = None
        st.rerun()

    tipo_usuario = usuario_logado["tipo"]

    # --- Callback de Navegação ---
    def navigate_to_sidebar(page):
        st.session_state.menu_selection = page

    # --- Sidebar ---
    st.sidebar.image("assets/logo.png", use_container_width=True)
    st.sidebar.markdown(f"<h3 style='color:{COR_DESTAQUE};'>{usuario_logado['nome'].title()}</h3>", unsafe_allow_html=True)
    st.sidebar.markdown(f"<small style='color:#ccc;'>Perfil: {tipo_usuario.capitalize()}</small>", unsafe_allow_html=True)
    
    st.sidebar.button("👤 Meu Perfil", on_click=navigate_to_sidebar, args=("Meu Perfil",), use_container_width=True)

    if tipo_usuario in ["admin", "professor"]:
        st.sidebar.button("👩‍🏫 Painel do Professor", on_click=navigate_to_sidebar, args=("Painel do Professor",), use_container_width=True)

    if tipo_usuario == "admin":
        st.sidebar.button("🔑 Gestão de Usuários", on_click=navigate_to_sidebar, args=("Gestão de Usuários",), use_container_width=True)

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sair", use_container_width=True):
        st.session_state.usuario = None
        st.session_state.pop("menu_selection", None)
        st.session_state.pop("token", None) 
        st.session_state.pop("registration_pending", None) 
        st.rerun()

    # --- Roteamento ---
    if "menu_selection" not in st.session_state:
        st.session_state.menu_selection = "Início"

    pagina = st.session_state.menu_selection

    # 1. Telas da Sidebar
    if pagina == "Meu Perfil":
        geral.tela_meu_perfil(usuario_logado)
    elif pagina == "Gestão de Usuários":
        admin.gestao_usuarios(usuario_logado)
    elif pagina == "Painel do Professor":
        professor.painel_professor()
    
    # 2. Tela Inicial
    elif pagina == "Início":
        geral.tela_inicio()

    # 3. Menu Horizontal
    else:
        if tipo_usuario in ["admin", "professor"]:
            opcoes = ["Modo Rola", "Exame de Faixa", "Ranking", "Gestão de Questões", "Gestão de Equipes", "Gestão de Exame"]
            icons = ["people-fill", "journal-check", "trophy-fill", "cpu-fill", "building-fill", "file-earmark-check-fill"]
        else:
            opcoes = ["Modo Rola", "Ranking", "Meus Certificados"]
            icons = ["people-fill", "trophy-fill", "patch-check-fill"]
            
            # Verifica se aluno pode ver exame (lógica simples aqui ou mover para utils)
            # ... (Lógica de verificação do exame_habilitado) ...
            # Se habilitado: opcoes.insert(1, "Exame de Faixa")

        opcoes.insert(0, "Início")
        icons.insert(0, "house-fill")

        menu = option_menu(
            menu_title=None, options=opcoes, icons=icons, key="menu_selection_component", 
            orientation="horizontal", default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": COR_FUNDO, "border-radius": "10px", "margin-bottom": "20px"},
                "icon": {"color": COR_DESTAQUE, "font-size": "18px"},
                "nav-link": {"font-size": "14px", "text-align": "center", "margin": "0px", "--hover-color": "#1a4d40", "color": COR_TEXTO, "font-weight": "600"},
                "nav-link-selected": {"background-color": COR_BOTAO, "color": COR_DESTAQUE},
            }
        )

        # Roteamento Menu
        if menu == "Início": geral.tela_inicio()
        elif menu == "Modo Rola": aluno.modo_rola(usuario_logado)
        elif menu == "Exame de Faixa": aluno.exame_de_faixa(usuario_logado)
        elif menu == "Ranking": aluno.ranking()
        elif menu == "Gestão de Equipes": professor.gestao_equipes()
        elif menu == "Gestão de Questões": admin.gestao_questoes()
        elif menu == "Gestão de Exame": admin.gestao_exame_de_faixa()
        elif menu == "Meus Certificados": aluno.meus_certificados(usuario_logado)

# Main Loop
if __name__ == "__main__":
    if "token" not in st.session_state: st.session_state.token = None
    if "registration_pending" not in st.session_state: st.session_state.registration_pending = None
    if "usuario" not in st.session_state: st.session_state.usuario = None

    if st.session_state.registration_pending:
        login.tela_completar_cadastro(st.session_state.registration_pending)
    elif st.session_state.usuario:
        app_principal()
    else:
        login.tela_login()
