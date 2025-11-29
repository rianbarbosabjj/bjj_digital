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
    page_icon="assets/logo.png", 
    layout="wide",
    initial_sidebar_state="expanded" 
)

# =========================================================
# 2. ESTILOS VISUAIS (CORREÇÃO DE MENU E MOLDURAS)
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

    /* --- FORÇAR TEXTO BRANCO EM TUDO --- */
    html, body, [class*="css"], .stMarkdown, .stMarkdown p, .stText, label, .stCaption, h1, h2, h3, h4, h5, h6 {{
        font-family: 'Poppins', sans-serif;
        color: {COR_TEXTO} !important;
    }}
    
    /* Exceção: Inputs devem ter texto escuro ou visível */
    input, textarea, select {{
        color: #333 !important;
    }}

    /* --- CORREÇÃO MENU MOBILE --- */
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

    /* --- BACKGROUND E SIDEBAR --- */
    .stApp {{
        background-color: {COR_FUNDO} !important;
    }}
    section[data-testid="stSidebar"] {{
        background-color: #091f1a !important; 
        border-right: 1px solid rgba(255, 215, 112, 0.1);
    }}

    /* --- TÍTULOS --- */
    h1, h2, h3 {{ 
        color: {COR_DESTAQUE} !important; 
        text-align: center; 
        font-weight: 700; 
        text-transform: uppercase;
    }}

    /* --- BOTÕES --- */
    div.stButton > button, div.stFormSubmitButton > button {{ 
        background: linear-gradient(135deg, {COR_BOTAO} 0%, #056853 100%) !important; 
        color: white !important; 
        border: 1px solid rgba(255,255,255,0.1) !important; 
        padding: 0.6em 1.2em !important; 
        border-radius: 8px !important; 
    }}
    div.stButton > button:hover {{ 
        background: {COR_HOVER} !important; 
        color: #0e2d26 !important; 
        border-color: {COR_DESTAQUE} !important;
    }}

    /* --- MOLDURAS (CARDS) CORRIGIDAS --- */
    div[data-testid="stVerticalBlock"] div[data-testid="stContainer"] {{ 
        background-color: rgba(0, 0, 0, 0.2) !important; /* Fundo escuro translúcido */
        border: 1px solid rgba(255, 215, 112, 0.15) !important; /* Borda dourada sutil */
        border-radius: 12px; 
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }}
    
    /* Correção específica para Metrics (números grandes) */
    [data-testid="stMetricValue"] {{
        color: {COR_DESTAQUE} !important;
    }}
    [data-testid="stMetricLabel"] {{
        color: #ccc !important;
    }}

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
        if os.path.exists("assets/logo.png"):
            cl, cc, cr = st.columns([1, 1, 1])
            with cc: st.image("assets/logo.png", use_container_width=True)
        st.write("") 
        with st.container(border=True):
            st.markdown("<h3 style='text-align:center;'>🔒 Troca de Senha</h3>", unsafe_allow_html=True)
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
        if os.path.exists("assets/logo.png"): st.image("assets/logo.png", use_container_width=True)
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

    # Roteamento Sidebar
    if pg == "Meu Perfil": geral.tela_meu_perfil(usuario); return
    if pg == "Gestão de Usuários": admin.gestao_usuarios(usuario); return
    if pg == "Painel do Professor": professor.painel_professor(); return
    if pg == "Início": geral.tela_inicio(); return

    # MENU HORIZONTAL (CONFIGURAÇÃO DE ESTILO AQUI)
    ops, icns = [], []
    if tipo in ["admin", "professor"]:
        ops = ["Início", "Modo Rola", "Exame de Faixa", "Ranking", "Gestão de Questões", "Gestão de Equipes", "Gestão de Exame"]
        icns = ["house", "people", "journal", "trophy", "list-task", "building", "file-earmark"]
    else:
        ops = ["Início", "Modo Rola", "Exame de Faixa", "Ranking", "Meus Certificados"]
        icns = ["house", "people", "journal", "trophy", "award"]

    try: idx = ops.index(pg)
    except: idx = 0
    
    # --- AQUI ESTÁ A CORREÇÃO DO MENU ---
    menu = option_menu(
        menu_title=None, 
        options=ops, 
        icons=icns, 
        default_index=idx, 
        orientation="horizontal",
        styles={
            "container": {"padding": "5px", "background-color": "#0e2d26"}, # Fundo Verde Escuro
            "icon": {"color": COR_DESTAQUE, "font-size": "16px"},
            "nav-link": {
                "font-size": "14px", 
                "text-align": "center", 
                "margin": "0px", 
                "color": "white" # Texto Branco
            },
            "nav-link-selected": {
                "background-color": COR_DESTAQUE, # Selecionado Dourado
                "color": "#0e2d26", # Texto do selecionado Escuro (contraste)
                "font-weight": "bold"
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
