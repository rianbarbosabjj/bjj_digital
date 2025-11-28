import streamlit as st
import pandas as pd
import os
import requests 
import bcrypt
from streamlit_oauth import OAuth2Component
# Importações locais
from auth import autenticar_local, criar_usuario_parcial_google, buscar_usuario_por_email
from utils import formatar_e_validar_cpf, formatar_cep, buscar_cep, gerar_senha_temporaria, enviar_email_recuperacao
from config import COR_DESTAQUE, COR_TEXTO
from database import get_db
from firebase_admin import firestore

# =========================================
# CONFIGURAÇÃO OAUTH (BLINDADA)
# =========================================
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
    except Exception as e:
        print(f"Erro ao iniciar OAuth: {e}")

# =========================================
# TELA DE LOGIN PRINCIPAL
# =========================================
def tela_login():
    st.session_state.setdefault("modo_login", "login")

    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        # --- MODO: LOGIN ---
        if st.session_state["modo_login"] == "login":
            if os.path.exists("assets/logo.png"):
                col_l, col_c, col_r = st.columns([1, 2, 1])
                with col_c: st.image("assets/logo.png", use_container_width=True)

            with st.container(border=True):
                st.markdown("<h3 style='text-align:center;'>Login</h3>", unsafe_allow_html=True)
                
                with st.form("login_form"):
                    user_input = st.text_input("Nome de Usuário, Email ou CPF:")
                    pwd = st.text_input("Senha:", type="password")
                    submit_login = st.form_submit_button("Entrar", use_container_width=True, type="primary")

                if submit_login:
                    if not user_input or not pwd:
                        st.warning("Preencha todos os campos.")
                    else:
                        with st.spinner("Conectando..."):
                            entrada = user_input.strip()
                            if "@" in entrada: entrada = entrada.lower()
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
                with col1:
                    if st.button("📋 Criar Conta", use_container_width=True):
                        st.session_state["modo_login"] = "cadastro"; st.rerun()
                with col2:
                    if st.button("🔑 Esqueci Senha", use_container_width=True):
                        st.session_state["modo_login"] = "recuperar"; st.rerun()

                st.markdown("<div style='text-align:center; margin: 10px 0;'>— OU —</div>", unsafe_allow_html=True)
                
                if oauth_google: 
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
                        st.warning("Recarregue a página (F5).")
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
                                st.error("Falha no Google.")
                        except Exception as e:
                            st.error(f"Erro Google: {e}")

        # --- MODO: CADASTRO ---
        elif st.session_state["modo_login"] == "cadastro":
            tela_cadastro_interno()

# --- MODO: RECUPERAR SENHA (ATUALIZADO COM TROCA OBRIGATÓRIA) ---
        elif st.session_state["modo_login"] == "recuperar":
            st.subheader("🔑 Recuperar Senha")
            st.markdown("Informe seu e-mail cadastrado. Enviaremos uma senha temporária.")
            
            email_rec = st.text_input("Email cadastrado:")
            
            if st.button("Enviar Nova Senha", use_container_width=True, type="primary"):
                if not email_rec:
                    st.warning("Por favor, informe o e-mail.")
                else:
                    db = get_db()
                    email_clean = email_rec.lower().strip()
                    
                    # 1. Buscar usuário pelo email no Firestore
                    users_ref = db.collection('usuarios')
                    query = list(users_ref.where('email', '==', email_clean).stream())
                    
                    if len(query) > 0:
                        doc = query[0]
                        usuario_encontrado = doc.to_dict()
                        doc_id = doc.id
                        
                        # 2. Verificar se é conta Google (não tem senha para recuperar)
                        if usuario_encontrado.get("auth_provider") == "google":
                            st.error("Este e-mail usa login social (Google). Clique em 'Continuar com Google' na tela inicial.")
                        else:
                            with st.spinner("Gerando senha e enviando e-mail..."):
                                # 3. Gerar senha temporária aleatória
                                nova_senha = gerar_senha_temporaria()
                                
                                # 4. Criptografar a senha (Hash) para salvar no banco
                                hashed_nova = bcrypt.hashpw(nova_senha.encode(), bcrypt.gensalt()).decode()
                                
                                # 5. Atualizar no Firestore e Enviar E-mail
                                try:
                                    # Atualiza banco com a senha E a flag de troca obrigatória
                                    db.collection('usuarios').document(doc_id).update({
                                        "senha": hashed_nova,
                                        "precisa_trocar_senha": True  # <--- ISSO FORÇA A TELA DE TROCA
                                    })
                                    
                                    # Envia E-mail
                                    enviou = enviar_email_recuperacao(email_clean, nova_senha)
                                    
                                    if enviou:
                                        st.success("✅ Sucesso! Verifique seu e-mail (e a caixa de spam) para pegar a nova senha.")
                                    else:
                                        st.error("Erro ao conectar com servidor de e-mail. Tente novamente.")
                                        
                                except Exception as e:
                                    st.error(f"Erro interno: {e}")
                    else:
                        st.error("E-mail não encontrado na nossa base de dados.")

            if st.button("Voltar", use_container_width=True):
                st.session_state["modo_login"] = "login"; st.rerun()

# =========================================
# TELA CADASTRO INTERNO (AUXILIAR)
# =========================================
def tela_cadastro_interno():
    st.subheader("📋 Cadastro de Novo Usuário")
    db = get_db()
    
    try:
        equipes_ref = db.collection('equipes').stream()
        lista_equipes = ["Nenhuma (Vínculo Pendente)"]
        mapa_equipes = {} 
        for doc in equipes_ref:
            d = doc.to_dict()
            nm = d.get('nome', 'Sem Nome')
            lista_equipes.append(nm)
            mapa_equipes[nm] = doc.id
        
        profs_users_ref = db.collection('usuarios').where('tipo_usuario', '==', 'professor').stream()
        mapa_nomes_profs = {} 
        for doc in profs_users_ref:
            mapa_nomes_profs[doc.id] = doc.to_dict().get('nome', 'Sem Nome')

        vincs_ref = db.collection('professores').where('status_vinculo', '==', 'ativo').stream()
        profs_por_equipe = {} 
        for doc in vincs_ref:
            d = doc.to_dict()
            eid = d.get('equipe_id')
            uid = d.get('usuario_id')
            if eid and uid and uid in mapa_nomes_profs:
                if eid not in profs_por_equipe: profs_por_equipe[eid] = []
                profs_por_equipe[eid].append((mapa_nomes_profs[uid], uid))
    except Exception as e:
        st.error(f"Erro ao carregar listas: {e}"); return

    nome = st.text_input("Nome de Usuário:") 
    email = st.text_input("E-mail:")
    cpf_inp = st.text_input("CPF:") 
    c1, c2 = st.columns(2)
    senha = c1.text_input("Senha:", type="password")
    conf = c2.text_input("Confirmar senha:", type="password")
    
    st.markdown("---")
    tipo = st.selectbox("Tipo:", ["Aluno", "Professor"])
    
    cf, ce = st.columns(2)
    nome_nova_equipe = None; desc_nova_equipe = None
    
    if tipo == "Aluno":
        with cf: faixa = st.selectbox("Faixa:", ["Branca", "Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"])
        with ce: eq_sel = st.selectbox("Equipe:", lista_equipes)
        
        lista_profs_filtrada = ["Nenhum (Vínculo Pendente)"]
        mapa_profs_final = {}
        eq_id_sel = mapa_equipes.get(eq_sel)
        if eq_id_sel and eq_id_sel in profs_por_equipe:
            for p_nome, p_uid in profs_por_equipe[eq_id_sel]:
                lista_profs_filtrada.append(p_nome)
                mapa_profs_final[p_nome] = p_uid
        prof_sel = st.selectbox("Professor:", lista_profs_filtrada)
        
    else: 
        with cf: faixa = st.selectbox("Faixa:", ["Marrom", "Preta"])
        st.caption("Professores devem ser Marrom ou Preta.")
        with ce:
            opcoes_prof_eq = lista_equipes + ["🆕 Criar Nova Equipe"]
            eq_sel = st.selectbox("Equipe:", opcoes_prof_eq)
        
        if eq_sel == "🆕 Criar Nova Equipe":
            st.info("Você será o **Responsável** desta nova equipe.")
            nome_nova_equipe = st.text_input("Nome da Nova Equipe:")
            desc_nova_equipe = st.text_input("Descrição (Opcional):")
        prof_sel = None 

    st.markdown("#### Endereço")
    if 'cad_cep' not in st.session_state: st.session_state.cad_cep = ''
    
    c_cep, c_btn = st.columns([3, 1])
    cep = c_cep.text_input("CEP:", key="input_cep_cad", value=st.session_state.cad_cep)
    if c_btn.button("Buscar", key="btn_cep_cad"):
        end = buscar_cep(cep)
        if end:
            st.session_state.cad_cep = cep
            st.session_state.cad_end = end
            st.success("OK!")
        else: st.error("Inválido")
    
    ec = st.session_state.get('cad_end', {})
    c1, c2 = st.columns(2)
    logr = c1.text_input("Logradouro:", value=ec.get('logradouro',''))
    bairro = c2.text_input("Bairro:", value=ec.get('bairro',''))
    c3, c4 = st.columns(2)
    cid = c3.text_input("Cidade:", value=ec.get('cidade',''))
    uf = c4.text_input("UF:", value=ec.get('uf',''))
    c5, c6 = st.columns(2)
    num = c5.text_input("Número:")
    comp = c6.text_input("Complemento:")

    if st.button("Cadastrar", use_container_width=True, type="primary"):
        nome_fin = nome.upper()
        email_fin = email.lower().strip()
        cpf_fin = formatar_e_validar_cpf(cpf_inp)
        cep_fin = formatar_cep(cep)

        if not (nome and email and cpf_inp and senha and conf):
            st.warning("Preencha obrigatórios."); return
        if senha != conf: st.error("Senhas não conferem."); return
        if not cpf_fin: st.error("CPF inválido."); return
        
        if tipo == "Professor" and eq_sel == "🆕 Criar Nova Equipe" and not nome_nova_equipe:
            st.warning("Informe o nome da equipe."); return

        users_ref = db.collection('usuarios')
        if len(list(users_ref.where('email', '==', email_fin).stream())) > 0:
            st.error("Email já cadastrado."); return
        if len(list(users_ref.where('cpf', '==', cpf_fin).stream())) > 0:
            st.error("CPF já cadastrado."); return
            
        try:
            with st.spinner("Criando..."):
                hashed = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
                tipo_db = tipo.lower()
                
                novo_user = {
                    "nome": nome_fin, "email": email_fin, "cpf": cpf_fin, 
                    "tipo_usuario": tipo_db, "senha": hashed, "auth_provider": "local", 
                    "perfil_completo": True, "cep": cep_fin, "logradouro": logr.upper(),
                    "numero": num, "complemento": comp.upper(), "bairro": bairro.upper(),
                    "cidade": cid.upper(), "uf": uf.upper(), "data_criacao": firestore.SERVER_TIMESTAMP
                }
                _, doc_ref = db.collection('usuarios').add(novo_user)
                user_id = doc_ref.id
                
                eq_id = None
                if tipo_db == "professor" and eq_sel == "🆕 Criar Nova Equipe":
                    _, ref_team = db.collection('equipes').add({
                        "nome": nome_nova_equipe.upper(), "descricao": desc_nova_equipe,
                        "professor_responsavel_id": user_id, "ativo": True
                    })
                    eq_id = ref_team.id
                    db.collection('professores').add({
                        "usuario_id": user_id, "equipe_id": eq_id, "status_vinculo": "ativo", 
                        "eh_responsavel": True, "pode_aprovar": True
                    })
                else:
                    eq_id = mapa_equipes.get(eq_sel)
                    prof_id = mapa_profs_final.get(prof_sel) if (tipo == "Aluno" and prof_sel) else None
                    if tipo_db == "aluno":
                        db.collection('alunos').add({
                            "usuario_id": user_id, "faixa_atual": faixa, "equipe_id": eq_id, 
                            "professor_id": prof_id, "status_vinculo": "pendente"
                        })
                    else:
                        db.collection('professores').add({
                            "usuario_id": user_id, "equipe_id": eq_id, "status_vinculo": "pendente"
                        })
                
                st.success("Sucesso!"); 
                st.session_state.usuario = {"id": user_id, "nome": nome_fin, "tipo": tipo_db}
                for k in ['cad_cep', 'cad_end']: st.session_state.pop(k, None)
                st.session_state["modo_login"] = "login"; st.rerun()
        except Exception as e: st.error(f"Erro: {e}")

    if st.button("Voltar", use_container_width=True):
        st.session_state["modo_login"] = "login"; st.rerun()

# =========================================
# TELA COMPLETAR CADASTRO (GOOGLE)
# =========================================
def tela_completar_cadastro(user_data):
    st.subheader(f"👋 Olá, {user_data.get('nome', 'Usuário').title()}!")
    st.info("Complete seu perfil para acessar a plataforma.")

    db = get_db()

    try:
        equipes_ref = db.collection('equipes').stream()
        lista_equipes = ["Nenhuma (Vínculo Pendente)"]
        mapa_equipes = {} 
        for doc in equipes_ref:
            d = doc.to_dict(); nm = d.get('nome', 'Sem Nome')
            lista_equipes.append(nm); mapa_equipes[nm] = doc.id
        
        profs_users_ref = db.collection('usuarios').where('tipo_usuario', '==', 'professor').stream()
        mapa_nomes_profs = {} 
        for doc in profs_users_ref: mapa_nomes_profs[doc.id] = doc.to_dict().get('nome', 'Sem Nome')

        vincs_ref = db.collection('professores').where('status_vinculo', '==', 'ativo').stream()
        profs_por_equipe = {} 
        for doc in vincs_ref:
            d = doc.to_dict(); eid = d.get('equipe_id'); uid = d.get('usuario_id')
            if eid and uid and uid in mapa_nomes_profs:
                if eid not in profs_por_equipe: profs_por_equipe[eid] = []
                profs_por_equipe[eid].append((mapa_nomes_profs[uid], uid))
    except Exception as e: st.error(f"Erro: {e}"); return

    nome = st.text_input("Nome:", value=user_data.get('nome',''))
    st.text_input("E-mail:", value=user_data.get('email',''), disabled=True)
    
    if 'cpf_g' not in st.session_state: st.session_state.cpf_g = ''
    cpf_inp = st.text_input("CPF:", value=st.session_state.cpf_g)
    
    st.markdown("---")
    tipo = st.radio("Perfil:", ["Aluno", "Professor"], horizontal=True)
    
    cf, ce = st.columns(2)
    nome_nova_equipe = None; desc_nova_equipe = None
    
    if tipo == "Aluno":
        with cf: faixa = st.selectbox("Faixa:", ["Branca", "Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"], key="fx_g")
        with ce: eq_sel = st.selectbox("Equipe:", lista_equipes, key="eq_g")
        
        lista_profs_filtrada = ["Nenhum (Vínculo Pendente)"]
        mapa_profs_final = {}
        eq_id_sel = mapa_equipes.get(eq_sel)
        if eq_id_sel and eq_id_sel in profs_por_equipe:
            for p_nome, p_uid in profs_por_equipe[eq_id_sel]:
                lista_profs_filtrada.append(p_nome); mapa_profs_final[p_nome] = p_uid
        prof_sel = st.selectbox("Professor:", lista_profs_filtrada, key="pf_g")
    else: 
        with cf: faixa = st.selectbox("Faixa:", ["Marrom", "Preta"], key="fx_g_p")
        with ce:
            opcoes_prof_eq = lista_equipes + ["🆕 Criar Nova Equipe"]
            eq_sel = st.selectbox("Equipe:", opcoes_prof_eq, key="eq_g_p")
        if eq_sel == "🆕 Criar Nova Equipe":
            nome_nova_equipe = st.text_input("Nome da Nova Equipe:", key="ne_g")
            desc_nova_equipe = st.text_input("Descrição (Opcional):", key="de_g")
        prof_sel = None

    st.markdown("#### Endereço")
    if 'cad_cep' not in st.session_state: st.session_state.cad_cep = ''
    
    c_cep, c_btn = st.columns([3, 1])
    cep = c_cep.text_input("CEP:", key="input_cep_cad", value=st.session_state.cad_cep)
    if c_btn.button("Buscar", key="btn_cep_cad"):
        end = buscar_cep(cep)
        if end:
            st.session_state.cad_cep = cep
            st.session_state.cad_end = end
            st.success("OK!")
        else: st.error("Inválido")
    
    ec = st.session_state.get('cad_end', {})
    c1, c2 = st.columns(2)
    logr = c1.text_input("Logradouro:", value=ec.get('logradouro',''))
    bairro = c2.text_input("Bairro:", value=ec.get('bairro',''))
    c3, c4 = st.columns(2)
    cid = c3.text_input("Cidade:", value=ec.get('cidade',''))
    uf = c4.text_input("UF:", value=ec.get('uf',''))
    c5, c6 = st.columns(2)
    num = c5.text_input("Número:")
    comp = c6.text_input("Complemento:")

    if st.button("Finalizar Cadastro", type="primary", use_container_width=True):
        cpf_fin = formatar_e_validar_cpf(cpf_inp)
        cep_fin = formatar_cep(cep)
        
        if not nome: st.warning("Nome obrigatório."); return
        if not cpf_fin: st.error("CPF inválido."); return
        if tipo == "Professor" and eq_sel == "🆕 Criar Nova Equipe" and not nome_nova_equipe: st.warning("Nome da equipe obrigatório."); return

        users_ref = db.collection('usuarios')
        if len(list(users_ref.where('cpf', '==', cpf_fin).stream())) > 0: st.error("CPF já em uso."); return

        try:
            tipo_db = tipo.lower()
            user_id = user_data['id']
            db.collection('usuarios').document(user_id).update({
                "nome": nome.upper(), "cpf": cpf_fin, "tipo_usuario": tipo_db, "perfil_completo": True,
                "cep": cep_fin, "logradouro": logr.upper(), "numero": num, "complemento": comp.upper(),
                "bairro": bairro.upper(), "cidade": cid.upper(), "uf": uf.upper()
            })

            eq_id = None
            if tipo_db == "professor" and eq_sel == "🆕 Criar Nova Equipe":
                _, ref_team = db.collection('equipes').add({
                    "nome": nome_nova_equipe.upper(), "descricao": desc_nova_equipe,
                    "professor_responsavel_id": user_id, "ativo": True
                })
                eq_id = ref_team.id
                db.collection('professores').add({
                    "usuario_id": user_id, "equipe_id": eq_id, "status_vinculo": "ativo",
                    "eh_responsavel": True, "pode_aprovar": True
                })
            else:
                eq_id = mapa_equipes.get(eq_sel)
                prof_id = mapa_profs_final.get(prof_sel) if (tipo == "Aluno" and prof_sel) else None
                if tipo_db == "aluno":
                    db.collection('alunos').add({
                        "usuario_id": user_id, "faixa_atual": faixa, "equipe_id": eq_id,
                        "professor_id": prof_id, "status_vinculo": "pendente"
                    })
                else:
                    db.collection('professores').add({
                        "usuario_id": user_id, "equipe_id": eq_id, "status_vinculo": "pendente"
                    })

            st.success("Pronto!")
            st.session_state.usuario = {"id": user_id, "nome": nome.upper(), "tipo": tipo_db}
            del st.session_state.registration_pending
            for k in ['goog_cep', 'goog_end', 'cpf_g', 'nmg', 'cpg']: st.session_state.pop(k, None)
            st.rerun()
        except Exception as e: st.error(f"Erro: {e}")
