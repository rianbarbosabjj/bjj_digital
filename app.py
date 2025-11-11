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
# BANCO DE DADOS
# =========================================
DB_PATH = os.path.join("database", "bjj_digital.db")
os.makedirs("database", exist_ok=True)

def criar_banco():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            tipo_usuario TEXT CHECK(tipo_usuario IN ('admin','professor','aluno')),
            senha TEXT NOT NULL
        )
    """)

    def criar_usuario(nome, tipo, senha):
        cursor.execute("SELECT * FROM usuarios WHERE nome=?", (nome,))
        if not cursor.fetchone():
            hashed = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
            cursor.execute("INSERT INTO usuarios (nome, tipo_usuario, senha) VALUES (?, ?, ?)", (nome, tipo, hashed))

    criar_usuario("admin", "admin", "1234")
    criar_usuario("professor", "professor", "1234")
    criar_usuario("aluno", "aluno", "1234")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resultados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT,
            faixa TEXT,
            pontuacao INTEGER,
            data DATETIME DEFAULT CURRENT_TIMESTAMP,
            codigo TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alunos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            faixa_atual TEXT,
            turma TEXT,
            professor TEXT,
            observacoes TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faixa TEXT,
            tema TEXT,
            pergunta TEXT,
            opcoes_json TEXT,
            resposta TEXT,
            autor TEXT,
            midia_tipo TEXT CHECK(midia_tipo IN ('imagem','video','nenhum')) DEFAULT 'nenhum',
            midia_caminho TEXT,
            status TEXT CHECK(status IN ('pendente','aprovada','rejeitada')) DEFAULT 'pendente',
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

criar_banco()

# =========================================
# LOGIN / LOGOUT
# =========================================
def autenticar_usuario(nome, senha):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT senha, tipo_usuario FROM usuarios WHERE nome=?", (nome,))
    row = cursor.fetchone()
    conn.close()
    if row and bcrypt.checkpw(senha.encode(), row[0].encode()):
        return row[1]
    return None

def tela_login():
    st.markdown("<h1>🥋 Login – BJJ Digital</h1>", unsafe_allow_html=True)
    nome = st.text_input("Usuário:")
    senha = st.text_input("Senha:", type="password")
    if st.button("Entrar"):
        tipo = autenticar_usuario(nome, senha)
        if tipo:
            st.session_state["usuario"] = nome
            st.session_state["tipo_usuario"] = tipo
            st.success(f"Bem-vindo(a), {nome}! Perfil: {tipo.upper()}")
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")

# =========================================
# CERTIFICADO PDF
# =========================================
def gerar_qrcode(codigo):
    os.makedirs("certificados/qrcodes", exist_ok=True)
    caminho = f"certificados/qrcodes/{codigo}.png"
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(f"https://bjjdigital.netlify.app/verificar?codigo={codigo}")
    qr.make(fit=True)
    qr.make_image(fill_color="black", back_color="white").save(caminho)
    return caminho

def gerar_pdf(usuario, faixa, pontuacao):
    pdf = FPDF("L", "mm", "A4")
    pdf.add_page()
    dourado, preto, branco = (218,165,32), (40,40,40), (255,255,255)
    pdf.set_fill_color(*branco)
    pdf.rect(0,0,297,210,"F")
    pdf.set_draw_color(*dourado)
    pdf.set_line_width(2)
    pdf.rect(8,8,281,194)
    pdf.set_text_color(*dourado)
    pdf.set_font("Helvetica","B",26)
    pdf.cell(0,15,"CERTIFICADO DE EXAME TEÓRICO DE FAIXA",align="C",ln=1)
    pdf.set_text_color(*preto)
    pdf.set_font("Helvetica","",14)
    pdf.cell(0,10,f"Certificamos que {usuario} obteve {pontuacao}% de aproveitamento na faixa {faixa}.",align="C",ln=1)
    caminho_pdf = f"relatorios/Certificado_{usuario}_{faixa}.pdf"
    os.makedirs("relatorios",exist_ok=True)
    pdf.output(caminho_pdf)
    return caminho_pdf

# =========================================
# EXAME DE FAIXA
# =========================================
def exame_faixa():
    st.markdown("<h1>🏁 Exame de Faixa</h1>", unsafe_allow_html=True)
    faixas = ["Cinza","Amarela","Laranja","Verde","Azul","Roxa","Marrom","Preta"]
    faixa = st.selectbox("Selecione a faixa:", faixas)
    tema = "regras"
    usuario = st.session_state["usuario"]

    path = f"questions/{tema}.json"
    if not os.path.exists(path):
        st.error("Nenhum arquivo de questões encontrado.")
        return

    with open(path, "r", encoding="utf-8") as f:
        questoes = json.load(f)

    random.shuffle(questoes)
    questoes = questoes[:5]
    respostas = {}
    for i, q in enumerate(questoes, 1):
        st.markdown(f"### {i}. {q['pergunta']}")
        resposta = st.radio("Escolha:", q["opcoes"], key=f"resp_{i}")
        respostas[i] = resposta

    if st.button("Finalizar Exame"):
        corretas = sum(1 for i,q in enumerate(questoes,1) if respostas[i] == q["resposta"])
        pontuacao = int((corretas / len(questoes)) * 100)
        codigo = f"BJJD-{random.randint(10000,99999)}"

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO resultados (usuario, faixa, pontuacao, codigo) VALUES (?,?,?,?)",
                       (usuario, faixa, pontuacao, codigo))
        conn.commit()
        conn.close()

        st.success(f"🎉 {usuario}, você obteve {pontuacao}% de aproveitamento!")
        caminho_pdf = gerar_pdf(usuario, faixa, pontuacao)
        with open(caminho_pdf, "rb") as f:
            st.download_button("📄 Baixar Certificado", f, file_name=os.path.basename(caminho_pdf))

# =========================================
# PAINEL DO PROFESSOR
# =========================================
def painel_professor():
    st.markdown("<h1>👩‍🏫 Painel do Professor</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    aba1, aba2 = st.tabs(["➕ Cadastrar Aluno", "📋 Alunos Cadastrados"])

    with aba1:
        with st.form("cadastro_aluno"):
            nome = st.text_input("Nome completo do aluno:")
            faixa = st.selectbox("Faixa atual:", ["Branca","Cinza","Amarela","Laranja","Verde","Azul","Roxa","Marrom","Preta"])
            turma = st.text_input("Turma:")
            professor = st.session_state["usuario"]
            observacoes = st.text_area("Observações (opcional):")
            submitted = st.form_submit_button("💾 Salvar Aluno")
            if submitted and nome.strip():
                cursor.execute("""
                    INSERT INTO alunos (nome, faixa_atual, turma, professor, observacoes)
                    VALUES (?,?,?,?,?)
                """, (nome, faixa, turma, professor, observacoes))
                conn.commit()
                st.success(f"Aluno(a) **{nome}** cadastrado(a) com sucesso!")

    with aba2:
        df = pd.read_sql_query("SELECT * FROM alunos WHERE professor=? ORDER BY nome ASC", conn, params=(st.session_state["usuario"],))
        if df.empty:
            st.info("Nenhum aluno cadastrado ainda.")
        else:
            st.dataframe(df,use_container_width=True)
    conn.close()

# =========================================
# BANCO DE QUESTÕES (PROFESSOR)
# =========================================
def banco_questoes():
    st.markdown("<h1>🧩 Banco de Questões</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    aba1, aba2 = st.tabs(["➕ Criar Nova Questão", "📚 Minhas Questões"])

    with aba1:
        with st.form("nova_questao"):
            faixa = st.selectbox("Faixa:", ["Cinza","Amarela","Laranja","Verde","Azul","Roxa","Marrom","Preta"])
            tema = st.text_input("Tema:")
            pergunta = st.text_area("Pergunta:")
            opcoes = [st.text_input(f"Opção {i+1}:") for i in range(4)]
            resposta = st.selectbox("Resposta correta:", opcoes)
            midia_tipo = st.radio("Deseja adicionar mídia?", ["nenhum","imagem","video"])
            midia_caminho = None
            if midia_tipo == "imagem":
                imagem = st.file_uploader("Envie uma imagem:", type=["jpg","jpeg","png"])
                if imagem:
                    os.makedirs("questions/assets", exist_ok=True)
                    nome_arquivo = f"img_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                    caminho_final = os.path.join("questions/assets", nome_arquivo)
                    with open(caminho_final,"wb") as f: f.write(imagem.read())
                    st.image(caminho_final)
                    midia_caminho = caminho_final
            elif midia_tipo == "video":
                midia_caminho = st.text_input("Cole o link do vídeo:")
                if midia_caminho: st.video(midia_caminho)
            enviar = st.form_submit_button("💾 Enviar Questão")
            if enviar and pergunta.strip():
                cursor.execute("""INSERT INTO questoes
                    (faixa,tema,pergunta,opcoes_json,resposta,autor,midia_tipo,midia_caminho,status)
                    VALUES (?,?,?,?,?,?,?,?,'pendente')
                """,(faixa,tema,pergunta,json.dumps(opcoes),resposta,st.session_state["usuario"],midia_tipo,midia_caminho))
                conn.commit()
                st.success("Questão enviada para aprovação!")

    with aba2:
        df = pd.read_sql_query("SELECT id,faixa,tema,pergunta,status FROM questoes WHERE autor=? ORDER BY data_criacao DESC", conn, params=(st.session_state["usuario"],))
        if df.empty:
            st.info("Nenhuma questão criada ainda.")
        else:
            st.dataframe(df,use_container_width=True)
    conn.close()

# =========================================
# APROVAÇÃO DE QUESTÕES (ADMIN)
# =========================================
def aprovacao_admin():
    st.markdown("<h1>🏛️ Aprovação de Questões</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    df = pd.read_sql_query("SELECT * FROM questoes WHERE status='pendente' ORDER BY data_criacao DESC", conn)
    if df.empty:
        st.info("Nenhuma questão pendente.")
    else:
        for _,row in df.iterrows():
            st.markdown(f"### {row['id']} – {row['faixa']} | {row['tema']}")
            st.write(row["pergunta"])
            for i,opt in enumerate(json.loads(row["opcoes_json"])):
                st.write(f"{chr(65+i)}) {opt}")
            if row["midia_tipo"]=="imagem" and row["midia_caminho"]:
                st.image(row["midia_caminho"])
            elif row["midia_tipo"]=="video" and row["midia_caminho"]:
                st.video(row["midia_caminho"])
            c1,c2=st.columns(2)
            with c1:
                if st.button(f"✅ Aprovar {row['id']}"):
                    cursor.execute("UPDATE questoes SET status='aprovada' WHERE id=?", (row["id"],))
                    conn.commit()
                    st.success("Aprovada!"); st.rerun()
            with c2:
                if st.button(f"❌ Rejeitar {row['id']}"):
                    cursor.execute("UPDATE questoes SET status='rejeitada' WHERE id=?", (row["id"],))
                    conn.commit()
                    st.warning("Rejeitada."); st.rerun()
    conn.close()

# =========================================
# GERENCIAMENTO DE USUÁRIOS (ADMIN)
# =========================================
def gerenciamento_admin():
    st.markdown("<h1>👑 Gerenciamento de Usuários</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    df = pd.read_sql_query("SELECT id,nome,tipo_usuario FROM usuarios ORDER BY nome", conn)
    st.dataframe(df,use_container_width=True)
    with st.form("novo_usuario"):
        nome = st.text_input("Nome do novo usuário:")
        tipo = st.selectbox("Tipo de usuário:", ["admin","professor","aluno"])
        senha = st.text_input("Senha:", type="password")
        enviar = st.form_submit_button("💾 Criar Usuário")
        if enviar and nome.strip():
            hashed = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
            cursor.execute("INSERT INTO usuarios (nome,tipo_usuario,senha) VALUES (?,?,?)",(nome,tipo,hashed))
            conn.commit()
            st.success(f"Usuário {nome} criado com sucesso!")
            st.rerun()
    conn.close()

# =========================================
# MENU PRINCIPAL
# =========================================
def menu_principal():
    tipo = st.session_state["tipo_usuario"]
    st.sidebar.image("assets/logo.png", use_container_width=True)
    st.sidebar.markdown(f"<h3 style='color:#FFD700;'>Usuário: {st.session_state['usuario']} ({tipo})</h3>", unsafe_allow_html=True)

    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear(); st.rerun()

    if tipo == "admin":
        opcoes = ["🏁 Exame de Faixa","👩‍🏫 Painel do Professor","🧩 Banco de Questões","🏛️ Aprovação de Questões","👑 Gerenciar Usuários"]
    elif tipo == "professor":
        opcoes = ["🏁 Exame de Faixa","👩‍🏫 Painel do Professor","🧩 Banco de Questões"]
    else:
        opcoes = ["🏁 Exame de Faixa"]

    escolha = st.sidebar.radio("Navegar:", opcoes)

    if escolha == "🏁 Exame de Faixa": exame_faixa()
    elif escolha == "👩‍🏫 Painel do Professor": painel_professor()
    elif escolha == "🧩 Banco de Questões": banco_questoes()
    elif escolha == "🏛️ Aprovação de Questões": aprovacao_admin()
    elif escolha == "👑 Gerenciar Usuários": gerenciamento_admin()

# =========================================
# EXECUÇÃO
# =========================================
if "usuario" not in st.session_state:
    tela_login()
else:
    menu_principal()
