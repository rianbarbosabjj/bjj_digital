import streamlit as st
import os
import sys

# 1. CONFIGURAÇÃO
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

from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
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

# Hack para Render/Railway
if "SECRETS_TOML" in os.environ:
    if not os.path.exists(".streamlit"): os.makedirs(".streamlit")
    with open(".streamlit/secrets.toml", "w") as f: f.write(os.environ["SECRETS_TOML"])

try:
    from streamlit_option_menu import option_menu
    from database import get_db 
    from views import login, geral, aluno, professor, admin
except ImportError as e:
    st.error(f"❌ Erro: {e}")
    st.stop()

# =========================================
# TELA DE VERIFICAÇÃO PÚBLICA
# =========================================
def tela_verificacao(codigo):
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Logo centralizado
    c1, c2, c3 = st.columns([1, 1, 1])
    if os.path.exists("assets/logo.png"):
        with c2: st.image("assets/logo.png", use_container_width=True)
    
    st.markdown(f"<h2 style='color:{COR_DESTAQUE}; text-align:center;'>Verificação de Autenticidade</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    with st.spinner("Verificando código na Blockchain BJJ Digital..."):
        db = get_db()
        
        # Busca no Firestore
        docs = list(db.collection('resultados').where('codigo_verificacao', '==', codigo).stream())
        
        if docs:
            dados = docs[0].to_dict()
            
            # Cartão de Sucesso
            st.success("✅ CERTIFICADO VÁLIDO E AUTÊNTICO")
            
            with st.container(border=True):
                st.markdown(f"### 🥋 Faixa {dados.get('faixa', 'Desconhecida')}")
                st.markdown(f"**Aluno:** {dados.get('usuario', 'N/A').upper()}")
                
                # Formata data
                data_exame = dados.get('data')
                if data_exame:
                    try: data_str = data_exame.strftime("%d/%m/%Y")
                    except: data_str = str(data_exame)[:10]
                else: data_str = "-"
                
                c1, c2 = st.columns(2)
                c1.write(f"**Data de Conclusão:** {data_str}")
                c2.write(f"**Aproveitamento:** {dados.get('pontuacao')}%")
                
                st.markdown("---")
                st.caption(f"Código Hash: {codigo}")
                st.caption("Este certificado foi emitido digitalmente pela plataforma BJJ Digital e sua autenticidade foi confirmada em nosso banco de dados.")
            
            if st.button("Voltar para Início"):
                st.query_params.clear() # Limpa URL
                st.rerun()
        else:
            st.error("❌ CÓDIGO NÃO ENCONTRADO OU INVÁLIDO")
            st.warning(f"O código **{codigo}** não consta em nossa base de dados oficial.")
            if st.button("Tentar Novamente"):
                st.query_params.clear()
                st.rerun()

# =========================================
# FUNÇÃO PRINCIPAL (ROTEADOR)
# =========================================
def app_principal():
    if "usuario" not in st.session_state or not st.session_state.usuario:
        st.error("Sessão perdida.")
        st.session_state.usuario = None
        st.rerun()
        return

    usuario_logado = st.session_state.usuario
    tipo_usuario = str(usuario_logado.get("tipo", "aluno")).lower()

    def ir_para(pagina): st.session_state.menu_selection = pagina

    with st.sidebar:
        if os.path.exists("assets/logo.png"): st.image("assets/logo.png", use_container_width=True)
        st.markdown(f"<h3 style='color:{COR_DESTAQUE};'>{usuario_logado['nome'].title()}</h3>", unsafe_allow_html=True)
        st.markdown(f"<small style='color:#ccc;'>Perfil: {tipo_usuario.capitalize()}</small>", unsafe_allow_html=True)
        
        if st.button("👤 Meu Perfil", use_container_width=True): ir_para("Meu Perfil")

        if tipo_usuario in ["admin", "professor"]:
            if st.button("👩‍🏫 Painel Professor", use_container_width=True): ir_para("Painel do Professor")

        if tipo_usuario == "admin":
            if st.button("🔑 Gestão Usuários", use_container_width=True): ir_para("Gestão de Usuários")

        st.markdown("---")
        if st.button("🚪 Sair", use_container_width=True):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

    if "menu_selection" not in st.session_state: st.session_state.menu_selection = "Início"
    pagina = st.session_state.menu_selection

    if pagina == "Meu Perfil":
        geral.tela_meu_perfil(usuario_logado)
        if st.button("⬅️ Voltar"): ir_para("Início")
    elif pagina == "Gestão de Usuários":
        admin.gestao_usuarios(usuario_logado)
        if st.button("⬅️ Voltar"): ir_para("Início")
    elif pagina == "Painel do Professor":
        professor.painel_professor()
        if st.button("⬅️ Voltar"): ir_para("Início")
    elif pagina == "Início":
        geral.tela_inicio()
    else:
        if tipo_usuario in ["admin", "professor"]:
            opcoes = ["Início", "Modo Rola", "Exame de Faixa", "Ranking", "Gestão de Questões", "Gestão de Equipes", "Gestão de Exame"]
            icons = ["house-fill", "people-fill", "journal-check", "trophy-fill", "cpu-fill", "building-fill", "file-earmark-check-fill"]
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

        if menu == "Início": geral.tela_inicio()
        elif menu == "Modo Rola": aluno.modo_rola(usuario_logado)
        elif menu == "Exame de Faixa": aluno.exame_de_faixa(usuario_logado)
        elif menu == "Ranking": aluno.ranking()
        elif menu == "Gestão de Equipes": professor.gestao_equipes()
        elif menu == "Gestão de Questões": admin.gestao_questoes()
        elif menu == "Gestão de Exame": admin.gestao_exame_de_faixa()
        elif menu == "Meus Certificados": aluno.meus_certificados(usuario_logado)

# =========================================
# START
# =========================================
if __name__ == "__main__":
    # 🚨 LÓGICA DE VERIFICAÇÃO PÚBLICA 🚨
    # Verifica se existe o parâmetro ?code=XXXX na URL
    query_params = st.query_params
    codigo_verificacao = query_params.get("code", None)

    if codigo_verificacao:
        # Se tiver código, mostra APENAS a tela de validação (ignora login)
        tela_verificacao(codigo_verificacao)
    else:
        # Fluxo normal do App
        if "usuario" not in st.session_state: st.session_state.usuario = None
        if "token" not in st.session_state: st.session_state.token = None
        if "registration_pending" not in st.session_state: st.session_state.registration_pending = None

        try:
            if st.session_state.registration_pending:
                login.tela_completar_cadastro(st.session_state.registration_pending)
            elif st.session_state.usuario:
                app_principal()
            else:
                login.tela_login()
        except Exception as e:
            st.error(f"Erro inesperado: {e}")
