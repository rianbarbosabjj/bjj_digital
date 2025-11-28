import streamlit as st
import os
import sys
import bcrypt # Necessário para a troca de senha
from database import get_db

# =========================================================
# 1. CONFIGURAÇÃO (PRIMEIRA LINHA OBRIGATÓRIA)
# =========================================================
# initial_sidebar_state="expanded" faz a barra começar aberta no PC
st.set_page_config(
    page_title="BJJ Digital", 
    page_icon="assets/logo.png", 
    layout="wide",
    initial_sidebar_state="expanded" 
)

# =========================================================
# 2. ESTILOS VISUAIS (CSS PREMIUM - TEMA BJJ MODERN)
# =========================================================

# Importa cores do config (ou define fallback)
try:
    from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
except ImportError:
    COR_FUNDO = "#0e2d26"  # Verde Escuro da Marca
    COR_TEXTO = "#FFFFFF"
    COR_DESTAQUE = "#FFD770" # Dourado
    COR_BOTAO = "#078B6C"
    COR_HOVER = "#FFD770"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');

    /* --- GLOBAL --- */
    html, body, [class*="css"] {{
        font-family: 'Poppins', sans-serif;
    }}

    /* --- CORREÇÃO DO MENU LATERAL (HAMBÚRGUER/SETA) --- */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    [data-testid="stDecoration"] {{display: none;}}
    
    header[data-testid="stHeader"] {{
        background-color: {COR_FUNDO} !important;
        z-index: 1;
    }}

    [data-testid="collapsedControl"] {{
        color: {COR_DESTAQUE} !important; 
        display: block !important; 
    }}
    
    [data-testid="collapsedControl"] svg {{
        fill: {COR_DESTAQUE} !important;
    }}

    /* --- SCROLLBAR PERSONALIZADA (ESTILO MODERNO) --- */
    ::-webkit-scrollbar {{
        width: 10px;
        height: 10px;
    }}
    ::-webkit-scrollbar-track {{
        background: #091f1a; 
    }}
    ::-webkit-scrollbar-thumb {{
        background: {COR_BOTAO}; 
        border-radius: 5px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: {COR_DESTAQUE}; 
    }}

    /* --- ESTRUTURA GERAL --- */
    .block-container {{padding-top: 3rem; padding-bottom: 3rem;}}

    .stApp {{
        background-color: {COR_FUNDO} !important;
        background-image: radial-gradient(circle at 50% 0%, #15453a 0%, #0e2d26 60%);
    }}

    /* --- SIDEBAR --- */
    section[data-testid="stSidebar"] {{
        background-color: #091f1a !important; 
        border-right: 1px solid rgba(255, 215, 112, 0.1);
        box-shadow: 2px 0 10px rgba(0,0,0,0.3);
    }}

    /* Imagem da Sidebar (Avatar Style) */
    section[data-testid="stSidebar"] .stImage img {{
        border-radius: 12px;
        border: 1px solid {COR_DESTAQUE};
        padding: 5px;
        background: rgba(255,255,255,0.05);
    }}

    /* --- TIPOGRAFIA --- */
    h1, h2, h3, h4, h5, h6 {{
        color: {COR_TEXTO};
    }}
    h1, h2, h3 {{ 
        color: {COR_DESTAQUE} !important; 
        text-align: center; 
        font-weight: 700; 
        text-transform: uppercase;
        letter-spacing: 1px;
    }}

    /* --- BOTÕES MODERNOS --- */
    div.stButton > button, div.stFormSubmitButton > button {{ 
        background: linear-gradient(135deg, {COR_BOTAO} 0%, #056853 100%) !important; 
        color: white !important; 
        font-weight: 600 !important;
        border: none !important; 
        padding: 0.6em 1.2em !important; 
        border-radius: 8px !important; 
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }}

    div.stButton > button:hover, div.stFormSubmitButton > button:hover {{ 
        background: {COR_HOVER} !important; 
        color: #0e2d26 !important; 
        transform: translateY(-2px); 
        box-shadow: 0 6px 12px rgba(255, 215, 112, 0.3); 
    }}

    /* --- INPUTS --- */
    div[data-baseweb="input"] {{
        background-color: rgba(255, 255, 255, 0.05) !important; 
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
    }}
    input.st-ai {{ color: white !important; }}

    /* --- CARDS (GLASSMORPHISM + HOVER) --- */
    div[data-testid="stVerticalBlock"] div[data-testid="stContainer"] {{ 
        background: rgba(255, 255, 255, 0.03); 
        backdrop-filter: blur(10px); 
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.05); 
        border-radius: 16px; 
        padding: 20px; 
        transition: all 0.3s ease; 
    }}

    div[data-testid="stVerticalBlock"] div[data-testid="stContainer"]:hover {{ 
        transform: translateY(-5px); 
        border-color: rgba(255, 215, 112, 0.3); 
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.4); 
        background: rgba(255, 255, 255, 0.06); 
    }}

    /* Remove efeito hover do form de login */
    div[data-testid="stForm"] {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }}

</style>
""", unsafe_allow_html=True)

# Hack para Render/Railway
if "SECRETS_TOML" in os.environ:
    if not os.path.exists(".streamlit"): os.makedirs(".streamlit")
    with open(".streamlit/secrets.toml", "w") as f: f.write(os.environ["SECRETS_TOML"])

# Importações dos Módulos
try:
    from streamlit_option_menu import option_menu
    from views import login, geral, aluno, professor, admin
except ImportError as e:
    st.error(f"❌ Erro crítico na importação de módulos: {e}")
    st.stop()

# =========================================
# FUNÇÃO: TELA DE TROCA DE SENHA
# =========================================
def tela_troca_senha_obrigatoria():
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if os.path.exists("assets/logo.png"):
            cl, cc, cr = st.columns([1, 1, 1])
            with cc: st.image("assets/logo.png", use_container_width=True)
        
        st.write("") 
        
        with st.container(border=True):
            st.markdown("<h3 style='text-align:center;'>🔒 Troca de Senha</h3>", unsafe_allow_html=True)
            st.warning("Por segurança, redefina sua senha temporária para continuar.")
            
            with st.form("frm_troca"):
                ns = st.text_input("Nova Senha:", type="password")
                cs = st.text_input("Confirmar Nova Senha:", type="password")
                btn = st.form_submit_button("Atualizar Senha", use_container_width=True)
            
            if btn:
                if ns and ns == cs:
                    if not ns: st.error("A senha não pode ser vazia.")
                    else:
                        try:
                            uid = st.session_state.usuario['id']
                            hashed = bcrypt.hashpw(ns.encode(), bcrypt.gensalt()).decode()
                            db = get_db()
                            db.collection('usuarios').document(uid).update({
                                "senha": hashed, "precisa_trocar_senha": False
                            })
                            st.success("Senha atualizada! Entrando...")
                            st.session_state.usuario['precisa_trocar_senha'] = False
                            st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")
                else: st.error("As senhas não conferem.")

# =========================================
# APP PRINCIPAL (ESTRUTURA COMPLETA)
# =========================================
def app_principal():
    if "usuario" not in st.session_state or not st.session_state.usuario:
        st.error("Sessão perdida. Por favor, faça login novamente.")
        st.session_state.usuario = None
        st.rerun()
        return

    usuario_logado = st.session_state.usuario
    tipo_usuario = str(usuario_logado.get("tipo", "aluno")).lower()

    def ir_para(pagina): st.session_state.menu_selection = pagina

    # --- SIDEBAR ---
    with st.sidebar:
        if os.path.exists("assets/logo.png"): 
            st.image("assets/logo.png", use_container_width=True)
            
        st.markdown(f"<h3 style='color:{COR_DESTAQUE}; margin-bottom:0; font-size: 20px;'>{usuario_logado['nome'].split()[0].title()}</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:#aaa; text-align:center; font-size:12px; margin-top: -10px;'>Perfil: {tipo_usuario.capitalize()}</p>", unsafe_allow_html=True)
        
        st.markdown("---") 

        if st.button("👤 Meu Perfil", use_container_width=True): ir_para("Meu Perfil")

        if tipo_usuario in ["admin", "professor"]:
            if st.button("👩‍🏫 Painel Professor", use_container_width=True): ir_para("Painel do Professor")

        if tipo_usuario == "admin":
            if st.button("🔑 Gestão Usuários", use_container_width=True): ir_para("Gestão de Usuários")

        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True) 
        if st.button("🚪 Sair", use_container_width=True):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    # --- ROTEAMENTO ---
    if "menu_selection" not in st.session_state: st.session_state.menu_selection = "Início"
    pagina = st.session_state.menu_selection

    if pagina == "Meu Perfil":
        geral.tela_meu_perfil(usuario_logado)
        if st.button("⬅️ Voltar"): ir_para("Início")
    elif pagina == "Gestão de Usuários":
        admin.gestao_usuarios(usuario_logado)
        if st.button("⬅️ Voltar"): ir_para("Início")
    elif pagina == "Painel do Professor":
        professor.painel_professor()
        if st.button("⬅️ Voltar"): ir_para("Início")
        
    elif pagina == "Início":
        geral.tela_inicio()
        
    else:
        if tipo_usuario in ["admin", "professor"]:
            opcoes = ["Início", "Modo Rola", "Exame de Faixa", "Ranking", "Gestão de Questões", "Gestão de Equipes", "Gestão de Exame"]
            icons = ["house-fill", "people-fill", "journal-check", "trophy-fill", "cpu-fill", "building-fill", "file-earmark-check-fill"]
        else: 
            opcoes = ["Início", "Modo Rola", "Exame de Faixa", "Ranking", "Meus Certificados"]
            icons = ["house-fill", "people-fill", "journal-check", "trophy-fill", "patch-check-fill"]

        try: index_atual = opcoes.index(pagina)
        except ValueError: index_atual = 0

        menu = option_menu(
            menu_title=None, options=opcoes, icons=icons, default_index=index_atual, orientation="horizontal",
            styles={
                "container": {
                    "padding": "5px !important", 
                    "background-color": "rgba(0,0,0,0.2)", 
                    "border-radius": "10px"
                },
                "icon": {"color": COR_DESTAQUE, "font-size": "16px"},
                "nav-link": {
                    "font-size": "14px", 
                    "margin": "0px", 
                    "color": "white",
                    "border-radius": "5px"
                },
                "nav-link-selected": {
                    "background-color": COR_BOTAO, 
                    "color": "white", 
                    "border": f"1px solid {COR_DESTAQUE}"
                },
            }
        )

        if menu != pagina:
            st.session_state.menu_selection = menu
            st.rerun()

        if menu == "Início": geral.tela_inicio()
        elif menu == "Modo Rola": aluno.modo_rola(usuario_logado)
        elif menu == "Exame de Faixa": aluno.exame_de_faixa(usuario_logado)
        elif menu == "Ranking": aluno.ranking()
        elif menu == "Gestão de Equipes": professor.gestao_equipes()
        elif menu == "Gestão de Questões": admin.gestao_questoes()
        elif menu == "Gestão de Exame": admin.gestao_exame_de_faixa()
        elif menu == "Meus Certificados": aluno.meus_certificados(usuario_logado)

# =========================================
# START (MAIN)
# =========================================
if __name__ == "__main__":
    if "usuario" not in st.session_state: st.session_state.usuario = None
    if "token" not in st.session_state: st.session_state.token = None
    if "registration_pending" not in st.session_state: st.session_state.registration_pending = None

    try:
        if st.session_state.registration_pending:
            login.tela_completar_cadastro(st.session_state.registration_pending)
            
        elif st.session_state.usuario:
            if st.session_state.usuario.get("precisa_trocar_senha") is True:
                tela_troca_senha_obrigatoria()
            else:
                app_principal()
                
        else:
            login.tela_login()
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {e}")
