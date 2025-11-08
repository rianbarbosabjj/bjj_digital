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
DB_PATH = "database/bjj_digital.db"

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
    conn.commit()
    conn.close()

criar_banco()

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
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=8,
        border=2,
    )
    qr.add_data(url_verificacao)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img.save(caminho_qr)
    return caminho_qr

def normalizar_nome(nome):
    nfkd = unicodedata.normalize("NFKD", nome)
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower().replace(" ", "_")

def obter_questoes_configuradas(faixa):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT questoes_json FROM config_exame
        WHERE faixa = ?
        ORDER BY data_config DESC LIMIT 1
    """, (faixa,))
    registro = cursor.fetchone()
    conn.close()
    if registro:
        return json.loads(registro[0])
    return None

# =========================================
# GERAÇÃO DE PDF
# =========================================
def gerar_pdf(usuario, faixa, pontuacao, total, codigo, professor=None):
    pdf = FPDF("L", "mm", "A4")
    pdf.add_page()
    verde_escuro = (14, 45, 38)
    dourado = (255, 215, 0)
    branco = (255, 255, 255)

    pdf.set_fill_color(*verde_escuro)
    pdf.rect(0, 0, 297, 210, "F")
    pdf.set_text_color(*dourado)
    pdf.set_font("Helvetica", "B", 26)
    pdf.cell(0, 10, "CERTIFICADO DE EXAME DE FAIXA", align="C", ln=True)
    pdf.set_draw_color(*dourado)
    pdf.line(40, 30, 257, 30)

    if os.path.exists("assets/logo.png"):
        pdf.image("assets/logo.png", x=130, y=40, w=35)

    percentual = int((pontuacao / total) * 100)
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")

    pdf.set_text_color(*branco)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_y(85)
    pdf.cell(0, 8, f"Certificamos que o(a) aluno(a)", align="C", ln=True)

    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*dourado)
    pdf.cell(0, 10, usuario.upper(), align="C", ln=True)

    pdf.set_text_color(*branco)
    pdf.set_font("Helvetica", "", 14)
    pdf.multi_cell(0, 8, f"concluiu o exame teórico para a faixa {faixa}, obtendo {percentual}% de aproveitamento, "
        f"realizado em {data_hora}.", align="C")

    resultado = "APROVADO" if pontuacao >= (total * 0.6) else "REPROVADO"
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*dourado)
    pdf.cell(0, 15, resultado, align="C", ln=True)

    if professor:
        assinatura = f"assets/assinaturas/{normalizar_nome(professor)}.png"
        if os.path.exists(assinatura):
            pdf.image(assinatura, x=120, y=135, w=60)

    caminho_qr = gerar_qrcode(codigo)
    pdf.image(caminho_qr, x=260, y=150, w=25)
    pdf.set_text_color(*dourado)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_xy(255, 175)
    pdf.cell(35, 5, f"Código: {codigo}", align="C")

    pdf.set_y(190)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 6, "Projeto Resgate GFTeam IAPC de Irajá - BJJ Digital", align="C")

    caminho_pdf = f"certificados/Certificado_{usuario}_{faixa}.pdf"
    pdf.output(caminho_pdf)
    return caminho_pdf

# =========================================
# DASHBOARD DO PROFESSOR (com Plotly)
# =========================================
def dashboard_professor():
    st.markdown("<h1 style='color:#FFD700;'>📈 Dashboard do Professor</h1>", unsafe_allow_html=True)
    abas = st.tabs(["📊 Indicadores", "📋 Histórico", "⚙️ Gerenciar Questões"])

    with abas[0]:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM resultados", conn)
        conn.close()

        if df.empty:
            st.info("Nenhum exame registrado ainda.")
            return

        total, media = len(df), df["pontuacao"].mean()
        taxa = (df[df["pontuacao"] >= 3].shape[0] / total) * 100
        aprovados = df[df["pontuacao"] >= 3].shape[0]
        reprovados = total - aprovados

        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Exames", total)
        col2.metric("Média de Pontuação", f"{media:.2f}")
        col3.metric("Taxa de Aprovação", f"{taxa:.1f}%")

        col1, col2 = st.columns(2)
        with col1:
            fig1 = px.bar(df, x="faixa", color="faixa",
                          title="Distribuição de Exames por Faixa",
                          color_discrete_sequence=px.colors.sequential.YlGn)
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            fig2 = px.pie(names=["Aprovados", "Reprovados"], values=[aprovados, reprovados],
                          title="Taxa de Aprovação", color_discrete_sequence=["#FFD700", "#0e2d26"])
            st.plotly_chart(fig2, use_container_width=True)

    # As demais abas (Histórico + Questões) permanecem iguais...
    # (mantendo filtros, exportação CSV e gerenciamento)
    # ... corte de código aqui para brevidade ...
