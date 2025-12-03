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
# 2. ESTILOS VISUAIS (CSS "DARK + GLASS MENU")
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

    /* GLOBAL */
    html, body, [class*="css"], .stMarkdown, p, label, .stCaption, span {{
        font-family: 'Poppins', sans-serif;
        color: {COR_TEXTO} !important;
    }}

    .stApp {{
        background-color: {COR_FUNDO} !important;
        background-image: radial-gradient(circle at 50% 0%, #164036 0%, {COR_FUNDO} 70%) !important;
    }}

    /* =========================================================
       🍸 MENU SUPERIOR – VIDRO FOSCO PREMIUM (SOMENTE NO MENU)
       ========================================================= */

    div[data-testid="stHorizontalBlock"] > div:first-child {{
        background: rgba(255, 255, 255, 0.07) !important;
        backdrop-filter: blur(14px) saturate(140%) !important;
        -webkit-backdrop-filter: blur(14px) saturate(140%) !important;
        border-radius: 14px !important;
        border: 1px solid rgba(255,255,255,0.15) !important;
        margin: 15px auto 25px auto !important;
        padding: 12px 18px !important;
        max-width: 98% !important;
        box-shadow: 0 8px 24px rgba(0,0,0,0.35) !important;
    }}

    /* LINKS DO MENU */
    div[data-testid="stHorizontalBlock"] > div:first-child .st-ae .st-af {{
        background: rgba(255,255,255,0.08) !important;
        border-radius: 10px !important;
        padding: 10px 16px !important;
        color: rgba(255,255,255,0.75) !important;
        transition: all 0.25s ease !important;
    }}

    div[data-testid="stHorizontalBlock"] > div:first-child .st-ae .st-af:hover {{
        background: rgba(255,215,112,0.18) !important;
        color: {COR_DESTAQUE} !important;
        border: 1px solid rgba(255,215,112,0.4) !important;
        transform: translateY(-2px);
    }}

    /* ITEM SELECIONADO */
    div[data-testid="stHorizontalBlock"] > div:first-child .st-ae .st-ag {{
        background: rgba(255,215,112,0.25) !important;
        color: {COR_DESTAQUE} !important;
        border-bottom: 2px solid {COR_DESTAQUE} !important;
        border-radius: 6px !important;
        font-weight: 700 !important;
    }}

    /* Scroll invisível */
    div[data-testid="stHorizontalBlock"] > div:first-child::-webkit-scrollbar {{
        height: 0px !important;
    }}

    /* =========================================================
       ✔ RESTAURAR BOTÃO DA SIDEBAR
       ========================================================= */

    [data-testid="stSidebarCollapsedControl"] {{
        visibility: visible !important;
        opacity: 1 !important;
    }}

    [data-testid="stSidebarCollapsedControl"] button {{
        background-color: rgba(255,255,255,0.1) !important;
        color: {COR_DESTAQUE} !important;
        border-radius: 6px !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
    }}

    [data-testid="stSidebarCollapsedControl"] button:hover {{
        background-color: {COR_HOVER} !important;
        color: {COR_FUNDO} !important;
    }}

    /* SIDEBAR */
    section[data-testid="stSidebar"] {{
        background-color: #091f1a !important; 
        border-right: 1px solid rgba(255,215,112,0.15);
    }}

    /* CARDS */
    div[data-testid="stVerticalBlock"] > div[data-testid="stContainer"],
    div[data-testid="stForm"] {{
        background-color: rgba(0,0,0,0.3) !important;
        border: 1px solid rgba(255,215,112,0.15) !important;
        border-radius: 12px !important;
        padding: 20px;
    }}

    /* INPUTS */
    input, textarea, select {{
        background-color: rgba(255,255,255,0.06) !important;
        border: 1px solid rgba(255,255,255,0.25) !important;
        color: white !important;
        border-radius: 8px !important;
    }}

    /* OCULTAR MENU PADRÃO */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}

</style>
""", unsafe_allow_html=True)

# =========================================================
# RESTANTE DO SEU CÓDIGO (NÃO ALTERADO)
# =========================================================

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
                        except:
                            st.error("Erro.")
                    else:
                        st.error("Senhas não conferem.")

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
            if st.button("🔑 Gestão Usuários", use_container_width=True): nav("Gestão de Usuários")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.clear(); st.rerun()

    if "menu_selection" not in st.session_state:
        st.session_state.menu_selection = "Início"

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

    try:
        idx = ops.index(pg)
    except:
        idx = 0

    menu = option_menu(
        menu_title=None,
        options=ops,
        icons=icns,
        default_index=idx,
        orientation="horizontal"
    )

    if menu != pg:
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
        if st.session_state.usuario.get("precisa_trocar_senha"):
            tela_troca_senha_obrigatoria()
        else:
            app_principal()
