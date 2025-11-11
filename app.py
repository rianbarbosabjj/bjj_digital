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

# =========================================
# CONFIGURAÇÕES GERAIS
# =========================================
st.set_page_config(page_title="BJJ Digital", page_icon="assets/logo.png", layout="wide")

COR_FUNDO = "#0e2d26"
COR_TEXTO = "#FFFFFF"
COR_DESTAQUE = "#FFD700"
COR_BOTAO = "#078B6C"
COR_HOVER = "#FFD700"

st.markdown(f"""
<style>
body {{
    background-color: {COR_FUNDO};
    color: {COR_TEXTO};
    font-family: 'Poppins', sans-serif;
}}
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
}}
h1, h2, h3 {{
    color: {COR_DESTAQUE};
    text-align: center;
    font-weight: 700;
}}
</style>
""", unsafe_allow_html=True)

# =========================================
# BANCO DE DADOS E TABELAS RELACIONADAS
# =========================================
DB_PATH = os.path.join("database", "bjj_digital.db")

def criar_banco():
    os.makedirs("database", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        tipo_usuario TEXT,
        senha TEXT
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
        data_pedido DATETIME DEFAULT CURRENT_TIMESTAMP
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
        codigo_verificacao TEXT
    );
    """)
    conn.commit()
    conn.close()

criar_banco()

# =========================================
# AUTENTICAÇÃO SIMPLES LOCAL
# =========================================
def autenticar(usuario, senha):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, tipo_usuario, senha FROM usuarios WHERE nome=?", (usuario,))
    dados = cursor.fetchone()
    conn.close()
    if dados and bcrypt.checkpw(senha.encode(), dados[3].encode()):
        return {"id": dados[0], "nome": dados[1], "tipo": dados[2]}
    return None

def criar_usuarios_teste():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for nome, tipo in [("admin", "admin"), ("professor", "professor"), ("aluno", "aluno")]:
        senha_hash = bcrypt.hashpw(nome.encode(), bcrypt.gensalt()).decode()
        cursor.execute("INSERT OR IGNORE INTO usuarios (nome, tipo_usuario, senha) VALUES (?, ?, ?)", (nome, tipo, senha_hash))
    conn.commit()
    conn.close()
criar_usuarios_teste()

# =========================================
# LOGIN
# =========================================
if "usuario" not in st.session_state:
    st.session_state.usuario = None

if st.session_state.usuario is None:
    st.image("assets/logo.png", use_container_width=True)
    st.markdown("<h2 style='text-align:center;color:#FFD700;'>Bem-vindo(a) ao BJJ Digital</h2>", unsafe_allow_html=True)
    user = st.text_input("Usuário:")
    pwd = st.text_input("Senha:", type="password")
    if st.button("Entrar"):
        u = autenticar(user, pwd)
        if u:
            st.session_state.usuario = u
            st.success(f"Login realizado com sucesso! Bem-vindo(a), {u['nome'].title()}.")
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")
    st.stop()

usuario_logado = st.session_state.usuario
tipo_usuario = usuario_logado["tipo"]

# =========================================
# PAINEL DO PROFESSOR
# =========================================
def painel_professor():
    st.markdown("<h1 style='color:#FFD700;'>👩‍🏫 Painel do Professor</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    aba1, aba2, aba3, aba4 = st.tabs([
        "➕ Cadastrar Aluno", "📋 Pedidos Pendentes", "⚙️ Gestão da Equipe", "📊 Desempenho dos Alunos"
    ])

    # Aba 1 - Cadastrar aluno
    with aba1:
        with st.form("cadastro_aluno"):
            nome = st.text_input("Nome completo do aluno:")
            faixa = st.selectbox("Faixa atual:", ["Branca","Cinza","Amarela","Laranja","Verde","Azul","Roxa","Marrom","Preta"])
            turma = st.text_input("Turma:")
            equipe = st.text_input("Equipe:")
            enviar = st.form_submit_button("💾 Salvar Aluno")
            if enviar and nome.strip():
                cursor.execute("INSERT INTO alunos (usuario_id, faixa_atual, turma, status_vinculo) VALUES (NULL,?,?, 'pendente')",
                               (faixa, turma))
                conn.commit()
                st.success(f"Aluno(a) **{nome}** cadastrado(a) e aguardando aprovação!")

    # Aba 2 - Pedidos pendentes
    with aba2:
        st.markdown("### ⏳ Pedidos de vínculo pendentes")
        df = pd.read_sql_query("SELECT * FROM alunos WHERE status_vinculo='pendente'", conn)
        if df.empty:
            st.info("Nenhum pedido pendente.")
        else:
            st.dataframe(df)
            id_sel = st.number_input("ID do aluno:", min_value=1, step=1)
            if st.button("✅ Aprovar"):
                cursor.execute("UPDATE alunos SET status_vinculo='ativo' WHERE id=?", (id_sel,))
                conn.commit()
                st.success("Aluno aprovado!")
                st.rerun()
            if st.button("❌ Rejeitar"):
                cursor.execute("UPDATE alunos SET status_vinculo='rejeitado' WHERE id=?", (id_sel,))
                conn.commit()
                st.warning("Aluno rejeitado.")
                st.rerun()

    # Aba 3 - Gestão da equipe
    with aba3:
        st.markdown("### ⚙️ Professores da equipe")
        professores = pd.read_sql_query("""
            SELECT p.id, u.nome, p.pode_aprovar, p.status_vinculo
            FROM professores p JOIN usuarios u ON p.usuario_id=u.id
        """, conn)
        if professores.empty:
            st.info("Nenhum professor cadastrado.")
        else:
            for _, row in professores.iterrows():
                col1, col2 = st.columns([3,1])
                col1.write(f"👨‍🏫 {row['nome']} ({row['status_vinculo']})")
                pode = col2.checkbox("Pode Aprovar", value=bool(row["pode_aprovar"]), key=f"prof_{row['id']}")
                if pode != bool(row["pode_aprovar"]):
                    cursor.execute("UPDATE professores SET pode_aprovar=? WHERE id=?", (int(pode), row["id"]))
                    conn.commit()
                    st.success(f"Permissão atualizada para {row['nome']}.")

    # Aba 4 - Desempenho
    with aba4:
        st.markdown("### 📊 Desempenho dos Alunos")
        df = pd.read_sql_query("SELECT * FROM resultados", conn)
        if df.empty:
            st.info("Nenhum exame encontrado.")
        else:
            total = len(df)
            media = df["pontuacao"].mean()
            taxa = (df[df["pontuacao"] >= 3].shape[0] / total) * 100
            c1, c2, c3 = st.columns(3)
            c1.metric("Total de Exames", total)
            c2.metric("Média de Pontuação", f"{media:.2f}")
            c3.metric("Taxa de Aprovação", f"{taxa:.1f}%")

            st.markdown("#### Evolução temporal")
            fig = px.line(df, x="data", y="pontuacao", color="faixa", title="Evolução das Notas")
            st.plotly_chart(fig, use_container_width=True)
    conn.close()

# =========================================
# TELA INICIAL
# =========================================
def tela_inicio():
    st.image("assets/logo.png", use_container_width=True)
    st.markdown("<h2 style='text-align:center;color:#FFD700;'>Bem-vindo(a) ao Sistema BJJ Digital</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Selecione uma das opções no menu lateral para começar.</p>", unsafe_allow_html=True)

# =========================================
# MENU DINÂMICO POR PERFIL
# =========================================
def main():
    st.sidebar.image("assets/logo.png", use_container_width=True)
    st.sidebar.markdown(f"<h3 style='color:{COR_DESTAQUE};'>Usuário: {usuario_logado['nome'].title()}</h3>", unsafe_allow_html=True)
    st.sidebar.markdown(f"<small style='color:#ccc;'>Perfil: {usuario_logado['tipo'].capitalize()}</small>", unsafe_allow_html=True)
    st.sidebar.markdown("---")

    if tipo_usuario == "admin":
        opcoes = ["🏠 Início", "👩‍🏫 Painel do Professor"]
    elif tipo_usuario == "professor":
        opcoes = ["🏠 Início", "👩‍🏫 Painel do Professor"]
    else:  # aluno
        opcoes = ["🏠 Início"]

    menu = st.sidebar.radio("Navegar:", opcoes)

    if menu == "🏠 Início":
        tela_inicio()
    elif menu == "👩‍🏫 Painel do Professor":
        painel_professor()

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.usuario = None
        st.rerun()

if __name__ == "__main__":
    main()
