import streamlit as st
import os
import sys
import bcrypt 
from database import get_db

def get_logo_path():
    if os.path.exists("assets/logo.jpg"): return "assets/logo.jpg"
    if os.path.exists("logo.jpg"): return "logo.jpg"
    if os.path.exists("assets/logo.png"): return "assets/logo.png"
    if os.path.exists("logo.png"): return "logo.png"
    return None

logo_file = get_logo_path()

st.set_page_config(
    page_title="BJJ Digital", 
    page_icon=logo_file, 
    layout="wide",
    initial_sidebar_state="expanded" 
)

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

    /* --- ESTILO DO RADIO BUTTON (Dourado) --- */
    div.stRadio > div[role="radiogroup"] > label > div:first-child {{
        border-color: {COR_DESTAQUE} !important;
        background-color: transparent !important;
    }}
    div.stRadio > div[role="radiogroup"] > label > div:first-child > div {{
        background-color: {COR_DESTAQUE} !important;
    }}
    /* --------------------------------------- */

    h1, h2, h3, h4, h5, h6 {{ 
        color: {COR_DESTAQUE} !important; 
        text-align: center !important; 
        font-weight: 700 !important; 
        text-transform: uppercase;
        letter-spacing: 1px;
    }}

    section[data-testid="stSidebar"] {{
        background-color: #091f1a !important; 
        border-right: 1px solid rgba(255, 215, 112, 0.15);
        box-shadow: 5px 0 15px rgba(0,0,0,0.3);
    }}
    section[data-testid="stSidebar"] svg, [data-testid="collapsedControl"] svg {{
        fill: {COR_DESTAQUE} !important;
        color: {COR_DESTAQUE} !important;
    }}

    div[data-testid="stVerticalBlock"] > div[data-testid="stContainer"], 
    div[data-testid="stForm"] {{
        background-color: rgba(0, 0, 0, 0.3) !important; 
        border: 1px solid rgba(255, 215, 112, 0.2) !important; 
        border-radius: 12px; 
        padding: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2); 
        margin-bottom: 20px;
    }}
    
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

    input, textarea, select, div[data-baseweb="select"] > div {{
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important; 
        border-radius: 8px !important;
    }}
    .stTextInput input, .stTextArea textarea {{ color: white !important; }}
    
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    [data-testid="stDecoration"] {{display: none;}}
    header[data-testid="stHeader"] {{ background-color: transparent !important; z-index: 1; }}

</style>
""", unsafe_allow_html=True)

if "SECRETS_TOML" in os.environ:
    if not os.path.exists(".streamlit"): os.makedirs(".streamlit")
    with open(".streamlit/secrets.toml", "w") as f: f.write(os.environ["SECRETS_TOML"])

try:
    from streamlit_option_menu import option_menu
    from views import login, geral, aluno, professor, admin
except ImportError as e:
    st.error(f"❌ Erro crítico nas importações: {e}")
    st.stop()

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
            if st.button("🥋 Painel Prof.", use_container_width=True): nav("Painel do Professor")
        if tipo == "admin":
            # --- MUDANÇA AQUI: Botão renomeado ---
            if st.button("📊 Gestão e Estatísticas", use_container_width=True): nav("Gestão e Estatísticas")
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.clear(); st.rerun()

    if "menu_selection" not in st.session_state: st.session_state.menu_selection = "Início"
    pg = st.session_state.menu_selection

    if pg == "Meu Perfil": geral.tela_meu_perfil(usuario); return
    # --- MUDANÇA AQUI: Rota atualizada ---
    if pg == "Gestão e Estatísticas": admin.gestao_usuarios(usuario); return
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
    
    menu = option_menu(
        menu_title=None, 
        options=ops, 
        icons=icns, 
        default_index=idx, 
        orientation="horizontal",
        styles={
            "container": {
                "padding": "5px 10px", 
                "background-color": COR_FUNDO, 
                "margin": "0px auto",
                "border-radius": "12px", 
                "border": "1px solid rgba(255, 215, 112, 0.15)", 
                "box-shadow": "0 4px 15px rgba(0,0,0,0.3)",
                "width": "100%",       
                "max-width": "100%",  
                "display": "flex",     
                "justify-content": "space-between" 
            },
            "icon": {
                "color": COR_DESTAQUE, 
                "font-size": "16px",
                "font-weight": "bold"
            }, 
            "nav-link": {
                "font-size": "14px", 
                "text-align": "center", 
                "margin": "0px 2px",  
                "color": "rgba(255, 255, 255, 0.8)",
                "font-weight": "400",
                "border-radius": "8px",
                "transition": "0.3s",
                "width": "100%",       
                "flex-grow": "1",     
                "display": "flex",
                "justify-content": "center",
                "align-items": "center"
            },
            "nav-link-selected": {
                "background-color": COR_DESTAQUE, 
                "color": "#0e2d26", 
                "font-weight": "700",
                "box-shadow": "0px 2px 8px rgba(0,0,0,0.2)",
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
