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

# =========================================
# CONFIGURAÇÕES GERAIS
# =========================================
st.set_page_config(page_title="BJJ Digital", page_icon="🥋", layout="wide")

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

def criar_banco():
    os.makedirs("database", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS resultados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        modo TEXT,
        tema TEXT,
        faixa TEXT,
        pontuacao INTEGER,
        tempo TEXT,
        data DATETIME DEFAULT CURRENT_TIMESTAMP,
        codigo_verificacao TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS config_exame (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        faixa TEXT,
        questoes_json TEXT,
        professor TEXT,
        data_config DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS alunos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        faixa_atual TEXT,
        turma TEXT,
        professor TEXT,
        observacoes TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS questoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        faixa TEXT,
        tema TEXT,
        pergunta TEXT,
        opcoes_json TEXT,
        resposta TEXT,
        autor TEXT,
        midia_tipo TEXT CHECK(midia_tipo IN ('imagem', 'video', 'nenhum')) DEFAULT 'nenhum',
        midia_caminho TEXT,
        status TEXT CHECK(status IN ('aprovada', 'pendente', 'rejeitada')) DEFAULT 'pendente',
        data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()
    conn.close()

try:
    criar_banco()
except Exception as e:
    st.error(f"Erro ao criar o banco de dados: {e}")

# =========================================
# FUNÇÕES AUXILIARES
# =========================================
def carregar_questoes(tema):
    path = f"questions/{tema}.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def gerar_codigo_unico():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM resultados")
    total = cursor.fetchone()[0] + 1
    conn.close()
    ano = datetime.now().year
    return f"BJJDIGITAL-{ano}-{total:05d}"

def salvar_resultado(usuario, modo, tema, faixa, pontuacao, tempo, codigo):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO resultados (usuario, modo, tema, faixa, pontuacao, tempo, codigo_verificacao)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (usuario, modo, tema, faixa, pontuacao, tempo, codigo))
    conn.commit()
    conn.close()

def exportar_certificados_json():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT usuario, faixa, pontuacao, modo, tema, data, codigo_verificacao
        FROM resultados
    """)
    registros = cursor.fetchall()
    conn.close()
    certificados = [
        {
            "codigo": codigo,
            "usuario": usuario,
            "faixa": faixa,
            "pontuacao": pontuacao,
            "modo": modo,
            "tema": tema,
            "data": data
        }
        for usuario, faixa, pontuacao, modo, tema, data, codigo in registros
    ]
    os.makedirs("certificados", exist_ok=True)
    with open("certificados/certificados.json", "w", encoding="utf-8") as f:
        json.dump(certificados, f, ensure_ascii=False, indent=2)

def gerar_qrcode(codigo):
    os.makedirs("certificados/qrcodes", exist_ok=True)
    caminho_qr = os.path.abspath(f"certificados/qrcodes/{codigo}.png")
    url_verificacao = f"https://bjjdigital.netlify.app/verificar?codigo={codigo}"
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=8, border=2)
    qr.add_data(url_verificacao)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img.save(caminho_qr)
    return caminho_qr

def normalizar_nome(nome):
    nfkd = unicodedata.normalize("NFKD", nome)
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower().replace(" ", "_")

# =========================================
# BANCO DE QUESTÕES MULTIMÍDIA (v1.6)
# =========================================
def banco_questoes_professor():
    st.markdown("<h1 style='color:#FFD700;'>🧩 Banco de Questões (Professor)</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    aba1, aba2 = st.tabs(["➕ Criar Nova Questão", "📚 Minhas Questões"])

    with aba1:
        with st.form("nova_questao"):
            faixa = st.selectbox("Selecione a faixa:", ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"])
            tema = st.text_input("Tema da questão:")
            pergunta = st.text_area("Digite o enunciado da questão:")
            autor = st.text_input("Nome do professor (autor):")

            midia_tipo = st.radio("Deseja adicionar mídia?", ["Nenhum", "Imagem", "Vídeo"])
            midia_caminho = None

            if midia_tipo == "Imagem":
                imagem = st.file_uploader("Envie uma imagem:", type=["jpg", "jpeg", "png"])
                if imagem:
                    os.makedirs("questions/assets", exist_ok=True)
                    nome_arquivo = f"q_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                    caminho_final = os.path.join("questions/assets", nome_arquivo)
                    with open(caminho_final, "wb") as f:
                        f.write(imagem.read())
                    midia_caminho = caminho_final
                    st.image(caminho_final, caption="Pré-visualização da imagem", use_container_width=True)
                    midia_tipo = "imagem"

            elif midia_tipo == "Vídeo":
                midia_caminho = st.text_input("Cole o link do vídeo (YouTube ou outro):")
                if midia_caminho:
                    st.video(midia_caminho)

            st.markdown("### Opções da Questão")
            opcoes = []
            for i in range(4):
                opcao = st.text_input(f"Opção {i+1}:")
                if opcao:
                    opcoes.append(opcao)
            resposta = st.selectbox("Selecione a resposta correta:", opcoes if opcoes else [""])
            enviar = st.form_submit_button("💾 Enviar para aprovação")

            if enviar:
                if not (pergunta and resposta and faixa and autor):
                    st.warning("Preencha todos os campos obrigatórios.")
                else:
                    cursor.execute("""
                        INSERT INTO questoes (faixa, tema, pergunta, opcoes_json, resposta, autor, midia_tipo, midia_caminho, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pendente')
                    """, (faixa, tema, pergunta, json.dumps(opcoes), resposta, autor, midia_tipo.lower(), midia_caminho))
                    conn.commit()
                    st.success("Questão enviada para aprovação do administrador!")

    with aba2:
        df = pd.read_sql_query("SELECT id, faixa, tema, pergunta, status FROM questoes ORDER BY data_criacao DESC", conn)
        if df.empty:
            st.info("Nenhuma questão cadastrada ainda.")
        else:
            st.dataframe(df)
    conn.close()

# =========================================
# PAINEL DO ADMINISTRADOR – APROVAÇÃO DE QUESTÕES
# =========================================
def painel_admin_questoes():
    st.markdown("<h1 style='color:#FFD700;'>🏛️ Aprovação de Questões (Administrador)</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    df = pd.read_sql_query("SELECT * FROM questoes WHERE status = 'pendente' ORDER BY data_criacao DESC", conn)

    if df.empty:
        st.info("Nenhuma questão pendente para aprovação.")
    else:
        for _, row in df.iterrows():
            st.markdown(f"### 🧠 Questão #{row['id']} – {row['faixa']} | Tema: {row['tema']}")
            st.write(row["pergunta"])
            opcoes = json.loads(row["opcoes_json"])
            for i, opcao in enumerate(opcoes):
                st.write(f"{chr(65+i)}) {opcao}")

            if row["midia_tipo"] == "imagem" and row["midia_caminho"]:
                st.image(row["midia_caminho"], use_container_width=True)
            elif row["midia_tipo"] == "video" and row["midia_caminho"]:
                st.video(row["midia_caminho"])

            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"✅ Aprovar #{row['id']}"):
                    cursor.execute("UPDATE questoes SET status='aprovada' WHERE id=?", (row["id"],))
                    conn.commit()
                    st.success(f"Questão {row['id']} aprovada!")
                    st.rerun()
            with col2:
                if st.button(f"❌ Rejeitar #{row['id']}"):
                    cursor.execute("UPDATE questoes SET status='rejeitada' WHERE id=?", (row["id"],))
                    conn.commit()
                    st.warning(f"Questão {row['id']} rejeitada.")
                    st.rerun()
    conn.close()

# =========================================
# MENU PRINCIPAL
# =========================================
def main():
    st.sidebar.image("assets/logo.png", use_container_width=True)
    st.sidebar.markdown("<h3 style='color:#FFD700;'>Plataforma BJJ Digital</h3>", unsafe_allow_html=True)

    menu = st.sidebar.radio("Navegar:", [
        "🏁 Exame de Faixa",
        "📜 Histórico de Certificados",
        "📈 Dashboard do Professor",
        "👩‍🏫 Painel do Professor",
        "🧩 Banco de Questões (Professor)",
        "🏛️ Aprovação de Questões (Admin)"
    ])

    if menu == "🧩 Banco de Questões (Professor)":
        banco_questoes_professor()
    elif menu == "🏛️ Aprovação de Questões (Admin)":
        painel_admin_questoes()
    elif menu == "🏁 Exame de Faixa":
        modo_exame()
    elif menu == "📜 Histórico de Certificados":
        painel_certificados()
    elif menu == "📈 Dashboard do Professor":
        dashboard_professor()
    elif menu == "👩‍🏫 Painel do Professor":
        painel_professor()

if __name__ == "__main__":
    main()
