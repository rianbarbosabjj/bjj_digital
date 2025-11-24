import streamlit as st
import pandas as pd
import os
import requests 
import bcrypt
from streamlit_oauth import OAuth2Component
from auth import autenticar_local, criar_usuario_parcial_google, buscar_usuario_por_email
from utils import formatar_e_validar_cpf, formatar_cep, buscar_cep
from config import COR_DESTAQUE, COR_TEXTO
from database import get_db
from firebase_admin import firestore

# =========================================
# CONFIGURAÇÃO OAUTH
# =========================================
try:
    GOOGLE_CLIENT_ID = st.secrets["GOOGLE_CLIENT_ID"]
    GOOGLE_CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
    REDIRECT_URI = "https://bjjdigital.streamlit.app/" 
except (FileNotFoundError, KeyError):
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

# =========================================
# FUNÇÕES DE TELA
# =========================================

def tela_login():
    """Tela de login com autenticação local (Firebase) e Google."""
    st.session_state.setdefault("modo_login", "login")

    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        if st.session_state["modo_login"] == "login":
            
            # --- LOGO ---
            if os.path.exists("assets/logo.png"):
                col_l, col_c, col_r = st.columns([1, 2, 1])
                with col_c:
                    st.image("assets/logo.png", use_container_width=True)

            with st.container(border=True):
                st.markdown("<h3 style='text-align:center;'>Login</h3>", unsafe_allow_html=True)
                
                user_input = st.text_input("Nome de Usuário, Email ou CPF:")
                pwd = st.text_input("Senha:", type="password")

                if st.button("Entrar", use_container_width=True, type="primary"):
                    entrada = user_input.strip()
                    if "@" in entrada:
                        entrada = entrada.lower()
                    else:
                        cpf = formatar_e_validar_cpf(entrada)
                        if cpf: entrada = cpf
                        
                    u = autenticar_local(entrada, pwd.strip()) 
                    if u:
                        st.session_state.usuario = u
                        st.success(f"Bem-vindo(a), {u['nome'].title()}!")
                        st.rerun()
                    else:
                        st.error("Credenciais inválidas.")

                col1, col2 = st.columns(2)
                if col1.button("📋 Criar Conta"):
                    st.session_state["modo_login"] = "cadastro"
                    st.rerun()
                if col2.button("🔑 Esqueci Senha"):
                    st.session_state["modo_login"] = "recuperar"
                    st.rerun()

                st.markdown("<div style='text-align:center; margin: 10px 0;'>— OU —</div>", unsafe_allow_html=True)
                
                # --- LÓGICA GOOGLE (BLINDADA) ---
                if GOOGLE_CLIENT_ID: 
                    try:
                        result = oauth_google.authorize_button(
                            name="Continuar com Google",
                            icon="https://www.google.com.br/favicon.ico",
                            redirect_uri=REDIRECT_URI,
                            scope="email profile",
                            key="google_auth_btn",
                            use_container_width=True,
                        )
                    except Exception:
                        st.warning("A conexão expirou. Recarregue a página (F5).")
                        result = None
                    
                    if result and result.get("token"):
                        st.session_state.token = result.get("token")
                        try:
                            token = result.get("token").get("access_token")
                            headers = {"Authorization": f"Bearer {token}"}
                            resp = requests.get("https://www.googleapis.com/oauth2/v1/userinfo", headers=headers)
                            
                            if resp.status_code == 200:
                                u_info = resp.json()
                                email = u_info["email"].lower()
                                nome = u_info.get("name", "").upper()
                                
                                exist = buscar_usuario_por_email(email)
                                if exist:
                                    if not exist.get("perfil_completo"):
                                        st.session_state.registration_pending = exist
                                        st.rerun()
                                    else:
                                        st.session_state.usuario = exist
                                        st.rerun()
                                else:
                                    novo = criar_usuario_parcial_google(email, nome)
                                    st.session_state.registration_pending = novo
                                    st.rerun()
                            else:
                                st.error("Falha ao obter dados do Google.")
                        except Exception as e:
                            st.error(f"Erro Google: {e}")
                else:
                    st.warning("Google Auth não configurado.")

        elif st.session_state["modo_login"] == "cadastro":
            tela_cadastro_interno()

        elif st.session_state["modo_login"] == "recuperar":
            st.subheader("🔑 Recuperar Senha")
            st.text_input("Email cadastrado:")
            if st.button("Enviar Instruções", use_container_width=True, type="primary"):
                st.info("Funcionalidade em breve.")
            
            if st.button("Voltar"):
                st.session_state["modo_login"] = "login"
                st.rerun()

def tela_cadastro_interno():
    """Cadastro manual salvando no FIRESTORE."""
    st.subheader("📋 Cadastro de Novo Usuário")
    nome = st.text_input("Nome de Usuário:") 
    email = st.text_input("E-mail:")
    cpf_inp = st.text_input("CPF:") 
    senha = st.text_input("Senha:", type="password")
    conf = st.text_input("Confirmar senha:", type="password")
    
    st.markdown("---")
    tipo = st.selectbox("Tipo:", ["Aluno", "Professor"])
    
    # Busca equipes do Firestore
    db = get_db()
    equipes_ref = db.collection('equipes').stream()
    lista_equipes = ["Nenhuma (Vínculo Pendente)"]
    mapa_equipes = {} # Nome -> ID
    
    for doc in equipes_ref:
        d = doc.to_dict()
        nome_eq = d.get('nome', 'Sem Nome')
        lista_equipes.append(nome_eq)
        mapa_equipes[nome_eq] = doc.id
        
    if tipo == "Aluno":
        faixa = st.selectbox("Faixa:", ["Branca", "Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"])
    else:
        faixa = st.selectbox("Faixa:", ["Marrom", "Preta"])
        st.caption("Professores devem ser Marrom ou Preta.")
        
    eq_sel = st.selectbox("Equipe:", lista_equipes)
    
    # Endereço
    st.markdown("#### Endereço")
    if 'cad_cep' not in st.session_state: st.session_state.cad_cep = ''
    
    col_cep, col_btn = st.columns([3, 1])
    with col_cep:
        cep = st.text_input("CEP:", key="input_cep_cad", value=st.session_state.cad_cep)
    with col_btn:
        st.markdown("<div style='height: 29px;'></div>", unsafe_allow_html=True)
        if st.button("Buscar", key="btn_cep_cad"):
            end = buscar_cep(cep)
            if end:
                st.session_state.cad_cep = cep
                st.session_state.cad_end = end
                st.success("OK!")
            else:
                st.error("Inválido")
    
    end_cache = st.session_state.get('cad_end', {})
    c1, c2 = st.columns(2)
    logr = c1.text_input("Logradouro:", value=end_cache.get('logradouro',''))
    bairro = c2.text_input("Bairro:", value=end_cache.get('bairro',''))
    c3, c4 = st.columns(2)
    cid = c3.text_input("Cidade:", value=end_cache.get('cidade',''))
    uf = c4.text_input("UF:", value=end_cache.get('uf',''))
    c5, c6 = st.columns(2)
    num = c5.text_input("Número:")
    comp = c6.text_input("Complemento:")

    if st.button("Cadastrar", use_container_width=True, type="primary"):
        nome_fin = nome.upper()
        email_fin = email.lower().strip()
        cpf_fin = formatar_e_validar_cpf(cpf_inp)
        cep_fin = formatar_cep(cep)

        if not (nome and email and cpf_inp and senha and conf):
            st.warning("Preencha campos obrigatórios.")
            return
        if senha != conf:
            st.error("Senhas não conferem.")
            return
        if not cpf_fin:
            st.error("CPF inválido.")
            return

        # Verifica duplicidade no Firestore
        users_ref = db.collection('usuarios')
        if len(list(users_ref.where('email', '==', email_fin).stream())) > 0:
            st.error("Email já cadastrado.")
            return
            
        try:
            hashed = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
            tipo_db = tipo.lower()
            
            # 1. Cria Usuário no Firestore
            novo_user = {
                "nome": nome_fin, "email": email_fin, "cpf": cpf_fin, 
                "tipo_usuario": tipo_db, "senha": hashed, "auth_provider": "local", 
                "perfil_completo": True, "cep": cep_fin, "logradouro": logr.upper(),
                "numero": num, "complemento": comp.upper(), "bairro": bairro.upper(),
                "cidade": cid.upper(), "uf": uf.upper(), "data_criacao": firestore.SERVER_TIMESTAMP
            }
            
            update_time, doc_ref = db.collection('usuarios').add(novo_user)
            user_id = doc_ref.id
            
            # 2. Cria vínculo
            eq_id = mapa_equipes.get(eq_sel)
            
            if tipo_db == "aluno":
                db.collection('alunos').add({
                    "usuario_id": user_id, "faixa_atual": faixa, 
                    "equipe_id": eq_id, "status_vinculo": "pendente"
                })
            else:
                db.collection('professores').add({
                    "usuario_id": user_id, "equipe_id": eq_id, 
                    "status_vinculo": "pendente"
                })
                
            st.success("Cadastro realizado! Faça login.")
            
            # Limpa sessão
            for k in ['cad_cep', 'cad_end']: st.session_state.pop(k, None)
            st.session_state["modo_login"] = "login"
            st.rerun()
            
        except Exception as e:
            st.error(f"Erro ao gravar: {e}")

    if st.button("Voltar"):
        st.session_state["modo_login"] = "login"
        st.rerun()

def tela_completar_cadastro(user_data):
    """Completa cadastro Google no FIRESTORE."""
    st.markdown(f"<h1 style='color:#FFD700;'>Quase lá, {user_data['nome']}!</h1>", unsafe_allow_html=True)
    
    # Busca Equipes
    db = get_db()
    equipes_ref = db.collection('equipes').stream()
    lista_equipes = ["Nenhuma (Vínculo Pendente)"]
    mapa_equipes = {} 
    for doc in equipes_ref:
        d = doc.to_dict()
        nm = d.get('nome', 'Sem Nome')
        lista_equipes.append(nm)
        mapa_equipes[nm] = doc.id

    # Dados
    nome = st.text_input("Nome:", value=user_data['nome'])
    st.text_input("Email:", value=user_data['email'], disabled=True)
    tipo = st.radio("Perfil:", ["Aluno", "Professor"], horizontal=True)
    
    c_faixa, c_eq = st.columns(2)
    with c_faixa:
        if tipo == "Aluno":
            faixa = st.selectbox("Faixa:", ["Branca", "Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"])
        else:
            faixa = st.selectbox("Faixa:", ["Marrom", "Preta"])
    with c_eq:
        eq_sel = st.selectbox("Equipe:", lista_equipes)

    st.markdown("#### Endereço")
    if 'goog_cep' not in st.session_state: st.session_state.goog_cep = ''
    
    col_cep, col_btn = st.columns([3, 1])
    with col_cep:
        cep = st.text_input("CEP:", key="input_cep_goog", value=st.session_state.goog_cep)
    with col_btn:
        st.markdown("<div style='height: 29px;'></div>", unsafe_allow_html=True)
        if st.button("Buscar", key="btn_cep_goog"):
            end = buscar_cep(cep)
            if end:
                st.session_state.goog_cep = cep
                st.session_state.goog_end = end
                st.success("OK!")
            else: st.error("Inválido")

    end_cache = st.session_state.get('goog_end', {})
    c1, c2 = st.columns(2)
    logr = c1.text_input("Logradouro:", value=end_cache.get('logradouro',''))
    bairro = c2.text_input("Bairro:", value=end_cache.get('bairro',''))
    c3, c4 = st.columns(2)
    cid = c3.text_input("Cidade:", value=end_cache.get('cidade',''))
    uf = c4.text_input("UF:", value=end_cache.get('uf',''))
    c5, c6 = st.columns(2)
    num = c5.text_input("Número:")
    comp = c6.text_input("Complemento:")

    if st.button("Salvar e Acessar", type="primary"):
        if not nome or not cep or not logr or not num:
            st.warning("Preencha Nome e Endereço completo.")
            return

        tipo_db = tipo.lower()
        eq_id = mapa_equipes.get(eq_sel)
        
        # Atualiza Usuário
        db.collection('usuarios').document(user_data['id']).update({
            "nome": nome.upper(), "tipo_usuario": tipo_db, "perfil_completo": True,
            "cep": formatar_cep(cep), "logradouro": logr.upper(), "numero": num, 
            "complemento": comp.upper(), "bairro": bairro.upper(), 
            "cidade": cid.upper(), "uf": uf.upper()
        })
        
        # Cria Vínculo
        if tipo_db == "aluno":
            db.collection('alunos').add({
                "usuario_id": user_data['id'], "faixa_atual": faixa, 
                "equipe_id": eq_id, "status_vinculo": "pendente"
            })
        else:
            db.collection('professores').add({
                "usuario_id": user_data['id'], "equipe_id": eq_id, 
                "status_vinculo": "pendente"
            })
            
        st.session_state.usuario = {"id": user_data['id'], "nome": nome.upper(), "tipo": tipo_db}
        
        for k in ['goog_cep', 'goog_end', 'registration_pending']:
            st.session_state.pop(k, None)
        st.rerun()
