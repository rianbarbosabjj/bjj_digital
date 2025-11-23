import streamlit as st
from streamlit_option_menu import option_menu
import os

# Importações dos Módulos que você criou
from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
from database import criar_banco, criar_usuarios_teste
from views import login, geral, aluno, professor, admin

# =========================================
# CONFIGURAÇÕES GERAIS
# =========================================
st.set_page_config(page_title="BJJ Digital", page_icon="assets/logo.png", layout="wide")

# CSS Global
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;700&display=swap');
.stButton>button {{ background: linear-gradient(90deg, {COR_BOTAO}, #056853); color: white; font-weight: bold; border: none; padding: 0.6em 1.2em; border-radius: 10px; transition: 0.3s; }}
.stButton>button:hover {{ background: {COR_HOVER}; color: {COR_FUNDO}; transform: scale(1.02); }}
h1, h2, h3 {{ color: {COR_DESTAQUE}; text-align: center; font-weight: 700; }}
div[data-testid="stVerticalBlock"] div[data-testid="stContainer"] {{ border-radius: 10px; }}
</style>
""", unsafe_allow_html=True)

# Garante que o banco existe ao iniciar
if not os.path.exists(os.path.expanduser("~/bjj_digital.db")):
    criar_banco()
    criar_usuarios_teste()

# =========================================
# FUNÇÃO PRINCIPAL (ROTEADOR)
# =========================================
def app_principal():
    usuario_logado = st.session_state.usuario
    if not usuario_logado:
        st.error("Sessão expirada. Faça login novamente.")
        st.session_state.usuario = None
        st.rerun()

    tipo_usuario = usuario_logado["tipo"]

    # --- Navegação Lateral (Sidebar) ---
    def ir_para(pagina):
        st.session_state.menu_selection = pagina

    st.sidebar.image("assets/logo.png", use_container_width=True)
    st.sidebar.markdown(f"<h3 style='color:{COR_DESTAQUE};'>{usuario_logado['nome'].title()}</h3>", unsafe_allow_html=True)
    st.sidebar.markdown(f"<small style='color:#ccc;'>Perfil: {tipo_usuario.capitalize()}</small>", unsafe_allow_html=True)
    
    st.sidebar.button("👤 Meu Perfil", on_click=ir_para, args=("Meu Perfil",), use_container_width=True)

    if tipo_usuario in ["admin", "professor"]:
        st.sidebar.button("👩‍🏫 Painel do Professor", on_click=ir_para, args=("Painel do Professor",), use_container_width=True)

    if tipo_usuario == "admin":
        st.sidebar.button("🔑 Gestão de Usuários", on_click=ir_para, args=("Gestão de Usuários",), use_container_width=True)

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sair", use_container_width=True):
        for key in ["usuario", "menu_selection", "token", "registration_pending"]:
            st.session_state.pop(key, None)
        st.rerun()

    # --- Roteamento das Telas ---
    if "menu_selection" not in st.session_state:
        st.session_state.menu_selection = "Início"

    pagina = st.session_state.menu_selection

    # 1. Telas da Sidebar (Prioritárias)
    if pagina == "Meu Perfil":
        geral.tela_meu_perfil(usuario_logado)
        if st.button("⬅️ Voltar ao Início"): ir_para("Início")
            
    elif pagina == "Gestão de Usuários":
        admin.gestao_usuarios(usuario_logado)
        if st.button("⬅️ Voltar ao Início"): ir_para("Início")
            
    elif pagina == "Painel do Professor":
        professor.painel_professor()
        if st.button("⬅️ Voltar ao Início"): ir_para("Início")
    
    # 2. Tela Inicial e Menu Horizontal
    else:
        # Define opções do menu baseado no perfil
        if tipo_usuario in ["admin", "professor"]:
            opcoes = ["Início", "Modo Rola", "Exame de Faixa", "Ranking", "Gestão de Questões", "Gestão de Equipes", "Gestão de Exame"]
            icons = ["house-fill", "people-fill", "journal-check", "trophy-fill", "cpu-fill", "building-fill", "file-earmark-check-fill"]
        else: # Aluno
            opcoes = ["Início", "Modo Rola", "Ranking", "Meus Certificados"]
            icons = ["house-fill", "people-fill", "trophy-fill", "patch-check-fill"]
            
            # Verifica se exame está habilitado (consulta rápida opcional ou via banco)
            # Para simplificar aqui, deixamos padrão, mas você pode reativar a query de 'exame_habilitado' se quiser.
            opcoes.insert(2, "Exame de Faixa")
            icons.insert(2, "journal-check")

        # Menu Horizontal
        menu = option_menu(
            menu_title=None, 
            options=opcoes, 
            icons=icons, 
            default_index=opcoes.index(pagina) if pagina in opcoes else 0,
            orientation="horizontal",
            styles={
                "container": {"padding": "0!important", "background-color": COR_FUNDO},
                "icon": {"color": COR_DESTAQUE, "font-size": "16px"},
                "nav-link": {"font-size": "14px", "text-align": "center", "margin": "0px", "color": COR_TEXTO},
                "nav-link-selected": {"background-color": COR_BOTAO, "color": COR_DESTAQUE},
            }
        )

        # Roteador do Menu Horizontal
        if menu == "Início": geral.tela_inicio()
        elif menu == "Modo Rola": aluno.modo_rola(usuario_logado)
        elif menu == "Exame de Faixa": aluno.exame_de_faixa(usuario_logado)
        elif menu == "Ranking": aluno.ranking()
        elif menu == "Gestão de Equipes": professor.gestao_equipes()
        elif menu == "Gestão de Questões": admin.gestao_questoes()
        elif menu == "Gestão de Exame": admin.gestao_exame_de_faixa()
        elif menu == "Meus Certificados": aluno.meus_certificados(usuario_logado)

# =========================================
# PONTO DE ENTRADA (Start)
# =========================================
if __name__ == "__main__":
    # Inicializa variáveis de sessão
    if "usuario" not in st.session_state: st.session_state.usuario = None
    if "token" not in st.session_state: st.session_state.token = None
    if "registration_pending" not in st.session_state: st.session_state.registration_pending = None

    # Fluxo de Controle
    if st.session_state.registration_pending:
        login.tela_completar_cadastro(st.session_state.registration_pending)
    elif st.session_state.usuario:
        app_principal()
    else:
        login.tela_login()
