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
DB_PATH = os.path.expanduser("~/bjj_digital.db")

def criar_banco():
    """Cria o banco de dados e suas tabelas, caso não existam."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tabela 'usuarios' COMPLETA
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        email TEXT UNIQUE,
        cpf TEXT UNIQUE, 
        tipo_usuario TEXT,
        senha TEXT, 
        auth_provider TEXT DEFAULT 'local', 
        perfil_completo BOOLEAN DEFAULT 0, 
        cep TEXT, 
        logradouro TEXT, 
        numero TEXT, 
        bairro TEXT, 
        cidade TEXT, 
        estado TEXT, 
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
    
    # 1. MIGRAÇÃO DA TABELA USUARIOS
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
            # st.toast(f"Coluna {coluna} (usuarios) adicionada.") # Comentado para não poluir
            
    # 2. MIGRAÇÃO DA TABELA ALUNOS (Datas de exame)
    try:
        cursor.execute("SELECT data_inicio_exame FROM alunos LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE alunos ADD COLUMN data_inicio_exame TEXT")
        cursor.execute("ALTER TABLE alunos ADD COLUMN data_fim_exame TEXT")
        conn.commit()
        # st.toast("Campos de Data de Exame adicionados à tabela 'alunos'.") # Comentado para não poluir
            
    conn.close()

# 5. Usuários de teste (CORRIGIDO: Senha é literal 'admin', 'professor', 'aluno')
def criar_usuarios_teste():
    """Cria usuários padrão locais com perfil completo."""
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
        ("Admin User", "admin", "admin@bjj.local", "00000000000"), 
        ("Professor Responsável", "professor", "professor@bjj.local", "11111111111"), 
        ("Aluno User", "aluno", "aluno@bjj.local", "22222222222")
    ]
    for nome, tipo, email, cpf in usuarios:
        cursor.execute("SELECT id FROM usuarios WHERE email=? OR cpf=?", (email, cpf))
        if cursor.fetchone() is None:
            
            # CORREÇÃO: Usa o tipo do usuário como senha plana, mais fácil de lembrar
            senha_plana = tipo 
            senha_hash = bcrypt.hashpw(senha_plana.encode(), bcrypt.gensalt()).decode()
            
            cursor.execute(
                """
                INSERT INTO usuarios (nome, tipo_usuario, senha, email, cpf, auth_provider, perfil_completo) 
                VALUES (?, ?, ?, ?, ?, 'local', 1)
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
    st.toast("Criando novo banco de dados...")
    criar_banco()
    criar_usuarios_teste() 

# Sempre execute a migração se o DB existir
migrar_db()

# =========================================
# AUTENTICAÇÃO
# =========================================

# 1. Configuração do Google OAuth (lendo do secrets.toml)
try:
    GOOGLE_CLIENT_ID = st.secrets["GOOGLE_CLIENT_ID"]
    GOOGLE_CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
    REDIRECT_URI = "https://bjjdigital.streamlit.app/" # Mude para sua URL de produção
except FileNotFoundError:
    st.error("Arquivo secrets.toml não encontrado. Crie .streamlit/secrets.toml")
    st.stop()
except KeyError:
    st.error("Configure GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET no secrets.toml")
    st.stop()

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
        # st.error(f"Erro na comunicação com a API de CEP: {e}") # Comentado para não poluir
        return None
    except Exception as e:
        # st.error(f"Erro desconhecido ao buscar CEP: {e}") # Comentado para não poluir
        return None

def autenticar_local(usuario_ou_email, senha):
    """Autentica o usuário local usando EMAIL ou CPF."""
    conn = sqlite3.connect(DB_PATH) 
    cursor = conn.cursor()
    dados = None
    
    try:
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

def get_professor_team_id(usuario_id):
    """Busca o ID da equipe principal do professor ativo."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    team_id = None
    try:
        cursor.execute(
            "SELECT equipe_id FROM professores WHERE usuario_id=? AND status_vinculo='ativo' LIMIT 1",
            (usuario_id,)
        )
        result = cursor.fetchone()
        if result:
            team_id = result[0]
    finally:
        conn.close()
    return team_id

def get_alunos_by_equipe(equipe_id):
    """Busca todos os alunos (e seus status de exame) de uma equipe."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    alunos = []
    try:
        cursor.execute(
            """
            SELECT 
                a.id as aluno_id, 
                u.nome as nome_aluno, 
                u.email, 
                a.faixa_atual, 
                a.status_vinculo,
                a.exame_habilitado,
                a.data_inicio_exame, 
                a.data_fim_exame 
            FROM alunos a
            JOIN usuarios u ON a.usuario_id = u.id
            WHERE a.equipe_id=?
            """,
            (equipe_id,)
        )
        alunos = cursor.fetchall()
    finally:
        conn.close()
    return alunos

def habilitar_exame_aluno(aluno_id, data_inicio_str, data_fim_str):
    """Habilita o exame e define o período na tabela alunos."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE alunos 
            SET exame_habilitado=1, data_inicio_exame=?, data_fim_exame=?
            WHERE id=?
            """,
            (data_inicio_str, data_fim_str, aluno_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao habilitar exame: {e}")
        return False
    finally:
        conn.close()

# --- FUNÇÕES DE CERTIFICADO E QUESTÕES (MOCK/HELPERS) ---
def normalizar_nome(nome):
    """Normaliza o nome para uso em nomes de arquivo."""
    return unicodedata.normalize('NFKD', nome).encode('ascii', 'ignore').decode('utf-8').replace(" ", "_")

def gerar_codigo_verificacao():
    """Gera um código de verificação único."""
    return ''.join(random.choices('0123456789ABCDEF', k=16))

def gerar_pdf(nome_aluno, faixa, acertos, total, codigo):
    """Gera o PDF do certificado de exame."""
    os.makedirs("relatorios", exist_ok=True)
    nome_arquivo = f"Certificado_{normalizar_nome(nome_aluno)}_{normalizar_nome(faixa)}.pdf"
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
    pdf.multi_cell(0, 10, f'Certificamos que {nome_aluno} foi aprovado(a) no Exame Teórico de Faixa.', 0, 'C')
    pdf.multi_cell(0, 10, f'Faixa: {faixa}', 0, 'C')
    pdf.multi_cell(0, 10, f'Desempenho: {acertos} acertos de um total de {total} questões.', 0, 'C')
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
# TELAS DO APP (DEFINIDAS ANTES DE app_principal)
# =========================================

# --- NOVO: TELA INICIAL (DASHBOARD) ---
def tela_inicio():
    st.markdown("<h1 style='color:#FFD700;'>🏠 Bem-vindo(a) ao BJJ Digital!</h1>", unsafe_allow_html=True)
    
    st.subheader("O que você deseja fazer hoje?")
    
    usuario_logado = st.session_state.usuario
    tipo_usuario = usuario_logado["tipo"]
    
    col1, col2, col3 = st.columns(3)

    if tipo_usuario in ["aluno"]:
        with col1:
            st.container(border=True).markdown("<h3>🤼 Modo Rola</h3><p>Treine seus conhecimentos técnicos.</p><p>Resultados salvos no Ranking.</p>", unsafe_allow_html=True)
            if st.button("Acessar Rola", key="go_rola", use_container_width=True):
                st.session_state.menu_selection = "Modo Rola"
                st.rerun()

        with col2:
            st.container(border=True).markdown("<h3>📜 Certificados</h3><p>Baixe seus certificados de aprovação em exames.</p><p>Disponível após aprovação no Exame.</p>", unsafe_allow_html=True)
            if st.button("Ver Certificados", key="go_cert", use_container_width=True):
                st.session_state.menu_selection = "Meus Certificados"
                st.rerun()
                
        with col3:
            st.container(border=True).markdown("<h3>🏆 Ranking</h3><p>Compare seu desempenho com outros alunos.</p><p>Mostra a média de acertos no Modo Rola.</p>", unsafe_allow_html=True)
            if st.button("Ver Ranking", key="go_rank", use_container_width=True):
                st.session_state.menu_selection = "Ranking"
                st.rerun()
                
    elif tipo_usuario in ["professor", "admin"]:
        with col1:
            st.container(border=True).markdown("<h3>👨‍🏫 Painel Professor</h3><p>Gerencie alunos e libere exames de faixa.</p><p>Aprovação de novos professores.</p>", unsafe_allow_html=True)
            if st.button("Acessar Painel", key="go_painel", use_container_width=True):
                st.session_state.menu_selection = "Painel do Professor"
                st.rerun()

        with col2:
            st.container(border=True).markdown("<h3>⚙️ Gestão Equipes</h3><p>Crie e administre equipes, e vincule professores.</p><p>Apenas para Admin e Responsáveis.</p>", unsafe_allow_html=True)
            if st.button("Acessar Gestão", key="go_equipe", use_container_width=True):
                st.session_state.menu_selection = "Gestão de Equipes"
                st.rerun()
                
        with col3:
            st.container(border=True).markdown("<h3>📝 Gestão de Exames</h3><p>Monte o exame de faixa para cada graduação.</p><p>Use questões cadastradas na Gestão de Questões.</p>", unsafe_allow_html=True)
            if st.button("Montar Exames", key="go_exame", use_container_width=True):
                st.session_state.menu_selection = "Gestão de Exame"
                st.rerun()

# --- NOVO: TELA MEU PERFIL ---
def tela_meu_perfil(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>👤 Meu Perfil</h1>", unsafe_allow_html=True)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Obter dados do usuário
    cursor.execute("SELECT * FROM usuarios WHERE id=?", (usuario_logado["id"],))
    dados_usuario = cursor.fetchone()
    
    # 2. Obter dados específicos (aluno/professor)
    dados_especificos = {}
    if usuario_logado["tipo"] == "aluno":
        cursor.execute("""
            SELECT 
                a.faixa_atual, a.status_vinculo, e.nome AS equipe_nome
            FROM alunos a
            LEFT JOIN equipes e ON a.equipe_id = e.id
            WHERE a.usuario_id=?
        """, (usuario_logado["id"],))
        dados_especificos = cursor.fetchone()
        
    elif usuario_logado["tipo"] == "professor":
        cursor.execute("""
            SELECT 
                p.eh_responsavel, e.nome AS equipe_nome
            FROM professores p
            LEFT JOIN equipes e ON p.equipe_id = e.id
            WHERE p.usuario_id=? AND p.status_vinculo='ativo'
        """, (usuario_logado["id"],))
        dados_especificos = cursor.fetchone()
        
    conn.close()

    if not dados_usuario:
        st.error("Dados do usuário não encontrados.")
        return

    st.subheader("Informações Básicas")
    
    col1, col2 = st.columns(2)
    col1.metric("Nome", dados_usuario["nome"])
    col2.metric("Email", dados_usuario["email"])
    
    col1.metric("CPF", dados_usuario["cpf"] or "N/A")
    col2.metric("Tipo de Acesso", dados_usuario["tipo_usuario"].capitalize())

    st.markdown("---")
    st.subheader("Endereço")
    
    if dados_usuario["logradouro"]:
        st.markdown(f"**CEP:** {dados_usuario['cep']}")
        st.markdown(f"**Endereço:** {dados_usuario['logradouro']}, {dados_usuario['numero']} - {dados_usuario['bairro']}")
        st.markdown(f"**Cidade/Estado:** {dados_usuario['cidade']} / {dados_usuario['estado']}")
    else:
        st.info("Endereço não cadastrado. Cadastre no login ou edite na Gestão de Usuários (Admin).")

    st.markdown("---")
    st.subheader("Status no Jiu-Jitsu")
    
    if usuario_logado["tipo"] == "aluno" and dados_especificos:
        st.metric("Faixa Atual", dados_especificos["faixa_atual"])
        st.metric("Equipe Vinculada", dados_especificos["equipe_nome"] or "Nenhuma")
        st.metric("Status de Vínculo", dados_especificos["status_vinculo"].capitalize())
        
    elif usuario_logado["tipo"] == "professor" and dados_especificos:
        st.metric("Equipe Responsável", dados_especificos["equipe_nome"] or "Nenhuma")
        if dados_especificos["eh_responsavel"]:
            st.success("Você é o Professor Responsável pela equipe.")
        else:
            st.info("Você é um Professor de Apoio.")
            
    elif usuario_logado["tipo"] == "admin":
        st.success("Administrador Global.")
    else:
        st.warning(f"Seu perfil de {usuario_logado['tipo']} ainda não possui vínculo ativo com equipe/graduação.")

def modo_rola(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>🤼 Modo Rola - Treino Livre</h1>", unsafe_allow_html=True)

    temas = [f.replace(".json", "") for f in os.listdir("questions") if f.endswith(".json")]
    temas.append("Todos os Temas")

    col1, col2 = st.columns(2)
    with col1:
        tema = st.selectbox("Selecione o tema:", temas)
    with col2:
        faixa = st.selectbox("Sua faixa:", ["Branca", "Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"])

    if st.button("Iniciar Treino 🤼", use_container_width=True):
        # 🔹 Carrega questões conforme seleção
        if tema == "Todos os Temas":
            questoes = carregar_todas_questoes()
        else:
            questoes = carregar_questoes(tema)

        if not questoes:
            st.error("Nenhuma questão disponível para este tema.")
            return

        random.shuffle(questoes)
        acertos = 0
        total = len(questoes)

        st.markdown(f"### 🧩 Total de questões: {total}")

        for i, q in enumerate(questoes, 1):
            st.markdown(f"### {i}. {q['pergunta']}")

            if q.get("imagem") and os.path.exists(q["imagem"].strip()):
                st.image(q["imagem"].strip(), use_container_width=True)
            if q.get("video"):
                try:
                    st.video(q["video"])
                except Exception:
                    st.warning("⚠️ Não foi possível carregar o vídeo associado a esta questão.")

            resposta = st.radio("Escolha a alternativa:", q["opcoes"], key=f"rola_{i}", index=None)

            if resposta and st.button(f"Confirmar resposta {i}", key=f"confirma_{i}"):
                if resposta.startswith(q["resposta"]):
                    acertos += 1
                    st.success("✅ Correto!")
                else:
                    st.error(f"❌ Incorreto. Resposta correta: {q['resposta']}")
            
            st.markdown("---")

        percentual = int((acertos / total) * 100)
        st.markdown(f"## Resultado Final: {percentual}% de acertos ({acertos}/{total})")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO rola_resultados (usuario, faixa, tema, acertos, total, percentual)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (usuario_logado["nome"], faixa, tema, acertos, total, percentual))
        conn.commit()
        conn.close()

        st.success("Resultado salvo com sucesso! 🏆")

def exame_de_faixa(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>🥋 Exame de Faixa</h1>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT exame_habilitado, data_inicio_exame, data_fim_exame FROM alunos WHERE usuario_id=?", (usuario_logado["id"],))
    dado = cursor.fetchone()
    conn.close()

    if usuario_logado["tipo"] not in ["admin", "professor"]:
        if not dado or dado[0] == 0:
            st.warning("🚫 Seu exame de faixa ainda não foi liberado. Aguarde a autorização do professor.")
            return
        
        if dado[0] == 1:
            data_inicio = datetime.strptime(dado[1], '%Y-%m-%d').date() if dado[1] else date.min
            data_fim = datetime.strptime(dado[2], '%Y-%m-%d').date() if dado[2] else date.max
            hoje = date.today()
            
            if hoje < data_inicio:
                st.info(f"O período do seu exame começa em **{data_inicio.strftime('%d/%m/%Y')}**. Aguarde a data de início.")
                return
            if hoje > data_fim:
                st.error(f"Seu prazo para realizar o exame terminou em **{data_fim.strftime('%d/%m/%Y')}**. Contate seu professor para solicitar uma nova liberação.")
                return


    faixa = st.selectbox(
        "Selecione sua faixa:",
        ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
    )

    exame_path = f"exames/faixa_{faixa.lower()}.json"
    if not os.path.exists(exame_path):
        st.error("Nenhum exame cadastrado para esta faixa ainda.")
        return

    try:
        with open(exame_path, "r", encoding="utf-8") as f:
            exame = json.load(f)
    except json.JSONDecodeError:
        st.error(f"⚠️ O arquivo '{exame_path}' está corrompido. Verifique o formato JSON.")
        return

    questoes = exame.get("questoes", [])
    if not questoes:
        st.info("Ainda não há questões cadastradas para esta faixa.")
        return

    st.markdown(f"### 🧩 Total de questões: {len(questoes)}")

    respostas = {}
    for i, q in enumerate(questoes, 1):
        st.markdown(f"### {i}. {q['pergunta']}")

        if q.get("imagem") and os.path.exists(q["imagem"].strip()):
            st.image(q["imagem"].strip(), use_container_width=True)

        if q.get("video"):
            try:
                st.video(q["video"])
            except Exception:
                st.warning("⚠️ Não foi possível carregar o vídeo associado a esta questão.")

        respostas[i] = st.radio(
            "Escolha a alternativa:",
            q["opcoes"],
            key=f"exame_{i}",
            index=None
        )

        st.markdown("---")

    finalizar = st.button("Finalizar Exame 🏁", use_container_width=True)

    if finalizar:
        acertos = sum(
            1 for i, q in enumerate(questoes, 1)
            if respostas.get(i, "") and respostas[i].startswith(q["resposta"])
        )

        total = len(questoes)
        percentual = int((acertos / total) * 100)
        st.markdown(f"## Resultado Final: {percentual}% de acertos ({acertos}/{total})")

        st.session_state["certificado_pronto"] = False

        if percentual >= 70:
            st.success("🎉 Parabéns! Você foi aprovado(a) no Exame de Faixa! 👏")

            codigo = gerar_codigo_verificacao()
            st.session_state["certificado_pronto"] = True
            st.session_state["dados_certificado"] = {
                "usuario": usuario_logado["nome"],
                "faixa": faixa,
                "acertos": acertos,
                "total": total,
                "codigo": codigo
            }

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO resultados (usuario, modo, faixa, pontuacao, acertos, total_questoes, data, codigo_verificacao)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (usuario_logado["nome"], "Exame de Faixa", faixa, percentual, acertos, total, datetime.now(), codigo))
            conn.commit()
            conn.close()

        else:
            st.error("😞 Você não atingiu a pontuação mínima (70%). Continue treinando e tente novamente! 💪")

    if st.session_state.get("certificado_pronto") and finalizar:
        dados = st.session_state["dados_certificado"]
        caminho_pdf = gerar_pdf(
            dados["usuario"],
            dados["faixa"],
            dados["acertos"],
            dados["total"],
            dados["codigo"]
        )

        st.info("Clique abaixo para gerar e baixar seu certificado.")
        with open(caminho_pdf, "rb") as f:
            st.download_button(
                label="📥 Baixar Certificado de Exame",
                data=f.read(),
                file_name=os.path.basename(caminho_pdf),
                mime="application/pdf",
                use_container_width=True
            )

        st.success("Certificado gerado com sucesso! 🥋")

def ranking():
    st.markdown("<h1 style='color:#FFD700;'>🏆 Ranking do Modo Rola</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM rola_resultados", conn)
    conn.close()

    if df.empty:
        st.info("Nenhum resultado disponível no ranking ainda.")
        return

    filtro_faixa = st.selectbox("Filtrar por faixa:", ["Todas"] + sorted(df["faixa"].unique().tolist()))
    if filtro_faixa != "Todas":
        df = df[df["faixa"] == filtro_faixa]

    if df.empty:
        st.info("Nenhum resultado para esta faixa.")
        return

    ranking_df = df.groupby("usuario", as_index=False).agg(
        media_percentual=("percentual", "mean"),
        total_treinos=("id", "count")
    ).sort_values(by="media_percentual", ascending=False).reset_index(drop=True)

    ranking_df["Posição"] = range(1, len(ranking_df) + 1)
    ranking_df["media_percentual"] = ranking_df["media_percentual"].round(2)
    
    st.dataframe(
        ranking_df[["Posição", "usuario", "media_percentual", "total_treinos"]], 
        use_container_width=True,
        column_config={"media_percentual": st.column_config.NumberColumn(format="%.2f%%")}
    )

    fig = px.bar(
        ranking_df.head(10),
        x="usuario",
        y="media_percentual",
        text_auto=True,
        title="Top 10 - Modo Rola (% Média de Acertos)",
        color="media_percentual",
        color_continuous_scale="YlOrBr",
    )
    fig.update_layout(xaxis_title="Usuário", yaxis_title="% Média de Acertos")
    st.plotly_chart(fig, use_container_width=True)

def painel_professor():
    st.title("🥋 Painel do Professor")
    
    conn = sqlite3.connect(DB_PATH) 
    cursor = conn.cursor()
    
    professor_id = st.session_state.usuario['id']
    usuario_tipo = st.session_state.usuario['tipo']
    
    equipe_responsavel = cursor.execute(
        "SELECT id, nome FROM equipes WHERE professor_responsavel_id=?", 
        (professor_id,)
    ).fetchone()
    
    equipe_id_responsavel = equipe_responsavel[0] if equipe_responsavel else None
    equipe_nome_responsavel = equipe_responsavel[1] if equipe_responsavel else 'N/A'
    
    if not equipe_id_responsavel and usuario_tipo != 'admin':
        st.warning("Você ainda não é o Professor Responsável por uma equipe. Esta seção não está disponível.")
        conn.close()
        return

    tab_alunos, tab_aprovacao = st.tabs(["Alunos da Equipe", "Solicitações Pendentes (Professores)"])

    with tab_alunos:
        equipe_id = equipe_id_responsavel if equipe_id_responsavel else 0 

        if equipe_id == 0:
             st.info("Você não é responsável por nenhuma equipe. Use a Gestão de Equipes para visualização completa.")
        else:
            st.header(f"Lista de Alunos da Equipe: {equipe_nome_responsavel}")
            
            dados_alunos = get_alunos_by_equipe(equipe_id)
            df_alunos = pd.DataFrame(dados_alunos)
            
            if df_alunos.empty:
                st.info("Nenhum aluno ativo ou pendente encontrado para sua equipe.")
            else:
                st.subheader("Liberar Período de Exame de Faixa")
                
                alunos_ativos = df_alunos[df_alunos['status_vinculo'] == 'ativo'].copy()
                
                if alunos_ativos.empty:
                    st.info("Não há alunos ativos para habilitar exames.")
                else:
                    alunos_para_selecao = {
                        f"{row['nome_aluno']} ({row['faixa_atual']})": row['aluno_id'] 
                        for index, row in alunos_ativos.iterrows()
                    }
                    
                    with st.form("form_habilitar_exame", clear_on_submit=True):
                        col1, col2 = st.columns(2)
                        aluno_selecionado_str = col1.selectbox("Selecione o Aluno",list(alunos_para_selecao.keys()),key="aluno_select")
                        aluno_id_selecionado = alunos_para_selecao.get(aluno_selecionado_str)

                        hoje = date.today()
                        data_inicio = col1.date_input("Data de Início do Exame", hoje)
                        data_fim = col2.date_input("Data Limite para o Exame", hoje + timedelta(days=14))
                        
                        if data_fim < data_inicio:
                            st.error("A Data Limite deve ser posterior à Data de Início.")
                            submetido = False
                        else:
                            submetido = st.form_submit_button("Habilitar Exame e Agendar Alerta")
                        
                        if submetido:
                            data_inicio_str = data_inicio.strftime('%Y-%m-%d')
                            data_fim_str = data_fim.strftime('%Y-%m-%d')
                            
                            if habilitar_exame_aluno(aluno_id_selecionado, data_inicio_str, data_fim_str):
                                st.success(f"Exame habilitado para **{aluno_selecionado_str}** de **{data_inicio_str}** até **{data_fim_str}**!")
                                st.session_state["refresh_professor_panel"] = True 
                            else:
                                st.error("Erro ao salvar no banco de dados. Tente novamente.")

                if "refresh_professor_panel" in st.session_state and st.session_state["refresh_professor_panel"]:
                    st.session_state["refresh_professor_panel"] = False
                    dados_alunos = get_alunos_by_equipe(equipe_id)
                    df_alunos = pd.DataFrame(dados_alunos)
                    
                df_display = df_alunos.copy()
                df_display['Data Início'] = df_display['data_inicio_exame'].fillna('N/A')
                df_display['Data Limite'] = df_display['data_fim_exame'].fillna('N/A')
                df_display['Habilitado'] = df_display['exame_habilitado'].apply(lambda x: '✅ Sim' if x else '❌ Não')
                
                st.markdown("---")
                st.subheader("Situação dos Exames")
                
                st.dataframe(
                    df_display[['nome_aluno', 'faixa_atual', 'status_vinculo', 'Habilitado', 'Data Início', 'Data Limite']],
                    column_config={
                        "nome_aluno": "Aluno",
                        "faixa_atual": "Faixa",
                        "status_vinculo": "Status Vínculo",
                        "Habilitado": "Exame Habilitado",
                    },
                    hide_index=True
                )

    with tab_aprovacao:
        if equipe_id_responsavel is None and usuario_tipo != 'admin':
            st.warning("Apenas o Professor Responsável ou Admin pode aprovar solicitações.")
            
        else:
            st.header("Solicitações de Ingresso de Professores")
            
            query = """
                SELECT 
                    p.id, u.nome, u.email, e.nome AS equipe_nome, p.usuario_id
                FROM professores p
                JOIN usuarios u ON p.usuario_id = u.id
                JOIN equipes e ON p.equipe_id = e.id
                WHERE p.status_vinculo = 'pendente' 
            """
            params = ()
            
            if usuario_tipo == 'professor':
                query += " AND p.equipe_id = ?"
                params = (equipe_id_responsavel,)
            
            professores_pendentes = pd.read_sql_query(query, conn, params=params)
            
            if professores_pendentes.empty:
                st.info("Nenhuma solicitação de professor pendente para aprovação.")
            else:
                st.dataframe(professores_pendentes, use_container_width=True)
                
                st.markdown("---")
                st.subheader("Aprovar/Rejeitar")
                
                for index, row in professores_pendentes.iterrows():
                    prof_id = row['id'] 
                    usuario_id_prof = row['usuario_id']
                    
                    with st.container(border=True):
                        st.markdown(f"**Professor:** {row['nome']} ({row['email']})")
                        st.markdown(f"**Equipe Solicitada:** {row['equipe_nome']}")
                        
                        col_aprov, col_rejeita = st.columns(2)
                        
                        if col_aprov.button("✅ Aprovar Ingresso", key=f"aprov_{prof_id}"):
                            cursor.execute("UPDATE professores SET status_vinculo='ativo' WHERE id=?", (prof_id,))
                            cursor.execute("UPDATE usuarios SET tipo_usuario='professor' WHERE id=?", (usuario_id_prof,))
                            conn.commit()
                            st.success(f"Professor {row['nome']} aprovado com sucesso! ✅")
                            st.rerun()
                            
                        if col_rejeita.button("❌ Rejeitar Ingresso", key=f"rejeita_{prof_id}"):
                            cursor.execute("UPDATE professores SET status_vinculo='rejeitado' WHERE id=?", (prof_id,))
                            conn.commit()
                            st.warning(f"Professor {row['nome']} rejeitado.")
                            st.rerun()

    conn.close() 

def gestao_equipes():
    st.markdown("<h1 style='color:#FFD700;'>🏛️ Gestão de Equipes</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    aba1, aba2, aba3 = st.tabs(["🏫 Equipes", "👩‍🏫 Professores", "🥋 Alunos"])

    with aba1:
        st.subheader("Cadastrar nova equipe")
        nome_equipe = st.text_input("Nome da nova equipe:")
        descricao = st.text_area("Descrição da nova equipe:")

        professores_df = pd.read_sql_query("SELECT id, nome FROM usuarios WHERE tipo_usuario='professor'", conn)
        professor_responsavel_id = None
        if not professores_df.empty:
            prof_resp_nome = st.selectbox(
                "👩‍🏫 Professor responsável:",
                ["Nenhum"] + professores_df["nome"].tolist()
            )
            if prof_resp_nome != "Nenhum":
                professor_responsavel_id = int(professores_df.loc[professores_df["nome"] == prof_resp_nome, "id"].values[0])

        if st.button("➕ Criar Equipe"):
            if nome_equipe.strip():
                cursor.execute(
                    "INSERT INTO equipes (nome, descricao, professor_responsavel_id) VALUES (?, ?, ?)",
                    (nome_equipe, descricao, professor_responsavel_id)
                )
                conn.commit()
                st.success(f"Equipe '{nome_equipe}' criada com sucesso!")
                st.rerun()
            else:
                st.error("O nome da equipe é obrigatório.")

        st.markdown("---")
        st.subheader("Equipes existentes")
        equipes_df = pd.read_sql_query("""
            SELECT e.id, e.nome, e.descricao, COALESCE(u.nome, 'Nenhum') AS professor_responsavel
            FROM equipes e
            LEFT JOIN usuarios u ON e.professor_responsavel_id = u.id
        """, conn)
        if equipes_df.empty:
            st.info("Nenhuma equipe cadastrada.")
        else:
            st.dataframe(equipes_df, use_container_width=True)
            st.markdown("### ✏️ Editar ou Excluir Equipe")

            equipe_lista = equipes_df["nome"].tolist()
            equipe_sel = st.selectbox("Selecione a equipe:", equipe_lista, index=None, placeholder="Selecione uma equipe para gerenciar...")
            
            if equipe_sel:
                equipe_id = int(equipes_df.loc[equipes_df["nome"] == equipe_sel, "id"].values[0])
                dados_equipe = equipes_df[equipes_df["id"] == equipe_id].iloc[0]

                with st.expander(f"Gerenciar {equipe_sel}", expanded=True):
                    novo_nome = st.text_input("Novo nome da equipe:", value=dados_equipe["nome"])
                    nova_desc = st.text_area("Descrição:", value=dados_equipe["descricao"] or "")

                    prof_atual = dados_equipe["professor_responsavel"]
                    prof_opcoes = ["Nenhum"] + professores_df["nome"].tolist()
                    index_atual = prof_opcoes.index(prof_atual) if prof_atual in prof_opcoes else 0
                    novo_prof = st.selectbox("👩‍🏫 Professor responsável:", prof_opcoes, index=index_atual)
                    novo_prof_id = None
                    if novo_prof != "Nenhum":
                        novo_prof_id = int(professores_df.loc[professores_df["nome"] == novo_prof, "id"].values[0])

                    col1, col2 = st.columns(2)
                    if col1.button("💾 Salvar Alterações"):
                        cursor.execute(
                            "UPDATE equipes SET nome=?, descricao=?, professor_responsavel_id=? WHERE id=?",
                            (novo_nome, nova_desc, novo_prof_id, equipe_id)
                        )
                        conn.commit()
                        st.success(f"Equipe '{novo_nome}' atualizada com sucesso! ✅")
                        st.rerun()

                    if col2.button("🗑️ Excluir Equipe"):
                        cursor.execute("DELETE FROM equipes WHERE id=?", (equipe_id,))
                        conn.commit()
                        st.warning(f"Equipe '{equipe_sel}' excluída com sucesso.")
                        st.rerun()


    with aba2:
        st.subheader("Vincular professor de apoio a uma equipe")

        professores_df = pd.read_sql_query("SELECT id, nome FROM usuarios WHERE tipo_usuario='professor'", conn)
        equipes_df = pd.read_sql_query("SELECT id, nome FROM equipes", conn)

        if professores_df.empty or equipes_df.empty:
            st.warning("Cadastre professores e equipes primeiro.")
        else:
            prof = st.selectbox("Professor de apoio:", professores_df["nome"], key="prof_apoio")
            equipe_prof = st.selectbox("Equipe:", equipes_df["nome"], key="equipe_apoio")
            prof_id = int(professores_df.loc[professores_df["nome"] == prof, "id"].values[0])
            equipe_id = int(equipes_df.loc[equipes_df["nome"] == equipe_prof, "id"].values[0])

            if st.button("📎 Vincular Professor de Apoio"):
                cursor.execute("""
                    INSERT INTO professores (usuario_id, equipe_id, pode_aprovar, status_vinculo)
                    VALUES (?, ?, ?, ?)
                """, (prof_id, equipe_id, 0, "ativo"))
                conn.commit()
                st.success(f"Professor {prof} vinculado como apoio à equipe {equipe_prof}.")
                st.rerun()

        st.markdown("---")
        st.subheader("Professores vinculados")
        profs_df = pd.read_sql_query("""
            SELECT p.id, u.nome AS professor, e.nome AS equipe, p.status_vinculo
            FROM professores p
            JOIN usuarios u ON p.usuario_id = u.id
            JOIN equipes e ON p.equipe_id = e.id
        """, conn)
        if profs_df.empty:
            st.info("Nenhum professor vinculado ainda.")
        else:
            st.dataframe(profs_df, use_container_width=True)

    with aba3:
        st.subheader("Vincular aluno a professor e equipe")

        alunos_df = pd.read_sql_query("SELECT id, nome FROM usuarios WHERE tipo_usuario='aluno'", conn)
        professores_df = pd.read_sql_query("""
            SELECT p.id, u.nome AS nome_professor, p.equipe_id 
            FROM professores p 
            JOIN usuarios u ON p.usuario_id = u.id 
            WHERE p.status_vinculo='ativo'
        """, conn)
        equipes_df = pd.read_sql_query("SELECT id, nome FROM equipes", conn)

        if alunos_df.empty or professores_df.empty or equipes_df.empty:
            st.warning("Cadastre alunos, professores e equipes antes de vincular.")
        else:
            aluno = st.selectbox("🥋 Aluno:", alunos_df["nome"], key="aluno_vinc")
            professor_nome = st.selectbox("👩‍🏫 Professor vinculado (nome):", professores_df["nome_professor"], key="prof_vinc")
            equipe_aluno = st.selectbox("🏫 Equipe do aluno:", equipes_df["nome"], key="equipe_vinc")

            aluno_id = int(alunos_df.loc[alunos_df["nome"] == aluno, "id"].values[0])
            professor_id = int(professores_df.loc[professores_df["nome_professor"] == professor_nome, "id"].values[0])
            equipe_id = int(equipes_df.loc[equipes_df["nome"] == equipe_aluno, "id"].values[0])

            if st.button("✅ Vincular Aluno"):
                # Verifica se já existe um vínculo ativo, se sim, deleta ou atualiza
                cursor.execute("DELETE FROM alunos WHERE usuario_id=?", (aluno_id,))
                
                cursor.execute("""
                    INSERT INTO alunos (usuario_id, faixa_atual, turma, professor_id, equipe_id, status_vinculo)
                    VALUES (?, ?, ?, ?, ?, 'ativo')
                """, (aluno_id, "Branca", "Turma 1", professor_id, equipe_id))
                conn.commit()
                st.success(f"Aluno {aluno} vinculado à equipe {equipe_aluno} sob orientação de {professor_nome}.")
                st.rerun()

        st.markdown("---")
        st.subheader("Alunos vinculados")
        alunos_vinc_df = pd.read_sql_query("""
            SELECT a.id, u.nome AS aluno, e.nome AS equipe, up.nome AS professor
            FROM alunos a
            JOIN usuarios u ON a.usuario_id = u.id
            JOIN equipes e ON a.equipe_id = e.id
            JOIN professores p ON a.professor_id = p.id
            JOIN usuarios up ON p.usuario_id = up.id
        """, conn)
        if alunos_vinc_df.empty:
            st.info("Nenhum aluno vinculado ainda.")
        else:
            st.dataframe(alunos_vinc_df, use_container_width=True)

    conn.close()

def gestao_usuarios(usuario_logado):
    """Página de gerenciamento de usuários, restrita ao Admin."""
    
    if usuario_logado["tipo"] != "admin":
        st.error("Acesso negado. Esta página é restrita aos administradores.")
        return

    st.markdown("<h1 style='color:#FFD700;'>🔑 Gestão de Usuários</h1>", unsafe_allow_html=True)
    st.markdown("Edite informações, redefina senhas ou altere o tipo de perfil de um usuário.")

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT id, nome, email, cpf, tipo_usuario, auth_provider, perfil_completo FROM usuarios ORDER BY nome", 
        conn
    )

    st.subheader("Visão Geral dos Usuários")
    st.dataframe(df, use_container_width=True)
    st.markdown("---")

    st.subheader("Editar Usuário")
    lista_nomes = df["nome"].tolist()
    nome_selecionado = st.selectbox(
        "Selecione um usuário para gerenciar:",
        options=lista_nomes,
        index=None,
        placeholder="Selecione..."
    )

    if nome_selecionado:
        try:
            user_id_selecionado = int(df[df["nome"] == nome_selecionado]["id"].values[0])
        except IndexError:
            st.error("Usuário não encontrado no DataFrame. Tente recarregar a página.")
            conn.close()
            return
            
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM usuarios WHERE id=?", (user_id_selecionado,))
        user_data = cursor.fetchone()
        
        if not user_data:
            st.error("Usuário não encontrado no banco de dados. (ID não correspondeu)")
            conn.close()
            return

        with st.expander(f"Gerenciando: {user_data['nome']}", expanded=True):
            
            with st.form(key="form_edit_user"):
                st.markdown("#### 1. Informações do Perfil")
                
                col1, col2 = st.columns(2)
                novo_nome = col1.text_input("Nome:", value=user_data['nome'])
                novo_email = col2.text_input("Email:", value=user_data['email'])
                novo_cpf = st.text_input("CPF:", value=user_data['cpf'] or "", help="Necessário para usuários locais.")
                
                opcoes_tipo = ["aluno", "professor", "admin"]
                tipo_atual_db = user_data['tipo_usuario']
                
                index_atual = 0 
                if tipo_atual_db:
                    try:
                        index_atual = [t.lower() for t in opcoes_tipo].index(tipo_atual_db.lower())
                    except ValueError:
                        index_atual = 0 
                
                novo_tipo = st.selectbox(
                    "Tipo de Usuário:",
                    options=opcoes_tipo,
                    index=index_atual 
                )
                
                st.text_input("Provedor de Auth:", value=user_data['auth_provider'], disabled=True)
                
                submitted_info = st.form_submit_button("💾 Salvar Alterações", use_container_width=True)
                
                if submitted_info:
                    if user_data['auth_provider'] == 'local' and not validar_cpf(novo_cpf):
                        st.error("CPF inválido. Por favor, corrija.")
                        st.stop()
                    
                    try:
                        cursor.execute(
                            "UPDATE usuarios SET nome=?, email=?, cpf=?, tipo_usuario=? WHERE id=?",
                            (novo_nome, novo_email, novo_cpf, novo_tipo, user_id_selecionado)
                        )
                        conn.commit()
                        st.success("Dados do usuário atualizados com sucesso!")
                    except sqlite3.IntegrityError:
                        st.error(f"Erro: O email '{novo_email}' ou CPF '{novo_cpf}' já está em uso por outro usuário.")
                    except Exception as e:
                        st.error(f"Ocorreu um erro: {e}")

            st.markdown("---")

            st.markdown("#### 2. Redefinição de Senha")
            if user_data['auth_provider'] == 'local':
                with st.form(key="form_reset_pass"):
                    nova_senha = st.text_input("Nova Senha:", type="password")
                    confirmar_senha = st.text_input("Confirmar Nova Senha:", type="password")
                    
                    submitted_pass = st.form_submit_button("🔑 Redefinir Senha", use_container_width=True)
                    
                    if submitted_pass:
                        if not nova_senha or not confirmar_senha:
                            st.warning("Por favor, preencha os dois campos de senha.")
                        elif nova_senha != confirmar_senha:
                            st.error("As senhas não coincidem.")
                        else:
                            novo_hash = bcrypt.hashpw(nova_senha.encode(), bcrypt.gensalt()).decode()
                            cursor.execute(
                                "UPDATE usuarios SET senha=? WHERE id=?",
                                (novo_hash, user_id_selecionado)
                            )
                            conn.commit()
                            st.success("Senha do usuário redefinida com sucesso!")
            else:
                st.info(f"Não é possível redefinir a senha de usuários via '{user_data['auth_provider']}'.")
    
    conn.close()

def gestao_questoes():
    st.markdown("<h1 style='color:#FFD700;'>📝 Gestão de Questões</h1>", unsafe_allow_html=True)
    st.info("Esta seção permite cadastrar, editar e excluir questões para os modos Rola e Exame.")
    os.makedirs("questions", exist_ok=True)

    tab_cad, tab_list = st.tabs(["Cadastrar Nova Questão", "Listar e Editar"])

    with tab_cad:
        with st.form("form_nova_questao", clear_on_submit=True):
            st.subheader("Nova Questão")
            
            tema = st.text_input("Tema da Questão (Ex: Defesas de Queda, Raspagens, etc.):")
            pergunta = st.text_area("Pergunta:")
            
            st.markdown("---")
            st.subheader("Alternativas")
            opcoes = []
            for i in range(4):
                opcoes.append(st.text_input(f"Opção {i+1}:", key=f"op_{i}"))
            
            resposta = st.selectbox("Resposta Correta:", opcoes, index=None)
            
            imagem = st.text_input("Caminho da Imagem (opcional, Ex: assets/posicao.png):")
            video = st.text_input("Link do Vídeo (opcional, Ex: URL do Youtube):")

            submitted = st.form_submit_button("Salvar Questão")

            if submitted:
                if not (tema and pergunta and resposta and all(opcoes)):
                    st.error("Por favor, preencha o Tema, a Pergunta, a Resposta Correta e todas as 4 Opções.")
                else:
                    nova_questao = {
                        "pergunta": pergunta,
                        "opcoes": opcoes,
                        "resposta": resposta,
                        "imagem": imagem,
                        "video": video
                    }

                    caminho = f"questions/{tema.strip().lower().replace(' ', '_')}.json"
                    
                    if os.path.exists(caminho):
                        try:
                            with open(caminho, "r", encoding="utf-8") as f:
                                questoes = json.load(f)
                        except json.JSONDecodeError:
                            questoes = []
                    else:
                        questoes = []

                    questoes.append(nova_questao)
                    
                    with open(caminho, "w", encoding="utf-8") as f:
                        json.dump(questoes, f, indent=4, ensure_ascii=False)
                    
                    st.success(f"Questão adicionada ao tema '{tema}' com sucesso! ✅")

    with tab_list:
        st.subheader("Lista de Questões Cadastradas")
        todas = carregar_todas_questoes()
        
        if not todas:
            st.info("Nenhuma questão cadastrada.")
            return

        df_questoes = pd.DataFrame(todas)
        df_questoes['opcoes'] = df_questoes['opcoes'].apply(lambda x: '; '.join(x))
        
        st.dataframe(df_questoes[['tema', 'pergunta', 'resposta', 'opcoes']], use_container_width=True)
        
        st.markdown("---")
        st.subheader("Excluir Questão")
        
        perguntas_list = [f"({q['tema']}) {q['pergunta']}" for q in todas]
        pergunta_excluir = st.selectbox("Selecione a pergunta para excluir:", perguntas_list, index=None)

        if pergunta_excluir and st.button("🗑️ Confirmar Exclusão", type="primary"):
            tema_excluir = pergunta_excluir.split(')')[0].replace('(', '').strip()
            pergunta_text = pergunta_excluir.split(')')[1].strip()
            
            caminho = f"questions/{tema_excluir.lower().replace(' ', '_')}.json"
            
            if os.path.exists(caminho):
                with open(caminho, "r", encoding="utf-8") as f:
                    questoes = json.load(f)
                    
                questoes = [q for q in questoes if q['pergunta'] != pergunta_text]
                
                with open(caminho, "w", encoding="utf-8") as f:
                    json.dump(questoes, f, indent=4, ensure_ascii=False)
                    
                st.success(f"Questão '{pergunta_text}' excluída.")
                st.rerun()
            else:
                st.error("Erro: Arquivo do tema não encontrado.")

def gestao_exame_de_faixa():
    st.markdown("<h1 style='color:#FFD700;'>🥋 Gestão de Exame de Faixa</h1>", unsafe_allow_html=True)

    os.makedirs("exames", exist_ok=True)
    faixas = ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
    faixa = st.selectbox("Selecione a faixa:", faixas)

    exame_path = f"exames/faixa_{faixa.lower()}.json"
    if os.path.exists(exame_path):
        try:
            with open(exame_path, "r", encoding="utf-8") as f:
                exame = json.load(f)
        except json.JSONDecodeError:
            st.error("Arquivo de exame corrompido. Criando um novo.")
            exame = {} 
    else:
        exame = {}

    if "questoes" not in exame:
        exame = {
            "faixa": faixa,
            "ultima_atualizacao": datetime.now().strftime("%Y-%m-%d"),
            "criado_por": st.session_state.usuario["nome"],
            "temas_incluidos": [],
            "questoes": []
        }

    todas_questoes = carregar_todas_questoes()
    if not todas_questoes:
        st.warning("Nenhuma questão cadastrada nos temas (pasta 'questions') até o momento.")
        return

    temas_disponiveis = sorted(list(set(q["tema"] for q in todas_questoes)))
    tema_filtro = st.selectbox("Filtrar questões por tema:", ["Todos"] + temas_disponiveis)

    if tema_filtro != "Todos":
        questoes_filtradas = [q for q in todas_questoes if q["tema"] == tema_filtro]
    else:
        questoes_filtradas = todas_questoes

    st.markdown("### ✅ Selecione as questões que farão parte do exame")
    selecao = []
    
    perguntas_no_exame = set(q["pergunta"] for q in exame["questoes"])
    questoes_para_selecao = [q for q in questoes_filtradas if q["pergunta"] not in perguntas_no_exame]

    if not questoes_para_selecao:
        st.info(f"Todas as questões {('do tema ' + tema_filtro) if tema_filtro != 'Todos' else ''} já foram adicionadas ou não há questões disponíveis.")

    for i, q in enumerate(questoes_para_selecao, 1):
        st.markdown(f"**{i}. ({q['tema']}) {q['pergunta']}**")
        if st.checkbox(f"Adicionar esta questão ({q['tema']})", key=f"{faixa}_{q['tema']}_{i}"):
            selecao.append(q)

    if selecao and st.button("➕ Inserir Questões Selecionadas"):
        exame["questoes"].extend(selecao)
        exame["temas_incluidos"] = sorted(list(set(q["tema"] for q in exame["questoes"])))
        exame["ultima_atualizacao"] = datetime.now().strftime("%Y-%m-%d")
        
        with open(exame_path, "w", encoding="utf-8") as f:
            json.dump(exame, f, indent=4, ensure_ascii=False)
        
        st.success(f"{len(selecao)} questão(ões) adicionada(s) ao exame da faixa {faixa}.")
        st.rerun()

    st.markdown("---")
    st.markdown("### 📋 Questões já incluídas no exame atual:")
    if not exame["questoes"]:
        st.info("Nenhuma questão adicionada ainda.")
    else:
        for i, q in enumerate(exame["questoes"], 1):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{i}. ({q['tema']}) {q['pergunta']}**")
                st.markdown(f"<small>Resposta correta: {q['resposta']}</small>", unsafe_allow_html=True)
            with col2:
                if st.button(f"Remover {i}", key=f"rem_{i}"):
                    exame["questoes"].pop(i - 1)
                    with open(exame_path, "w", encoding="utf-8") as f:
                        json.dump(exame, f, indent=4, ensure_ascii=False)
                    st.rerun()

    st.markdown("---")
    if st.button("🗑️ Excluir exame completo desta faixa", type="primary"):
        if os.path.exists(exame_path):
            os.remove(exame_path)
            st.warning(f"O exame da faixa {faixa} foi excluído.")
            st.rerun()
        else:
            st.error("O arquivo de exame não existe.")

def meus_certificados(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>📜 Meus Certificados</h1>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT faixa, pontuacao, data, codigo_verificacao, acertos, total_questoes
        FROM resultados
        WHERE usuario = ? AND modo = 'Exame de Faixa'
        ORDER BY data DESC
    """, (usuario_logado["nome"],))
    certificados = cursor.fetchall()
    conn.close()

    if not certificados:
        st.info("Você ainda não possui certificados emitidos. Complete um exame de faixa para conquistá-los! 🥋")
        return

    for i, (faixa, pontuacao, data, codigo, acertos, total) in enumerate(certificados, 1):
        st.markdown(f"### 🥋 {i}. Faixa {faixa}")
        st.markdown(f"- **Aproveitamento:** {pontuacao}%")
        st.markdown(f"- **Data:** {datetime.fromisoformat(data).strftime('%d/%m/%Y às %H:%M')}")
        st.markdown(f"- **Código de Verificação:** `{codigo}`")

        nome_arquivo = f"Certificado_{normalizar_nome(usuario_logado['nome'])}_{normalizar_nome(faixa)}.pdf"
        caminho_pdf_esperado = f"relatorios/{nome_arquivo}"

        if not os.path.exists(caminho_pdf_esperado):
            
            acertos_pdf = acertos if acertos is not None else int((pontuacao / 100) * 10) 
            total_pdf = total if total is not None else 10 

            caminho_pdf = gerar_pdf(
                usuario_logado["nome"],
                faixa,
                acertos_pdf,
                total_pdf,
                codigo
            )
        else:
            caminho_pdf = caminho_pdf_esperado
            
        try:
            with open(caminho_pdf, "rb") as f:
                st.download_button(
                    label=f"📥 Baixar Certificado - Faixa {faixa}",
                    data=f.read(),
                    file_name=os.path.basename(caminho_pdf),
                    mime="application/pdf",
                    key=f"baixar_{i}",
                    use_container_width=True
                )
        except FileNotFoundError:
            st.error(f"Erro ao tentar recarregar o certificado '{nome_arquivo}'. Tente novamente.")
            
        st.markdown("---")

# --- NOVO: TELA COMPLETAR CADASTRO (GOOGLE) ---
def tela_completar_cadastro(user_info):
    st.markdown("<h1 style='color:#FFD700;'>📝 Complete Seu Cadastro</h1>", unsafe_allow_html=True)
    st.warning(f"Bem-vindo, {user_info['nome']}! Seu primeiro login via Google requer que você complete algumas informações.")
    
    st.session_state.setdefault("endereco_cache", {}) 
    
    with st.form("form_completar_cadastro"):
        
        st.markdown("#### Informações Obrigatórias")
        cpf = st.text_input("CPF:", help="Apenas números. Necessário para identificação única.")
        
        tipo_usuario = st.selectbox("Tipo de Usuário:", ["Aluno", "Professor"])
        
        faixa = "Branca"
        equipe_sel = None
        
        if tipo_usuario == "Aluno":
            faixa = st.selectbox("Graduação (faixa):", [
                "Branca", "Cinza", "Amarela", "Laranja", "Verde",
                "Azul", "Roxa", "Marrom", "Preta"
            ])
            
        elif tipo_usuario == "Professor":
            st.info("O vínculo de professor requer aprovação do responsável pela equipe.")
            equipes_disponiveis = buscar_equipes()
            equipe_map = {nome: id for id, nome in equipes_disponiveis}
            lista_equipes = ["Nenhuma (Será vinculado pelo Admin)"] + list(equipe_map.keys())
            equipe_nome_sel = st.selectbox("Selecione a Equipe:", lista_equipes)
            if equipe_nome_sel != lista_equipes[0]:
                 equipe_sel = equipe_map[equipe_nome_sel]

        
        st.markdown("---")
        st.markdown("#### Endereço (Opcional)")
        
        def handle_cep_search_form():
            cep_digitado = st.session_state.perfil_cep_input
            if not cep_digitado:
                st.warning("Por favor, digite um CEP para buscar.")
                return
            
            endereco = buscar_endereco_por_cep(cep_digitado)
            if endereco:
                endereco["cep_original"] = cep_digitado
                st.session_state["endereco_cache"] = endereco
                st.success("Endereço encontrado e campos preenchidos.")
            else:
                st.error("CEP não encontrado ou inválido.")

        col_cep, col_btn_cep = st.columns([3, 1])
        cep_input = col_cep.text_input("CEP:", key="perfil_cep_input", value=st.session_state["endereco_cache"].get("cep_original", ""))
        
        col_btn_cep.form_submit_button(
            "🔍 Buscar", 
            key="buscar_cep_btn_2", 
            on_click=handle_cep_search_form
        )

        cache = st.session_state["endereco_cache"]
        
        logradouro = st.text_input("Logradouro (Rua/Av):", value=cache.get('logradouro', ""))
        col_num, col_comp = st.columns(2)
        numero = col_num.text_input("Número:") 
        col_comp.text_input("Complemento:") 

        bairro = st.text_input("Bairro:", value=cache.get('bairro', ""))
        col_cid, col_est = st.columns(2)
        cidade = col_cid.text_input("Cidade:", value=cache.get('localidade', ""))
        estado = col_est.text_input("Estado (UF):", value=cache.get('uf', ""))
        
        submitted = st.form_submit_button("Finalizar Cadastro", use_container_width=True, type="primary")

        if submitted:
            if not cpf:
                st.error("O campo CPF é obrigatório.")
                st.stop()
            elif not validar_cpf(cpf):
                st.error("CPF inválido. Por favor, verifique o número.")
                st.stop()
            
            conn = sqlite3.connect(DB_PATH) 
            cursor = conn.cursor()
            
            cursor.execute("SELECT id FROM usuarios WHERE cpf=? AND id!=?", (cpf, user_info['id']))
            if cursor.fetchone():
                st.error("CPF já cadastrado em outro usuário.")
                conn.close()
                st.stop()

            try:
                tipo_db = "aluno" if tipo_usuario == "Aluno" else "professor"
                
                cursor.execute(
                    """
                    UPDATE usuarios SET 
                        cpf=?, tipo_usuario=?, perfil_completo=1, 
                        cep=?, logradouro=?, numero=?, bairro=?, cidade=?, estado=?
                    WHERE id=?
                    """,
                    (cpf, tipo_db, cep_input, logradouro, numero, bairro, cidade, estado, user_info['id'])
                )
                
                if tipo_db == "aluno":
                    cursor.execute(
                        """
                        INSERT INTO alunos (usuario_id, faixa_atual, equipe_id, status_vinculo) 
                        VALUES (?, ?, ?, 'pendente')
                        """,
                        (user_info['id'], faixa, equipe_sel) 
                    )
                else: 
                    cursor.execute(
                        """
                        INSERT INTO professores (usuario_id, equipe_id, status_vinculo) 
                        VALUES (?, ?, ?)
                        """,
                        (user_info['id'], equipe_sel, 'pendente') 
                    )
                
                conn.commit()
                conn.close()
                st.success("Cadastro finalizado com sucesso! Você está logado.")
                
                st.session_state.usuario = {
                    "id": user_info['id'], 
                    "nome": user_info['nome'], 
                    "tipo": tipo_db
                }
                
                st.session_state.pop("registration_pending", None) 
                if "endereco_cache" in st.session_state: del st.session_state["endereco_cache"]
                st.rerun()
                
            except Exception as e:
                conn.rollback() 
                conn.close()
                st.error(f"Erro ao finalizar cadastro: {e}")

def tela_login():
    """Tela de login com autenticação local, Google e opção de cadastro."""
    st.session_state.setdefault("modo_login", "login")
    st.session_state.setdefault("cadastro_endereco_cache", {})

    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2: 
        if st.session_state["modo_login"] == "login":
            with st.container(border=True):
                st.markdown("<h3 style='color:white; text-align:center;'>Login</h3>", unsafe_allow_html=True)
                
                user_ou_cpf = st.text_input("Email ou CPF para Login:")
                pwd = st.text_input("Senha:", type="password")

                if st.button("Entrar", use_container_width=True, key="entrar_btn", type="primary"):
                    u = autenticar_local(user_ou_cpf.strip(), pwd.strip()) 
                    if u:
                        st.session_state.usuario = u
                        st.success(f"Login realizado com sucesso! Bem-vindo(a), {u['nome'].title()}.")
                        st.rerun()
                    else:
                        st.error("Email/CPF ou senha incorretos. Tente novamente.")

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
            
            equipes_disponiveis = buscar_equipes()
            equipe_map = {nome: id for id, nome in equipes_disponiveis}
            lista_equipes = ["Nenhuma (Professor será vinculado pelo Admin)"] + list(equipe_map.keys())
            
            with st.container(border=True):
                st.markdown("<h3 style='color:white; text-align:center;'>📋 Cadastro de Novo Usuário (Local)</h3>", unsafe_allow_html=True)
                
                with st.form(key="form_cadastro_local"):
                    
                    def handle_cadastro_cep_search_form():
                        cep_digitado = st.session_state.cadastro_cep_input
                        if not cep_digitado:
                            st.warning("Por favor, digite um CEP para buscar.")
                            return
                        
                        endereco = buscar_endereco_por_cep(cep_digitado)
                        if endereco:
                            endereco["cep_original"] = cep_digitado
                            st.session_state["cadastro_endereco_cache"] = endereco
                            st.success("Endereço encontrado e campos preenchidos. Complete o restante, se necessário.")
                        else:
                            st.error("CEP não encontrado ou inválido.")

                    st.markdown("#### Informações de Acesso")
                    nome = st.text_input("Nome Completo:") 
                    email = st.text_input("E-mail:")
                    cpf = st.text_input("CPF:", help="Apenas números. Será usado para login e identificação única.")
                    senha = st.text_input("Senha:", type="password")
                    confirmar = st.text_input("Confirmar senha:", type="password")
                    
                    st.markdown("---")
                    st.markdown("#### Classificação")
                    tipo_usuario = st.selectbox("Tipo de Usuário:", ["Aluno", "Professor"])
                    
                    equipe_sel = None
                    if tipo_usuario == "Aluno":
                        faixa = st.selectbox("Graduação (faixa):", [
                            "Branca", "Cinza", "Amarela", "Laranja", "Verde",
                            "Azul", "Roxa", "Marrom", "Preta"
                        ])
                    else:
                        faixa = "Preta" 
                        st.info("O vínculo de professor requer aprovação do responsável pela equipe.")
                        
                        equipe_nome_sel = st.selectbox("Selecione a Equipe:", lista_equipes)
                        if equipe_nome_sel != lista_equipes[0]:
                             equipe_sel = equipe_map[equipe_nome_sel]

                    
                    st.markdown("---")
                    st.markdown("#### Endereço (Opcional)")
                    
                    col_cep, col_btn_cep = st.columns([3, 1])
                    cep_input = col_cep.text_input("CEP:", key="cadastro_cep_input", value=st.session_state["cadastro_endereco_cache"].get("cep_original", ""))
                    
                    # BUGFIX: Corrigido o erro Missing Submit Button
                    if col_btn_cep.form_submit_button(
                        "🔍 Buscar", 
                        key="buscar_cep_btn", 
                        on_click=handle_cadastro_cep_search_form
                    ):
                        pass # Ação é executada na função de callback

                    cache = st.session_state["cadastro_endereco_cache"]
                    
                    logradouro = st.text_input("Logradouro (Rua/Av):", value=cache.get('logradouro', ""))
                    col_num, col_comp = st.columns(2)
                    numero = col_num.text_input("Número:", value="", help="O número do endereço.") 
                    col_comp.text_input("Complemento:", value="") 

                    bairro = st.text_input("Bairro:", value=cache.get('bairro', ""))
                    col_cid, col_est = st.columns(2)
                    cidade = col_cid.text_input("Cidade:", value=cache.get('cidade', ""))
                    estado = col_est.text_input("Estado (UF):", value=cache.get('estado', ""))
                    
                    submitted = st.form_submit_button("Cadastrar", use_container_width=True, type="primary")

                    if submitted:
                        if not (nome and email and senha and confirmar and cpf):
                            st.error("Preencha todos os campos obrigatórios: Nome Completo, Email, Senha e CPF.")
                            st.stop()
                        elif senha != confirmar:
                            st.error("As senhas não coincidem.")
                            st.stop()
                        elif not validar_cpf(cpf):
                            st.error("CPF inválido. Por favor, verifique o número.")
                            st.stop()
                        
                        conn = sqlite3.connect(DB_PATH) 
                        cursor = conn.cursor()
                        
                        cursor.execute("SELECT id FROM usuarios WHERE email=? OR cpf=?", (email, cpf))
                        if cursor.fetchone():
                            st.error("Email ou CPF já cadastrado. Use outro ou faça login.")
                            conn.close()
                            st.stop()
                        else:
                            try:
                                hashed = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
                                tipo_db = "aluno" if tipo_usuario == "Aluno" else "professor"
                                cep_final = cep_input 
                                
                                cursor.execute(
                                    """
                                    INSERT INTO usuarios (nome, email, cpf, tipo_usuario, senha, auth_provider, perfil_completo, cep, logradouro, numero, bairro, cidade, estado)
                                    VALUES (?, ?, ?, ?, ?, 'local', 1, ?, ?, ?, ?, ?, ?)
                                    """,
                                    (nome, email, cpf, tipo_db, hashed, cep_final, logradouro, numero, bairro, cidade, estado)
                                )
                                novo_id = cursor.lastrowid
                                
                                if tipo_db == "aluno":
                                    cursor.execute(
                                        """
                                        INSERT INTO alunos (usuario_id, faixa_atual, equipe_id, status_vinculo) 
                                        VALUES (?, ?, ?, 'pendente')
                                        """,
                                        (novo_id, faixa, equipe_sel) 
                                    )
                                else: 
                                    cursor.execute(
                                        """
                                        INSERT INTO professores (usuario_id, equipe_id, status_vinculo) 
                                        VALUES (?, ?, ?)
                                        """,
                                        (novo_id, equipe_sel, 'pendente') 
                                    )
                                
                                conn.commit()
                                conn.close()
                                st.success("Usuário cadastrado com sucesso! Faça login para continuar.")
                                
                                if tipo_db == "professor" and equipe_sel:
                                     st.info("Seu cadastro como professor está **pendente de aprovação** pelo responsável da equipe.")

                                st.session_state["modo_login"] = "login"
                                if "cadastro_endereco_cache" in st.session_state: del st.session_state["cadastro_endereco_cache"]
                                st.rerun()
                                
                            except Exception as e:
                                conn.rollback() 
                                conn.close()
                                st.error(f"Erro ao cadastrar: {e}")

            if st.button("⬅️ Voltar para Login", use_container_width=True):
                st.session_state["modo_login"] = "login"
                if "cadastro_endereco_cache" in st.session_state: del st.session_state["cadastro_endereco_cache"]
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

def app_principal():
    """Função 'main' refatorada - executa o app principal quando logado."""
    usuario_logado = st.session_state.usuario
    if not usuario_logado:
        st.error("Sessão expirada. Faça login novamente.")
        st.session_state.usuario = None
        st.rerun()

    tipo_usuario = usuario_logado["tipo"]

    def navigate_to_sidebar(page):
        st.session_state.menu_selection = page

    st.sidebar.image("assets/logo.png", use_container_width=True)
    st.sidebar.markdown(
        f"<h3 style='color:{COR_DESTAQUE};'>{usuario_logado['nome'].title()}</h3>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        f"<small style='color:#ccc;'>Perfil: {tipo_usuario.capitalize()}</small>",
        unsafe_allow_html=True,
    )
    
    st.sidebar.button(
        "👤 Meu Perfil", 
        on_click=navigate_to_sidebar, 
        args=("Meu Perfil",), 
        use_container_width=True
    )

    if tipo_usuario == "admin":
        st.sidebar.button(
            "🔑 Gestão de Usuários", 
            on_click=navigate_to_sidebar, 
            args=("Gestão de Usuários",), 
            use_container_width=True
        )

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sair", use_container_width=True):
        st.session_state.usuario = None
        st.session_state.pop("menu_selection", None)
        st.session_state.pop("token", None) 
        st.session_state.pop("registration_pending", None) 
        if "endereco_cache" in st.session_state: del st.session_state["endereco_cache"]
        st.rerun()

    
    if "menu_selection" not in st.session_state:
        st.session_state.menu_selection = "Início"

    pagina_selecionada = st.session_state.menu_selection

    if pagina_selecionada in ["Meu Perfil", "Gestão de Usuários"]:
        
        if pagina_selecionada == "Meu Perfil":
            tela_meu_perfil(usuario_logado)
        elif pagina_selecionada == "Gestão de Usuários":
            gestao_usuarios(usuario_logado) 
        
        if st.button("⬅️ Voltar ao Início", use_container_width=True):
            navigate_to_sidebar("Início")
            st.rerun()

    elif pagina_selecionada == "Início":
        # A tela de início não precisa de menu de navegação por si só,
        # mas os botões internos disparam a navegação.
        tela_inicio()

    else:
        if tipo_usuario in ["admin", "professor"]:
            opcoes = ["Modo Rola", "Exame de Faixa", "Ranking", "Painel do Professor", "Gestão de Questões", "Gestão de Equipes", "Gestão de Exame"]
            icons = ["people-fill", "journal-check", "trophy-fill", "easel-fill", "cpu-fill", "building-fill", "file-earmark-check-fill"]
        
        else: # aluno
            opcoes = ["Modo Rola", "Ranking", "Meus Certificados"]
            icons = ["people-fill", "trophy-fill", "patch-check-fill"]
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT exame_habilitado FROM alunos WHERE usuario_id=?", (usuario_logado["id"],))
            dado = cursor.fetchone()
            conn.close()
            if dado and dado[0] == 1:
                opcoes.insert(1, "Exame de Faixa") 
                icons.insert(1, "journal-check")
        
        opcoes.insert(0, "Início")
        icons.insert(0, "house-fill")

        menu = option_menu(
            menu_title=None,
            options=opcoes,
            icons=icons,
            key="menu_horizontal_selection", # Chave diferente para evitar conflito com a sidebar
            orientation="horizontal",
            default_index=opcoes.index(pagina_selecionada) if pagina_selecionada in opcoes else 0,
            on_change=lambda: st.session_state.update(menu_selection=st.session_state.menu_horizontal_selection),
            styles={
                "container": {"padding": "0!important", "background-color": COR_FUNDO, "border-radius": "10px", "margin-bottom": "20px"},
                "icon": {"color": COR_DESTAQUE, "font-size": "18px"},
                "nav-link": {"font-size": "14px", "text-align": "center", "--hover-color": "#1a4d40", "color": COR_TEXTO, "font-weight": "600"},
                "nav-link-selected": {"background-color": COR_BOTAO, "color": COR_DESTAQUE},
            }
        )
        
        # A navegação é feita pelo st.session_state.menu_selection (atualizado pelo on_change)
        # Se a seleção mudar, o rerun ocorrerá e o roteamento será feito abaixo.
        
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
