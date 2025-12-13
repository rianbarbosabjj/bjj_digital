import streamlit as st
import os
import requests 
import bcrypt
import time
from datetime import datetime, date

# Importações locais simplificadas
try:
    from auth import autenticar_local, criar_usuario_parcial_google, buscar_usuario_por_email
    from utils import formatar_e_validar_cpf, formatar_cep, buscar_cep, gerar_senha_temporaria, enviar_email_recuperacao
    from database import get_db, OPCOES_SEXO
    from firebase_admin import firestore
except ImportError as e:
    st.error(f"Erro nas importações: {e}")

def get_logo_path():
    if os.path.exists("assets/logo.jpg"): return "assets/logo.jpg"
    if os.path.exists("logo.jpg"): return "logo.jpg"
    if os.path.exists("assets/logo.png"): return "assets/logo.png"
    if os.path.exists("logo.png"): return "logo.png"
    return None

def tela_login():
    st.session_state.setdefault("modo_login", "login")
    logo = get_logo_path()

    if "registration_pending" in st.session_state:
        tela_completar_cadastro(st.session_state.registration_pending)
        return

    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        if st.session_state["modo_login"] == "login":
            if logo:
                st.image(logo, use_container_width=True)

            with st.container(border=True):
                st.markdown("<h3 style='text-align:center;'>Login</h3>", unsafe_allow_html=True)
                
                with st.form("login_form"):
                    user_input = st.text_input("Acesse com seu Email ou CPF:")
                    pwd = st.text_input("Senha:", type="password")
                    submit_login = st.form_submit_button("Entrar", type="primary", use_container_width=True)

                if submit_login:
                    if not user_input or not pwd:
                        st.warning("Preencha todos os campos.")
                    else:
                        with st.spinner("Conectando..."):
                            entrada = user_input.strip()
                            u = autenticar_local(entrada, pwd.strip()) 
                            
                            if u:
                                st.session_state.usuario = u
                                st.success(f"Bem-vindo(a), {u['nome'].title()}!")
                                time.sleep(1)
                                st.rerun() 
                            else:
                                st.error("Credenciais inválidas.")

                col_a, col_b = st.columns(2)
                if col_a.button("📋 Criar Conta", use_container_width=True):
                    st.session_state["modo_login"] = "cadastro"
                    st.rerun()
                if col_b.button("🔑 Recuperar Senha", use_container_width=True):
                    st.session_state["modo_login"] = "recuperar"
                    st.rerun()

        elif st.session_state["modo_login"] == "cadastro":
            tela_cadastro_interno()

        elif st.session_state["modo_login"] == "recuperar":
            st.subheader("🔑 Recuperar Senha")
            st.markdown("Informe seu e-mail cadastrado.")
            
            email_rec = st.text_input("Email cadastrado:")
            
            if st.button("Enviar Nova Senha", use_container_width=True, type="primary"):
                if not email_rec:
                    st.warning("Informe o e-mail.")
                else:
                    db = get_db()
                    if not db:
                        st.error("Erro no banco.")
                        return
                    
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
                st.session_state["modo_login"] = "login"
                st.rerun()

def tela_cadastro_interno():
    st.subheader("📋 Cadastro de Novo Usuário")
    db = get_db()
    if not db:
        st.error("Erro de conexão.")
        return
    
    try:
        equipes_ref = db.collection('equipes').stream()
        lista_equipes = ["Nenhuma (Vínculo Pendente)"]
        mapa_equipes = {}
        
        for doc in equipes_ref:
            d = doc.to_dict()
            nm = d.get('nome', 'Sem Nome')
            lista_equipes.append(nm)
            mapa_equipes[nm] = doc.id
                
    except Exception as e:
        st.error(f"Erro ao carregar listas: {e}")
        return

    nome = st.text_input("Nome completo:")
    email = st.text_input("E-mail:")
    
    c_cpf, c_sexo, c_nasc = st.columns([2, 1, 1])
    cpf_inp = c_cpf.text_input("CPF:")
    sexo = c_sexo.selectbox("Sexo:", OPCOES_SEXO)
    data_nasc = c_nasc.date_input("Nascimento:", value=None, min_value=date(1940,1,1), max_value=date.today(), format="DD/MM/YYYY")

    c1, c2 = st.columns(2)
    senha = c1.text_input("Senha:", type="password")
    conf = c2.text_input("Confirmar senha:", type="password")
    
    st.markdown("---")
    tipo = st.selectbox("Tipo:", ["Aluno(a)", "Professor(a)"])
    
    if "Aluno" in tipo:
        faixa = st.selectbox("Faixa:", [
            "Branca", "Cinza e Branca", "Cinza", "Cinza e Preta",
            "Amarela e Branca", "Amarela", "Amarela e Preta",
            "Laranja e Branca", "Laranja", "Laranja e Preta",
            "Verde e Branca", "Verde", "Verde e Preta",
            "Azul", "Roxa", "Marrom", "Preta"
        ])
        eq_sel = st.selectbox("Equipe:", lista_equipes)
    else:
        faixa = st.selectbox("Faixa:", ["Marrom", "Preta"])
        st.caption("Professores(as) devem ser Marrom ou Preta.")
        eq_sel = st.selectbox("Equipe:", lista_equipes + ["🆕 Criar Nova Equipe"])

    st.markdown("#### Endereço")
    c_cep, c_btn = st.columns([3, 1])
    cep = c_cep.text_input("CEP:", key="input_cep_cad")
    
    c1, c2 = st.columns(2)
    logr = c1.text_input("Logradouro:")
    bairro = c2.text_input("Bairro:")
    c3, c4 = st.columns(2)
    cid = c3.text_input("Cidade:")
    uf = c4.text_input("UF:")
    c5, c6 = st.columns(2)
    num = c5.text_input("Número:")
    comp = c6.text_input("Complemento:")

    if st.button("Cadastrar", use_container_width=True, type="primary"):
        nome_fin = nome.upper() if nome else ""
        email_fin = email.lower().strip() if email else ""
        cpf_fin = formatar_e_validar_cpf(cpf_inp) if cpf_inp else None
        
        if not (nome and email and cpf_inp and senha and conf):
            st.warning("Preencha campos obrigatórios.")
            return
        if senha != conf:
            st.error("Senhas não conferem.")
            return
        if not cpf_fin:
            st.error("CPF inválido.")
            return

        users_ref = db.collection('usuarios')
        if len(list(users_ref.where('email', '==', email_fin).stream())) > 0:
            st.error("Email já cadastrado.")
            return
        if len(list(users_ref.where('cpf', '==', cpf_fin).stream())) > 0:
            st.error("CPF já cadastrado.")
            return
            
        try:
            with st.spinner("Criando..."):
                hashed = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
                tipo_db = "professor" if "Professor" in tipo else "aluno"
                
                novo_user = {
                    "nome": nome_fin,
                    "email": email_fin,
                    "cpf": cpf_fin,
                    "tipo_usuario": tipo_db,
                    "senha": hashed,
                    "auth_provider": "local",
                    "perfil_completo": True,
                    "logradouro": logr.upper() if logr else "",
                    "numero": num if num else "",
                    "complemento": comp.upper() if comp else "",
                    "bairro": bairro.upper() if bairro else "",
                    "cidade": cid.upper() if cid else "",
                    "uf": uf.upper() if uf else "",
                    "data_criacao": firestore.SERVER_TIMESTAMP,
                    "sexo": sexo,
                    "data_nascimento": data_nasc.isoformat() if data_nasc else None,
                    "faixa_atual": faixa
                }
                _, doc_ref = db.collection('usuarios').add(novo_user)
                user_id = doc_ref.id
                
                st.success("Cadastro realizado com sucesso!")
                st.session_state.usuario = {"id": user_id, "nome": nome_fin, "tipo": tipo_db}
                st.session_state["modo_login"] = "login"
                time.sleep(1)
                st.rerun()
        except Exception as e:
            st.error(f"Erro: {e}")

    if st.button("Voltar", use_container_width=True):
        st.session_state["modo_login"] = "login"
        st.rerun()

def tela_completar_cadastro(user_data):
    st.subheader(f"👋 Olá, {user_data.get('nome')}!")
    st.info("Para finalizar seu acesso via Google, precisamos de alguns dados.")
    
    db = get_db()
    if not db:
        st.error("Erro banco")
        return

    c_cpf, c_sexo, c_nasc = st.columns([2, 1, 1])
    cpf_inp = c_cpf.text_input("CPF (Obrigatório):")
    sexo = c_sexo.selectbox("Sexo:", OPCOES_SEXO)
    data_nasc = c_nasc.date_input("Nascimento:", value=None, min_value=date(1940,1,1), max_value=date.today(), format="DD/MM/YYYY")

    tipo = st.selectbox("Sou:", ["Aluno(a)", "Professor(a)"])
    
    if "Aluno" in tipo:
        faixa = st.selectbox("Faixa:", [
            "Branca", "Cinza e Branca", "Cinza", "Cinza e Preta",
            "Amarela e Branca", "Amarela", "Amarela e Preta",
            "Laranja e Branca", "Laranja", "Laranja e Preta",
            "Verde e Branca", "Verde", "Verde e Preta",
            "Azul", "Roxa", "Marrom", "Preta"
        ])
    else:
        faixa = st.selectbox("Faixa:", ["Marrom", "Preta"])

    st.markdown("#### Endereço")
    c_cep, c_btn = st.columns([3, 1])
    cep = c_cep.text_input("CEP:", key="cep_g")
    
    c1, c2 = st.columns(2)
    logr = c1.text_input("Logradouro:")
    bairro = c2.text_input("Bairro:")
    c3, c4 = st.columns(2)
    cid = c3.text_input("Cidade:")
    uf = c4.text_input("UF:")
    c5, c6 = st.columns(2)
    num = c5.text_input("Número:")
    comp = c6.text_input("Complemento:")

    if st.button("Finalizar Cadastro", type="primary", use_container_width=True):
        cpf_fin = formatar_e_validar_cpf(cpf_inp)
        if not cpf_fin:
            st.error("CPF Inválido.")
            return
        
        q_cpf = list(db.collection('usuarios').where('cpf', '==', cpf_fin).stream())
        for d in q_cpf:
            if d.id != user_data['id']:
                st.error("CPF já cadastrado em outra conta.")
                return
        
        try:
            with st.spinner("Salvando..."):
                uid = user_data['id']
                tipo_db = "professor" if "Professor" in tipo else "aluno"
                
                db.collection('usuarios').document(uid).update({
                    "cpf": cpf_fin,
                    "tipo_usuario": tipo_db,
                    "perfil_completo": True,
                    "logradouro": logr.upper() if logr else "",
                    "numero": num if num else "",
                    "complemento": comp.upper() if comp else "",
                    "bairro": bairro.upper() if bairro else "",
                    "cidade": cid.upper() if cid else "",
                    "uf": uf.upper() if uf else "",
                    "faixa_atual": faixa,
                    "sexo": sexo,
                    "data_nascimento": data_nasc.isoformat() if data_nasc else None
                })
                
                user_data['perfil_completo'] = True
                user_data['tipo'] = tipo_db
                st.session_state.usuario = user_data
                if 'registration_pending' in st.session_state:
                    del st.session_state.registration_pending
                st.success("Cadastro Completo!")
                time.sleep(1)
                st.rerun()

        except Exception as e:
            st.error(f"Erro ao salvar: {e}")

    if st.button("Cancelar e Sair", use_container_width=True):
        if 'registration_pending' in st.session_state:
            del st.session_state.registration_pending
        st.rerun()
