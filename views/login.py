import streamlit as st
import os
import bcrypt
import time
from datetime import date

# ============================================
# IMPORTAÇÕES COM FALLBACK ROBUSTO
# ============================================
def importar_com_fallback():
    """Importa módulos com fallback robusto"""
    
    # Módulo database
    try:
        from database import get_db, OPCOES_SEXO
        DB_DISPONIVEL = True
    except ImportError:
        DB_DISPONIVEL = False
        get_db = lambda: None
        OPCOES_SEXO = [" ", "Masculino", "Feminino", "Outros"]
        st.warning("⚠️ Módulo database não disponível")
    
    # Módulo auth
    try:
        from auth import autenticar_local, buscar_usuario_por_email
        AUTH_DISPONIVEL = True
    except ImportError:
        AUTH_DISPONIVEL = False
        autenticar_local = lambda x, y: None
        buscar_usuario_por_email = lambda x: None
        st.warning("⚠️ Módulo auth não disponível")
    
    # Módulo utils
    try:
        from utils import (
            formatar_e_validar_cpf, 
            formatar_cep, 
            buscar_cep, 
            gerar_senha_temporaria, 
            enviar_email_recuperacao
        )
        UTILS_DISPONIVEL = True
    except ImportError:
        UTILS_DISPONIVEL = False
        formatar_e_validar_cpf = lambda x: x
        formatar_cep = lambda x: x
        buscar_cep = lambda x: None
        gerar_senha_temporaria = lambda: "temp123"
        enviar_email_recuperacao = lambda x, y: False
        st.warning("⚠️ Módulo utils não disponível")
    
    # Firebase
    try:
        from firebase_admin import firestore
        FIRESTORE_DISPONIVEL = True
    except ImportError:
        FIRESTORE_DISPONIVEL = False
        class FirestoreMock:
            SERVER_TIMESTAMP = "TIMESTAMP"
        firestore = FirestoreMock()
    
    return {
        'get_db': get_db,
        'OPCOES_SEXO': OPCOES_SEXO,
        'autenticar_local': autenticar_local,
        'buscar_usuario_por_email': buscar_usuario_por_email,
        'formatar_e_validar_cpf': formatar_e_validar_cpf,
        'formatar_cep': formatar_cep,
        'buscar_cep': buscar_cep,
        'gerar_senha_temporaria': gerar_senha_temporaria,
        'enviar_email_recuperacao': enviar_email_recuperacao,
        'firestore': firestore
    }

# Importa tudo
imports = importar_com_fallback()

# Atribui às variáveis globais
get_db = imports['get_db']
OPCOES_SEXO = imports['OPCOES_SEXO']
autenticar_local = imports['autenticar_local']
buscar_usuario_por_email = imports['buscar_usuario_por_email']
formatar_e_validar_cpf = imports['formatar_e_validar_cpf']
formatar_cep = imports['formatar_cep']
buscar_cep = imports['buscar_cep']
gerar_senha_temporaria = imports['gerar_senha_temporaria']
enviar_email_recuperacao = imports['enviar_email_recuperacao']
firestore = imports['firestore']

# ============================================
# FUNÇÕES AUXILIARES
# ============================================
def get_logo_path():
    """Busca o logo em várias localizações"""
    paths = [
        "assets/logo.jpg",
        "logo.jpg", 
        "assets/logo.png",
        "logo.png",
        "assets/logo.jpeg",
        "logo.jpeg"
    ]
    for path in paths:
        if os.path.exists(path):
            return path
    return None

# ============================================
# TELA DE LOGIN PRINCIPAL
# ============================================
def tela_login():
    """Tela principal de login"""
    
    # Inicializa estado se necessário
    if "modo_login" not in st.session_state:
        st.session_state.modo_login = "login"
    
    logo = get_logo_path()
    
    # Verifica se há cadastro pendente
    if "registration_pending" in st.session_state:
        tela_completar_cadastro(st.session_state.registration_pending)
        return
    
    # Container central
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Logo
        if logo:
            st.image(logo, use_container_width=True)
        
        # Título
        st.markdown("<h2 style='text-align: center; color: #FFD770;'>BJJ Digital</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; opacity: 0.8;'>Sistema de Gestão de Jiu-Jitsu</p>", unsafe_allow_html=True)
        
        # Escolhe qual tela mostrar
        if st.session_state.modo_login == "login":
            mostrar_tela_login()
        elif st.session_state.modo_login == "cadastro":
            tela_cadastro_interno()
        elif st.session_state.modo_login == "recuperar":
            tela_recuperar_senha()

def mostrar_tela_login():
    """Mostra o formulário de login"""
    
    with st.container(border=True):
        st.markdown("<h3 style='text-align:center;'>🔐 Login</h3>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            user_input = st.text_input("**Email ou CPF:**", placeholder="seu@email.com ou 123.456.789-00")
            pwd = st.text_input("**Senha:**", type="password", placeholder="Sua senha")
            
            col_submit, _ = st.columns([1, 1])
            with col_submit:
                submit_login = st.form_submit_button("🚀 Entrar", type="primary", use_container_width=True)
            
            if submit_login:
                if not user_input or not pwd:
                    st.warning("⚠️ Preencha todos os campos.")
                else:
                    processar_login(user_input, pwd)
        
        # Botões auxiliares
        st.markdown("---")
        col_cad, col_rec = st.columns(2)
        
        with col_cad:
            if st.button("📋 Criar Conta", use_container_width=True):
                st.session_state.modo_login = "cadastro"
                st.rerun()
        
        with col_rec:
            if st.button("🔑 Esqueci a Senha", use_container_width=True):
                st.session_state.modo_login = "recuperar"
                st.rerun()

def processar_login(user_input, password):
    """Processa tentativa de login"""
    with st.spinner("🔍 Verificando credenciais..."):
        resultado = autenticar_local(user_input.strip(), password.strip())
        
        if resultado and isinstance(resultado, dict) and 'id' in resultado:
            st.session_state.usuario = resultado
            st.success(f"✅ Bem-vindo(a), {resultado.get('nome', 'Usuário').title()}!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ Email/CPF ou senha incorretos.")

# ============================================
# TELA DE CADASTRO
# ============================================
def tela_cadastro_interno():
    """Tela de cadastro de novo usuário"""
    
    st.markdown("<h3 style='text-align:center;'>📋 Criar Nova Conta</h3>", unsafe_allow_html=True)
    
    db = get_db()
    
    # Carrega equipes disponíveis
    lista_equipes = ["Nenhuma (Vínculo Pendente)"]
    try:
        if db:
            equipes_ref = db.collection('equipes').stream()
            for doc in equipes_ref:
                d = doc.to_dict()
                nome_eq = d.get('nome', 'Sem Nome')
                lista_equipes.append(nome_eq)
    except:
        pass
    
    # Formulário de cadastro
    with st.form("form_cadastro"):
        # Dados pessoais
        st.markdown("#### 👤 Dados Pessoais")
        
        nome = st.text_input("**Nome Completo:**", placeholder="Seu nome completo")
        email = st.text_input("**E-mail:**", placeholder="seu@email.com")
        
        col_cpf, col_sexo, col_nasc = st.columns([2, 1, 1])
        with col_cpf:
            cpf_input = st.text_input("**CPF:**", placeholder="123.456.789-00")
        with col_sexo:
            sexo = st.selectbox("**Sexo:**", OPCOES_SEXO)
        with col_nasc:
            data_nasc = st.date_input("**Nascimento:**", value=None, format="DD/MM/YYYY")
        
        # Senha
        st.markdown("#### 🔒 Senha de Acesso")
        col_senha, col_conf = st.columns(2)
        with col_senha:
            senha = st.text_input("**Senha:**", type="password")
        with col_conf:
            conf_senha = st.text_input("**Confirmar Senha:**", type="password")
        
        # Tipo de conta
        st.markdown("#### 🥋 Perfil na Academia")
        tipo = st.selectbox("**Tipo de Conta:**", ["Aluno(a)", "Professor(a)"])
        
        # Informações específicas
        if "Aluno" in tipo:
            faixa = st.selectbox("**Faixa Atual:**", [
                "Branca", "Cinza e Branca", "Cinza", "Cinza e Preta",
                "Amarela e Branca", "Amarela", "Amarela e Preta",
                "Laranja e Branca", "Laranja", "Laranja e Preta",
                "Verde e Branca", "Verde", "Verde e Preta",
                "Azul", "Roxa", "Marrom", "Preta"
            ])
            equipe = st.selectbox("**Equipe:**", lista_equipes)
        else:
            faixa = st.selectbox("**Faixa:**", ["Marrom", "Preta"])
            equipe = st.selectbox("**Equipe:**", lista_equipes + ["🆕 Criar Nova Equipe"])
            st.caption("Professores(as) devem ser faixa Marrom ou Preta.")
        
        # Endereço
        st.markdown("#### 📍 Endereço (Opcional)")
        col_cep, col_num = st.columns([2, 1])
        with col_cep:
            cep = st.text_input("CEP:", placeholder="00000-000")
        with col_num:
            numero = st.text_input("Número:", placeholder="123")
        
        logradouro = st.text_input("Logradouro:", placeholder="Rua, Avenida, etc.")
        col_bairro, col_cidade, col_uf = st.columns([2, 2, 1])
        with col_bairro:
            bairro = st.text_input("Bairro:")
        with col_cidade:
            cidade = st.text_input("Cidade:")
        with col_uf:
            uf = st.text_input("UF:", placeholder="SP", max_chars=2).upper()
        
        complemento = st.text_input("Complemento (opcional):")
        
        # Botões
        st.markdown("---")
        col_btn1, col_btn2 = st.columns([1, 2])
        
        with col_btn1:
            if st.form_submit_button("❌ Cancelar", use_container_width=True):
                st.session_state.modo_login = "login"
                st.rerun()
        
        with col_btn2:
            if st.form_submit_button("🚀 Criar Minha Conta", type="primary", use_container_width=True):
                processar_cadastro(
                    nome=nome,
                    email=email,
                    cpf=cpf_input,
                    sexo=sexo,
                    data_nasc=data_nasc,
                    senha=senha,
                    conf_senha=conf_senha,
                    tipo=tipo,
                    faixa=faixa,
                    equipe=equipe,
                    cep=cep,
                    logradouro=logradouro,
                    numero=numero,
                    bairro=bairro,
                    cidade=cidade,
                    uf=uf,
                    complemento=complemento,
                    db=db
                )

def processar_cadastro(**kwargs):
    """Processa o cadastro do usuário"""
    
    # Validações básicas
    campos_obrigatorios = ['nome', 'email', 'cpf', 'senha', 'conf_senha']
    for campo in campos_obrigatorios:
        if not kwargs.get(campo):
            st.error(f"⚠️ O campo '{campo.replace('_', ' ').title()}' é obrigatório.")
            return
    
    if kwargs['senha'] != kwargs['conf_senha']:
        st.error("❌ As senhas não conferem.")
        return
    
    cpf_formatado = formatar_e_validar_cpf(kwargs['cpf'])
    if not cpf_formatado:
        st.error("❌ CPF inválido.")
        return
    
    # Verifica se já existe
    db = kwargs.get('db')
    if db:
        try:
            # Verifica email
            email_existe = list(db.collection('usuarios').where('email', '==', kwargs['email'].lower()).stream())
            if email_existe:
                st.error("❌ Este e-mail já está cadastrado.")
                return
            
            # Verifica CPF
            cpf_existe = list(db.collection('usuarios').where('cpf', '==', cpf_formatado).stream())
            if cpf_existe:
                st.error("❌ Este CPF já está cadastrado.")
                return
        except:
            pass
    
    # Cria usuário
    try:
        with st.spinner("🔄 Criando sua conta..."):
            tipo_db = "professor" if "Professor" in kwargs['tipo'] else "aluno"
            
            usuario_data = {
                "nome": kwargs['nome'].upper(),
                "email": kwargs['email'].lower().strip(),
                "cpf": cpf_formatado,
                "tipo_usuario": tipo_db,
                "senha": bcrypt.hashpw(kwargs['senha'].encode(), bcrypt.gensalt()).decode(),
                "auth_provider": "local",
                "perfil_completo": True,
                "sexo": kwargs['sexo'],
                "faixa_atual": kwargs['faixa'],
                "data_criacao": firestore.SERVER_TIMESTAMP if hasattr(firestore, 'SERVER_TIMESTAMP') else time.time()
            }
            
            # Adiciona endereço se fornecido
            if kwargs.get('logradouro'):
                usuario_data.update({
                    "logradouro": kwargs['logradouro'].upper(),
                    "numero": kwargs['numero'],
                    "bairro": kwargs['bairro'].upper() if kwargs['bairro'] else "",
                    "cidade": kwargs['cidade'].upper() if kwargs['cidade'] else "",
                    "uf": kwargs['uf'].upper() if kwargs['uf'] else "",
                    "complemento": kwargs['complemento'].upper() if kwargs['complemento'] else "",
                    "cep": formatar_cep(kwargs['cep']) if kwargs['cep'] else ""
                })
            
            if kwargs.get('data_nasc'):
                usuario_data["data_nascimento"] = kwargs['data_nasc'].isoformat()
            
            # Salva no banco se disponível
            if db:
                _, doc_ref = db.collection('usuarios').add(usuario_data)
                usuario_id = doc_ref.id
            else:
                usuario_id = "temp_" + str(int(time.time()))
            
            # Atualiza session state
            st.session_state.usuario = {
                "id": usuario_id,
                "nome": usuario_data["nome"],
                "tipo": tipo_db,
                "email": usuario_data["email"]
            }
            
            st.success("🎉 Conta criada com sucesso!")
            st.balloons()
            time.sleep(2)
            st.rerun()
            
    except Exception as e:
        st.error(f"❌ Erro ao criar conta: {str(e)}")

# ============================================
# TELA DE RECUPERAÇÃO DE SENHA
# ============================================
def tela_recuperar_senha():
    """Tela para recuperação de senha"""
    
    st.markdown("<h3 style='text-align:center;'>🔑 Recuperar Senha</h3>", unsafe_allow_html=True)
    st.info("Informe seu e-mail cadastrado para receber uma nova senha.")
    
    email = st.text_input("**E-mail cadastrado:**", placeholder="seu@email.com")
    
    col_btn1, col_btn2 = st.columns([1, 2])
    
    with col_btn1:
        if st.button("← Voltar", use_container_width=True):
            st.session_state.modo_login = "login"
            st.rerun()
    
    with col_btn2:
        if st.button("📧 Enviar Nova Senha", type="primary", use_container_width=True):
            if not email:
                st.warning("⚠️ Informe seu e-mail.")
            else:
                processar_recuperacao(email)

def processar_recuperacao(email):
    """Processa solicitação de recuperação de senha"""
    db = get_db()
    
    if not db:
        st.error("⚠️ Serviço temporariamente indisponível.")
        return
    
    try:
        email_clean = email.lower().strip()
        users_ref = db.collection('usuarios')
        query = list(users_ref.where('email', '==', email_clean).stream())
        
        if query:
            doc = query[0]
            u_data = doc.to_dict()
            
            if u_data.get("auth_provider") == "google":
                st.error("❌ Este e-mail usa login Google. Use a opção 'Entrar com Google'.")
                return
            
            nova_senha = gerar_senha_temporaria()
            hashed = bcrypt.hashpw(nova_senha.encode(), bcrypt.gensalt()).decode()
            
            db.collection('usuarios').document(doc.id).update({
                "senha": hashed,
                "precisa_trocar_senha": True
            })
            
            if enviar_email_recuperacao(email_clean, nova_senha):
                st.success("✅ Nova senha enviada para seu e-mail! Verifique sua caixa de entrada e spam.")
            else:
                st.info("📝 Sua nova senha é: **{}**".format(nova_senha))
                st.warning("⚠️ Anote esta senha e altere após o login.")
            
            time.sleep(3)
            st.session_state.modo_login = "login"
            st.rerun()
        else:
            st.error("❌ E-mail não encontrado.")
            
    except Exception as e:
        st.error(f"❌ Erro ao processar: {str(e)}")

# ============================================
# TELA DE COMPLETAR CADASTRO (GOOGLE)
# ============================================
def tela_completar_cadastro(user_data):
    """Completa cadastro para usuários Google"""
    
    st.markdown("<h2 style='text-align:center; color:#FFD770;'>👋 Complete seu Cadastro</h2>", unsafe_allow_html=True)
    st.info("Precisamos de algumas informações adicionais para finalizar seu acesso.")
    
    with st.form("form_completar_cadastro"):
        # Dados obrigatórios
        st.markdown("#### 📝 Dados Obrigatórios")
        
        cpf_input = st.text_input("**CPF:**", placeholder="123.456.789-00", help="CPF é obrigatório para todos os usuários")
        sexo = st.selectbox("**Sexo:**", OPCOES_SEXO)
        data_nasc = st.date_input("**Data de Nascimento:**", value=None, format="DD/MM/YYYY")
        
        # Tipo de conta
        st.markdown("#### 🥋 Seu Perfil")
        tipo = st.selectbox("**Você é:**", ["Aluno(a)", "Professor(a)"])
        
        if "Aluno" in tipo:
            faixa = st.selectbox("**Sua Faixa:**", [
                "Branca", "Cinza e Branca", "Cinza", "Cinza e Preta",
                "Amarela e Branca", "Amarela", "Amarela e Preta",
                "Laranja e Branca", "Laranja", "Laranja e Preta",
                "Verde e Branca", "Verde", "Verde e Preta",
                "Azul", "Roxa", "Marrom", "Preta"
            ])
        else:
            faixa = st.selectbox("**Sua Faixa:**", ["Marrom", "Preta"])
            st.caption("Professores devem ser faixa Marrom ou Preta.")
        
        # Endereço (opcional)
        st.markdown("#### 📍 Endereço (Opcional)")
        cep = st.text_input("CEP:", placeholder="00000-000")
        logradouro = st.text_input("Logradouro:")
        numero = st.text_input("Número:")
        bairro = st.text_input("Bairro:")
        cidade = st.text_input("Cidade:")
        uf = st.text_input("UF:", placeholder="SP", max_chars=2).upper()
        
        # Botões
        st.markdown("---")
        col_cancel, col_save = st.columns([1, 2])
        
        with col_cancel:
            if st.form_submit_button("❌ Cancelar", use_container_width=True):
                if 'registration_pending' in st.session_state:
                    del st.session_state.registration_pending
                st.rerun()
        
        with col_save:
            if st.form_submit_button("✅ Finalizar Cadastro", type="primary", use_container_width=True):
                completar_cadastro_process(
                    user_data=user_data,
                    cpf=cpf_input,
                    sexo=sexo,
                    data_nasc=data_nasc,
                    tipo=tipo,
                    faixa=faixa,
                    cep=cep,
                    logradouro=logradouro,
                    numero=numero,
                    bairro=bairro,
                    cidade=cidade,
                    uf=uf
                )

def completar_cadastro_process(**kwargs):
    """Processa completamento de cadastro"""
    
    user_data = kwargs.get('user_data', {})
    cpf_input = kwargs.get('cpf', '')
    
    if not cpf_input:
        st.error("❌ CPF é obrigatório.")
        return
    
    cpf_formatado = formatar_e_validar_cpf(cpf_input)
    if not cpf_formatado:
        st.error("❌ CPF inválido.")
        return
    
    # Verifica se CPF já existe
    db = get_db()
    if db:
        try:
            cpf_existe = list(db.collection('usuarios').where('cpf', '==', cpf_formatado).stream())
            for doc in cpf_existe:
                if doc.id != user_data.get('id'):
                    st.error("❌ Este CPF já está cadastrado em outra conta.")
                    return
        except:
            pass
    
    try:
        tipo_db = "professor" if "Professor" in kwargs['tipo'] else "aluno"
        
        update_data = {
            "cpf": cpf_formatado,
            "tipo_usuario": tipo_db,
            "perfil_completo": True,
            "sexo": kwargs['sexo'],
            "faixa_atual": kwargs['faixa']
        }
        
        if kwargs.get('data_nasc'):
            update_data["data_nascimento"] = kwargs['data_nasc'].isoformat()
        
        if kwargs.get('logradouro'):
            update_data.update({
                "logradouro": kwargs['logradouro'].upper(),
                "numero": kwargs['numero'],
                "bairro": kwargs['bairro'].upper() if kwargs['bairro'] else "",
                "cidade": kwargs['cidade'].upper() if kwargs['cidade'] else "",
                "uf": kwargs['uf'].upper() if kwargs['uf'] else "",
                "cep": formatar_cep(kwargs['cep']) if kwargs['cep'] else ""
            })
        
        # Atualiza no banco
        if db and user_data.get('id'):
            db.collection('usuarios').document(user_data['id']).update(update_data)
        
        # Atualiza session state
        user_data.update({
            "perfil_completo": True,
            "tipo": tipo_db,
            "cpf": cpf_formatado
        })
        st.session_state.usuario = user_data
        
        if 'registration_pending' in st.session_state:
            del st.session_state.registration_pending
        
        st.success("🎉 Cadastro completo! Redirecionando...")
        time.sleep(2)
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Erro ao completar cadastro: {str(e)}")

# ============================================
# FUNÇÃO PARA TESTE RÁPIDO
# ============================================
if __name__ == "__main__":
    # Para testar diretamente este arquivo
    st.set_page_config(page_title="Login Test", layout="centered")
    tela_login()
