import streamlit as st
import os
import sys
import bcrypt
from database import get_db

# =========================================================
# 1. CONFIGURAÇÃO OBRIGATÓRIA (PRIMEIRA LINHA DE CÓDIGO)
# =========================================================
st.set_page_config(page_title="BJJ Digital", page_icon="assets/logo.png", layout="wide")

# CSS e Estilos
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 1rem;}
</style>
""", unsafe_allow_html=True)

# Imports após set_page_config
try:
    from streamlit_option_menu import option_menu
    from views import login, geral, aluno, professor, admin
    from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO
except ImportError:
    COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO = "#0e2d26", "#FFFFFF", "#FFD770", "#078B6C"

# =========================================
# TELA DE TROCA DE SENHA OBRIGATÓRIA (VISUAL AJUSTADO)
# =========================================
def tela_troca_senha_obrigatoria():
    # Colunas para centralizar o bloco no meio da tela
    c1, c2, c3 = st.columns([1, 2, 1])
    
    with c2:
        # --- 1. LOGO CENTRALIZADA NO TOPO ---
        if os.path.exists("assets/logo.png"):
            # Truque de colunas aninhadas para centralizar a imagem menor
            cl, cc, cr = st.columns([1, 1, 1]) 
            with cc:
                st.image("assets/logo.png", use_container_width=True)
        
        # Espaço visual
        st.write("") 
        
        # --- 2. CAIXA COM TÍTULO, AVISO E FORMULÁRIO ---
        with st.container(border=True):
            st.markdown("<h3 style='text-align:center;'>🔒 Troca de Senha</h3>", unsafe_allow_html=True)
            
            # O aviso fica logo abaixo do título e logo acima do formulário
            st.warning("Por segurança, redefina sua senha temporária para continuar.")
            
            with st.form("frm_troca"):
                ns = st.text_input("Nova Senha:", type="password")
                cs = st.text_input("Confirmar Nova Senha:", type="password")
                
                # Botão ocupando toda a largura
                btn = st.form_submit_button("Atualizar Senha", type="primary", use_container_width=True)
            
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
                            # Atualiza senha e REMOVE a trava (precisa_trocar_senha = False)
                            db.collection('usuarios').document(uid).update({
                                "senha": hashed, 
                                "precisa_trocar_senha": False
                            })
                            
                            st.success("Senha atualizada! Entrando no sistema...")
                            
                            # Atualiza a sessão localmente para liberar o acesso instantâneo
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
        # Se a flag for True, mostra SÓ a tela de troca
        if st.session_state.usuario.get("precisa_trocar_senha") is True:
            tela_troca_senha_obrigatoria()
        else:
            # Se for False, libera o app principal
            app_principal()
            
    # 3. Se não está logado
    else:
        login.tela_login()
