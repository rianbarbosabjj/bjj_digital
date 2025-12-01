import streamlit as st
import os
import sys
import bcrypt 
from database import get_db

# =========================================================
# 1. CONFIGURAÇÃO
# =========================================================
st.set_page_config(
    page_title="BJJ Digital", 
    page_icon="assets/logo.jpg", 
    layout="wide",
    initial_sidebar_state="expanded" 
)

# =========================================================
# 2. ESTILOS VISUAIS (CSS "DARK PREMIUM" FORÇADO)
# =========================================================
try:
    from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
except ImportError:
    COR_FUNDO = "#0e2d26"
    COR_TEXTO = "#FFFFFF"
    COR_DESTAQUE = "#FFD770"
    COR_BOTAO = "#078B6C"
    COR_HOVER = "#FFD770"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');

    /* --- GLOBAL: TEXTO BRANCO E FONTE --- */
    html, body, [class*="css"], .stMarkdown, p, label, .stCaption, span, h1, h2, h3, h4, h5, h6 {{
        font-family: 'Poppins', sans-serif;
        color: {COR_TEXTO} !important;
    }}

    /* --- BACKGROUND --- */
    .stApp {{
        background-color: {COR_FUNDO} !important;
        background-image: radial-gradient(circle at 50% 0%, #164036 0%, #0e2d26 70%);
    }}
    
    /* --- CORREÇÃO DAS LINHAS (DIVISÓRIAS) --- */
    hr {{
        margin: 2em 0 !important;
        border: 0 !important;
        border-top: 1px solid rgba(255, 255, 255, 0.3) !important;
        opacity: 1 !important;
    }}

    /* --- TÍTULOS CENTRALIZADOS --- */
    h1, h2, h3, h4, h5, h6 {{ 
        color: {COR_DESTAQUE} !important; 
        text-align: center !important; 
        font-weight: 700 !important; 
        text-transform: uppercase;
        width: 100%; 
    }}

    /* --- SIDEBAR --- */
    section[data-testid="stSidebar"] {{
        background-color: #091f1a !important; 
        border-right: 1px solid rgba(255, 215, 112, 0.2);
        box-shadow: 4px 0 15px rgba(0,0,0,0.3);
    }}
    section[data-testid="stSidebar"] svg, [data-testid="collapsedControl"] svg {{
        fill: {COR_DESTAQUE} !important;
        color: {COR_DESTAQUE} !important;
    }}

    /* --- MOLDURAS E CARDS (CONTAINERS) --- */
    div[data-testid="stVerticalBlock"] > div[data-testid="stContainer"], 
    div[data-testid="stForm"] {{
        background-color: rgba(0, 0, 0, 0.4) !important; 
        border: 2px solid rgba(255, 215, 112, 0.25) !important; 
        border-radius: 16px; 
        padding: 25px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.4); 
        margin-bottom: 20px;
    }}
    
    /* --- EXPANDER (ACORDEÃO) --- */
    .streamlit-expanderHeader {{
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: {COR_DESTAQUE} !important;
        border: 1px solid {COR_DESTAQUE} !important;
        border-radius: 8px;
    }}
    .streamlit-expanderHeader svg {{
        fill: {COR_TEXTO} !important; 
        color: {COR_TEXTO} !important;
    }}

    /* --- BOTÕES --- */
    div.stButton > button, div.stFormSubmitButton > button {{ 
        background: linear-gradient(135deg, {COR_BOTAO} 0%, #056853 100%) !important; 
        color: white !important; 
        border: 1px solid rgba(255,255,255,0.2) !important; 
        padding: 0.7em 1.5em !important; 
        font-weight: bold !important;
        border-radius: 10px !important; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        width: 100%; 
    }}
    div.stButton > button:hover {{ 
        background: {COR_HOVER} !important; 
        color: #0e2d26 !important; 
        border-color: {COR_DESTAQUE} !important;
        transform: translateY(-2px);
    }}

    /* --- INPUTS --- */
    input, textarea, select, div[data-baseweb="select"] > div {{
        background-color: #1a3b32 !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important; 
    }}
    .stTextInput input, .stTextArea textarea {{
        color: white !important;
    }}

    /* --- MENU DE CIMA --- */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    [data-testid="stDecoration"] {{display: none;}}
    header[data-testid="stHeader"] {{ background-color: transparent !important; z-index: 1; }}

</style>
""", unsafe_allow_html=True)

# Hack para Render/Railway
if "SECRETS_TOML" in os.environ:
    if not os.path.exists(".streamlit"): os.makedirs(".streamlit")
    with open(".streamlit/secrets.toml", "w") as f: f.write(os.environ["SECRETS_TOML"])

# Importações
try:
    from streamlit_option_menu import option_menu
    from views import login, geral, aluno, professor, admin
except ImportError as e:
    st.error(f"❌ Erro crítico: {e}")
    st.stop()

# =========================================
# TELA DE TROCA DE SENHA
# =========================================
def tela_troca_senha_obrigatoria():
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if os.path.exists("assets/logo.jpg"):
            cl, cc, cr = st.columns([1, 1, 1])
            with cc: st.image("assets/logo.jpg", use_container_width=True)
        st.write("") 
        with st.container(border=True):
            st.markdown("<h3>🔒 Troca de Senha</h3>", unsafe_allow_html=True)
            st.warning("Por segurança, redefina sua senha.")
            with st.form("frm_troca"):
                ns = st.text_input("Nova Senha:", type="password")
                cs = st.text_input("Confirmar:", type="password")
                if st.form_submit_button("Atualizar", use_container_width=True):
                    if ns and ns == cs:
                        try:
                            uid = st.session_state.usuario['id']
                            hashed = bcrypt.hashpw(ns.encode(), bcrypt.gensalt()).decode()
                            db = get_db()
                            db.collection('usuarios').document(uid).update({"senha": hashed, "precisa_trocar_senha": False})
                            st.success("Sucesso! Entrando..."); st.session_state.usuario['precisa_trocar_senha'] = False; st.rerun()
                        except: st.error("Erro ao salvar.")
                    else: st.error("Senhas não conferem.")

# =========================================
# APP PRINCIPAL
# =========================================
def app_principal():
    if not st.session_state.get('usuario'):
        st.session_state.clear(); st.rerun(); return

    usuario = st.session_state.usuario
    tipo = str(usuario.get("tipo", "aluno")).lower()

    # SIDEBAR
    with st.sidebar:
        if os.path.exists("assets/logo.jpg"): st.image("assets/logo.jpg", use_container_width=True)
        st.markdown(f"<h3 style='color:{COR_DESTAQUE}; margin:0;'>{usuario['nome'].split()[0]}</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align:center; color:#aaa;'>{tipo.capitalize()}</p>", unsafe_allow_html=True)
        st.markdown("---")
        
        def nav(pg): st.session_state.menu_selection = pg
        if st.button("👤 Meu Perfil", use_container_width=True): nav("Meu Perfil")
        if tipo in ["admin", "professor"]:
            if st.button("👩‍🏫 Painel Prof.", use_container_width=True): nav("Painel do Professor")
        if tipo == "admin":
            if st.button("🔑 Gestão Usuários", use_container_width=True): nav("Gestão de Usuários")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.clear(); st.rerun()

    if "menu_selection" not in st.session_state: st.session_state.menu_selection = "Início"
    pg = st.session_state.menu_selection

    # Roteamento Sidebar (prioritário)
    if pg == "Meu Perfil": geral.tela_meu_perfil(usuario); return
    if pg == "Gestão de Usuários": admin.gestao_usuarios(usuario); return
    if pg == "Painel do Professor": professor.painel_professor(); return
    if pg == "Início": geral.tela_inicio(); return

    # MENU HORIZONTAL
    ops, icns = [], []
    if tipo in ["admin", "professor"]:
        ops = ["Início", "Modo Rola", "Exame de Faixa", "Ranking", "Gestão de Questões", "Gestão de Equipes", "Gestão de Exame"]
        icns = ["house", "people", "journal", "trophy", "list-task", "building", "file-earmark"]
    else:
        ops = ["Início", "Modo Rola", "Exame de Faixa", "Ranking", "Meus Certificados"]
        icns = ["house", "people", "journal", "trophy", "award"]

    try: idx = ops.index(pg)
    except: idx = 0
    
    # -------------------------------------------------------------
    # MENU SÓLIDO (COR DO FUNDO) COM BORDA DOURADA
    # -------------------------------------------------------------
    menu = option_menu(
        menu_title=None, 
        options=ops, 
        icons=icns, 
        default_index=idx, 
        orientation="horizontal",
        styles={
            "container": {
                "padding": "5px", 
                # Fundo Sólido (Cor da Página)
                "background-color": COR_FUNDO, 
                # Bordas arredondadas e Douradas
                "border-radius": "16px",
                "border": f"1px solid {COR_DESTAQUE}", 
                # Sombra suave
                "box-shadow": "0 4px 15px rgba(0, 0, 0, 0.3)"
            },
            "icon": {
                "color": COR_DESTAQUE, 
                "font-size": "16px",
                "font-weight": "bold"
            },
            "nav-link": {
                "font-size": "14px", 
                "text-align": "center", 
                "margin": "0px 4px", 
                "color": "white",
                "border-radius": "8px"
            },
            "nav-link-selected": {
                # Dourado Sutil no fundo do item selecionado
                "background-color": "rgba(255, 215, 112, 0.2)", 
                "color": COR_DESTAQUE, 
                "font-weight": "800",
                "border": f"1px solid {COR_DESTAQUE}",
                "box-shadow": "0 0 10px rgba(255, 215, 112, 0.3)"
            },
        }
    )

    if menu != pg: st.session_state.menu_selection = menu; st.rerun()

    if menu == "Início": geral.tela_inicio()
    elif menu == "Modo Rola": aluno.modo_rola(usuario)
    elif menu == "Exame de Faixa": aluno.exame_de_faixa(usuario)
    elif menu == "Ranking": aluno.ranking()
    elif menu == "Gestão de Equipes": professor.gestao_equipes()
    elif menu == "Gestão de Questões": admin.gestao_questoes()
    elif menu == "Gestão de Exame": admin.gestao_exame_de_faixa()
    elif menu == "Meus Certificados": aluno.meus_certificados(usuario)

if __name__ == "__main__":
    if not st.session_state.get('usuario') and not st.session_state.get('registration_pending'):
        login.tela_login()
    elif st.session_state.get('registration_pending'):
        login.tela_completar_cadastro(st.session_state.registration_pending)
    elif st.session_state.get('usuario'):
        if st.session_state.usuario.get("precisa_trocar_senha"): tela_troca_senha_obrigatoria()
        else: app_principal()
