import streamlit as st
import os
import sys
import bcrypt 
from database import get_db

# =========================================================
# FUNÇÃO PARA ENCONTRAR O LOGO
# =========================================================
def get_logo_path():
    if os.path.exists("assets/logo.jpg"): return "assets/logo.jpg"
    if os.path.exists("logo.jpg"): return "logo.jpg"
    if os.path.exists("assets/logo.png"): return "assets/logo.png"
    if os.path.exists("logo.png"): return "logo.png"
    return None

logo_file = get_logo_path()

# =========================================================
# 1. CONFIGURAÇÃO
# =========================================================
st.set_page_config(
    page_title="BJJ Digital", 
    page_icon=logo_file, 
    layout="wide",
    initial_sidebar_state="expanded" 
)

# =========================================================
# 2. ESTILOS VISUAIS (CSS "DARK PREMIUM" - MENU FLUTUANTE)
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

    /* --- GLOBAL --- */
    html, body, [class*="css"], .stMarkdown, p, label, .stCaption, span {{
        font-family: 'Poppins', sans-serif;
        color: {COR_TEXTO} !important;
    }}

    .stApp {{
        background-color: {COR_FUNDO} !important;
        background-image: radial-gradient(circle at 50% 0%, #164036 0%, #0e2d26 70%) !important;
    }}
    
    hr {{
        margin: 2em 0 !important;
        border: 0 !important;
        height: 1px !important;
        background-image: linear-gradient(to right, rgba(255, 255, 255, 0), rgba(255, 255, 255, 0.5), rgba(255, 255, 255, 0)) !important;
    }}

    h1, h2, h3, h4, h5, h6 {{ 
        color: {COR_DESTAQUE} !important; 
        text-align: center !important; 
        font-weight: 700 !important; 
        text-transform: uppercase;
        letter-spacing: 1px;
    }}

    /* --- SIDEBAR --- */
    section[data-testid="stSidebar"] {{
        background-color: #091f1a !important; 
        border-right: 1px solid rgba(255, 215, 112, 0.15);
    }}
    
    section[data-testid="stSidebar"] svg {{
        fill: {COR_DESTAQUE} !important;
        color: {COR_DESTAQUE} !important;
    }}

    /* --- BOTÃO SIDEBAR (SAFE MODE) --- */
    [data-testid="stSidebarCollapsedControl"] {{
        color: {COR_DESTAQUE} !important;
    }}
    [data-testid="stSidebarCollapsedControl"] button {{
        background-color: rgba(0,0,0,0.2) !important;
        color: {COR_DESTAQUE} !important;
    }}
    [data-testid="stSidebarCollapsedControl"] button:hover {{
        background-color: {COR_HOVER} !important;
        color: {COR_FUNDO} !important;
    }}

    /* --- CARDS & CONTAINERS --- */
    div[data-testid="stVerticalBlock"] > div[data-testid="stContainer"], 
    div[data-testid="stForm"] {{
        background-color: rgba(0, 0, 0, 0.3) !important; 
        border: 1px solid rgba(255, 215, 112, 0.2) !important; 
        border-radius: 12px; 
        padding: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2); 
        margin-bottom: 20px;
    }}
    
    /* --- BOTÕES --- */
    div.stButton > button, div.stFormSubmitButton > button {{ 
        background: linear-gradient(135deg, {COR_BOTAO} 0%, #056853 100%) !important; 
        color: white !important; 
        border: 1px solid rgba(255,255,255,0.1) !important; 
        padding: 0.6em 1.5em !important; 
        font-weight: 600 !important;
        border-radius: 8px !important; 
        transition: all 0.3s ease !important;
    }}
    div.stButton > button:hover {{ 
        background: {COR_HOVER} !important; 
        color: #0e2d26 !important; 
        transform: translateY(-2px);
    }}

    /* --- INPUTS --- */
    input, textarea, select, div[data-baseweb="select"] > div {{
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important; 
        border-radius: 8px !important;
    }}
    
    /* --- NOVO MENU FLUTUANTE (PREMIUM) --- */
    
    /* CONTAINER DO MENU */
    .st-emotion-cache-1v7f65g {{
        background: rgba(14, 45, 38, 0.9) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 215, 112, 0.2) !important;
        border-radius: 12px !important;
        padding: 8px !important;
        margin: 10px auto 30px auto !important;
        max-width: 95% !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
        display: flex !important;
        justify-content: center !important;
        flex-wrap: nowrap !important;
        overflow-x: auto !important;
    }}
    
    /* ITENS DO MENU */
    .st-emotion-cache-1v7f65g .st-ae .st-af {{
        padding: 10px 20px !important;
        border-radius: 8px !important;
        margin: 0 4px !important;
        transition: all 0.3s ease !important;
        position: relative !important;
        overflow: hidden !important;
        white-space: nowrap !important;
    }}
    
    /* ITEM NORMAL */
    .st-emotion-cache-1v7f65g .st-ae .st-af:not(.st-ag) {{
        background: transparent !important;
        color: rgba(255, 255, 255, 0.7) !important;
        border: 1px solid transparent !important;
    }}
    
    /* ITEM NORMAL HOVER */
    .st-emotion-cache-1v7f65g .st-ae .st-af:not(.st-ag):hover {{
        color: {COR_DESTAQUE} !important;
        background: rgba(255, 215, 112, 0.1) !important;
        border: 1px solid rgba(255, 215, 112, 0.3) !important;
        transform: translateY(-2px) !important;
    }}
    
    /* ITEM SELECIONADO */
    .st-emotion-cache-1v7f65g .st-ae .st-ag {{
        background: linear-gradient(135deg, {COR_DESTAQUE} 0%, #ffedb3 100%) !important;
        color: {COR_FUNDO} !important;
        font-weight: 700 !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(255, 215, 112, 0.4) !important;
        position: relative !important;
    }}
    
    /* EFEITO BRILHO NO ITEM SELECIONADO */
    .st-emotion-cache-1v7f65g .st-ae .st-ag::before {{
        content: '';
        position: absolute;
        top: -2px;
        left: -2px;
        right: -2px;
        bottom: -2px;
        background: linear-gradient(45deg, {COR_DESTAQUE}, transparent, {COR_DESTAQUE});
        z-index: -1;
        border-radius: 10px;
        animation: pulse-glow 2s infinite;
    }}
    
    /* ÍCONES */
    .st-emotion-cache-1v7f65g .st-ae svg {{
        color: inherit !important;
        filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
    }}
    
    @keyframes pulse-glow {{
        0%, 100% {{ opacity: 0.7; }}
        50% {{ opacity: 1; }}
    }}
    
    /* Scrollbar do menu para mobile */
    .st-emotion-cache-1v7f65g > div > div::-webkit-scrollbar {{
        height: 4px;
    }}
    .st-emotion-cache-1v7f65g > div > div::-webkit-scrollbar-thumb {{
        background: {COR_DESTAQUE};
        border-radius: 10px;
    }}

    /* --- REMOVE PADDING EXTRA --- */
    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}} header {{visibility: hidden;}}
    .block-container {{padding-top: 1.5rem !important;}}

</style>
""", unsafe_allow_html=True)

if "SECRETS_TOML" in os.environ:
    if not os.path.exists(".streamlit"): os.makedirs(".streamlit")
    with open(".streamlit/secrets.toml", "w") as f: f.write(os.environ["SECRETS_TOML"])

try:
    from streamlit_option_menu import option_menu
    from views import login, geral, aluno, professor, admin, dashboard
except ImportError as e:
    st.error(f"❌ Erro crítico nas importações: {e}")
    st.stop()

def tela_troca_senha_obrigatoria():
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.container(border=True):
            st.markdown("<h3>🔒 Troca de Senha</h3>", unsafe_allow_html=True)
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
                            st.success("Sucesso!"); st.session_state.usuario['precisa_trocar_senha'] = False; st.rerun()
                        except: st.error("Erro.")
                    else: st.error("Senhas não conferem.")

def app_principal():
    if not st.session_state.get('usuario'):
        st.session_state.clear(); st.rerun(); return

    usuario = st.session_state.usuario
    tipo = str(usuario.get("tipo", "aluno")).lower()

    def nav(pg): st.session_state.menu_selection = pg

    with st.sidebar:
        if logo_file: st.image(logo_file, use_container_width=True)
        st.markdown(f"<h3 style='color:{COR_DESTAQUE}; margin:0;'>{usuario['nome'].split()[0]}</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align:center; color:#aaa; font-size: 0.9em;'>{tipo.capitalize()}</p>", unsafe_allow_html=True)
        st.markdown("---")
        
        if st.button("👤 Meu Perfil", use_container_width=True): nav("Meu Perfil")
        if tipo != "admin":
            if st.button("🏅 Meus Certificados", use_container_width=True): nav("Meus Certificados")
        if tipo in ["admin", "professor"]:
            if st.button("👩‍🏫 Painel Prof.", use_container_width=True): nav("Painel do Professor")
        if tipo == "admin":
            if st.button("🔑 Gestão Usuários", use_container_width=True): nav("Gestão de Usuários")
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.clear(); st.rerun()

    if "menu_selection" not in st.session_state: st.session_state.menu_selection = "Início"
    pg = st.session_state.menu_selection

    if pg == "Meu Perfil": geral.tela_meu_perfil(usuario); return
    if pg == "Gestão de Usuários": admin.gestao_usuarios(usuario); return
    if pg == "Painel do Professor": professor.painel_professor(); return
    if pg == "Meus Certificados": aluno.meus_certificados(usuario); return 
    if pg == "Início": geral.tela_inicio(); return

    ops, icns = [], []
    if tipo in ["admin", "professor"]:
        ops = ["Início", "Modo Rola", "Exame de Faixa", "Ranking", "Gestão de Questões", "Gestão de Equipes", "Gestão de Exame"]
        icns = ["house", "people", "journal", "trophy", "list-task", "building", "file-earmark"]
    else:
        ops = ["Início", "Modo Rola", "Exame de Faixa", "Ranking"]
        icns = ["house", "people", "journal", "trophy"]

    try: idx = ops.index(pg)
    except: idx = 0
    
    # -------------------------------------------------------------
    # MENU SUPERIOR - NOVO DESIGN "PREMIUM FLOATING"
    # -------------------------------------------------------------
    menu = option_menu(
        menu_title=None, 
        options=ops, 
        icons=icns, 
        default_index=idx, 
        orientation="horizontal",
        styles={
            "container": {
                "padding": "0!important", 
                "background-color": "transparent",
                "border": "none",
                "display": "flex",
                "justify-content": "center"
            },
            "icon": {
                "color": "inherit", 
                "font-size": "18px",
                "margin-right": "8px"
            }, 
            "nav-link": {
                "font-size": "14px", 
                "text-align": "center", 
                "margin": "0px 4px", 
                "padding": "12px 20px",
                "border-radius": "8px",
                "color": "rgba(255, 255, 255, 0.7)",
                "font-weight": "500",
                "background": "transparent",
                "transition": "all 0.3s ease",
                "display": "flex",
                "align-items": "center",
                "justify-content": "center",
                "white-space": "nowrap",
                "min-width": "fit-content"
            },
            "nav-link-selected": {
                "background": f"linear-gradient(135deg, {COR_DESTAQUE} 0%, #ffedb3 100%)",
                "color": COR_FUNDO,
                "font-weight": "700",
                "box-shadow": "0 4px 15px rgba(255, 215, 112, 0.4)",
                "border": "none",
                "position": "relative"
            },
        }
    )

    if menu != pg:
        if pg == "Meus Certificados" and menu == "Início": pass 
        else:
            st.session_state.menu_selection = menu
            st.rerun()

    if pg == "Modo Rola": aluno.modo_rola(usuario)
    elif pg == "Exame de Faixa": aluno.exame_de_faixa(usuario)
    elif pg == "Ranking": aluno.ranking()
    elif pg == "Gestão de Equipes": professor.gestao_equipes()
    elif pg == "Gestão de Questões": admin.gestao_questoes()
    elif pg == "Gestão de Exame": admin.gestao_exame_de_faixa()

if __name__ == "__main__":
    if not st.session_state.get('usuario') and not st.session_state.get('registration_pending'):
        login.tela_login()
    elif st.session_state.get('registration_pending'):
        login.tela_completar_cadastro(st.session_state.registration_pending)
    elif st.session_state.get('usuario'):
        if st.session_state.usuario.get("precisa_trocar_senha"): tela_troca_senha_obrigatoria()
        else: app_principal()
