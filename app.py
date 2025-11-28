import streamlit as st
import os
import sys
import bcrypt # Necessário para a troca de senha
from database import get_db

# =========================================================
# 1. CONFIGURAÇÃO (PRIMEIRA LINHA)
# =========================================================
st.set_page_config(page_title="BJJ Digital", page_icon="assets/logo.png", layout="wide")

# =========================================================
# 2. ESTILOS VISUAIS (CSS RESTAURADO + BOTÕES VERDES)
# =========================================================
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 1rem; padding-bottom: 1rem;}
</style>
""", unsafe_allow_html=True)

# Importa cores do config
try:
    from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
except ImportError:
    COR_FUNDO = "#0e2d26"
    COR_TEXTO = "#FFFFFF"
    COR_DESTAQUE = "#FFD770"
    COR_BOTAO = "#078B6C"
    COR_HOVER = "#FFD770"

# CSS COMBINADO: Fontes originais + Forçar Botões Verdes
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;700&display=swap');

/* Força TODOS os botões a serem verdes (gradiente BJJ) */
div.stButton > button, div.stFormSubmitButton > button {{ 
    background: linear-gradient(90deg, {COR_BOTAO} 0%, #056853 100%) !important; 
    color: white !important; 
    font-weight: bold !important;
    border: none !important; 
    padding: 0.6em 1.2em !important; 
    border-radius: 10px !important; 
    transition: 0.3s !important;
}}

div.stButton > button:hover, div.stFormSubmitButton > button:hover {{ 
    background: {COR_HOVER} !important; 
    color: {COR_FUNDO} !important; 
    transform: scale(1.02); 
}}

h1, h2, h3 {{ color: {COR_DESTAQUE}; text-align: center; font-weight: 700; }}
div[data-testid="stVerticalBlock"] div[data-testid="stContainer"] {{ border-radius: 10px; }}
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
# NOVA FUNÇÃO: TELA DE TROCA DE SENHA
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
                # Botão verde automático pelo CSS acima
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
# APP PRINCIPAL (LÓGICA ORIGINAL RESTAURADA)
# =========================================
def app_principal():
    # Verificação de Segurança
    if "usuario" not in st.session_state or not st.session_state.usuario:
        st.error("Sessão perdida. Por favor, faça login novamente.")
        st.session_state.usuario = None
        st.rerun()
        return

    usuario_logado = st.session_state.usuario
    tipo_usuario = str(usuario_logado.get("tipo", "aluno")).lower()

    # Função auxiliar de navegação (Restaurada)
    def ir_para(pagina): st.session_state.menu_selection = pagina

    # --- SIDEBAR (Restaurada) ---
    with st.sidebar:
        if os.path.exists("assets/logo.png"): 
            st.image("assets/logo.png", use_container_width=True)
            
        st.markdown(f"<h3 style='color:{COR_DESTAQUE};'>{usuario_logado['nome'].title()}</h3>", unsafe_allow_html=True)
        st.markdown(f"<small style='color:#ccc;'>Perfil: {tipo_usuario.capitalize()}</small>", unsafe_allow_html=True)
        
        if st.button("👤 Meu Perfil", use_container_width=True): ir_para("Meu Perfil")

        if tipo_usuario in ["admin", "professor"]:
            if st.button("👩‍🏫 Painel Professor", use_container_width=True): ir_para("Painel do Professor")

        if tipo_usuario == "admin":
            if st.button("🔑 Gestão Usuários",
