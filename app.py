import streamlit as st
import os
import sys
import bcrypt
from database import get_db

# =========================================================
# 1. CONFIGURAÇÃO OBRIGATÓRIA (PRIMEIRA LINHA DE CÓDIGO)
# =========================================================
st.set_page_config(page_title="BJJ Digital", page_icon="assets/logo.png", layout="wide")

# =========================================================
# 2. CONFIGURAÇÃO VISUAL (CORES E CSS)
# =========================================================

# Definição das Cores (Verde BJJ)
COR_FUNDO = "#0e2d26"
COR_TEXTO = "#FFFFFF"
COR_DESTAQUE = "#FFD770"
COR_BOTAO = "#078B6C" # Verde Principal
COR_HOVER = "#FFD770"

# Injeção de CSS (Forçando os botões verdes)
st.markdown(f"""
<style>
    /* Ocultar elementos padrão do Streamlit */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    .block-container {{padding-top: 1rem;}}

    /* Estilo Global dos Botões (Normais e de Formulário) */
    div.stButton > button, div.stFormSubmitButton > button {{ 
        background: linear-gradient(90deg, {COR_BOTAO} 0%, #056853 100%) !important; 
        color: white !important; 
        font-weight: bold !important;
        border: none !important; 
        padding: 0.6em 1.2em !important; 
        border-radius: 10px !important; 
        transition: 0.3s !important;
    }}

    /* Efeito Hover (Passar o mouse) */
    div.stButton > button:hover, div.stFormSubmitButton > button:hover {{ 
        background: {COR_HOVER} !important; 
        color: {COR_FUNDO} !important; 
        transform: scale(1.02); 
    }}

    /* Títulos */
    h1, h2, h3 {{ color: {COR_DESTAQUE}; text-align: center; font-weight: 700; }}
    
    /* Bordas arredondadas nos containers */
    div[data-testid="stVerticalBlock"] div[data-testid="stContainer"] {{ border-radius: 10px; }}
</style>
""", unsafe_allow_html=True)

# Imports após set_page_config
try:
    from streamlit_option_menu import option_menu
    from views import login, geral, aluno, professor, admin
except ImportError: pass

# =========================================
# TELA DE TROCA DE SENHA OBRIGATÓRIA
# =========================================
def tela_troca_senha_obrigatoria():
    # Colunas para centralizar o bloco no meio da tela
    c1, c2, c3 = st.columns([1, 2, 1])
    
    with c2:
        # --- 1. LOGO CENTRALIZADA NO TOPO ---
        if os.path.exists("assets/logo.png"):
            cl, cc, cr = st.columns([1, 1, 1]) 
            with cc:
                st.image("assets/logo.png", use_container_width=True)
        
        st.write("") 
        
        # --- 2. CAIXA COM TÍTULO, AVISO E FORMULÁRIO ---
        with st.container(border=True):
            st.markdown("<h3 style='text-align:center;'>🔒 Troca de Senha</h3>", unsafe_allow_html=True)
            
            # Aviso
            st.warning("Por segurança, redefina sua senha temporária para continuar.")
            
            with st.form("frm_troca"):
                ns = st.text_input("Nova Senha:", type="password")
                cs = st.text_input("Confirmar Nova Senha:", type="password")
                
                # O botão agora será VERDE por causa do CSS acima
                btn = st.form_submit_button("Atualizar Senha", use_container_width=True)
            
            if btn:
                if ns and ns == cs:
                    if not ns:
                        st.error("A senha não pode ser vazia.")
                    else:
                        try:
                            uid = st.session_state.usuario['id']
                            # Criptografia
                            hashed = bcrypt.hashpw(ns.encode(), bcrypt.gensalt()).decode()
                            
                            db = get_db()
                            # Atualiza senha e REMOVE a trava
                            db.collection('usuarios').document(uid).update({
                                "senha": hashed, 
                                "precisa_trocar_senha": False
                            })
                            
                            st.success("Senha atualizada! Entrando no sistema...")
                            
                            # Atualiza a sessão localmente
                            st.session_state.usuario['precisa_trocar_senha'] = False
                            st.rerun()
                        except Exception as e: 
                            st.error(f"Erro ao salvar: {e}")
                else: 
                    st.error("As senhas não conferem.")

# =========================================
# APP PRINCIPAL
# =========================================
def app_principal():
    usuario = st.session_state.usuario
    tipo = usuario.get("tipo", "aluno").lower()

    # --- SIDEBAR ---
    with st.sidebar:
        if os.path.exists("assets/logo.png"): st.image("assets/logo.png")
        st.markdown(f"### Olá, {usuario['nome'].split()[0].title()}")
        st.caption(f"Perfil: {tipo.capitalize()}")
        
        if st.button("Sair", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # --- ROTEAMENTO ---
    if "menu_selection" not in st.session_state: st.session_state.menu_selection = "Início"
    
    # Define as opções do menu com base no perfil
    if tipo == "admin": 
        opcoes = ["Início", "Gestão de Usuários", "Gestão de Questões", "Gestão de Equipes"]
        icones = ["house", "people", "list-task", "building"]
    elif tipo == "professor":
        opcoes = ["Início", "Minha Equipe", "Gestão de Equipes"]
        icones = ["house", "people", "building"]
    else: # Aluno
        opcoes = ["Início", "Modo Rola", "Exame de Faixa", "Ranking", "Meus Certificados"]
        icones = ["house", "activity", "journal-check", "trophy", "award"]
    
    # Renderiza o Menu
    menu = option_menu(None, opcoes, icons=icones, orientation="horizontal")
    
    # Lógica de Navegação (Views)
    if menu == "Início": geral.tela_inicio()
    
    # Admin
    elif menu == "Gestão de Usuários": admin.gestao_usuarios(usuario)
    elif menu == "Gestão de Questões": admin.gestao_questoes()
    elif menu == "Gestão de Equipes" and tipo in ["admin", "professor"]: professor.gestao_equipes()
    
    # Professor
    elif menu == "Minha Equipe": professor.painel_professor()
    
    # Aluno
    elif menu == "Modo Rola": aluno.modo_rola(usuario)
    elif menu == "Exame de Faixa": aluno.exame_de_faixa(usuario)
    elif menu == "Ranking": aluno.ranking()
    elif menu == "Meus Certificados": aluno.meus_certificados(usuario)

# =========================================
# EXECUÇÃO (MAIN)
# =========================================
if __name__ == "__main__":
    # Garante inicialização das variáveis de estado
    if "usuario" not in st.session_state: st.session_state.usuario = None
    if "registration_pending" not in st.session_state: st.session_state.registration_pending = None

    # 1. Se tem cadastro pendente (Google)
    if st.session_state.registration_pending:
        login.tela_completar_cadastro(st.session_state.registration_pending)
    
    # 2. Se o usuário está logado
    elif st.session_state.usuario:
        
        # ---> BLOQUEIO DE SEGURANÇA <---
        if st.session_state.usuario.get("precisa_trocar_senha") is True:
            tela_troca_senha_obrigatoria()
        else:
            app_principal()
            
    # 3. Se não está logado
    else:
        login.tela_login()
