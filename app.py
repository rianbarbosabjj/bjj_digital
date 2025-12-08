import streamlit as st
import os
import sys
import bcrypt 
import time
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
    
    div.stRadio > div[role="radiogroup"] > label > div:first-child {{
        border-color: {COR_DESTAQUE} !important;
    }}
    div.stRadio > div[role="radiogroup"] > label > div:first-child > div {{
        background-color: {COR_DESTAQUE} !important;
    }}

    section[data-testid="stSidebar"] {{
        background-color: #091f1a !important; 
        border-right: 1px solid rgba(255, 215, 112, 0.15);
    }}

    div.stButton > button {{ 
        background: linear-gradient(135deg, {COR_BOTAO} 0%, #056853 100%) !important; 
        color: white !important; 
        border: 1px solid rgba(255,255,255,0.1) !important; 
    }}
    div.stButton > button:hover {{ 
        background: {COR_HOVER} !important; 
        color: #0e2d26 !important; 
    }}

    input, textarea, select, div[data-baseweb="select"] > div {{
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important; 
    }}
    
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header[data-testid="stHeader"] {{ background-color: transparent !important; }}
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
                            st.success("Sucesso! Entrando...")
                            st.session_state.usuario['precisa_trocar_senha'] = False
                            time.sleep(1)
                            st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")
                    else: st.error("Senhas não conferem.")

def app_principal():
    if not st.session_state.get('usuario'):
        st.session_state.clear(); st.rerun(); return

    usuario = st.session_state.usuario
    raw_tipo = str(usuario.get("tipo_usuario", usuario.get("tipo", "aluno"))).lower()
    
    if "admin" in raw_tipo: tipo_code = "admin"
    elif "professor" in raw_tipo: tipo_code = "professor"
    else: tipo_code = "aluno"

    def nav(pg): st.session_state.menu_selection = pg

    with st.sidebar:
        if logo_file: st.image(logo_file, use_container_width=True)
        st.markdown(f"<h3 style='color:{COR_DESTAQUE}; margin:0;'>{usuario['nome'].split()[0]}</h3>", unsafe_allow_html=True)
        st.markdown("---")
        
        if st.button("👤 Meu Perfil", use_container_width=True): nav("Meu Perfil")
        if tipo_code != "admin" and tipo_code != "professor":
             if st.button("🏅 Meus Certificados", use_container_width=True): nav("Meus Certificados")
        if tipo_code == "admin":
            if st.button("📊 Gestão e Estatísticas", use_container_width=True): nav("Gestão e Estatísticas")
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.clear(); st.rerun()

    if "menu_selection" not in st.session_state: st.session_state.menu_selection = "Início"
    pg = st.session_state.menu_selection

    if pg == "Meu Perfil": geral.tela_meu_perfil(usuario); return
    if pg == "Gestão e Estatísticas": admin.gestao_usuarios_geral(usuario); return # Só Admin
    if pg == "Meus Certificados": aluno.meus_certificados(usuario); return 
    if pg == "Início": geral.tela_inicio(); return

    # --- MENU PRINCIPAL ---
    ops, icns = [], []
    
    # ADICIONEI "Gestão de Equipe" AQUI PARA ADMIN E PROFESSOR
    if tipo_code == "admin":
        ops = ["Início", "Modo Rola", "Exame de Faixa", "Ranking", "Gestão de Questões", "Gestão de Equipe", "Gestão de Exame"]
        icns = ["house", "people", "journal", "trophy", "list-task", "people-fill", "file-earmark"]
    
    elif tipo_code == "professor":
        ops = ["Início", "Modo Rola", "Exame de Faixa", "Ranking", "Gestão de Questões", "Gestão de Equipe", "Gestão de Exame"]
        icns = ["house", "people", "journal", "trophy", "list-task", "people-fill", "file-earmark"]
    
    else: # Aluno
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
            "container": {"padding": "5px", "background-color": COR_FUNDO},
            "icon": {"color": COR_DESTAQUE, "font-size": "14px"}, 
            "nav-link": {"font-size": "13px", "text-align": "center", "margin": "0px", "color": "white"},
            "nav-link-selected": {"background-color": COR_DESTAQUE, "color": "#0e2d26"},
        }
    )

    if menu != pg:
        st.session_state.menu_selection = menu
        st.rerun()

    # --- ROTEAMENTO ---
    if pg == "Modo Rola": aluno.modo_rola(usuario)
    elif pg == "Exame de Faixa": aluno.exame_de_faixa(usuario)
    elif pg == "Ranking": aluno.ranking()
    
    # Rotas Admin/Prof
    elif pg == "Gestão de Questões": admin.gestao_questoes()
    elif pg == "Gestão de Equipe": admin.gestao_equipes_tab() # <--- ESSA LINHA FAZ O BOTÃO FUNCIONAR
    elif pg == "Gestão de Exame": admin.gestao_exame_de_faixa()

if __name__ == "__main__":
    if not st.session_state.get('usuario') and not st.session_state.get('registration_pending'):
        login.tela_login()
    elif st.session_state.get('registration_pending'):
        login.tela_completar_cadastro(st.session_state.registration_pending)
    elif st.session_state.get('usuario'):
        if st.session_state.usuario.get("precisa_trocar_senha"): tela_troca_senha_obrigatoria()
        else: app_principal()
