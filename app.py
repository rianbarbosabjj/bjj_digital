import streamlit as st
import os
import sys
import bcrypt 
import time

# ============================================
# CORREÇÃO: Adiciona o diretório ao path
# ============================================
current_dir = os.path.dirname(os.path.abspath(__file__))
views_dir = os.path.join(current_dir, 'views')

# Adiciona ao sys.path
if views_dir not in sys.path:
    sys.path.insert(0, views_dir)
    sys.path.insert(0, current_dir)

# ============================================
# CONFIGURAÇÃO BÁSICA
# ============================================
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

# Cores padrão
COR_FUNDO = "#0e2d26"
COR_TEXTO = "#FFFFFF"
COR_DESTAQUE = "#FFD770"
COR_BOTAO = "#078B6C"
COR_HOVER = "#FFD770"

# ============================================
# IMPORTAÇÕES COM TRY/EXCEPT SIMPLES
# ============================================
try:
    from streamlit_option_menu import option_menu
except:
    st.error("streamlit_option_menu não instalado. Execute: pip install streamlit-option-menu")
    st.stop()

# Importa módulos individualmente com fallback
def importar_modulo(modulo_nome, fallback_nome=None):
    """Importa módulo com fallback"""
    try:
        if fallback_nome:
            return __import__(modulo_nome)
        else:
            # Tenta importação relativa
            import importlib
            return importlib.import_module(f"views.{modulo_nome}")
    except ImportError as e:
        st.warning(f"Módulo {modulo_nome} não encontrado: {e}")
        return None

# Importa cada módulo
login = importar_modulo("login")
geral = importar_modulo("geral")
aluno = importar_modulo("aluno")
professor = importar_modulo("professor")
admin = importar_modulo("admin")

# Verifica se todos os módulos necessários foram carregados
modulos_necessarios = [login, geral, aluno, professor, admin]
nomes_modulos = ["login", "geral", "aluno", "professor", "admin"]

for i, mod in enumerate(modulos_necessarios):
    if mod is None:
        st.error(f"❌ Módulo crítico '{nomes_modulos[i]}' não encontrado!")
        st.error(f"Verifique se o arquivo views/{nomes_modulos[i]}.py existe")
        st.stop()

# Importação especial para cursos (pode ser opcional)
try:
    from views.cursos import pagina_cursos as cursos_pagina
    cursos = type('obj', (object,), {'pagina_cursos': cursos_pagina})
except ImportError:
    # Fallback para cursos
    st.warning("⚠️ Módulo de cursos não encontrado. Usando versão simplificada.")
    class CursosSimples:
        @staticmethod
        def pagina_cursos(usuario):
            st.markdown("<h1 style='color:#FFD770;'>📚 Cursos BJJ</h1>", unsafe_allow_html=True)
            st.info("Sistema de cursos em desenvolvimento.")
            if st.button("🏠 Voltar"):
                st.session_state.menu_selection = "Início"
                st.rerun()
    cursos = CursosSimples()

# ============================================
# CONEXÃO COM BANCO (SIMPLIFICADA)
# ============================================
def get_db():
    """Versão simplificada para evitar erros"""
    try:
        from database import get_db as get_db_original
        return get_db_original()
    except:
        st.warning("⚠️ Banco de dados temporariamente indisponível")
        return None

# ============================================
# ESTILOS CSS
# ============================================
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Poppins', sans-serif;
        color: {COR_TEXTO} !important;
    }}

    .stApp {{
        background-color: {COR_FUNDO};
        background-image: radial-gradient(circle at 50% 0%, #164036 0%, #0e2d26 70%);
    }}

    h1, h2, h3, h4, h5, h6 {{ 
        color: {COR_DESTAQUE} !important; 
        text-align: center;
        font-weight: 700;
    }}

    div.stButton > button {{ 
        background: {COR_BOTAO} !important; 
        color: white !important;
        border-radius: 8px;
    }}

    div.stButton > button:hover {{ 
        background: {COR_HOVER} !important; 
        color: #0e2d26 !important;
    }}
</style>
""", unsafe_allow_html=True)

# ============================================
# FUNÇÃO DE TROCA DE SENHA
# ============================================
def tela_troca_senha_obrigatoria():
    st.markdown("<h2>🔒 Troca de Senha</h2>", unsafe_allow_html=True)
    st.warning("Por segurança, redefina sua senha.")
    
    with st.form("frm_troca"):
        ns = st.text_input("Nova Senha:", type="password")
        cs = st.text_input("Confirmar:", type="password")
        if st.form_submit_button("Atualizar"):
            if ns and ns == cs:
                try:
                    user = st.session_state.get('usuario')
                    if not user or 'id' not in user:
                        st.error("Erro de sessão")
                        return
                    
                    db = get_db()
                    if db:
                        hashed = bcrypt.hashpw(ns.encode(), bcrypt.gensalt()).decode()
                        db.collection('usuarios').document(user['id']).update({
                            "senha": hashed, 
                            "precisa_trocar_senha": False
                        })
                    
                    st.session_state.usuario['precisa_trocar_senha'] = False
                    st.success("Senha atualizada! Redirecionando...")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")
            else:
                st.error("Senhas não conferem")

# ============================================
# APLICAÇÃO PRINCIPAL
# ============================================
def app_principal():
    if not st.session_state.get('usuario'):
        st.session_state.clear()
        st.rerun()
        return

    usuario = st.session_state.usuario
    tipo = usuario.get("tipo", "aluno").lower()
    
    # Sidebar simplificada
    with st.sidebar:
        if logo_file:
            st.image(logo_file, use_container_width=True)
        
        st.markdown(f"**{usuario['nome'].split()[0]}**")
        st.caption(f"{tipo.capitalize()}")
        st.markdown("---")
        
        if st.button("👤 Meu Perfil"):
            st.session_state.menu_selection = "Meu Perfil"
            st.rerun()
        
        if st.button("🏠 Início"):
            st.session_state.menu_selection = "Início"
            st.rerun()
        
        if tipo in ["professor", "admin"]:
            if st.button("🥋 Painel Prof."):
                st.session_state.menu_selection = "Painel de Professores"
                st.rerun()
        
        if tipo == "admin":
            if st.button("📊 Gestão"):
                st.session_state.menu_selection = "Gestão e Estatísticas"
                st.rerun()
        
        st.markdown("---")
        if st.button("🚪 Sair"):
            st.session_state.clear()
            st.rerun()

    # Navegação principal
    if "menu_selection" not in st.session_state:
        st.session_state.menu_selection = "Início"
    
    pagina = st.session_state.menu_selection
    
    # Menu horizontal
    if tipo in ["admin", "professor"]:
        opcoes = ["Início", "Cursos", "Exame de Faixa", "Ranking", "Questões", "Equipes"]
        icons = ["house", "book", "journal", "trophy", "list-task", "building"]
    else:
        opcoes = ["Início", "Cursos", "Exame de Faixa", "Ranking"]
        icons = ["house", "book", "journal", "trophy"]
    
    try:
        menu = option_menu(
            menu_title=None,
            options=opcoes,
            icons=icons,
            default_index=opcoes.index(pagina) if pagina in opcoes else 0,
            orientation="horizontal"
        )
        
        if menu != pagina:
            st.session_state.menu_selection = menu
            st.rerun()
    except:
        # Fallback se option_menu falhar
        st.write("Navegação: " + " | ".join(opcoes))
        for op in opcoes:
            if st.button(op, key=f"btn_{op}"):
                st.session_state.menu_selection = op
                st.rerun()
    
    # Renderiza página
    if pagina == "Meu Perfil":
        geral.tela_meu_perfil(usuario)
    elif pagina == "Painel de Professores":
        professor.painel_professor()
    elif pagina == "Gestão e Estatísticas":
        admin.gestao_usuarios(usuario)
    elif pagina == "Meus Certificados":
        aluno.meus_certificados(usuario)
    elif pagina == "Início":
        geral.tela_inicio()
    elif pagina == "Cursos":
        cursos.pagina_cursos(usuario)
    elif pagina == "Exame de Faixa":
        aluno.exame_de_faixa(usuario)
    elif pagina == "Ranking":
        aluno.ranking()
    elif pagina == "Questões":
        admin.gestao_questoes()
    elif pagina == "Equipes":
        professor.gestao_equipes()
    else:
        st.info(f"Página '{pagina}' em desenvolvimento")

# ============================================
# PONTO DE ENTRADA
# ============================================
if __name__ == "__main__":
    # Inicializa session_state
    if 'usuario' not in st.session_state:
        st.session_state.usuario = None
    
    if 'menu_selection' not in st.session_state:
        st.session_state.menu_selection = "Início"
    
    if 'registration_pending' not in st.session_state:
        st.session_state.registration_pending = None
    
    # Fluxo principal
    if not st.session_state.usuario and not st.session_state.registration_pending:
        # Tela de login
        try:
            login.tela_login()
        except Exception as e:
            st.error(f"Erro no login: {e}")
            # Fallback para login básico
            st.markdown("<h1>BJJ Digital</h1>", unsafe_allow_html=True)
            email = st.text_input("Email")
            senha = st.text_input("Senha", type="password")
            if st.button("Entrar"):
                st.error("Sistema de login temporariamente indisponível")
    
    elif st.session_state.registration_pending:
        # Cadastro pendente
        try:
            login.tela_completar_cadastro(st.session_state.registration_pending)
        except:
            st.error("Erro no cadastro")
    
    elif st.session_state.usuario:
        # Usuário logado
        if st.session_state.usuario.get("precisa_trocar_senha"):
            tela_troca_senha_obrigatoria()
        else:
            app_principal()
