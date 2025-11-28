import streamlit as st
import os
import sys

# 1. CONFIGURAÇÃO DEVE SER A PRIMEIRA LINHA DO STREAMLIT
st.set_page_config(page_title="BJJ Digital", page_icon="assets/logo.png", layout="wide")

# ---------------------------------------------------------
# ESTILOS VISUAIS (PWA & TEMA)
# ---------------------------------------------------------
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
    # Fallback se config.py não for encontrado imediatamente
    COR_FUNDO = "#0e2d26"
    COR_TEXTO = "#FFFFFF"
    COR_DESTAQUE = "#FFD770"
    COR_BOTAO = "#078B6C"
    COR_HOVER = "#FFD770"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;700&display=swap');
.stButton>button {{ 
    background: linear-gradient(90deg, {COR_BOTAO}, #056853); 
    color: white; font-weight: bold; border: none; 
    padding: 0.6em 1.2em; border-radius: 10px; transition: 0.3s; 
}}
.stButton>button:hover {{ 
    background: {COR_HOVER}; color: {COR_FUNDO}; transform: scale(1.02); 
}}
h1, h2, h3 {{ color: {COR_DESTAQUE}; text-align: center; font-weight: 700; }}
div[data-testid="stVerticalBlock"] div[data-testid="stContainer"] {{ border-radius: 10px; }}
</style>
""", unsafe_allow_html=True)

# Hack para Render/Railway (Criação de secrets.toml via Variável de Ambiente)
if "SECRETS_TOML" in os.environ:
    if not os.path.exists(".streamlit"): os.makedirs(".streamlit")
    with open(".streamlit/secrets.toml", "w") as f: f.write(os.environ["SECRETS_TOML"])

# Importações dos Módulos
try:
    from streamlit_option_menu import option_menu
    from database import get_db 
    from views import login, geral, aluno, professor, admin
except ImportError as e:
    st.error(f"❌ Erro crítico na importação de módulos: {e}")
    st.stop()
# --- NOVA FUNÇÃO PARA A TELA DE TROCA ---
def tela_troca_senha_obrigatoria():
    # Centraliza o formulário
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.warning("🔒 Por segurança, redefina sua senha temporária para continuar.")
        
        with st.form("form_troca_senha"):
            nova_senha = st.text_input("Nova Senha:", type="password")
            conf_senha = st.text_input("Confirmar Nova Senha:", type="password")
            submit = st.form_submit_button("Atualizar Senha", use_container_width=True, type="primary")
            
        if submit:
            if not nova_senha:
                st.error("A senha não pode ser vazia.")
            elif nova_senha != conf_senha:
                st.error("As senhas não conferem.")
            else:
                try:
                    # Criptografa a nova senha
                    hashed = bcrypt.hashpw(nova_senha.encode(), bcrypt.gensalt()).decode()
                    
                    # Atualiza no banco e remove a obrigatoriedade
                    db = get_db()
                    uid = st.session_state.usuario['id']
                    
                    db.collection('usuarios').document(uid).update({
                        "senha": hashed,
                        "precisa_trocar_senha": False
                    })
                    
                    st.success("Senha atualizada! Redirecionando...")
                    
                    # Atualiza a sessão para liberar o acesso IMEDIATAMENTE
                    st.session_state.usuario['precisa_trocar_senha'] = False
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
# =========================================
# FUNÇÃO PRINCIPAL (ROTEADOR)
# =========================================
def app_principal():
    # Verificação de Segurança da Sessão
    if "usuario" not in st.session_state or not st.session_state.usuario:
        st.error("Sessão perdida. Por favor, faça login novamente.")
        st.session_state.usuario = None
        st.rerun()
        return

    usuario_logado = st.session_state.usuario
    # Normaliza o tipo do usuário
    tipo_usuario = str(usuario_logado.get("tipo", "aluno")).lower()

    def ir_para(pagina): st.session_state.menu_selection = pagina

    # --- SIDEBAR ---
    with st.sidebar:
        if os.path.exists("assets/logo.png"): 
            st.image("assets/logo.png", use_container_width=True)
            
        st.markdown(f"<h3 style='color:{COR_DESTAQUE};'>{usuario_logado['nome'].title()}</h3>", unsafe_allow_html=True)
        st.markdown(f"<small style='color:#ccc;'>Perfil: {tipo_usuario.capitalize()}</small>", unsafe_allow_html=True)
        
        if st.button("👤 Meu Perfil", use_container_width=True): ir_para("Meu Perfil")

        if tipo_usuario in ["admin", "professor"]:
            if st.button("👩‍🏫 Painel Professor", use_container_width=True): ir_para("Painel do Professor")

        if tipo_usuario == "admin":
            if st.button("🔑 Gestão Usuários", use_container_width=True): ir_para("Gestão de Usuários")

        st.markdown("---")
        if st.button("🚪 Sair", use_container_width=True):
            # Limpa sessão
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    # --- ROTEAMENTO ---
    if "menu_selection" not in st.session_state: st.session_state.menu_selection = "Início"
    pagina = st.session_state.menu_selection

    # Telas da Sidebar (Sem menu horizontal)
    if pagina == "Meu Perfil":
        geral.tela_meu_perfil(usuario_logado)
        if st.button("⬅️ Voltar"): ir_para("Início")
    elif pagina == "Gestão de Usuários":
        admin.gestao_usuarios(usuario_logado)
        if st.button("⬅️ Voltar"): ir_para("Início")
    elif pagina == "Painel do Professor":
        professor.painel_professor()
        if st.button("⬅️ Voltar"): ir_para("Início")
        
    # Tela Inicial
    elif pagina == "Início":
        geral.tela_inicio()
        
    # Telas do Menu Horizontal
    else:
        # Menu Admin/Professor
        if tipo_usuario in ["admin", "professor"]:
            opcoes = ["Início", "Modo Rola", "Exame de Faixa", "Ranking", "Gestão de Questões", "Gestão de Equipes", "Gestão de Exame"]
            icons = ["house-fill", "people-fill", "journal-check", "trophy-fill", "cpu-fill", "building-fill", "file-earmark-check-fill"]
        
        # Menu Aluno
        else: 
            opcoes = ["Início", "Modo Rola", "Exame de Faixa", "Ranking", "Meus Certificados"]
            icons = ["house-fill", "people-fill", "journal-check", "trophy-fill", "patch-check-fill"]

        try: index_atual = opcoes.index(pagina)
        except ValueError: index_atual = 0

        menu = option_menu(
            menu_title=None, options=opcoes, icons=icons, default_index=index_atual, orientation="horizontal",
            styles={
                "container": {"padding": "0!important", "background-color": COR_FUNDO},
                "icon": {"color": COR_DESTAQUE, "font-size": "16px"},
                "nav-link": {"font-size": "14px", "margin": "0px", "color": COR_TEXTO},
                "nav-link-selected": {"background-color": COR_BOTAO, "color": COR_DESTAQUE},
            }
        )

        if menu != pagina:
            st.session_state.menu_selection = menu
            st.rerun()

        # Router do Menu
        if menu == "Início": geral.tela_inicio()
        elif menu == "Modo Rola": aluno.modo_rola(usuario_logado)
        elif menu == "Exame de Faixa": aluno.exame_de_faixa(usuario_logado)
        elif menu == "Ranking": aluno.ranking()
        elif menu == "Gestão de Equipes": professor.gestao_equipes()
        elif menu == "Gestão de Questões": admin.gestao_questoes()
        elif menu == "Gestão de Exame": admin.gestao_exame_de_faixa()
        elif menu == "Meus Certificados": aluno.meus_certificados(usuario_logado)

# =========================================
# START (PONTO DE PARTIDA)
# =========================================
if __name__ == "__main__":
    # Inicializa variáveis
    if "usuario" not in st.session_state: st.session_state.usuario = None
    if "registration_pending" not in st.session_state: st.session_state.registration_pending = None

    try:
        # 1. Pendência de cadastro Google
        if st.session_state.registration_pending:
            login.tela_completar_cadastro(st.session_state.registration_pending)
        
        # 2. Usuário Logado
        elif st.session_state.usuario:
            
            # --- VERIFICAÇÃO DE TROCA DE SENHA (AQUI ESTÁ A MÁGICA) ---
            if st.session_state.usuario.get("precisa_trocar_senha") is True:
                # Se for True, mostra SÓ isso e não carrega o resto do app
                tela_troca_senha_obrigatoria()
            else:
                # Se for False, carrega o app normal
                app_principal()
                
        # 3. Usuário Deslogado
        else:
            login.tela_login()
            
    except Exception as e:
        st.error(f"Erro crítico: {e}")
