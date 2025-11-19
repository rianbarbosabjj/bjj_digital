import streamlit as st
from fpdf import FPDF
from PIL import Image
import sqlite3
import json
import random
import os
import qrcode
import unicodedata
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import bcrypt
from streamlit_option_menu import option_menu
from streamlit_oauth import OAuth2Component
import requests
import base64

# =========================================
# CONFIGURAÇÕES GERAIS
# =========================================
st.set_page_config(page_title="BJJ Digital", page_icon="assets/logo.png", layout="wide")

COR_FUNDO = "#0e2d26"
COR_TEXTO = "#FFFFFF"
COR_DESTAQUE = "#FFD770"
COR_BOTAO = "#078B6C"
COR_HOVER = "#FFD770"

# [CSS (Corrigido para forçar a renderização do conteúdo principal)]
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;700&display=swap');

/* --- CORREÇÃO CRÍTICA: GARANTE QUE O BACKGROUND E O CONTEÚDO APAREÇAM --- */

[data-testid="stAppViewContainer"] > .main {{
    background-color: {COR_FUNDO} !important;
    color: {COR_TEXTO} !important;
    min-height: 100vh;
}}

[data-testid="stSidebar"] {{
    background-color: #0c241e !important;
}}

/* --- ESTILOS ORIGINAIS --- */

.stButton>button {{
    background: linear-gradient(90deg, {COR_BOTAO}, #056853);
    color: white;
    font-weight: bold;
    border: none;
    padding: 0.6em 1.2em;
    border-radius: 10px;
    transition: 0.3s;
}}
.stButton>button:hover {{
    background: {COR_HOVER};
    color: {COR_FUNDO};
    transform: scale(1.02);
}}
h1, h2, h3 {{
    color: {COR_DESTAQUE};
    text-align: center;
    font-weight: 700;
}}
/* Estilo para os cards de navegação */
div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] div[data-testid="stVerticalBlock"] div[data-testid="stContainer"] {{
    background-color: #0c241e; 
    border: 1px solid #078B6C;
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
    transition: 0.3s;
    height: 190px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}}
div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] div[data-testid="stVerticalBlock"] div[data-testid="stContainer"]:hover {{
    transform: scale(1.03); 
    border-color: {COR_DESTAQUE};
    background-color: #1a4d40;
}}
div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] div[data-testid="stVerticalBlock"] div[data-testid="stContainer"] h3 {{
     color: {COR_DESTAQUE};
     margin-bottom: 10px;
     font-size: 1.8rem;
}}
div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] div[data-testid="stVerticalBlock"] div[data-testid="stContainer"] p {{
     color: {COR_TEXTO};
     font-size: 0.95rem;
}}
</style>
""", unsafe_allow_html=True)

# =========================================
# BANCO DE DADOS E MIGRAÇÃO
# =========================================
DB_PATH = os.path.expanduser("~/bjj_digital_original.db") 

def criar_banco():
    """Cria o banco de dados e suas tabelas, caso não existam."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tabela 'usuarios' AGORA COM CPF/ENDEREÇO
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        email TEXT UNIQUE,
        cpf TEXT UNIQUE, -- NOVO
        tipo_usuario TEXT,
        senha TEXT, 
        auth_provider TEXT DEFAULT 'local', 
        perfil_completo BOOLEAN DEFAULT 0,
        cep TEXT, -- NOVO
        logradouro TEXT, -- NOVO
        numero TEXT, -- NOVO
        bairro TEXT, -- NOVO
        cidade TEXT, -- NOVO
        estado TEXT, -- NOVO
        data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS equipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        descricao TEXT,
        professor_responsavel_id INTEGER,
        ativo BOOLEAN DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS professores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        equipe_id INTEGER,
        pode_aprovar BOOLEAN DEFAULT 0,
        eh_responsavel BOOLEAN DEFAULT 0,
        status_vinculo TEXT CHECK(status_vinculo IN ('pendente','ativo','rejeitado')) DEFAULT 'pendente',
        data_vinculo DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS alunos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        faixa_atual TEXT,
        turma TEXT,
        professor_id INTEGER,
        equipe_id INTEGER,
        status_vinculo TEXT CHECK(status_vinculo IN ('pendente','ativo','rejeitado')) DEFAULT 'pendente',
        data_pedido DATETIME DEFAULT CURRENT_TIMESTAMP,
        exame_habilitado BOOLEAN DEFAULT 0,
        data_inicio_exame TEXT, 
        data_fim_exame TEXT 
    );

    CREATE TABLE IF NOT EXISTS resultados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        modo TEXT,
        tema TEXT,
        faixa TEXT,
        pontuacao INTEGER,
        tempo TEXT,
        data DATETIME DEFAULT CURRENT_TIMESTAMP,
        codigo_verificacao TEXT,
        acertos INTEGER,
        total_questoes INTEGER
    );

    CREATE TABLE IF NOT EXISTS rola_resultados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        faixa TEXT,
        tema TEXT,
        acertos INTEGER,
        total INTEGER,
        percentual REAL,
        data DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    conn.close()


def migrar_db():
    """Garante que todas as colunas existam nas tabelas, adicionando se necessário."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. MIGRAÇÃO DA TABELA USUARIOS (CPF/ENDEREÇO)
    colunas_novas_usuarios = {
        'cpf': 'TEXT UNIQUE', 'cep': 'TEXT', 'logradouro': 'TEXT', 'bairro': 'TEXT', 
        'cidade': 'TEXT', 'estado': 'TEXT', 'numero': 'TEXT'
    }
    for coluna, tipo in colunas_novas_usuarios.items():
        try:
            cursor.execute(f"SELECT {coluna} FROM usuarios LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {coluna} {tipo}")
            conn.commit()
            st.toast(f"Coluna {coluna} (usuarios) adicionada.")
            
    # 2. MIGRAÇÃO DA TABELA ALUNOS (Datas de exame)
    try:
        cursor.execute("SELECT data_inicio_exame FROM alunos LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE alunos ADD COLUMN data_inicio_exame TEXT")
        cursor.execute("ALTER TABLE alunos ADD COLUMN data_fim_exame TEXT")
        conn.commit()
        st.toast("Campos de Data de Exame adicionados à tabela 'alunos'.")
            
    conn.close()

# 5. Usuários de teste (Versão Corrigida: Senha é literal)
def criar_usuarios_teste():
    """Cria usuários padrão locais com senha simples no banco original."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # CRIA UMA EQUIPE PADRÃO SE NÃO EXISTIR
    cursor.execute("SELECT id FROM equipes WHERE nome=?", ("EQUIPE TESTE",))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO equipes (nome, descricao) VALUES (?, ?)", ("EQUIPE TESTE", "Equipe padrão para testes."))
        conn.commit()
        
    cursor.execute("SELECT id FROM equipes WHERE nome=?", ("EQUIPE TESTE",))
    equipe_teste_id = cursor.fetchone()[0]


    usuarios = [
        ("Admin User", "admin", "admin@bjj.local", "admin", "00000000000"), 
        ("Professor Responsável", "professor", "professor@bjj.local", "professor", "11111111111"), 
        ("Aluno User", "aluno", "aluno@bjj.local", "aluno", "22222222222")
    ]
    for nome, tipo, email, senha_plana, cpf in usuarios:
        cursor.execute("SELECT id FROM usuarios WHERE email=?", (email,))
        if cursor.fetchone() is None:
            
            senha_hash = bcrypt.hashpw(senha_plana.encode(), bcrypt.gensalt()).decode()
            
            cursor.execute(
                """
                INSERT INTO usuarios (nome, tipo_usuario, senha, email, auth_provider, perfil_completo, cpf) 
                VALUES (?, ?, ?, ?, 'local', 1, ?)
                """,
                (nome, tipo, senha_hash, email, cpf),
            )
            novo_id = cursor.lastrowid
            
            if tipo == 'professor':
                # VINCULA O PROFESSOR TESTE À EQUIPE TESTE E O TORNA RESPONSÁVEL
                cursor.execute(
                    "UPDATE equipes SET professor_responsavel_id=? WHERE id=?", 
                    (novo_id, equipe_teste_id)
                )
                cursor.execute(
                    "INSERT INTO professores (usuario_id, equipe_id, eh_responsavel, status_vinculo) VALUES (?, ?, 1, 'ativo')",
                    (novo_id, equipe_teste_id)
                )
            elif tipo == 'aluno':
                # VINCULA O ALUNO TESTE À EQUIPE TESTE 
                 cursor.execute(
                    "INSERT INTO alunos (usuario_id, faixa_atual, equipe_id, status_vinculo) VALUES (?, 'Branca', ?, 'ativo')",
                    (novo_id, equipe_teste_id)
                )

    conn.commit()
    conn.close()

# 🔹 Lógica de inicialização do topo do script
if not os.path.exists(DB_PATH):
    st.toast("Criando novo banco de dados (Com CPF)...")
    criar_banco()
    criar_usuarios_teste() 

# Sempre execute a migração se o DB existir
migrar_db()


# =========================================
# AUTENTICAÇÃO (GLOBAL FIX)
# =========================================

# 1. Configuração do Google OAuth (lendo do secrets.toml)
try:
    GOOGLE_CLIENT_ID = st.secrets["GOOGLE_CLIENT_ID"]
    GOOGLE_CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
    REDIRECT_URI = "https://bjjdigital.streamlit.app/" # Mude para sua URL de produção
except FileNotFoundError:
    GOOGLE_CLIENT_ID = "MOCK_ID" 
    GOOGLE_CLIENT_SECRET = "MOCK_SECRET"
    REDIRECT_URI = "http://localhost:8501/" 

except KeyError:
    GOOGLE_CLIENT_ID = "MOCK_ID" 
    GOOGLE_CLIENT_SECRET = "MOCK_SECRET"
    REDIRECT_URI = "http://localhost:8501/" 

# 2. Inicialização do componente OAuth (DEFINIÇÃO GLOBAL - FIX)
oauth_google = OAuth2Component(
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    authorize_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
    token_endpoint="https://oauth2.googleapis.com/token",
    refresh_token_endpoint="https://oauth2.googleapis.com/token",
    revoke_token_endpoint="https://oauth2.googleapis.com/revoke",
)


# =========================================
# FUNÇÕES DE UTILIDADE E AUTENTICAÇÃO
# =========================================

def validar_cpf(cpf):
    """Verifica se o CPF tem 11 dígitos e se os dígitos verificadores são válidos."""
    cpf = ''.join(filter(str.isdigit, cpf))
    if len(cpf) != 11 or len(set(cpf)) == 1:
        return False
    soma = 0
    for i in range(9):
        soma += int(cpf[i]) * (10 - i)
    resto = soma % 11
    digito_1 = 0 if resto < 2 else 11 - resto
    if int(cpf[9]) != digito_1:
        return False
    soma = 0
    for i in range(10):
        soma += int(cpf[i]) * (11 - i)
    resto = soma % 11
    digito_2 = 0 if resto < 2 else 11 - resto
    if int(cpf[10]) != digito_2:
        return False
    return True

def buscar_endereco_por_cep(cep):
    """Busca endereço usando a API ViaCEP."""
    cep = ''.join(filter(str.isdigit, cep))
    if len(cep) != 8:
        return None
    url = f"https://viacep.com.br/ws/{cep}/json/"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status() 
        data = response.json()
        if data.get('erro'):
            return None
        return {
            "logradouro": data.get("logradouro", ""),
            "bairro": data.get("bairro", ""),
            "cidade": data.get("localidade", ""),
            "estado": data.get("uf", "")
        }
    except requests.exceptions.RequestException as e:
        return None
    except Exception as e:
        return None

# 3. Autenticação local (Login/Senha)
def autenticar_local(usuario_ou_email, senha):
    """Atualizado: Autentica o usuário local usando EMAIL ou CPF."""
    conn = sqlite3.connect(DB_PATH) 
    cursor = conn.cursor()
    dados = None
    
    try:
        # Busca por 'email' OU 'cpf'
        cursor.execute(
            "SELECT id, nome, tipo_usuario, senha FROM usuarios WHERE (email=? OR cpf=?) AND auth_provider='local'", 
            (usuario_ou_email, usuario_ou_email)
        )
        dados = cursor.fetchone()
        
        if dados is not None and dados[3]:
            if bcrypt.checkpw(senha.encode(), dados[3].encode()):
                return {"id": dados[0], "nome": dados[1], "tipo": dados[2]}
            
    except Exception as e:
        st.error(f"Erro de autenticação no DB: {e}")
        
    finally:
        conn.close() 
        
    return None

# 4. Funções de busca e criação de usuário
def buscar_usuario_por_email(email):
    """Busca um usuário pelo email e retorna seus dados."""
    conn = sqlite3.connect(DB_PATH) 
    cursor = conn.cursor()
    dados = None
    
    try:
        cursor.execute(
            "SELECT id, nome, tipo_usuario, perfil_completo FROM usuarios WHERE email=?", (email,)
        )
        dados = cursor.fetchone()
        
        if dados:
            return {
                "id": dados[0], 
                "nome": dados[1], 
                "tipo": dados[2], 
                "perfil_completo": bool(dados[3])
            }
    finally:
        conn.close()
        
    return None

def criar_usuario_parcial_google(email, nome):
    """Cria um registro inicial para um novo usuário do Google."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    novo_id = None
    
    try:
        cursor.execute(
            """
            INSERT INTO usuarios (email, nome, auth_provider, perfil_completo)
            VALUES (?, ?, 'google', 0)
            """, (email, nome)
        )
        conn.commit()
        novo_id = cursor.lastrowid
        
    except sqlite3.IntegrityError: 
        pass
        
    finally:
        conn.close()
        
    if novo_id:
        return {"id": novo_id, "email": email, "nome": nome}
    return None

def buscar_equipes():
    """Retorna uma lista de tuplas (id, nome) de todas as equipes ativas."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    equipes = cursor.execute("SELECT id, nome FROM equipes WHERE ativo=1").fetchall()
    conn.close()
    return equipes

# --- FUNÇÕES DE GESTÃO DO PROFESSOR (PLACEHOLDERS) ---

def get_professor_team_id(usuario_id):
    """Busca o ID da equipe principal do professor ativo."""
    # Apenas MOCK para evitar erros de Painel do Professor antes da implementação completa
    return 1 if usuario_id == 2 else None 

def get_alunos_by_equipe(equipe_id):
    """Busca todos os alunos (e seus status de exame) de uma equipe."""
    # MOCK
    return []

def habilitar_exame_aluno(aluno_id, data_inicio_str, data_fim_str):
    """Habilita o exame e define o período na tabela alunos."""
    # MOCK
    return True

# --- FUNÇÕES DE CERTIFICADO E QUESTÕES (HELPERS) ---
def normalizar_nome(nome):
    """Normaliza o nome para uso em nomes de arquivo."""
    return unicodedata.normalize('NFKD', nome).encode('ascii', 'ignore').decode('utf-8').replace(" ", "_")

def gerar_codigo_verificacao():
    """Gera um código de verificação único."""
    return ''.join(random.choices('0123456789ABCDEF', k=16))

def gerar_pdf(usuario, faixa, pontuacao, total, codigo, professor=None):
    """Gera o PDF do certificado de exame. (Simplificado para estabilidade)"""
    os.makedirs("relatorios", exist_ok=True)
    nome_arquivo = f"Certificado_{normalizar_nome(usuario)}_{normalizar_nome(faixa)}.pdf"
    caminho_pdf = f"relatorios/{nome_arquivo}"

    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 15)
            self.cell(0, 10, 'CERTIFICADO DE APROVAÇÃO', 0, 1, 'C')
            self.ln(10)
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Código de Verificação: {codigo}', 0, 0, 'C')

    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Arial', '', 12)
    pdf.multi_cell(0, 10, f'Certificamos que {usuario} foi aprovado(a) no Exame Teórico de Faixa.', 0, 'C')
    pdf.multi_cell(0, 10, f'Faixa: {faixa}', 0, 'C')
    pdf.multi_cell(0, 10, f'Desempenho: {pontuacao}%', 0, 'C')
    pdf.output(caminho_pdf, 'F')
    return caminho_pdf

def carregar_questoes(tema):
    """Carrega questões de um tema específico (arquivo JSON)."""
    caminho = f"questions/{tema}.json"
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            st.warning(f"⚠️ Arquivo '{caminho}' corrompido.")
            return []
    return []

def carregar_todas_questoes():
    """Carrega todas as questões de todos os temas."""
    todas_questoes = []
    os.makedirs("questions", exist_ok=True)
    for arquivo in os.listdir("questions"):
        if arquivo.endswith(".json"):
            tema = arquivo.replace(".json", "")
            questoes = carregar_questoes(tema)
            for q in questoes:
                q['tema'] = tema
            todas_questoes.extend(questoes)
    return todas_questoes


# =========================================
# TELAS DO APP (POSICIONADAS CORRETAMENTE)
# =========================================

# --- TELA INICIAL ---
def tela_inicio():
    # 1. 👇 FUNÇÃO DE CALLBACK PARA NAVEGAÇÃO
    def navigate_to(page_name):
        st.session_state.menu_selection = page_name

    # Logo e Boas Vindas
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode()
        logo_html = f"<img src='data:image/png;base64,{logo_base64}' style='width:180px;max-width:200px;height:auto;margin-bottom:10px;'/>"
    else:
        logo_html = "<p style='color:red;'>Logo não encontrada.</p>"

    st.markdown(f"""
        <div style='display:flex;flex-direction:column;align-items:center;justify-content:center;margin-bottom:30px;'>
            {logo_html}
            <h2 style='color:{COR_DESTAQUE};text-align:center;'>Painel BJJ Digital</h2>
            <p style='color:{COR_TEXTO};text-align:center;font-size:1.1em;'>Bem-vindo(a), {st.session_state.usuario['nome'].title()}! Use a navegação acima ou os cartões abaixo.</p>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # --- Cartões Principais (Para todos) ---
    col1, col2, col3 = st.columns(3)

    with col1:
        with st.container(border=True):
            st.markdown("<h3>🤼 Modo Rola</h3>", unsafe_allow_html=True)  
            st.markdown("""<p style='text-align: center; min-height: 50px;'>Treino livre com questões aleatórias de todos os temas.</p> """, unsafe_allow_html=True)
            st.button("Acessar", key="nav_rola", on_click=navigate_to, args=("Modo Rola",), use_container_width=True)

    with col2:
        with st.container(border=True):
            st.markdown("<h3>🥋 Exame de Faixa</h3>", unsafe_allow_html=True)
            st.markdown("""<p style='text-align: center; min-height: 50px;'>Realize sua avaliação teórica oficial quando liberada.</p> """, unsafe_allow_html=True)
            st.button("Acessar", key="nav_exame", on_click=navigate_to, args=("Exame de Faixa",), use_container_width=True)
            
    with col3:
        with st.container(border=True):
            st.markdown("<h3>🏆 Ranking</h3>", unsafe_allow_html=True)
            st.markdown("""<p style='text-align: center; min-height: 50px;'>Veja sua posição e a dos seus colegas no Modo Rola.</p> """, unsafe_allow_html=True)
            st.button("Acessar", key="nav_ranking", on_click=navigate_to, args=("Ranking",), use_container_width=True)

    # --- Cartões de Gestão (Admin/Professor) ---
    if st.session_state.usuario["tipo"] in ["admin", "professor"]:
        st.markdown("---")
        st.markdown(f"<h2 style='color:{COR_DESTAQUE};text-align:center; margin-top:30px;'>Painel de Gestão</h2>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            with st.container(border=True):
                st.markdown("<h3>🧠 Gestão de Questões</h3>", unsafe_allow_html=True)
                st.markdown("""<p style='text-align: center; min-height: 50px;'>Adicione, edite ou remova questões dos temas.</p> """, unsafe_allow_html=True)
                st.button("Gerenciar", key="nav_gest_questoes", on_click=navigate_to, args=("Gestão de Questões",), use_container_width=True)
        with c2:
            with st.container(border=True):
                st.markdown("<h3>🏛️ Gestão de Equipes</h3>", unsafe_allow_html=True)
                st.markdown("""<p style='text-align: center; min-height: 50px;'>Gerencie equipes, professores e alunos vinculados.</p> """, unsafe_allow_html=True)
                st.button("Gerenciar", key="nav_gest_equipes", on_click=navigate_to, args=("Gestão de Equipes",), use_container_width=True)
        with c3:
            with st.container(border=True):
                st.markdown("<h3>📜 Gestão de Exame</h3>", unsafe_allow_html=True)
                st.markdown("""<p style='text-align: center; min-height: 50px;'>Monte as provas oficiais selecionando questões.</p> """, unsafe_allow_html=True)
                st.button("Gerenciar", key="nav_gest_exame", on_click=navigate_to, args=("Gestão de Exame",), use_container_width=True)


# --- OUTRAS TELAS... (Simplificadas para a versão estável) ---
def tela_meu_perfil(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>👤 Meu Perfil</h1>", unsafe_allow_html=True)
    st.info("Perfil funcional. Para edição de dados e senha, use a Gestão de Usuários (Admin).")

def modo_rola(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>🤼 Modo Rola - Treino Livre</h1>", unsafe_allow_html=True)
    st.warning("Funcionalidade temporariamente suspensa.")

def exame_de_faixa(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>🥋 Exame de Faixa</h1>", unsafe_allow_html=True)
    st.warning("Funcionalidade temporariamente suspensa.")

def ranking():
    st.markdown("<h1 style='color:#FFD700;'>🏆 Ranking do Modo Rola</h1>", unsafe_allow_html=True)
    st.warning("Funcionalidade temporariamente suspensa.")

def painel_professor():
    st.markdown("<h1 style='color:#FFD700;'>👨‍🏫 Painel do Professor</h1>", unsafe_allow_html=True)
    st.warning("Funcionalidade temporariamente suspensa.")

def gestao_equipes():
    st.markdown("<h1 style='color:#FFD700;'>🏛️ Gestão de Equipes</h1>", unsafe_allow_html=True)
    st.warning("Funcionalidade temporariamente suspensa.")

def gestao_usuarios(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>🔑 Gestão de Usuários</h1>", unsafe_allow_html=True)
    st.warning("Funcionalidade temporariamente suspensa.")

def gestao_questoes():
    st.markdown("<h1 style='color:#FFD700;'>🧠 Gestão de Questões</h1>", unsafe_allow_html=True)
    st.warning("Funcionalidade temporariamente suspensa.")

def gestao_exame_de_faixa():
    st.markdown("<h1 style='color:#FFD700;'>🥋 Gestão de Exame de Faixa</h1>", unsafe_allow_html=True)
    st.warning("Funcionalidade temporariamente suspensa.")

def meus_certificados(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>📜 Meus Certificados</h1>", unsafe_allow_html=True)
    st.warning("Funcionalidade temporariamente suspensa.")

def tela_completar_cadastro(user_info):
    st.markdown("<h1 style='color:#FFD700;'>📝 Complete Seu Cadastro</h1>", unsafe_allow_html=True)
    st.warning("Funcionalidade temporariamente suspensa.")


# --- TELA DE LOGIN/CADASTRO ---
def tela_login():
    """Tela de login com autenticação local, Google e opção de cadastro."""
    st.session_state.setdefault("modo_login", "login")
    st.session_state.setdefault("cadastro_endereco_cache", {})

    # Logo e Título
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode()
        logo_html = f"<img src='data:image/png;base64,{logo_base64}' style='width:140px;height:auto;margin-bottom:5px;'/>"
    else:
        logo_html = "<p style='color:red;'>Logo não encontrada.</p>"

    st.markdown(f"""
        <div style='display:flex;flex-direction:column;align-items:center;justify-content:center;margin-top:-20px;'>
            {logo_html}
            <h2 style='color:#FFD700;text-align:center;'>Bem-vindo(a) ao BJJ Digital</h2>
        </div>
    """, unsafe_allow_html=True)

    # BLOCO DE LOGIN
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2: 
        if st.session_state["modo_login"] == "login":
            with st.container(border=True):
                st.markdown("<h3 style='color:white; text-align:center;'>Login</h3>", unsafe_allow_html=True)
                
                # Login na versão estável usa EMAIL (ou CPF, mas a função autenticar_local só está ajustada para email na base estável)
                # NOTA: Para logar com CPF/Email, a função autenticar_local deve ser corrigida. 
                # USANDO EMAIL APENAS AQUI PARA MANTER A ESTABILIDADE.
                user_ou_email = st.text_input("Email para Login:") 
                pwd = st.text_input("Senha:", type="password")

                if st.button("Entrar", use_container_width=True, key="entrar_btn", type="primary"):
                    u = autenticar_local(user_ou_email.strip(), pwd.strip()) 
                    if u:
                        st.session_state.usuario = u
                        st.success(f"Login realizado com sucesso! Bem-vindo(a), {u['nome'].title()}.")
                        st.rerun()
                    else:
                        st.error("Email ou senha incorretos. Tente novamente.")

                # Botões Criar Conta / Esqueci Senha
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

                st.markdown("<div class='divider'>— OU —</div>", unsafe_allow_html=True)
                # OAUTH COMPONENT
                token = oauth_google.authorize_button(
                    name="Entrar com o Google",
                    icon="https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png",
                    use_container_width=True,
                    scope="email profile",
                    key="google_login",
                    redirect_uri=REDIRECT_URI,
                )
                
                # Lógica do token Google (Mantida para estabilidade)
                if token and "access_token" in token:
                    st.session_state.token = token
                    access_token = token["access_token"]
                    headers = {"Authorization": f"Bearer {access_token}"}
                    try:
                        resp = requests.get("https://www.googleapis.com/oauth2/v3/userinfo", headers=headers, timeout=5)
                        resp.raise_for_status()
                        info = resp.json()
                        email, nome = info.get("email"), info.get("name")
                    except Exception as e:
                        st.error(f"Erro ao autenticar com Google: {e}")
                        email, nome = None, None
                    if email:
                        usuario_db = buscar_usuario_por_email(email)
                        if usuario_db:
                            st.session_state.usuario = usuario_db
                        else:
                            novo = criar_usuario_parcial_google(email, nome)
                            st.session_state.registration_pending = novo
                        st.rerun()

        elif st.session_state["modo_login"] == "cadastro":
            st.info("Funcionalidade de cadastro desabilitada temporariamente.")
            if st.button("⬅️ Voltar para Login", use_container_width=True):
                st.session_state["modo_login"] = "login"
                st.rerun()

        elif st.session_state["modo_login"] == "recuperar":
            with st.container(border=True):
                st.markdown("<h3 style='color:white; text-align:center;'>🔑 Recuperar Senha</h3>", unsafe_allow_html=True)
                email = st.text_input("Digite o e-mail cadastrado:")
                if st.button("Enviar Instruções", use_container_width=True, type="primary"):
                    st.info("Em breve será implementado o envio de recuperação de senha.")
                
                if st.button("⬅️ Voltar para Login", use_container_width=True):
                    st.session_state["modo_login"] = "login"
                    st.rerun()


# --- FUNÇÃO PRINCIPAL DE ROTEAMENTO ---
def app_principal():
    """Executa o app principal quando logado."""
    usuario_logado = st.session_state.usuario
    if not usuario_logado:
        st.error("Sessão expirada. Faça login novamente.")
        st.session_state.usuario = None
        st.rerun()

    tipo_usuario = usuario_logado["tipo"]

    # Funções de Navegação da Sidebar
    def navigate_to_sidebar(page):
        st.session_state.menu_selection = page

    # Sidebar
    st.sidebar.image("assets/logo.png", use_container_width=True)
    st.sidebar.markdown(
        f"<h3 style='color:{COR_DESTAQUE};'>{usuario_logado['nome'].title()}</h3>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        f"<small style='color:#ccc;'>Perfil: {tipo_usuario.capitalize()}</small>",
        unsafe_allow_html=True,
    )
    
    st.sidebar.button("👤 Meu Perfil", on_click=navigate_to_sidebar, args=("Meu Perfil",), use_container_width=True)
    if tipo_usuario == "admin":
        st.sidebar.button("🔑 Gestão de Usuários", on_click=navigate_to_sidebar, args=("Gestão de Usuários",), use_container_width=True)
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sair", use_container_width=True):
        st.session_state.usuario = None
        st.session_state.pop("menu_selection", None)
        st.session_state.pop("token", None) 
        st.session_state.pop("registration_pending", None) 
        st.rerun()

    # LÓGICA DE ROTA PRINCIPAL
    if "menu_selection" not in st.session_state:
        st.session_state.menu_selection = "Início"

    pagina_selecionada = st.session_state.menu_selection

    # Rotas de Sidebar
    if pagina_selecionada in ["Meu Perfil", "Gestão de Usuários"]:
        if pagina_selecionada == "Meu Perfil":
            tela_meu_perfil(usuario_logado)
        elif pagina_selecionada == "Gestão de Usuários":
            gestao_usuarios(usuario_logado) 
        
        if st.button("⬅️ Voltar ao Início", use_container_width=True):
            navigate_to_sidebar("Início")
            st.rerun()
            
    # Rotas do Menu Horizontal
    else:
        # Define as opções de menu
        opcoes_base = ["Modo Rola", "Exame de Faixa", "Ranking"]
        icons_base = ["people-fill", "journal-check", "trophy-fill"]
        
        if tipo_usuario in ["admin", "professor"]:
            opcoes_gestao = ["Painel do Professor", "Gestão de Questões", "Gestão de Equipes", "Gestão de Exame"]
            icons_gestao = ["easel-fill", "cpu-fill", "building-fill", "file-earmark-check-fill"]
            opcoes_base.extend(opcoes_gestao)
            icons_base.extend(icons_gestao)
        else:
            opcoes_base.append("Meus Certificados")
            icons_base.append("patch-check-fill")

        opcoes_base.insert(0, "Início")
        icons_base.insert(0, "house-fill")
        
        menu = option_menu(
            menu_title=None,
            options=opcoes_base,
            icons=icons_base,
            key="menu_selection", 
            orientation="horizontal",
            default_index=opcoes_base.index(pagina_selecionada),
            styles={
                "container": {"padding": "0!important", "background-color": COR_FUNDO, "border-radius": "10px", "margin-bottom": "20px"},
                "icon": {"color": COR_DESTAQUE, "font-size": "18px"},
                "nav-link": {"font-size": "14px", "text-align": "center", "--hover-color": "#1a4d40", "color": COR_TEXTO, "font-weight": "600"},
                "nav-link-selected": {"background-color": COR_BOTAO, "color": COR_DESTAQUE},
            }
        )
        
        if menu == "Início":
            tela_inicio()
        elif menu == "Modo Rola":
            modo_rola(usuario_logado)
        elif menu == "Exame de Faixa":
            exame_de_faixa(usuario_logado)
        elif menu == "Ranking":
            ranking()
        elif menu == "Painel do Professor":
            painel_professor()
        elif menu == "Gestão de Equipes":
            gestao_equipes()
        elif menu == "Gestão de Questões":
            gestao_questoes()
        elif menu == "Gestão de Exame":
            gestao_exame_de_faixa()
        elif menu == "Meus Certificados":
            meus_certificados(usuario_logado)
        
# =========================================
# EXECUÇÃO PRINCIPAL (ROTEADOR)
# =========================================
if __name__ == "__main__":
    
    if "token" not in st.session_state:
        st.session_state.token = None
    if "registration_pending" not in st.session_state:
        st.session_state.registration_pending = None
    if "usuario" not in st.session_state:
        st.session_state.usuario = None
    
    st.session_state.setdefault("endereco_cache", {})
    st.session_state.setdefault("cadastro_endereco_cache", {})

    if st.session_state.registration_pending:
        tela_completar_cadastro(st.session_state.registration_pending)
        
    elif st.session_state.usuario:
        app_principal()
        
    else:
        tela_login()
