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
    
    hr {{
        margin: 2em 0 !important;
        border: 0 !important;
        height: 1px !important;
        background-image: linear-gradient(to right, rgba(255, 255, 255, 0), rgba(255, 255, 255, 0.5), rgba(255, 255, 255, 0)) !important;
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

    input, textarea, select {{
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important; 
        border-radius: 8px !important;
    }}

</style>
""", unsafe_allow_html=True)

if "SECRETS_TOML" in os.environ:
    if not os.path.exists(".streamlit"): os.makedirs(".streamlit")
    with open(".streamlit/secrets.toml", "w") as f: f.write(os.environ["SECRETS_TOML"])

# 🔥 IMPORTAÇÃO ATUALIZADA — inclui cursos
try:
    from streamlit_option_menu import option_menu
    from views import login, geral, aluno, professor, admin, cursos
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
                            user_sessao = st.session_state.get('usuario')
                            if not user_sessao:
                                st.error("Usuário não identificado.")
                                return

                            uid = user_sessao['id']
                            hashed = bcrypt.hashpw(ns.encode(), bcrypt.gensalt()).decode()

                            db = get_db()
                            if not db:
                                st.error("Erro de conexão.")
                                return

                            db.collection('usuarios').document(uid).update({
                                "senha": hashed, 
                                "precisa_trocar_senha": False
                            })

                            st.success("Senha atualizada!")
                            st.session_state.usuario['precisa_trocar_senha'] = False
                            time.sleep(1)
                            st.rerun()

                        except Exception as e:
                            st.error(f"Erro: {e}")
                    else:
                        st.error("Senhas não conferem.")


def app_principal():
    if not st.session_state.get('usuario'):
        st.session_state.clear(); st.rerun(); return

    usuario = st.session_state.usuario
    raw_tipo = str(usuario.get("tipo", "aluno")).lower()

    if "admin" in raw_tipo: tipo_code = "admin"
    elif "professor" in raw_tipo: tipo_code = "professor"
    else: tipo_code = "aluno"

    label_tipo = raw_tipo.capitalize()
    if tipo_code == "admin": label_tipo = "Administrador(a)"
    elif tipo_code == "professor": label_tipo = "Professor(a)"
    elif tipo_code == "aluno": label_tipo = "Aluno(a)"

    def nav(pg): st.session_state.menu_selection = pg

    # SIDEBAR
    with st.sidebar:
        if logo_file: st.image(logo_file, use_container_width=True)

        st.markdown(f"<h3 style='color:{COR_DESTAQUE}; text-align:center;'>{usuario['nome'].split()[0]}</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align:center; color:#aaa;'>{label_tipo}</p>", unsafe_allow_html=True)
        st.markdown("---")

        if st.button("👤 Meu Perfil", use_container_width=True): nav("Meu Perfil")

        if tipo_code in ["admin", "professor"]:
            if st.button("🥋 Painel Prof.", use_container_width=True): nav("Painel de Professores")

        if tipo_code != "admin":
            if st.button("🏅 Meus Certificados", use_container_width=True): nav("Meus Certificados")

        if tipo_code == "admin":
            if st.button("📊 Gestão e Estatísticas", use_container_width=True): nav("Gestão e Estatísticas")

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.clear(); st.rerun()

    if "menu_selection" not in st.session_state:
        st.session_state.menu_selection = "Início"

    pg = st.session_state.menu_selection

    # ROTAS ESPECIAIS
    if pg == "Meu Perfil": geral.tela_meu_perfil(usuario); return
    if pg == "Gestão e Estatísticas": admin.gestao_usuarios(usuario); return
    if pg == "Painel de Professores": professor.painel_professor(); return
    if pg == "Meus Certificados": aluno.meus_certificados(usuario); return
    if pg == "Início": geral.tela_inicio(); return

    # 🔥 MENU HORIZONTAL — ATUALIZADO COM "Cursos"
    if tipo_code in ["admin", "professor"]:
        ops = ["Início", "Modo Rola", "Cursos", "Exame de Faixa", "Ranking",
               "Gestão de Questões", "Gestão de Equipes", "Gestão de Exame"]

        icns = ["house", "people", "book", "journal", "trophy",
                "list-task", "building", "file-earmark"]

    else:
        ops = ["Início", "Modo Rola", "Cursos", "Exame de Faixa", "Ranking"]
        icns = ["house", "people", "book", "journal", "trophy"]

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

    # 🔥 NOVA ROTA: Cursos
    if pg == "Cursos":
        cursos.pagina_cursos(usuario)
        return

    # ROTAS NORMAIS
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
