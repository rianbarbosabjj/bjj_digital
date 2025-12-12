import streamlit as st
import os
import requests 
import bcrypt
import time
from datetime import datetime, date
from streamlit_oauth import OAuth2Component

# Importações locais
from auth import autenticar_local, criar_usuario_parcial_google, buscar_usuario_por_email
from utils import formatar_e_validar_cpf, formatar_cep, buscar_cep, gerar_senha_temporaria, enviar_email_recuperacao
from database import get_db, OPCOES_SEXO
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
                cl, cc, cr = st.columns([1, 2, 1])
                with cc: st.image(logo, use_container_width=True)

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
                                st.rerun() 
                            else:
                                st.error("Credenciais inválidas.")

                col_a, col_b = st.columns(2)
                if col_a.button("📋 Criar Conta", use_container_width=True):
                    st.session_state["modo_login"] = "cadastro"; st.rerun()
                if col_b.button("🔑 Recuperar Senha", use_container_width=True):
                    st.session_state["modo_login"] = "recuperar"; st.rerun()

                st.markdown("""
                    <div style='display: flex; align-items: center; justify-content: center; margin: 20px 0;'>
                        <div style='flex: 1; height: 1px; background-color: #555;'></div>
                        <span style='padding: 0 10px; color: #888; font-size: 0.8em;'>OU ENTRE COM</span>
                        <div style='flex: 1; height: 1px; background-color: #555;'></div>
                    </div>
                """, unsafe_allow_html=True)
                
                if oauth_google:
                    try:
                        # Botão Google Estilizado
                        res = oauth_google.authorize_button(
                            name="Continuar com Google",
                            icon="https://www.google.com/favicon.ico",
                            redirect_uri=REDIRECT_URI, 
                            scope="email profile", 
                            key="google_auth", 
                            use_container_width=True
                        )
                        
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
                                st.error(f"Erro de conexão Google: {e}")
                                
                    except Exception as e:
                        st.warning("Sessão expirada. Recarregando...")
                        st.query_params.clear()
                        time.sleep(1)
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
                    if not db: st.error("Erro no banco."); return
                    
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
                st.session_state["modo_login"] = "login"; st.rerun()

def tela_cadastro_interno():
    st.subheader("📋 Cadastro de Novo Usuário")
    db = get_db()
    if not db: st.error("Erro de conexão."); return
    
    try:
        equipes_ref = db.collection('equipes').stream()
        lista_equipes = ["Nenhuma (Vínculo Pendente)"]
        mapa_equipes = {} 
        info_equipes = {} 
        
        for doc in equipes_ref:
            d = doc.to_dict()
            nm = d.get('nome', 'Sem Nome')
            lista_equipes.append(nm)
            mapa_equipes[nm] = doc.id
            info_equipes[doc.id] = d
        
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
    
    cf, ce = st.columns(2)
    nome_nova_equipe = None; desc_nova_equipe = None
    
    # Lógica de seleção (Inclusiva)
    if "Aluno" in tipo:
        with cf: faixa = st.selectbox("Faixa:", [
            " ", "Branca", "Cinza e Branca", "Cinza", "Cinza e Preta",
            "Amarela e Branca", "Amarela", "Amarela e Preta",
            "Laranja e Branca", "Laranja", "Laranja e Preta",
            "Verde e Branca", "Verde", "Verde e Preta",
            "Azul", "Roxa", "Marrom", "Preta"
        ])
        with ce: eq_sel = st.selectbox("Equipe:", lista_equipes)
        
        lista_profs_filtrada = ["Nenhum (Vínculo Pendente)"]
        mapa_profs_final = {}
        eq_id_sel = mapa_equipes.get(eq_sel)
        prof_resp_id = None

        if eq_id_sel:
            dados_eq = info_equipes.get(eq_id_sel, {})
            prof_resp_id = dados_eq.get('professor_responsavel_id')
            
            if prof_resp_id and prof_resp_id in mapa_nomes_profs:
                nome_resp = mapa_nomes_profs[prof_resp_id]
                label_resp = f"{nome_resp} (Responsável)"
                lista_profs_filtrada.append(label_resp)
                mapa_profs_final[label_resp] = prof_resp_id

            if eq_id_sel in profs_por_equipe:
                for p_nome, p_uid in profs_por_equipe[eq_id_sel]:
                    if p_uid != prof_resp_id:
                        lista_profs_filtrada.append(p_nome)
                        mapa_profs_final[p_nome] = p_uid
        
        prof_sel = st.selectbox("Professor(a):", lista_profs_filtrada)
        
    else: 
        with cf: faixa = st.selectbox("Faixa:", ["Marrom", "Preta"])
        st.caption("Professores(as) devem ser Marrom ou Preta.")
        with ce:
            opcoes_prof_eq = lista_equipes + ["🆕 Criar Nova Equipe"]
            eq_sel = st.selectbox("Equipe:", opcoes_prof_eq)
        
        if eq_sel == "🆕 Criar Nova Equipe":
            st.info("⭐ Você será cadastrado como **Professor(a) Responsável**.")
            nome_nova_equipe = st.text_input("Nome da Nova Equipe:")
            desc_nova_equipe = st.text_input("Descrição (Opcional):")
        else:
            st.info("ℹ️ Solicitação para **Professor(a) Adjunto(a)**.")
            st.checkbox("Confirmar: Sou Professor(a) Adjunto", value=True)

    st.markdown("#### Endereço")
    if 'cad_cep' not in st.session_state: st.session_state.cad_cep = ''
    
    c_cep, c_btn = st.columns([3, 1])
    cep = c_cep.text_input("CEP:", key="input_cep_cad", value=st.session_state.cad_cep)
    if c_btn.button("🔎Buscar CEP", key="btn_cep_cad"):
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
        
        if "Professor" in tipo and eq_sel == "🆕 Criar Nova Equipe" and not nome_nova_equipe:
            st.warning("Informe o nome da equipe."); return

        users_ref = db.collection('usuarios')
        if len(list(users_ref.where('email', '==', email_fin).stream())) > 0:
            st.error("Email já cadastrado."); return
        if len(list(users_ref.where('cpf', '==', cpf_fin).stream())) > 0:
            st.error("CPF já cadastrado."); return
            
        try:
            with st.spinner("Criando..."):
                hashed = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
                # Normaliza para banco (remove o (a))
                tipo_db = "professor" if "Professor" in tipo else "aluno"
                
                novo_user = {
                    "nome": nome_fin, "email": email_fin, "cpf": cpf_fin, 
                    "tipo_usuario": tipo_db, "senha": hashed, "auth_provider": "local", 
                    "perfil_completo": True, "cep": cep_fin, "logradouro": logr.upper(),
                    "numero": num, "complemento": comp.upper(), "bairro": bairro.upper(),
                    "cidade": cid.upper(), "uf": uf.upper(), "data_criacao": firestore.SERVER_TIMESTAMP,
                    "sexo": sexo,
                    "data_nascimento": data_nasc.isoformat() if data_nasc else None
                }
                _, doc_ref = db.collection('usuarios').add(novo_user)
                user_id = doc_ref.id
                
                eq_id = None
                if tipo_db == "professor":
                    if eq_sel == "🆕 Criar Nova Equipe":
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
                        db.collection('professores').add({
                            "usuario_id": user_id, 
                            "equipe_id": eq_id, 
                            "status_vinculo": "pendente",
                            "eh_responsavel": False,
                            "tipo_solicitacao": "adjunto"
                        })
                else:
                    eq_id = mapa_equipes.get(eq_sel)
                    prof_id = mapa_profs_final.get(prof_sel) if (tipo == "Aluno(a)" and prof_sel) else None
                    db.collection('alunos').add({
                        "usuario_id": user_id, "faixa_atual": faixa, "equipe_id": eq_id, 
                        "professor_id": prof_id, "status_vinculo": "pendente"
                    })
                
                st.success("Sucesso!"); 
                st.session_state.usuario = {"id": user_id, "nome": nome_fin, "tipo": tipo_db}
                for k in ['cad_cep', 'cad_end']: st.session_state.pop(k, None)
                st.session_state["modo_login"] = "login"; st.rerun()
        except Exception as e: st.error(f"Erro: {e}")

    if st.button("Voltar", use_container_width=True):
        st.session_state["modo_login"] = "login"; st.rerun()

def tela_completar_cadastro(user_data):
    """Tela para completar cadastro após registro via Google"""
    
    # CORREÇÃO 1: Validação segura do user_data
    if not user_data:
        st.error("❌ Dados de registro não encontrados.")
        st.session_state.registration_pending = None
        time.sleep(1)
        st.rerun()
        return
    
    # CORREÇÃO 2: Garantir que temos um nome válido
    nome_usuario = user_data.get('nome', '')
    if not nome_usuario or nome_usuario == '':
        nome_usuario = "Novo Usuário"
    
    # CORREÇÃO 3: Exibir header de forma segura
    st.subheader(f"👋 Olá, {nome_usuario}!")
    st.info("Para finalizar seu acesso via Google, precisamos de alguns dados.")
    
    db = get_db()
    if not db: 
        st.error("Erro de conexão com o banco de dados")
        return

    # CORREÇÃO 4: Verificar se user_data tem ID
    if 'id' not in user_data:
        st.error("ID do usuário não encontrado nos dados de registro.")
        st.session_state.registration_pending = None
        time.sleep(1)
        st.rerun()
        return

    # ... (Carga de listas igual ao cadastro interno) ...
    try:
        equipes_ref = db.collection('equipes').stream()
        lista_equipes = ["Nenhuma (Vínculo Pendente)"]
        mapa_equipes = {} 
        info_equipes = {} 
        for doc in equipes_ref:
            d = doc.to_dict(); nm = d.get('nome', 'Sem Nome')
            lista_equipes.append(nm); mapa_equipes[nm] = doc.id; info_equipes[doc.id] = d
        
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
    except Exception as e:
        st.warning(f"Algumas opções podem estar limitadas: {e}")

    # CORREÇÃO 5: Adicionar validação do CPF como obrigatório
    c_cpf, c_sexo, c_nasc = st.columns([2, 1, 1])
    cpf_inp = c_cpf.text_input("CPF (Obrigatório):", help="Digite seu CPF para completar o cadastro")
    
    # CORREÇÃO 6: Validar CPF antes de prosseguir
    if cpf_inp:
        cpf_validado = formatar_e_validar_cpf(cpf_inp)
        if cpf_validado:
            # Verificar se CPF já existe no banco
            q_cpf = list(db.collection('usuarios').where('cpf', '==', cpf_validado).stream())
            for d in q_cpf:
                if d.id != user_data['id']:
                    st.error("⚠️ Este CPF já está cadastrado em outra conta.")
                    cpf_inp = ""
                    st.stop()
    
    sexo = c_sexo.selectbox("Sexo:", OPCOES_SEXO)
    data_nasc = c_nasc.date_input("Nascimento:", value=None, min_value=date(1940,1,1), max_value=date.today(), format="DD/MM/YYYY")

    tipo = st.selectbox("Sou:", ["Aluno(a)", "Professor(a)"])
    
    cf, ce = st.columns(2)
    nome_nova_equipe = None; desc_nova_equipe = None
    
    # CORREÇÃO 7: Faixas corretas para aluno
    if "Aluno" in tipo:
        with cf: 
            faixa = st.selectbox("Faixa:", [
                "Branca", "Cinza e Branca", "Cinza", "Cinza e Preta",
                "Amarela e Branca", "Amarela", "Amarela e Preta",
                "Laranja e Branca", "Laranja", "Laranja e Preta",
                "Verde e Branca", "Verde", "Verde e Preta",
                "Azul", "Roxa", "Marrom", "Preta"
            ])
        with ce: eq_sel = st.selectbox("Equipe:", lista_equipes)
        
        lista_profs_filtrada = ["Nenhum (Vínculo Pendente)"]
        mapa_profs_final = {}
        eq_id_sel = mapa_equipes.get(eq_sel)
        prof_resp_id = None

        if eq_id_sel:
            dados_eq = info_equipes.get(eq_id_sel, {})
            prof_resp_id = dados_eq.get('professor_responsavel_id')
            if prof_resp_id and prof_resp_id in mapa_nomes_profs:
                nome_resp = mapa_nomes_profs[prof_resp_id]
                label_resp = f"{nome_resp} (Responsável)"
                lista_profs_filtrada.append(label_resp)
                mapa_profs_final[label_resp] = prof_resp_id
            if eq_id_sel in profs_por_equipe:
                for p_nome, p_uid in profs_por_equipe[eq_id_sel]:
                    if p_uid != prof_resp_id:
                        lista_profs_filtrada.append(p_nome)
                        mapa_profs_final[p_nome] = p_uid
        prof_sel = st.selectbox("Professor:", lista_profs_filtrada)
        
    else: 
        with cf: faixa = st.selectbox("Faixa:", ["Marrom", "Preta"])
        with ce:
            opcoes_prof_eq = lista_equipes + ["🆕 Criar Nova Equipe"]
            eq_sel = st.selectbox("Equipe:", opcoes_prof_eq)
        if eq_sel == "🆕 Criar Nova Equipe":
            nome_nova_equipe = st.text_input("Nome da Nova Equipe:")
            desc_nova_equipe = st.text_input("Descrição:")

    st.markdown("#### Endereço")
    if 'google_cep' not in st.session_state: st.session_state.google_cep = ''
    
    c_cep, c_btn = st.columns([3, 1])
    cep = c_cep.text_input("CEP:", key="cep_g", value=st.session_state.google_cep)
    if c_btn.button("Buscar", key="btn_g"):
        end = buscar_cep(cep)
        if end:
            st.session_state.google_cep = cep
            st.session_state.google_end = end
            st.success("OK!")
        else: st.error("Inválido")
    
    ec = st.session_state.get('google_end', {})
    c1, c2 = st.columns(2)
    logr = c1.text_input("Logradouro:", value=ec.get('logradouro',''))
    bairro = c2.text_input("Bairro:", value=ec.get('bairro',''))
    c3, c4 = st.columns(2)
    cid = c3.text_input("Cidade:", value=ec.get('cidade',''))
    uf = c4.text_input("UF:", value=ec.get('uf',''))
    c5, c6 = st.columns(2)
    num = c5.text_input("Número:")
    comp = c6.text_input("Complemento:")

    # CORREÇÃO 8: Adicionar validação obrigatória do CPF
    if st.button("Finalizar Cadastro", type="primary", use_container_width=True):
        if not cpf_inp:
            st.error("❌ CPF é obrigatório para completar o cadastro.")
            return
        
        cpf_fin = formatar_e_validar_cpf(cpf_inp)
        if not cpf_fin: 
            st.error("❌ CPF Inválido. Digite um CPF válido.")
            return
        
        # Verificação adicional de CPF duplicado
        q_cpf = list(db.collection('usuarios').where('cpf', '==', cpf_fin).stream())
        for d in q_cpf:
            if d.id != user_data['id']:
                st.error("❌ CPF já cadastrado em outra conta.")
                return
        
        try:
            with st.spinner("Salvando..."):
                uid = user_data['id']
                tipo_db = "professor" if "Professor" in tipo else "aluno"
                
                # CORREÇÃO 9: Atualizar apenas os campos necessários
                update_data = {
                    "cpf": cpf_fin, 
                    "tipo_usuario": tipo_db, 
                    "perfil_completo": True,
                    "cep": formatar_cep(cep) if cep else None, 
                    "logradouro": logr.upper() if logr else None, 
                    "numero": num if num else None,
                    "complemento": comp.upper() if comp else None, 
                    "bairro": bairro.upper() if bairro else None, 
                    "cidade": cid.upper() if cid else None, 
                    "uf": uf.upper() if uf else None, 
                    "faixa_atual": faixa,
                    "sexo": sexo,
                    "data_nascimento": data_nasc.isoformat() if data_nasc else None,
                    "auth_provider": "google",  # Garantir que está marcado como Google
                    "ultima_atualizacao": firestore.SERVER_TIMESTAMP
                }
                
                # Remover campos None para não sobrescrever com None
                update_data = {k: v for k, v in update_data.items() if v is not None}
                
                db.collection('usuarios').document(uid).update(update_data)
                
                # Criar vínculos
                if tipo_db == "professor":
                    if eq_sel == "🆕 Criar Nova Equipe":
                        if not nome_nova_equipe:
                            st.error("Informe o nome da nova equipe.")
                            return
                            
                        _, ref_team = db.collection('equipes').add({
                            "nome": nome_nova_equipe.upper(), 
                            "descricao": desc_nova_equipe,
                            "professor_responsavel_id": uid, 
                            "ativo": True,
                            "data_criacao": firestore.SERVER_TIMESTAMP
                        })
                        eq_id = ref_team.id
                        db.collection('professores').add({
                            "usuario_id": uid, 
                            "equipe_id": eq_id, 
                            "status_vinculo": "ativo", 
                            "eh_responsavel": True, 
                            "pode_aprovar": True,
                            "data_vinculo": firestore.SERVER_TIMESTAMP
                        })
                    else:
                        eq_id = mapa_equipes.get(eq_sel)
                        if eq_id:
                            db.collection('professores').add({
                                "usuario_id": uid, 
                                "equipe_id": eq_id, 
                                "status_vinculo": "pendente", 
                                "eh_responsavel": False,
                                "data_solicitacao": firestore.SERVER_TIMESTAMP
                            })
                else:
                    eq_id = mapa_equipes.get(eq_sel)
                    prof_id = mapa_profs_final.get(prof_sel) if (tipo == "Aluno(a)" and prof_sel and prof_sel != "Nenhum (Vínculo Pendente)") else None
                    
                    if eq_id:
                        db.collection('alunos').add({
                            "usuario_id": uid, 
                            "faixa_atual": faixa, 
                            "equipe_id": eq_id, 
                            "professor_id": prof_id, 
                            "status_vinculo": "pendente",
                            "data_solicitacao": firestore.SERVER_TIMESTAMP
                        })
                
                # Atualizar sessão
                user_data.update({
                    'perfil_completo': True,
                    'tipo': tipo_db,
                    'faixa_atual': faixa
                })
                st.session_state.usuario = user_data
                
                # Limpar estado de registro pendente
                del st.session_state.registration_pending
                
                # Limpar estados temporários
                for key in ['google_cep', 'google_end']:
                    if key in st.session_state:
                        del st.session_state[key]
                
                st.success("✅ Cadastro Completo! Redirecionando...")
                time.sleep(2)
                st.rerun()

        except Exception as e:
            st.error(f"❌ Erro ao salvar: {e}")
            st.info("Por favor, tente novamente ou entre em contato com o suporte.")

    # CORREÇÃO 10: Botão de cancelar melhorado
    st.markdown("---")
    col_cancel1, col_cancel2, col_cancel3 = st.columns([1, 2, 1])
    
    with col_cancel2:
        if st.button("❌ Cancelar e Sair", use_container_width=True, type="secondary"):
            if st.confirm("Tem certeza que deseja cancelar o cadastro? Seus dados parciais serão mantidos para tentar novamente mais tarde."):
                del st.session_state.registration_pending
                st.success("Cadastro cancelado. Você pode completá-lo mais tarde.")
                time.sleep(1)
                st.rerun()
