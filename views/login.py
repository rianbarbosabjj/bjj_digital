import streamlit as st
import sqlite3
import bcrypt
import pandas as pd
from streamlit_oauth import OAuth2Component
from auth import autenticar_local, criar_usuario_parcial_google, buscar_usuario_por_email
from utils import formatar_e_validar_cpf, formatar_cep, buscar_cep
from config import DB_PATH, COR_DESTAQUE, COR_TEXTO

# Configuração OAuth (Copiado do original)
try:
    GOOGLE_CLIENT_ID = st.secrets["GOOGLE_CLIENT_ID"]
    GOOGLE_CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
    REDIRECT_URI = "https://bjjdigital.streamlit.app/" # Ajuste se necessário
except (FileNotFoundError, KeyError):
    # Valores dummy para não quebrar se não tiver secrets configurado ainda
    GOOGLE_CLIENT_ID = ""
    GOOGLE_CLIENT_SECRET = ""
    REDIRECT_URI = ""

oauth_google = OAuth2Component(
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    authorize_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
    token_endpoint="https://oauth2.googleapis.com/token",
    refresh_token_endpoint="https://oauth2.googleapis.com/token",
    revoke_token_endpoint="https://oauth2.googleapis.com/revoke",
)

def tela_login():
    """Tela de login com autenticação local, Google e opção de cadastro."""
    st.session_state.setdefault("modo_login", "login")

    # Layout de colunas para centralizar
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        if st.session_state["modo_login"] == "login":
            with st.container(border=True):
                st.markdown("<h3 style='text-align:center;'>Login</h3>", unsafe_allow_html=True)
                
                user_ou_email = st.text_input("Nome de Usuário, Email ou CPF:")
                pwd = st.text_input("Senha:", type="password")

                if st.button("Entrar", use_container_width=True, key="entrar_btn", type="primary"):
                    u = autenticar_local(user_ou_email.strip(), pwd.strip()) 
                    if u:
                        st.session_state.usuario = u
                        st.success(f"Login realizado com sucesso! Bem-vindo(a), {u['nome'].title()}.")
                        st.rerun()
                    else:
                        st.error("Usuário/Email/CPF ou senha incorretos.")

                colx, coly, colz = st.columns([1, 2, 1])
                with coly:
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("📋 Criar Conta", key="criar_conta_btn"):
                            st.session_state["modo_login"] = "cadastro"
                            st.rerun()
                    with col2:
                        if st.button("🔑 Esqueci Senha", key="esqueci_btn"):
                            st.session_state["modo_login"] = "recuperar"
                            st.rerun()

                st.markdown("<div style='text-align:center; margin: 10px 0;'>— OU —</div>", unsafe_allow_html=True)
                
                # Botão Google
                result = oauth_google.authorize_button(
                    name="Continuar com Google",
                    icon="https://www.google.com.br/favicon.ico",
                    redirect_uri=REDIRECT_URI,
                    scope="email profile",
                    key="google_auth_btn",
                    use_container_width=True,
                )
                
                if result and result.get("token"):
                    st.session_state.token = result.get("token")
                    user_info = oauth_google.get_user_info(st.session_state.token)
                    if user_info:
                        email = user_info["email"]
                        nome = user_info.get("name", email.split("@")[0])
                        
                        existente = buscar_usuario_por_email(email)
                        if existente:
                            if not existente["perfil_completo"]:
                                st.session_state.registration_pending = existente
                                st.rerun()
                            else:
                                st.session_state.usuario = existente
                                st.rerun()
                        else:
                            novo_user = criar_usuario_parcial_google(email, nome)
                            st.session_state.registration_pending = novo_user
                            st.rerun()

        elif st.session_state["modo_login"] == "cadastro":
            tela_cadastro_interno()

        elif st.session_state["modo_login"] == "recuperar":
            st.subheader("🔑 Recuperar Senha")
            st.text_input("Digite o e-mail cadastrado:")
            if st.button("Enviar Instruções", use_container_width=True, type="primary"):
                st.info("Funcionalidade em desenvolvimento.")
            if st.button("⬅️ Voltar para Login", use_container_width=True):
                st.session_state["modo_login"] = "login"
                st.rerun()

def tela_cadastro_interno():
    # Lógica de cadastro (extraída e simplificada do seu original para caber aqui)
    st.subheader("📋 Cadastro de Novo Usuário")
    nome = st.text_input("Nome de Usuário (login):") 
    email = st.text_input("E-mail:")
    cpf_input = st.text_input("CPF:") 
    senha = st.text_input("Senha:", type="password")
    confirmar = st.text_input("Confirmar senha:", type="password")
    
    st.markdown("---")
    tipo_usuario = st.selectbox("Tipo de Usuário:", ["Aluno", "Professor"])
    
    # ... (Lógica de endereço e botão cadastrar do seu código original vai aqui) ...
    # DICA: Copie o bloco "elif st.session_state['modo_login'] == 'cadastro':" do seu app.py original para cá
    # e lembre-se de ajustar os imports se usar funções de banco diretas.
    
    if st.button("⬅️ Voltar para Login", use_container_width=True):
        st.session_state["modo_login"] = "login"
        st.rerun()

def tela_completar_cadastro(user_data):
    """Exibe formulário para completar perfil Google."""
    st.markdown(f"<h1 style='color:#FFD700;'>Quase lá, {user_data['nome']}!</h1>", unsafe_allow_html=True)
    
    with st.form(key="form_completar_cadastro"):
        st.text_input("Seu nome:", value=user_data['nome'], key="cadastro_nome")
        st.text_input("Seu Email:", value=user_data['email'], disabled=True)
        tipo_usuario = st.radio("Qual o seu tipo de perfil?", ["🥋 Sou Aluno", "👩‍🏫 Sou Professor"], key="cadastro_tipo")
        
        if tipo_usuario == "🥋 Sou Aluno":
            st.selectbox("Sua faixa atual:", ["Branca", "Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"], key="cadastro_faixa")
            
        if st.form_submit_button("Salvar e Acessar"):
            # Lógica de salvar no banco (UPDATE usuarios e INSERT alunos/professores)
            # Copie a lógica do final do seu app.py original
            novo_tipo = "aluno" if "Aluno" in tipo_usuario else "professor"
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE usuarios SET nome=?, tipo_usuario=?, perfil_completo=1 WHERE id=?", (st.session_state.cadastro_nome, novo_tipo, user_data['id']))
            
            if novo_tipo == "aluno":
                cursor.execute("INSERT INTO alunos (usuario_id, faixa_atual, status_vinculo) VALUES (?, ?, 'pendente')", (user_data['id'], st.session_state.cadastro_faixa))
            else:
                cursor.execute("INSERT INTO professores (usuario_id, status_vinculo) VALUES (?, 'pendente')", (user_data['id'],))
            
            conn.commit()
            conn.close()
            
            st.session_state.usuario = {"id": user_data['id'], "nome": st.session_state.cadastro_nome, "tipo": novo_tipo}
            del st.session_state.registration_pending
            st.rerun()
