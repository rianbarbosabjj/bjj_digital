import streamlit as st
import os
import requests 
import bcrypt
from streamlit_oauth import OAuth2Component

# Importações locais
from auth import autenticar_local, criar_usuario_parcial_google, buscar_usuario_por_email
from utils import formatar_e_validar_cpf, formatar_cep, buscar_cep, gerar_senha_temporaria, enviar_email_recuperacao
from database import get_db
from firebase_admin import firestore

# Configuração Google
GOOGLE_CLIENT_ID = st.secrets.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = st.secrets.get("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = "https://bjjdigital.streamlit.app/" 

oauth_google = None
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    try:
        oauth_google = OAuth2Component(
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            authorize_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
            token_endpoint="https://oauth2.googleapis.com/token",
            refresh_token_endpoint="https://oauth2.googleapis.com/token",
            revoke_token_endpoint="https://oauth2.googleapis.com/revoke",
        )
    except: pass

def tela_login():
    st.session_state.setdefault("modo_login", "login")

    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        # --- MODO: LOGIN ---
        if st.session_state["modo_login"] == "login":
            if os.path.exists("assets/logo.png"):
                cl, cc, cr = st.columns([1, 2, 1])
                with cc: st.image("assets/logo.png", use_container_width=True)

            with st.container(border=True):
                st.markdown("<h3 style='text-align:center;'>Login</h3>", unsafe_allow_html=True)
                
                # --- INÍCIO DO FORMULÁRIO ---
                with st.form("login_form"):
                    user_input = st.text_input("Usuário, Email ou CPF:")
                    pwd = st.text_input("Senha:", type="password")
                    
                    # Botão de submissão dentro do form, mas capturando o retorno
                    submit_login = st.form_submit_button("Entrar", type="primary", use_container_width=True)
                # --- FIM DO FORMULÁRIO ---

                # --- LÓGICA DE PROCESSAMENTO (FORA DO FORM) ---
                if submit_login:
                    if not user_input or not pwd:
                        st.warning("Preencha todos os campos.")
                    else:
                        with st.spinner("Conectando..."):
                            entrada = user_input.strip()
                            if "@" in entrada: 
                                entrada = entrada.lower()
                            else:
                                cpf = formatar_e_validar_cpf(entrada)
                                if cpf: entrada = cpf
                            
                            # Tenta autenticar
                            u = autenticar_local(entrada, pwd.strip()) 
                            
                            if u:
                                st.session_state.usuario = u
                                st.success(f"Bem-vindo(a), {u['nome'].title()}!")
                                st.rerun() # Recarrega para entrar no app
                            else:
                                st.error("Credenciais inválidas.")

                # Botões auxiliares
                col_a, col_b = st.columns(2)
                if col_a.button("📋 Criar Conta", use_container_width=True):
                    st.session_state["modo_login"] = "cadastro"; st.rerun()
                if col_b.button("🔑 Recuperar Senha", use_container_width=True):
                    st.session_state["modo_login"] = "recuperar"; st.rerun()

                st.markdown("<div style='text-align:center; margin: 10px 0;'>— OU —</div>", unsafe_allow_html=True)
                
                # Login Social Google
                if oauth_google:
                    res = oauth_google.authorize_button("Continuar com Google", redirect_uri=REDIRECT_URI, scope="email profile", key="google_auth", use_container_width=True)
                    if res and res.get("token"):
                        token = res.get("token").get("access_token")
                        try:
                            r = requests.get("https://www.googleapis.com/oauth2/v1/userinfo", headers={"Authorization": f"Bearer {token}"})
                            if r.status_code == 200:
                                u_info = r.json()
                                email = u_info["email"].lower()
                                nome = u_info.get("name", "").upper()
                                
                                exist = buscar_usuario_por_email(email)
                                if exist:
                                    if not exist.get("perfil_completo"):
                                        st.session_state.registration_pending = exist
                                    else:
                                        st.session_state.usuario = exist
                                    st.rerun()
                                else:
                                    novo = criar_usuario_parcial_google(email, nome)
                                    st.session_state.registration_pending = novo
                                    st.rerun()
                        except Exception as e:
                            st.error(f"Erro no Google: {e}")

        # --- MODO: CADASTRO ---
        elif st.session_state["modo_login"] == "cadastro":
            tela_cadastro_interno()

        # --- MODO: RECUPERAR SENHA ---
        elif st.session_state["modo_login"] == "recuperar":
            st.subheader("🔑 Recuperar Senha")
            st.markdown("Informe seu e-mail cadastrado. Enviaremos uma senha temporária.")
            
            email_rec = st.text_input("Email cadastrado:")
            
            if st.button("Enviar Nova Senha", use_container_width=True, type="primary"):
                if not email_rec:
                    st.warning("Informe o e-mail.")
                else:
                    db = get_db()
                    email_clean = email_rec.lower().strip()
                    users_ref = db.collection('usuarios')
                    query = list(users_ref.where('email', '==', email_clean).stream())
                    
                    if len(query) > 0:
                        doc = query[0]
                        u_data = doc.to_dict()
                        
                        if u_data.get("auth_provider") == "google":
                            st.error("Este e-mail usa login Google.")
                        else:
                            with st.spinner("Processando..."):
                                nova_s = gerar_senha_temporaria()
                                hashed = bcrypt.hashpw(nova_s.encode(), bcrypt.gensalt()).decode()
                                
                                # Atualiza banco e ativa flag de troca obrigatória
                                db.collection('usuarios').document(doc.id).update({
                                    "senha": hashed,
                                    "precisa_trocar_senha": True
                                })
                                
                                if enviar_email_recuperacao(email_clean, nova_s):
                                    st.success("✅ Verifique seu e-mail (e a caixa de spam).")
                                else:
                                    st.error("Erro no envio do e-mail.")
                    else:
                        st.error("E-mail não encontrado.")

            if st.button("Voltar", use_container_width=True):
                st.session_state["modo_login"] = "login"; st.rerun()

# Funções auxiliares mantidas (Cadastro e Completar)
def tela_cadastro_interno():
    # ... (Seu código de cadastro original aqui - se não tiver, me avise que mando completo)
    # Por segurança, vou colocar um botão de voltar simples se você não tiver o código
    st.info("Tela de cadastro (Copie seu código anterior se necessário)")
    if st.button("Voltar"): st.session_state["modo_login"] = "login"; st.rerun()

def tela_completar_cadastro(user_data):
    st.subheader(f"Completar cadastro: {user_data.get('nome')}")
    # ... (Lógica de completar cadastro Google)
    if st.button("Cancelar"):
        del st.session_state.registration_pending
        st.rerun()
