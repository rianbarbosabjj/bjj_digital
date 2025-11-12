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
from datetime import datetime
import bcrypt
import base64
from streamlit_option_menu import option_menu
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
import google.auth.transport.requests

# =========================================
# CONFIGURAÇÕES GERAIS
# =========================================
st.set_page_config(page_title="BJJ Digital", page_icon="assets/logo.png", layout="wide")

COR_FUNDO = "#0e2d26"
COR_TEXTO = "#FFFFFF"
COR_DESTAQUE = "#FFD770"
COR_BOTAO = "#078B6C"
COR_HOVER = "#FFD770"

# =========================================
# ESTILO
# =========================================
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;700&display=swap');
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
</style>
""", unsafe_allow_html=True)


# =========================================
# BANCO DE DADOS
# =========================================
DB_PATH = os.path.expanduser("~/bjj_digital.db")

# =========================================
# FUNÇÃO: LOGIN COM GOOGLE
# =========================================
def login_com_google():
    """Autenticação via Google OAuth 2.0"""
    CLIENT_SECRETS_FILE = "google_client_secret.json"  # Arquivo JSON baixado do Google Cloud

    if not os.path.exists(CLIENT_SECRETS_FILE):
        st.error("⚠️ O arquivo 'google_client_secret.json' não foi encontrado. Configure as credenciais OAuth.")
        return None

    redirect_uri = "http://localhost:8501" if st.secrets.get("env") == "dev" else "https://bjjdigital.netlify.app"
    )

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"],
        redirect_uri=redirect_uri,
    )

    # Constrói a URL de autorização
    auth_url, _ = flow.authorization_url(prompt="consent")

    st.markdown(f"""
        <div style='text-align:center;margin-top:20px;'>
            <a href="{auth_url}" target="_self">
                <button style="
                    background-color:{COR_BOTAO};
                    color:white;
                    font-size:1em;
                    border:none;
                    padding:10px 20px;
                    border-radius:8px;
                    cursor:pointer;
                    font-weight:bold;">
                    🔐 Entrar com Google
                </button>
            </a>
        </div>
    """, unsafe_allow_html=True)

    # Recupera o código de autorização da URL
    query_params = st.query_params
    if "code" in query_params:
        code = query_params["code"]

        try:
            flow.fetch_token(code=code)
            credentials = flow.credentials
            request_session = google.auth.transport.requests.Request()
            id_info = id_token.verify_oauth2_token(
                credentials.id_token, request_session, flow.client_config["client_id"]
            )

            email = id_info.get("email")
            nome = id_info.get("name")

            # 🔹 Verifica se o usuário já existe
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, nome, tipo_usuario, perfil_completo FROM usuarios WHERE email=?", (email,))
            dados = cursor.fetchone()

            if dados:
                usuario = {
                    "id": dados[0],
                    "nome": dados[1],
                    "email": email,
                    "tipo": dados[2],
                    "perfil_completo": dados[3],
                }
            else:
                cursor.execute(
                    "INSERT INTO usuarios (nome, email, tipo_usuario, perfil_completo) VALUES (?, ?, ?, 0)",
                    (nome, email, "aluno"),
                )
                conn.commit()
                usuario_id = cursor.lastrowid
                usuario = {
                    "id": usuario_id,
                    "nome": nome,
                    "email": email,
                    "tipo": "aluno",
                    "perfil_completo": 0,
                }

            conn.close()
            return usuario

        except Exception as e:
            st.error(f"Erro na autenticação Google: {e}")
            return None


# =========================================
# LOGIN TRADICIONAL E VIA GOOGLE
# =========================================
if "usuario" not in st.session_state:
    st.session_state.usuario = None

if st.session_state.usuario is None:
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode()
        logo_html = f"<img src='data:image/png;base64,{logo_base64}' style='width:180px;margin-bottom:10px;'/>"
    else:
        logo_html = "<p style='color:red;'>Logo não encontrada.</p>"

    st.markdown(f"""
        <div style='text-align:center;margin-top:30px;'>
            {logo_html}
            <h2 style='color:#FFD700;'>Bem-vindo(a) ao BJJ Digital</h2>
            <p style='color:#ccc;'>Faça login para continuar</p>
        </div>
    """, unsafe_allow_html=True)

    aba_login = st.tabs(["🔑 Login Tradicional", "🔐 Entrar com Google"])[0]

    with aba_login:
        user = st.text_input("Usuário:", key="login_user")
        pwd = st.text_input("Senha:", type="password", key="login_pwd")

        if st.button("Entrar", use_container_width=True):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, nome, tipo_usuario, senha, perfil_completo FROM usuarios WHERE nome=?", (user,))
            dados = cursor.fetchone()
            conn.close()
            if dados and bcrypt.checkpw(pwd.encode(), dados[3].encode()):
                st.session_state.usuario = {
                    "id": dados[0],
                    "nome": dados[1],
                    "tipo": dados[2],
                    "perfil_completo": dados[4],
                }
                st.success(f"Login realizado com sucesso! Bem-vindo(a), {dados[1].title()}.")
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

    # Aba de login com Google
    st.markdown("<br>", unsafe_allow_html=True)
    usuario_google = login_com_google()
    if usuario_google:
        st.session_state.usuario = usuario_google
        st.success(f"Login Google bem-sucedido! Bem-vindo(a), {usuario_google['nome']}.")
        st.rerun()

    st.stop()
# =========================================
# 🧾 TELA DE COMPLETAR CADASTRO
# =========================================
def tela_completar_cadastro(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>🧾 Complete seu Cadastro</h1>", unsafe_allow_html=True)
    st.info("Por favor, complete seus dados para continuar utilizando o sistema BJJ Digital.")

    # Campos complementares
    nome_completo = st.text_input("Nome completo:", value=usuario_logado.get("nome", ""))
    tipo_usuario = st.selectbox("Selecione seu perfil:", ["aluno", "professor"])
    faixa_atual = st.selectbox("Faixa atual:", ["Branca", "Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"])
    equipe = st.text_input("Equipe/Academia:")
    telefone = st.text_input("Telefone (opcional):")

    if st.button("Salvar Cadastro ✅", use_container_width=True):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Atualiza o perfil do usuário
        cursor.execute("""
            UPDATE usuarios 
            SET nome=?, tipo_usuario=?, perfil_completo=1
            WHERE id=?
        """, (nome_completo.strip(), tipo_usuario, usuario_logado["id"]))
        conn.commit()

        # Se for aluno, insere na tabela alunos (caso ainda não exista)
        if tipo_usuario == "aluno":
            cursor.execute("SELECT id FROM alunos WHERE usuario_id=?", (usuario_logado["id"],))
            if cursor.fetchone() is None:
                cursor.execute("""
                    INSERT INTO alunos (usuario_id, faixa_atual, turma, equipe_id, status_vinculo)
                    VALUES (?, ?, ?, NULL, 'pendente')
                """, (usuario_logado["id"], faixa_atual, equipe))
                conn.commit()

        # Se for professor, cria o vínculo na tabela professores
        elif tipo_usuario == "professor":
            cursor.execute("SELECT id FROM professores WHERE usuario_id=?", (usuario_logado["id"],))
            if cursor.fetchone() is None:
                cursor.execute("""
                    INSERT INTO professores (usuario_id, pode_aprovar, status_vinculo)
                    VALUES (?, 1, 'ativo')
                """, (usuario_logado["id"],))
                conn.commit()

        conn.close()

        # Atualiza sessão
        st.session_state.usuario["tipo"] = tipo_usuario
        st.session_state.usuario["perfil_completo"] = 1
        st.success("Cadastro completado com sucesso! 🎉")
        st.rerun()
# =========================================
# 🚀 MAIN (Atualizado com integração Google e perfil_completo)
# =========================================
def main():
    usuario_logado = st.session_state.usuario

    # Caso algo falhe no session (segurança extra)
    if not usuario_logado:
        st.error("Sessão expirada. Faça login novamente.")
        st.session_state.usuario = None
        st.rerun()

    # Se o cadastro ainda não foi completado
    if usuario_logado.get("perfil_completo", 1) == 0:
        tela_completar_cadastro(usuario_logado)
        st.stop()

    tipo_usuario = usuario_logado["tipo"]

    # --- MENU LATERAL ---
    st.sidebar.image("assets/logo.png", use_container_width=True)
    st.sidebar.markdown(
        f"<h3 style='color:{COR_DESTAQUE};'>👋 {usuario_logado['nome'].title()}</h3>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        f"<small style='color:#ccc;'>Perfil: {tipo_usuario.capitalize()}</small>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("---")

    # --- Opções do menu por tipo de usuário ---
    if tipo_usuario in ["admin", "professor"]:
        opcoes = [
            "🏠 Início",
            "🤼 Modo Rola",
            "🥋 Exame de Faixa",
            "🏆 Ranking",
            "👩‍🏫 Painel do Professor",
            "🧠 Gestão de Questões",
            "🥋 Gestão de Exame de Faixa"
        ]
    else:  # aluno
        opcoes = ["🏠 Início", "🤼 Modo Rola", "🏆 Ranking", "📜 Meus Certificados"]
        # Checa se exame está habilitado pelo professor
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT exame_habilitado FROM alunos WHERE usuario_id=?", (usuario_logado["id"],))
        dado = cursor.fetchone()
        conn.close()
        if dado and dado[0] == 1:
            opcoes.insert(2, "🥋 Exame de Faixa")

    # --- Navegação entre módulos ---
    menu = st.sidebar.radio("Navegar:", opcoes)

    if menu == "🏠 Início":
        tela_inicio()
    elif menu == "🤼 Modo Rola":
        modo_rola(usuario_logado)
    elif menu == "🥋 Exame de Faixa":
        exame_de_faixa(usuario_logado)
    elif menu == "🏆 Ranking":
        ranking()
    elif menu == "👩‍🏫 Painel do Professor":
        painel_professor()
    elif menu == "🧠 Gestão de Questões":
        gestao_questoes()
    elif menu == "🥋 Gestão de Exame de Faixa":
        gestao_exame_de_faixa()
    elif menu == "📜 Meus Certificados":
        meus_certificados(usuario_logado)

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.usuario = None
        st.rerun()
# =========================================
# 🧱 BANCO DE DADOS (versão final unificada)
# =========================================
DB_PATH = os.path.expanduser("~/bjj_digital.db")

def criar_banco():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executescript("""
    -----------------------------------------------------
    -- 👥 Usuários (suporte a login Google / iCloud)
    -----------------------------------------------------
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        email TEXT UNIQUE,
        tipo_usuario TEXT CHECK(tipo_usuario IN ('admin','professor','aluno')) DEFAULT 'aluno',
        senha TEXT,
        perfil_completo INTEGER DEFAULT 0,
        data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    -----------------------------------------------------
    -- 🏫 Equipes
    -----------------------------------------------------
    CREATE TABLE IF NOT EXISTS equipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        descricao TEXT,
        professor_responsavel_id INTEGER,
        ativo BOOLEAN DEFAULT 1,
        FOREIGN KEY(professor_responsavel_id) REFERENCES usuarios(id)
    );

    -----------------------------------------------------
    -- 👨‍🏫 Professores
    -----------------------------------------------------
    CREATE TABLE IF NOT EXISTS professores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        equipe_id INTEGER,
        pode_aprovar BOOLEAN DEFAULT 0,
        status_vinculo TEXT CHECK(status_vinculo IN ('pendente','ativo','rejeitado')) DEFAULT 'pendente',
        data_vinculo DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
        FOREIGN KEY(equipe_id) REFERENCES equipes(id)
    );

    -----------------------------------------------------
    -- 🧒 Alunos
    -----------------------------------------------------
    CREATE TABLE IF NOT EXISTS alunos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        faixa_atual TEXT,
        turma TEXT,
        professor_id INTEGER,
        equipe_id INTEGER,
        status_vinculo TEXT CHECK(status_vinculo IN ('pendente','ativo','rejeitado')) DEFAULT 'pendente',
        data_pedido DATETIME DEFAULT CURRENT_TIMESTAMP,
        exame_habilitado BOOLEAN DEFAULT 0,
        FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
        FOREIGN KEY(professor_id) REFERENCES professores(id),
        FOREIGN KEY(equipe_id) REFERENCES equipes(id)
    );

    -----------------------------------------------------
    -- 📊 Resultados de Exame
    -----------------------------------------------------
    CREATE TABLE IF NOT EXISTS resultados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        modo TEXT,
        tema TEXT,
        faixa TEXT,
        pontuacao INTEGER,
        tempo TEXT,
        data DATETIME DEFAULT CURRENT_TIMESTAMP,
        codigo_verificacao TEXT
    );

    -----------------------------------------------------
    -- 🤼 Resultados do Modo Rola
    -----------------------------------------------------
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

# Garante criação das tabelas
criar_banco()
