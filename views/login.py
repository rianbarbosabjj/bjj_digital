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

    # CORREÇÃO MELHORADA: Verificação mais detalhada
    if "registration_pending" in st.session_state:
        user_data = st.session_state.registration_pending
        print(f"DEBUG - registration_pending: {user_data}")
        print(f"DEBUG - Tipo: {type(user_data)}")
        
        # Validação mais permissiva para testes
        if user_data and isinstance(user_data, dict):
            # Verificar se tem pelo menos email ou id
            if 'email' in user_data or 'id' in user_data:
                tela_completar_cadastro(user_data)
                return
            else:
                print(f"DEBUG - user_data sem email nem id: {user_data.keys()}")
        
        # Se falhou, mostrar mensagem mais específica
        st.error(f"⚠️ Dados de registro inválidos. Tipo: {type(user_data)}, Conteúdo: {user_data}")
        
        # Botão para limpar e recomeçar
        if st.button("🔄 Tentar Novamente"):
            st.session_state.registration_pending = None
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
                                    
                                    print(f"DEBUG - Google OAuth: Email={email}, Nome={nome}")
                                    
                                    exist = buscar_usuario_por_email(email)
                                    print(f"DEBUG - Usuário encontrado no banco: {exist}")
                                    
                                    if exist:
                                        # CORREÇÃO CRÍTICA: Verificar se exist tem estrutura correta
                                        if isinstance(exist, dict):
                                            if not exist.get("perfil_completo", True):
                                                # Garantir que temos todos os campos necessários
                                                if 'id' not in exist and '_id' in exist:
                                                    exist['id'] = exist['_id']
                                                if 'nome' not in exist:
                                                    exist['nome'] = nome
                                                if 'email' not in exist:
                                                    exist['email'] = email
                                                
                                                st.session_state.registration_pending = exist
                                                print(f"DEBUG - registration_pending definido: {exist}")
                                            else:
                                                st.session_state.usuario = exist
                                            st.rerun()
                                        else:
                                            st.error(f"Formato inválido do usuário: {type(exist)}")
                                    else:
                                        novo = criar_usuario_parcial_google(email, nome)
                                        print(f"DEBUG - Novo usuário criado: {novo}")
                                        
                                        if novo and isinstance(novo, dict):
                                            # Garantir estrutura correta
                                            if 'id' not in novo and '_id' in novo:
                                                novo['id'] = novo['_id']
                                            if 'nome' not in novo:
                                                novo['nome'] = nome
                                            if 'email' not in novo:
                                                novo['email'] = email
                                            
                                            st.session_state.registration_pending = novo
                                        else:
                                            st.error("Erro: função retornou dados inválidos")
                                        st.rerun()
                            except Exception as e:
                                st.error(f"Erro de conexão Google: {e}")
                                print(f"DEBUG - Erro detalhado: {str(e)}")
                                
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

# ... (mantenha as funções tela_cadastro_interno e tela_completar_cadastro iguais do código anterior) ...

def tela_cadastro_interno():
    # ... (mantenha o código original da função tela_cadastro_interno) ...
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
    
    print(f"DEBUG tela_completar_cadastro - user_data recebido: {user_data}")
    
    # CORREÇÃO MAIS PERMISSIVA para testes
    if not user_data:
        st.error("❌ Erro: Nenhum dado recebido.")
        if "registration_pending" in st.session_state:
            del st.session_state.registration_pending
        st.rerun()
        return
    
    # Aceitar qualquer dicionário que tenha pelo menos email
    if not isinstance(user_data, dict):
        st.error(f"❌ Erro: Formato inválido. Tipo recebido: {type(user_data)}")
        if "registration_pending" in st.session_state:
            del st.session_state.registration_pending
        st.rerun()
        return
    
    # Tentar extrair informações de várias formas possíveis
    nome_usuario = user_data.get('nome') or user_data.get('name') or 'Novo Usuário'
    email_usuario = user_data.get('email') or user_data.get('Email') or 'E-mail não informado'
    
    # Tentar obter ID de várias formas possíveis
    user_id = None
    for key in ['id', '_id', 'uid', 'user_id']:
        if key in user_data:
            user_id = user_data[key]
            break
    
    if not user_id:
        # Se não tem ID, tentar buscar pelo email
        db = get_db()
        if db:
            try:
                users_ref = db.collection('usuarios')
                query = list(users_ref.where('email', '==', email_usuario.lower()).stream())
                if query:
                    user_id = query[0].id
                    user_data['id'] = user_id
            except:
                pass
    
    # Se ainda não tem ID, vamos criar um temporário
    if not user_id:
        user_id = f"temp_{int(time.time())}"
        user_data['id'] = user_id
    
    print(f"DEBUG - Nome: {nome_usuario}, Email: {email_usuario}, ID: {user_id}")
    
    # Header amigável
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1>👋 Bem-vindo(a), {nome_usuario}!</h1>
        <p style="opacity: 0.8;">Vamos completar seu cadastro</p>
        <p><small>📧 {email_usuario}</small></p>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("📋 Precisamos de algumas informações adicionais para configurar sua conta.")
    
    db = get_db()
    if not db: 
        st.error("⚠️ Erro temporário de conexão. Tente novamente em alguns instantes.")
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
    except Exception as e:
        st.warning(f"⚠️ Não foi possível carregar a lista de equipes: {str(e)}")
        lista_equipes = ["Nenhuma (Vínculo Pendente)"]
        mapa_equipes = {}
        info_equipes = {}
    
    # Formulário simplificado para testes
    with st.container(border=True):
        st.markdown("### 📝 Informações Básicas")
        
        # CPF (obrigatório)
        cpf_inp = st.text_input("CPF *", 
                               placeholder="000.000.000-00",
                               help="Digite seu CPF para completar o cadastro")
        
        # Sexo
        sexo = st.selectbox("Sexo *", OPCOES_SEXO)
        
        # Data de nascimento
        data_nasc = st.date_input("Data de Nascimento *", 
                                 value=date(1990, 1, 1),
                                 min_value=date(1940, 1, 1), 
                                 max_value=date.today(), 
                                 format="DD/MM/YYYY")
        
        # Tipo de usuário
        tipo = st.selectbox("Eu sou *", ["Aluno(a)", "Professor(a)"])
        
        # Faixa
        if "Aluno" in tipo:
            faixa = st.selectbox("Minha faixa atual *", [
                "Branca", "Cinza e Branca", "Cinza", "Cinza e Preta",
                "Amarela e Branca", "Amarela", "Amarela e Preta",
                "Laranja e Branca", "Laranja", "Laranja e Preta",
                "Verde e Branca", "Verde", "Verde e Preta",
                "Azul", "Roxa", "Marrom", "Preta"
            ])
        else:
            faixa = st.selectbox("Minha faixa atual *", ["Marrom", "Preta"])
            st.caption("Professores devem ser faixa Marrom ou Preta")
        
        # Equipe
        eq_sel = st.selectbox("Equipe", lista_equipes)
        
        # Opções extras para professores
        nome_nova_equipe = None
        if tipo == "Professor(a)" and eq_sel == "Nenhuma (Vínculo Pendente)":
            criar_nova = st.checkbox("Desejo criar uma nova equipe")
            if criar_nova:
                nome_nova_equipe = st.text_input("Nome da Nova Equipe *")
                desc_nova_equipe = st.text_input("Descrição (Opcional)")
    
    # Botões de ação
    st.markdown("---")
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("✅ Finalizar Cadastro", type="primary", use_container_width=True):
            # Validações básicas
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
                    if d.id != user_id:
                        st.error("❌ Este CPF já está cadastrado em outra conta")
                        return
            except Exception as e:
                print(f"DEBUG - Erro ao verificar CPF: {e}")
            
            # Validar criação de nova equipe
            if tipo == "Professor(a)" and criar_nova and not nome_nova_equipe:
                st.error("❌ Informe o nome da nova equipe")
                return
            
            try:
                with st.spinner("Salvando seus dados..."):
                    tipo_db = "professor" if "Professor" in tipo else "aluno"
                    
                    # Dados para atualização
                    update_data = {
                        "cpf": cpf_fin,
                        "tipo_usuario": tipo_db,
                        "perfil_completo": True,
                        "faixa_atual": faixa,
                        "sexo": sexo,
                        "data_nascimento": data_nasc.isoformat(),
                        "auth_provider": "google",
                        "ultima_atualizacao": firestore.SERVER_TIMESTAMP
                    }
                    
                    # Se for um ID temporário, precisamos criar o usuário
                    if user_id.startswith('temp_'):
                        # Criar novo usuário no banco
                        user_data_to_save = {
                            "nome": nome_usuario,
                            "email": email_usuario.lower(),
                            "cpf": cpf_fin,
                            "tipo_usuario": tipo_db,
                            "auth_provider": "google",
                            "perfil_completo": True,
                            "faixa_atual": faixa,
                            "sexo": sexo,
                            "data_nascimento": data_nasc.isoformat(),
                            "data_criacao": firestore.SERVER_TIMESTAMP
                        }
                        
                        doc_ref = db.collection('usuarios').add(user_data_to_save)
                        user_id = doc_ref[1].id
                        user_data['id'] = user_id
                    else:
                        # Atualizar usuário existente
                        db.collection('usuarios').document(user_id).update(update_data)
                    
                    # Criar vínculos se necessário
                    if eq_sel != "Nenhuma (Vínculo Pendente)":
                        eq_id = mapa_equipes.get(eq_sel)
                        
                        if tipo_db == "professor":
                            if criar_nova and nome_nova_equipe:
                                # Criar nova equipe
                                _, ref_team = db.collection('equipes').add({
                                    "nome": nome_nova_equipe.upper(),
                                    "descricao": desc_nova_equipe if desc_nova_equipe else "",
                                    "professor_responsavel_id": user_id,
                                    "ativo": True,
                                    "data_criacao": firestore.SERVER_TIMESTAMP
                                })
                                eq_id = ref_team.id
                                
                                # Criar vínculo como responsável
                                db.collection('professores').add({
                                    "usuario_id": user_id,
                                    "equipe_id": eq_id,
                                    "status_vinculo": "ativo",
                                    "eh_responsavel": True,
                                    "pode_aprovar": True,
                                    "data_vinculo": firestore.SERVER_TIMESTAMP
                                })
                            elif eq_id:
                                # Vínculo como professor adjunto
                                db.collection('professores').add({
                                    "usuario_id": user_id,
                                    "equipe_id": eq_id,
                                    "status_vinculo": "pendente",
                                    "eh_responsavel": False,
                                    "tipo_solicitacao": "adjunto",
                                    "data_solicitacao": firestore.SERVER_TIMESTAMP
                                })
                        else:  # Aluno
                            if eq_id:
                                db.collection('alunos').add({
                                    "usuario_id": user_id,
                                    "faixa_atual": faixa,
                                    "equipe_id": eq_id,
                                    "status_vinculo": "pendente",
                                    "data_solicitacao": firestore.SERVER_TIMESTAMP
                                })
                    
                    # Atualizar sessão
                    user_data.update({
                        'perfil_completo': True,
                        'tipo': tipo_db,
                        'faixa_atual': faixa,
                        'nome': nome_usuario,
                        'id': user_id
                    })
                    st.session_state.usuario = user_data
                    
                    # Limpar estado
                    if "registration_pending" in st.session_state:
                        del st.session_state.registration_pending
                    
                    st.success("""
                    🎉 **Cadastro completado com sucesso!**
                    
                    Redirecionando para o sistema...
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
                st.warning("Cadastro cancelado")
                time.sleep(1)
                st.rerun()
