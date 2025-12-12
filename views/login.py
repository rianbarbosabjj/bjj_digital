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

    # CORREÇÃO: Verificar se registration_pending existe e tem dados
    if "registration_pending" in st.session_state:
        # CORREÇÃO: Passar o valor direto, não uma referência
        user_data = st.session_state.registration_pending
        
        # Verificar se user_data tem dados válidos
        if user_data and isinstance(user_data, dict) and ('id' in user_data or 'email' in user_data):
            tela_completar_cadastro(user_data)
        else:
            st.error("Dados de registro inválidos ou incompletos.")
            st.session_state.registration_pending = None
            time.sleep(2)
            st.rerun()
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
                                r = requests.get("https://www.googleapis.com/oauth2/v1/userinfo", 
                                               headers={"Authorization": f"Bearer {token}"})
                                if r.status_code == 200:
                                    u_info = r.json()
                                    email = u_info["email"].lower()
                                    nome = u_info.get("name", "").upper()
                                    
                                    # CORREÇÃO: Debug para ver o que está vindo
                                    print(f"Google Login: Email={email}, Nome={nome}")
                                    
                                    exist = buscar_usuario_por_email(email)
                                    if exist:
                                        # CORREÇÃO: Verificar estrutura do usuário
                                        if not exist.get("perfil_completo", True):
                                            st.session_state.registration_pending = exist
                                            print(f"Usuário encontrado: {exist}")
                                        else:
                                            st.session_state.usuario = exist
                                        st.rerun()
                                    else:
                                        # CORREÇÃO: Criar usuário parcial
                                        novo = criar_usuario_parcial_google(email, nome)
                                        if novo:
                                            st.session_state.registration_pending = novo
                                            print(f"Novo usuário criado: {novo}")
                                        else:
                                            st.error("Erro ao criar usuário parcial")
                                        st.rerun()
                            except Exception as e:
                                st.error(f"Erro de conexão Google: {e}")
                                print(f"Erro detalhado: {str(e)}")
                                
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
        with cf: 
            faixa = st.selectbox("Faixa:", [
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
    
    # CORREÇÃO CRÍTICA: Verificação robusta do user_data
    if not user_data:
        st.error("❌ Erro: Dados do usuário não recebidos.")
        if "registration_pending" in st.session_state:
            del st.session_state.registration_pending
        st.rerun()
        return
    
    # CORREÇÃO: Garantir que é um dicionário
    if not isinstance(user_data, dict):
        st.error("❌ Erro: Formato inválido dos dados do usuário.")
        if "registration_pending" in st.session_state:
            del st.session_state.registration_pending
        st.rerun()
        return
    
    # CORREÇÃO: Verificar campos mínimos
    required_fields = ['id', 'email']
    missing_fields = [field for field in required_fields if field not in user_data]
    
    if missing_fields:
        st.error(f"❌ Dados incompletos. Faltam: {', '.join(missing_fields)}")
        print(f"DEBUG: user_data recebido = {user_data}")
        if "registration_pending" in st.session_state:
            del st.session_state.registration_pending
        st.rerun()
        return
    
    # CORREÇÃO: Obter nome de forma segura
    nome_usuario = user_data.get('nome', '')
    if not nome_usuario or nome_usuario.strip() == '':
        # Tentar obter do email se nome estiver vazio
        email = user_data.get('email', '')
        if email:
            nome_usuario = email.split('@')[0].title()
        else:
            nome_usuario = "Novo Usuário"
    
    email_usuario = user_data.get('email', 'E-mail não informado')
    
    # Header corrigido
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1>👋 Olá, {nome_usuario}!</h1>
        <p style="opacity: 0.8;">Complete seu cadastro para acessar o sistema</p>
        <p><small>E-mail: {email_usuario}</small></p>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("📋 Para finalizar seu acesso via Google, precisamos de alguns dados adicionais.")
    
    db = get_db()
    if not db: 
        st.error("Erro de conexão com o banco de dados")
        return

    # Carregar listas para o formulário
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
                if eid not in profs_por_equipe: 
                    profs_por_equipe[eid] = []
                profs_por_equipe[eid].append((mapa_nomes_profs[uid], uid))
    except Exception as e:
        st.warning(f"⚠️ Algumas opções podem estar limitadas: {str(e)}")
        lista_equipes = ["Nenhuma (Vínculo Pendente)"]
        mapa_equipes = {}
        info_equipes = {}
        mapa_nomes_profs = {}
        profs_por_equipe = {}

    # Formulário de dados
    with st.container(border=True):
        st.markdown("### 📝 Dados Pessoais")
        
        c_cpf, c_sexo, c_nasc = st.columns([2, 1, 1])
        
        with c_cpf:
            cpf_inp = st.text_input("CPF (Obrigatório):", 
                                   placeholder="000.000.000-00",
                                   help="Digite apenas números ou com pontuação")
        
        with c_sexo:
            sexo = st.selectbox("Sexo:", OPCOES_SEXO)
        
        with c_nasc:
            data_nasc = st.date_input("Data de Nascimento:", 
                                     value=date(1990, 1, 1),
                                     min_value=date(1940, 1, 1), 
                                     max_value=date.today(), 
                                     format="DD/MM/YYYY")

        # Tipo de usuário
        tipo = st.selectbox("Sou:", ["Aluno(a)", "Professor(a)"])
        
        # Faixa e equipe
        cf, ce = st.columns(2)
        nome_nova_equipe = None
        desc_nova_equipe = None
        
        if "Aluno" in tipo:
            with cf: 
                faixa = st.selectbox("Faixa:", [
                    "Branca", "Cinza e Branca", "Cinza", "Cinza e Preta",
                    "Amarela e Branca", "Amarela", "Amarela e Preta",
                    "Laranja e Branca", "Laranja", "Laranja e Preta",
                    "Verde e Branca", "Verde", "Verde e Preta",
                    "Azul", "Roxa", "Marrom", "Preta"
                ])
            
            with ce: 
                eq_sel = st.selectbox("Equipe:", lista_equipes)
            
            # Professores disponíveis para a equipe selecionada
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
            
            prof_sel = st.selectbox("Professor Responsável:", lista_profs_filtrada)
            
        else:  # Professor
            with cf: 
                faixa = st.selectbox("Faixa:", ["Marrom", "Preta"])
                st.caption("Professores devem ser faixa Marrom ou Preta")
            
            with ce:
                opcoes_prof_eq = lista_equipes + ["🆕 Criar Nova Equipe"]
                eq_sel = st.selectbox("Equipe:", opcoes_prof_eq)
            
            if eq_sel == "🆕 Criar Nova Equipe":
                st.info("⭐ Você será cadastrado como **Professor(a) Responsável**.")
                nome_nova_equipe = st.text_input("Nome da Nova Equipe:")
                desc_nova_equipe = st.text_input("Descrição (Opcional):")
            else:
                st.info("ℹ️ Você será registrado como **Professor(a) Adjunto(a)**.")

        # Endereço
        st.markdown("### 📍 Endereço")
        
        if 'google_cep' not in st.session_state: 
            st.session_state.google_cep = ''
        
        c_cep, c_btn = st.columns([3, 1])
        
        with c_cep:
            cep = st.text_input("CEP:", key="cep_g", 
                               value=st.session_state.google_cep,
                               placeholder="00000-000")
        
        with c_btn:
            st.write("")  # Espaçamento
            if st.button("🔍 Buscar", key="btn_g", use_container_width=True):
                if cep:
                    end = buscar_cep(cep)
                    if end:
                        st.session_state.google_cep = cep
                        st.session_state.google_end = end
                        st.success("✅ Endereço encontrado!")
                    else:
                        st.error("CEP não encontrado")
                else:
                    st.warning("Digite um CEP")
        
        # Campos de endereço
        ec = st.session_state.get('google_end', {})
        
        col1, col2 = st.columns(2)
        with col1:
            logr = st.text_input("Logradouro:", 
                                value=ec.get('logradouro', ''),
                                placeholder="Rua, Avenida, etc.")
            cid = st.text_input("Cidade:", 
                               value=ec.get('cidade', ''),
                               placeholder="Nome da cidade")
        
        with col2:
            bairro = st.text_input("Bairro:", 
                                  value=ec.get('bairro', ''),
                                  placeholder="Nome do bairro")
            uf = st.text_input("UF:", 
                              value=ec.get('uf', ''),
                              placeholder="SP",
                              max_chars=2).upper()
        
        col_num, col_comp = st.columns(2)
        with col_num:
            num = st.text_input("Número:", placeholder="123")
        
        with col_comp:
            comp = st.text_input("Complemento:", placeholder="Apto, Bloco, etc.")

    # Botões de ação
    st.markdown("---")
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("✅ Finalizar Cadastro", type="primary", use_container_width=True):
            # Validações
            if not cpf_inp:
                st.error("❌ CPF é obrigatório")
                return
            
            cpf_fin = formatar_e_validar_cpf(cpf_inp)
            if not cpf_fin:
                st.error("❌ CPF inválido")
                return
            
            # Verificar duplicidade de CPF
            try:
                q_cpf = list(db.collection('usuarios').where('cpf', '==', cpf_fin).stream())
                for d in q_cpf:
                    if d.id != user_data['id']:
                        st.error("❌ Este CPF já está cadastrado em outra conta")
                        return
            except Exception as e:
                st.error(f"Erro ao verificar CPF: {e}")
                return
            
            # Validar criação de nova equipe
            if tipo == "Professor(a)" and eq_sel == "🆕 Criar Nova Equipe":
                if not nome_nova_equipe:
                    st.error("❌ Informe o nome da nova equipe")
                    return
            
            # Processar dados
            try:
                with st.spinner("Salvando seus dados..."):
                    uid = user_data['id']
                    tipo_db = "professor" if "Professor" in tipo else "aluno"
                    
                    # Dados para atualização
                    update_data = {
                        "cpf": cpf_fin,
                        "tipo_usuario": tipo_db,
                        "perfil_completo": True,
                        "faixa_atual": faixa,
                        "sexo": sexo,
                        "data_nascimento": data_nasc.isoformat() if data_nasc else None,
                        "auth_provider": "google",
                        "ultima_atualizacao": firestore.SERVER_TIMESTAMP
                    }
                    
                    # Adicionar endereço se preenchido
                    if cep:
                        update_data["cep"] = formatar_cep(cep)
                    if logr:
                        update_data["logradouro"] = logr.upper()
                    if num:
                        update_data["numero"] = num
                    if comp:
                        update_data["complemento"] = comp.upper()
                    if bairro:
                        update_data["bairro"] = bairro.upper()
                    if cid:
                        update_data["cidade"] = cid.upper()
                    if uf:
                        update_data["uf"] = uf.upper()
                    
                    # Atualizar usuário
                    db.collection('usuarios').document(uid).update(update_data)
                    
                    # Criar vínculos
                    if tipo_db == "professor":
                        if eq_sel == "🆕 Criar Nova Equipe":
                            # Criar nova equipe
                            _, ref_team = db.collection('equipes').add({
                                "nome": nome_nova_equipe.upper(),
                                "descricao": desc_nova_equipe if desc_nova_equipe else "",
                                "professor_responsavel_id": uid,
                                "ativo": True,
                                "data_criacao": firestore.SERVER_TIMESTAMP
                            })
                            eq_id = ref_team.id
                            
                            # Criar vínculo como responsável
                            db.collection('professores').add({
                                "usuario_id": uid,
                                "equipe_id": eq_id,
                                "status_vinculo": "ativo",
                                "eh_responsavel": True,
                                "pode_aprovar": True,
                                "data_vinculo": firestore.SERVER_TIMESTAMP
                            })
                        else:
                            # Vínculo como professor adjunto
                            eq_id = mapa_equipes.get(eq_sel)
                            if eq_id:
                                db.collection('professores').add({
                                    "usuario_id": uid,
                                    "equipe_id": eq_id,
                                    "status_vinculo": "pendente",
                                    "eh_responsavel": False,
                                    "tipo_solicitacao": "adjunto",
                                    "data_solicitacao": firestore.SERVER_TIMESTAMP
                                })
                    else:  # Aluno
                        eq_id = mapa_equipes.get(eq_sel)
                        prof_id = None
                        
                        if prof_sel and prof_sel != "Nenhum (Vínculo Pendente)":
                            prof_id = mapa_profs_final.get(prof_sel)
                        
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
                        'faixa_atual': faixa,
                        'nome': nome_usuario
                    })
                    st.session_state.usuario = user_data
                    
                    # Limpar estado
                    if "registration_pending" in st.session_state:
                        del st.session_state.registration_pended
                    
                    # Limpar estados temporários
                    for key in ['google_cep', 'google_end']:
                        if key in st.session_state:
                            del st.session_state[key]
                    
                    st.success("""
                    🎉 **Cadastro completado com sucesso!**
                    
                    Você será redirecionado para o sistema em instantes...
                    """)
                    
                    time.sleep(2)
                    st.rerun()
                    
            except Exception as e:
                st.error(f"❌ Erro ao salvar: {str(e)}")
                print(f"DEBUG - Erro detalhado: {str(e)}")
    
    with col_btn2:
        if st.button("❌ Cancelar", type="secondary", use_container_width=True):
            if st.confirm("Deseja realmente cancelar o cadastro?"):
                if "registration_pending" in st.session_state:
                    del st.session_state.registration_pending
                
                # Limpar estados temporários
                for key in ['google_cep', 'google_end']:
                    if key in st.session_state:
                        del st.session_state[key]
                
                st.warning("Cadastro cancelado")
                time.sleep(1)
                st.rerun()
