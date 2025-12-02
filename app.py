import streamlit as st
import os
import sys
import bcrypt 
from database import get_db

# =========================================================
# FUNÇÃO PARA ENCONTRAR O LOGO
# =========================================================
def get_logo_path():
    """Procura o logo na pasta assets ou na raiz."""
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
# 2. ESTILOS VISUAIS (CSS "DARK PREMIUM")
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

    /* --- BACKGROUND --- */
    .stApp {{
        background-color: {COR_FUNDO} !important;
        background-image: radial-gradient(circle at 50% 0%, #164036 0%, #0e2d26 70%) !important;
    }}
    
    /* --- LINHAS DIVISÓRIAS ELEGANTES --- */
    hr {{
        margin: 2em 0 !important;
        border: 0 !important;
        height: 1px !important;
        background-image: linear-gradient(to right, rgba(255, 255, 255, 0), rgba(255, 255, 255, 0.5), rgba(255, 255, 255, 0)) !important;
    }}

    /* --- TÍTULOS --- */
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
        box-shadow: 5px 0 15px rgba(0,0,0,0.3);
    }}
    /* Ícones da Sidebar */
    section[data-testid="stSidebar"] svg, [data-testid="collapsedControl"] svg {{
        fill: {COR_DESTAQUE} !important;
        color: {COR_DESTAQUE} !important;
    }}

    /* --- CONTAINERS E CARDS --- */
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
        box-shadow: 0 4px 12px rgba(255, 215, 112, 0.3);
    }}

    /* --- INPUTS --- */
    input, textarea, select, div[data-baseweb="select"] > div {{
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important; 
        border-radius: 8px !important;
    }}
    
    /* --- MENU SUPERIOR RESPONSIVO --- */
    /* Container do menu - SEM FUNDO PRETO */
    .st-emotion-cache-1v7f65g {{
        background: linear-gradient(135deg, rgba(14, 45, 38, 0.9) 0%, rgba(9, 31, 26, 0.9) 100%) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 215, 112, 0.15) !important;
        border-radius: 50px !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
        margin: 20px auto !important;
        max-width: 95% !important;
        width: auto !important;
        min-width: 300px !important;
        overflow: hidden !important;
        display: flex !important;
        flex-wrap: nowrap !important;
        white-space: nowrap !important;
        padding: 0 !important;
    }}
    
    /* Remover qualquer fundo preto dos elementos internos */
    .st-emotion-cache-1v7f65g .st-ae,
    .st-emotion-cache-1v7f65g .st-af,
    .st-emotion-cache-1v7f65g .st-ag,
    .st-emotion-cache-1v7f65g > div,
    .st-emotion-cache-1v7f65g > div > div {{
        background-color: transparent !important;
        background-image: none !important;
    }}
    
    /* Itens do menu */
    .st-emotion-cache-1v7f65g .st-ae .st-af {{
        background: transparent !important;
        color: rgba(255, 255, 255, 0.7) !important;
        border: 1px solid transparent !important;
        font-size: 14px !important;
        text-align: center !important;
        margin: 4px 2px !important;
        padding: 12px 20px !important;
        border-radius: 50px !important;
        font-weight: 500 !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        flex-shrink: 0 !important;
        white-space: nowrap !important;
    }}
    
    /* Itens do menu - hover */
    .st-emotion-cache-1v7f65g .st-ae .st-af:hover {{
        color: {COR_DESTAQUE} !important;
        background: rgba(255, 215, 112, 0.1) !important;
        border: 1px solid rgba(255, 215, 112, 0.3) !important;
        transform: translateY(-2px) !important;
    }}
    
    /* Item selecionado */
    .st-emotion-cache-1v7f65g .st-ae .st-ag {{
        background: linear-gradient(135deg, {COR_DESTAQUE} 0%, #ffedb3 100%) !important;
        color: {COR_FUNDO} !important;
        font-weight: 700 !important;
        box-shadow: 0 5px 20px rgba(255, 215, 112, 0.4) !important;
        border: none !important;
        animation: pulse 2s infinite !important;
    }}
    
    /* Scrollbar personalizada para telas pequenas */
    .st-emotion-cache-1v7f65g > div > div {{
        overflow-x: auto !important;
        overflow-y: hidden !important;
        scrollbar-width: thin !important;
        scrollbar-color: rgba(255, 215, 112, 0.3) rgba(9, 31, 26, 0.1) !important;
        padding: 4px 8px !important;
    }}
    
    .st-emotion-cache-1v7f65g > div > div::-webkit-scrollbar {{
        height: 6px !important;
    }}
    
    .st-emotion-cache-1v7f65g > div > div::-webkit-scrollbar-track {{
        background: rgba(9, 31, 26, 0.1) !important;
        border-radius: 10px !important;
        margin: 0 20px !important;
    }}
    
    .st-emotion-cache-1v7f65g > div > div::-webkit-scrollbar-thumb {{
        background: rgba(255, 215, 112, 0.3) !important;
        border-radius: 10px !important;
    }}
    
    /* Ícones do menu */
    .st-emotion-cache-1v7f65g .st-ae .st-af i {{
        color: inherit !important;
        font-size: 16px !important;
        margin-right: 8px !important;
        transition: all 0.3s ease !important;
    }}
    
    .st-emotion-cache-1v7f65g .st-ae .st-ag i {{
        filter: drop-shadow(0 2px 3px rgba(0,0,0,0.2)) !important;
    }}
    
    /* Responsividade */
    @media (max-width: 1024px) {{
        .st-emotion-cache-1v7f65g .st-ae .st-af {{
            padding: 10px 15px !important;
            font-size: 13px !important;
        }}
    }}
    
    @media (max-width: 768px) {{
        .st-emotion-cache-1v7f65g .st-ae .st-af {{
            padding: 8px 12px !important;
            font-size: 12px !important;
        }}
        
        .st-emotion-cache-1v7f65g .st-ae .st-af i {{
            font-size: 14px !important;
            margin-right: 5px !important;
        }}
        
        .st-emotion-cache-1v7f65g {{
            max-width: 98% !important;
            border-radius: 30px !important;
        }}
    }}
    
    @media (max-width: 576px) {{
        .st-emotion-cache-1v7f65g .st-ae .st-af span {{
            display: none !important;
        }}
        
        .st-emotion-cache-1v7f65g .st-ae .st-af {{
            padding: 10px 15px !important;
            min-width: 50px !important;
        }}
        
        .st-emotion-cache-1v7f65g .st-ae .st-af i {{
            margin-right: 0 !important;
            font-size: 16px !important;
        }}
        
        .st-emotion-cache-1v7f65g {{
            border-radius: 25px !important;
            padding: 2px !important;
        }}
    }}
    
    @media (max-width: 360px) {{
        .st-emotion-cache-1v7f65g .st-ae .st-af {{
            padding: 8px 10px !important;
            min-width: 45px !important;
        }}
        
        .st-emotion-cache-1v7f65g .st-ae .st-af i {{
            font-size: 14px !important;
        }}
    }}
    
    @keyframes pulse {{
        0% {{ box-shadow: 0 5px 20px rgba(255, 215, 112, 0.4); }}
        50% {{ box-shadow: 0 5px 25px rgba(255, 215, 112, 0.6); }}
        100% {{ box-shadow: 0 5px 20px rgba(255, 215, 112, 0.4); }}
    }}
    
    /* REMOVE MARGENS PADRÃO DO STREAMLIT */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    [data-testid="stDecoration"] {{display: none;}}
    .block-container {{padding-top: 1rem !important;}}

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
    st.error(f"❌ Erro crítico nas importações: {e}")
    st.stop()

# =========================================
# TELA DE TROCA DE SENHA
# =========================================
def tela_troca_senha_obrigatoria():
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if logo_file:
            cl, cc, cr = st.columns([1, 1, 1])
            with cc: st.image(logo_file, use_container_width=True)
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

    def nav(pg): st.session_state.menu_selection = pg

    # SIDEBAR
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

    # Roteamento Sidebar
    if pg == "Meu Perfil": geral.tela_meu_perfil(usuario); return
    if pg == "Gestão de Usuários": admin.gestao_usuarios(usuario); return
    if pg == "Painel do Professor": professor.painel_professor(); return
    if pg == "Meus Certificados": aluno.meus_certificados(usuario); return 
    if pg == "Início": geral.tela_inicio(); return

    # MENU HORIZONTAL PRINCIPAL (RESPONSIVO)
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
    # MENU SUPERIOR MODERNO E RESPONSIVO
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
                "margin": "0 auto",
                "display": "flex",
                "justify-content": "center",
                "max-width": "100%"
            },
            "icon": {
                "color": "inherit",
                "font-size": "16px",
                "margin-right": "8px",
                "transition": "all 0.3s ease"
            },
            "nav-link": {
                "font-size": "14px",
                "text-align": "center",
                "margin": "4px 2px",
                "padding": "12px 20px",
                "border-radius": "50px",
                "color": "rgba(255, 255, 255, 0.7)",
                "font-weight": "500",
                "background": "transparent",
                "transition": "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
                "border": "1px solid transparent",
                "display": "flex",
                "align-items": "center",
                "justify-content": "center",
                "flex-shrink": "0",
                "white-space": "nowrap",
                "min-width": "fit-content"
            },
            "nav-link:hover": {
                "color": COR_DESTAQUE,
                "background": "rgba(255, 215, 112, 0.1)",
                "border": f"1px solid rgba(255, 215, 112, 0.3)",
                "transform": "translateY(-2px)"
            },
            "nav-link-selected": {
                "background": f"linear-gradient(135deg, {COR_DESTAQUE} 0%, #ffedb3 100%)",
                "color": COR_FUNDO,
                "font-weight": "700",
                "box-shadow": "0 5px 20px rgba(255, 215, 112, 0.4)",
                "border": "none",
                "position": "relative"
            }
        }
    )

    if menu != pg:
        if pg == "Meus Certificados" and menu == "Início": pass 
        else:
            st.session_state.menu_selection = menu
            st.rerun()

    # Navegação das páginas
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
