import streamlit as st
import sqlite3
import bcrypt
import pandas as pd
import os  # <--- 1. ADICIONADO O IMPORT OS
from streamlit_oauth import OAuth2Component
from auth import autenticar_local, criar_usuario_parcial_google, buscar_usuario_por_email
from utils import formatar_e_validar_cpf, formatar_cep, buscar_cep
from config import DB_PATH, COR_DESTAQUE, COR_TEXTO

# =========================================
# CONFIGURAÇÃO OAUTH
# =========================================
try:
    GOOGLE_CLIENT_ID = st.secrets["GOOGLE_CLIENT_ID"]
    GOOGLE_CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
    REDIRECT_URI = "https://bjjdigital.streamlit.app/" # Ajuste se necessário para localhost durante testes
except (FileNotFoundError, KeyError):
    # Valores vazios para não quebrar se não tiver secrets configurado ainda
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
    """Tela de login com autenticação local, Google e opção de cadastro."""
    st.session_state.setdefault("modo_login", "login")

    # Layout de colunas para centralizar
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        if st.session_state["modo_login"] == "login":
            
            # --- LOGO ACIMA DO CARD ---
            if os.path.exists("assets/logo.png"):
                # Usamos colunas internas para centralizar a imagem visualmente
                col_l, col_c, col_r = st.columns([1, 2, 1])
                with col_c:
                    st.image("assets/logo.png", use_container_width=True)
            # -----------------------------------------------

            with st.container(border=True):
                st.markdown("<h3 style='text-align:center;'>Login</h3>", unsafe_allow_html=True)
                
                user_ou_email = st.text_input("Nome de Usuário, Email ou CPF:")
                pwd = st.text_input("Senha:", type="password")

                if st.button("Entrar", use_container_width=True, key="entrar_btn", type="primary"):
                    # Lógica inteligente para identificar o tipo de entrada
                    entrada = user_ou_email.strip()
                    
                    # 1. Se tiver '@', tratamos como Email (minúsculo)
                    if "@" in entrada:
                        entrada = entrada.lower()
                    
                    # 2. Se não, verificamos se parece um CPF
                    else:
                        # Tenta extrair CPF usando a função de utils
                        cpf_detectado = formatar_e_validar_cpf(entrada)
                        if cpf_detectado:
                            # Se for um CPF válido, usamos apenas os números
                            entrada = cpf_detectado
                        # Se não for CPF, mantemos como está (Nome de Usuário)
                        
                    u = autenticar_local(entrada, pwd.strip()) 
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
                if GOOGLE_CLIENT_ID: # Só mostra se tiver configurado
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
                            email = user_info["email"].lower() # Garante minúsculo vindo do Google
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
                else:
                    st.warning("Google Auth não configurado (.streamlit/secrets.toml)")

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
    """Formulário de cadastro completo."""
    st.subheader("📋 Cadastro de Novo Usuário")
    nome = st.text_input("Nome de Usuário (login):") 
    email = st.text_input("E-mail:")
    cpf_input = st.text_input("CPF:") 
    senha = st.text_input("Senha:", type="password")
    confirmar = st.text_input("Confirmar senha:", type="password")
    
    st.markdown("---")
    tipo_usuario = st.selectbox("Tipo de Usuário:", ["Aluno", "Professor"])
    
    conn = sqlite3.connect(DB_PATH)
    equipes_df = pd.read_sql_query("SELECT id, nome, professor_responsavel_id FROM equipes", conn)
    
    # --- Faixa e Equipe ---
    if tipo_usuario == "Aluno":
        faixa = st.selectbox("Graduação (faixa):", [
            "Branca", "Cinza", "Amarela", "Laranja", "Verde",
            "Azul", "Roxa", "Marrom", "Preta"
        ])
    else: # Professor
        faixa = st.selectbox("Graduação (faixa):", ["Marrom", "Preta"])
        st.info("Professores devem ser Marrom ou Preta.")
        
    opcoes_equipe = ["Nenhuma (Vínculo Pendente)"] + equipes_df["nome"].tolist()
    # Apenas visual, lógica de vínculo seria implementada aqui se necessário
    _ = st.selectbox("Selecione sua Equipe (Opcional):", opcoes_equipe)
    
    st.markdown("---")
    st.markdown("#### 3. Endereço") 

    # Inicializa estado para busca de CEP no cadastro
    st.session_state.setdefault('endereco_cep_cadastro', {
        'cep': '', 'logradouro': '', 'bairro': '', 'cidade': '', 'uf': ''
    })

    # --- Sincronização de Chaves ---
    st.session_state.setdefault('reg_logradouro', st.session_state.endereco_cep_cadastro['logradouro'])
    st.session_state.setdefault('reg_bairro', st.session_state.endereco_cep_cadastro['bairro'])
    st.session_state.setdefault('reg_cidade', st.session_state.endereco_cep_cadastro['cidade'])
    st.session_state.setdefault('reg_uf', st.session_state.endereco_cep_cadastro['uf'])
    st.session_state.setdefault('reg_cep_input', st.session_state.endereco_cep_cadastro['cep'])

    col_cep, col_btn = st.columns([3, 1])
    with col_cep:
        st.text_input("CEP:", max_chars=9, key='reg_cep_input')
        cep_digitado_limpo = formatar_cep(st.session_state.reg_cep_input)
        if cep_digitado_limpo:
             st.info(f"CEP Formatado: {cep_digitado_limpo[:5]}-{cep_digitado_limpo[5:]}")

    with col_btn:
        st.markdown("<div style='height: 29px;'></div>", unsafe_allow_html=True)
        if st.button("Buscar CEP 🔍", use_container_width=True, key='btn_buscar_reg_cep'):
            cep_digitado = st.session_state.reg_cep_input
            endereco = buscar_cep(cep_digitado)
            
            if endereco:
                st.session_state.endereco_cep_cadastro = {
                    'cep': cep_digitado,
                    **endereco
                }
                # Atualiza widgets
                st.session_state['reg_logradouro'] = endereco['logradouro']
                st.session_state['reg_bairro'] = endereco['bairro']
                st.session_state['reg_cidade'] = endereco['cidade']
                st.session_state['reg_uf'] = endereco['uf']
                st.success("Endereço encontrado!")
            else:
                st.error("CEP inválido ou não encontrado.")
                st.session_state['reg_logradouro'] = ''
                st.session_state['reg_bairro'] = ''
                st.session_state['reg_cidade'] = ''
                st.session_state['reg_uf'] = ''
            st.rerun()

    # CAMPOS HABILITADOS
    col_logr, col_bairro = st.columns(2)
    novo_logradouro = col_logr.text_input("Logradouro:", key='reg_logradouro')
    novo_bairro = col_bairro.text_input("Bairro:", key='reg_bairro')

    col_cidade, col_uf = st.columns(2)
    novo_cidade = col_cidade.text_input("Cidade:", key='reg_cidade')
    novo_uf = col_uf.text_input("UF:", key='reg_uf')
    
    col_num, col_comp = st.columns(2)
    novo_numero = col_num.text_input("Número (Opcional):", value="", key='reg_numero')
    novo_complemento = col_comp.text_input("Complemento (Opcional):", value="", key='reg_complemento')

    if st.button("Cadastrar", use_container_width=True, type="primary"):
        # Formatação
        nome_final = nome.upper() # Nome continua Maiúsculo
        email_final = email.lower().strip() # <--- MUDANÇA AQUI: Email agora é Minúsculo
        cpf_final = formatar_e_validar_cpf(cpf_input)
        cep_final = formatar_cep(st.session_state.reg_cep_input)

        if not (nome and email and cpf_input and senha and confirmar):
            st.warning("Preencha todos os campos obrigatórios.")
        elif senha != confirmar:
            st.error("As senhas não coincidem.")
        elif not cpf_final:
            st.error("CPF inválido.")
        elif not (cep_final and novo_logradouro and novo_bairro and novo_cidade and novo_uf):
            st.error("Endereço incompleto.")
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM usuarios WHERE nome=? OR email=? OR cpf=?", (nome_final, email_final, cpf_final))
            
            if cursor.fetchone():
                st.error("Usuário já cadastrado.")
            else: 
                try:
                    hashed = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
                    tipo_db = "aluno" if tipo_usuario == "Aluno" else "professor"

                    cursor.execute("""
                        INSERT INTO usuarios (
                            nome, email, cpf, tipo_usuario, senha, auth_provider, perfil_completo,
                            cep, logradouro, numero, complemento, bairro, cidade, uf
                        ) VALUES (?, ?, ?, ?, ?, 'local', 1, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        nome_final, email_final, cpf_final, tipo_db, hashed,
                        cep_final, 
                        novo_logradouro.upper(), 
                        novo_numero.upper() if novo_numero else None, 
                        novo_complemento.upper() if novo_complemento else None, 
                        novo_bairro.upper(), 
                        novo_cidade.upper(), 
                        novo_uf.upper()
                    ))
                    novo_id = cursor.lastrowid
                    
                    if tipo_db == "aluno":
                         cursor.execute("INSERT INTO alunos (usuario_id, faixa_atual, status_vinculo) VALUES (?, ?, 'pendente')", (novo_id, faixa))
                    else:
                         cursor.execute("INSERT INTO professores (usuario_id, status_vinculo) VALUES (?, 'pendente')", (novo_id,))

                    conn.commit()
                    st.session_state.pop('endereco_cep_cadastro', None)
                    st.success("Cadastro realizado! Faça login.")
                    st.session_state["modo_login"] = "login"
                    st.rerun()
                except Exception as e:
                    conn.rollback() 
                    st.error(f"Erro ao cadastrar: {e}")
            conn.close()

    if st.button("⬅️ Voltar para Login", use_container_width=True):
        st.session_state.pop('endereco_cep_cadastro', None)
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
            novo_tipo = "aluno" if "Aluno" in tipo_usuario else "professor"
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Nome continua sendo salvo em Maiúsculo para padronização
            nome_salvar = st.session_state.cadastro_nome.upper()
            
            cursor.execute("UPDATE usuarios SET nome=?, tipo_usuario=?, perfil_completo=1 WHERE id=?", (nome_salvar, novo_tipo, user_data['id']))
            
            if novo_tipo == "aluno":
                cursor.execute("INSERT INTO alunos (usuario_id, faixa_atual, status_vinculo) VALUES (?, ?, 'pendente')", (user_data['id'], st.session_state.cadastro_faixa))
            else:
                cursor.execute("INSERT INTO professores (usuario_id, status_vinculo) VALUES (?, 'pendente')", (user_data['id'],))
            
            conn.commit()
            conn.close()
            
            st.session_state.usuario = {"id": user_data['id'], "nome": nome_salvar, "tipo": novo_tipo}
            del st.session_state.registration_pending
            st.rerun()
