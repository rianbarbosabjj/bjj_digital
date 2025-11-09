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

# =========================================
# GERAÇÃO DE PDF (NOME CENTRALIZADO E DOURADO)
# =========================================
def gerar_pdf(usuario, faixa, pontuacao, total, codigo, professor=None):
    pdf = FPDF("L", "mm", "A4")
    pdf.add_page()

    # Cores base
    verde_escuro = (14, 45, 38)
    dourado = (255, 215, 0)
    branco = (255, 255, 255)

    # Fundo
    pdf.set_fill_color(*verde_escuro)
    pdf.rect(0, 0, 297, 210, "F")

    # Título
    pdf.set_text_color(*dourado)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_xy(0, 10)
    pdf.cell(297, 12, "CERTIFICADO DE EXAME TEÓRICO DE FAIXA", align="C")
    pdf.set_draw_color(*dourado)
    pdf.set_line_width(0.8)
    pdf.line(30, 22, 267, 22)

    # Logo
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=130, y=25, w=35)

    # Corpo principal
    pdf.set_text_color(*branco)
    pdf.set_font("Helvetica", "", 14)
    percentual = int((pontuacao / total) * 100)
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")

    pdf.set_xy(10, 70)
    pdf.cell(277, 8, "Certificamos que o(a) aluno(a)", align="C")

    pdf.set_text_color(*dourado)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_xy(10, 80)
    pdf.cell(277, 10, usuario.upper(), align="C")

    pdf.set_text_color(*branco)
    pdf.set_font("Helvetica", "", 14)
    linha2 = f"concluiu o exame teórico para a faixa {faixa}, obtendo {percentual}% de aproveitamento, realizado em {data_hora}."
    pdf.set_xy(10, 95)
    pdf.multi_cell(277, 8, linha2, align="C")

    # Resultado
    resultado = "APROVADO" if pontuacao >= (total * 0.6) else "REPROVADO"
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*dourado)
    pdf.set_xy(0, 112)
    pdf.cell(297, 10, resultado, align="C")

    # Assinatura
    pdf.set_text_color(*branco)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_xy(0, 132)
    pdf.cell(297, 8, "Assinatura do Professor Responsável", align="C")
    pdf.line(108, 140, 189, 140)

    if professor:
        nome_normalizado = normalizar_nome(professor)
        assinatura_path = f"assets/assinaturas/{nome_normalizado}.png"
        if os.path.exists(assinatura_path):
            pdf.image(assinatura_path, x=118, y=124, w=60)

    # ==========================
    # QR Code centralizado
    # ==========================
    caminho_qr = gerar_qrcode(codigo)
    if os.path.exists(caminho_qr):
        qr_w = 26  # largura do QR Code
        page_width = pdf.w
        x_center = (page_width - qr_w) / 2
        y_qr = 145  # mesma altura base

        pdf.image(caminho_qr, x=x_center, y=y_qr, w=qr_w)

        # Código abaixo do QR Code
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*dourado)
        pdf.set_xy(0, y_qr + qr_w + 3)
        pdf.cell(page_width, 6, f"Código: {codigo}", align="C")

    # Rodapé
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*dourado)
    pdf.set_xy(0, 184)
    pdf.cell(297, 6, "Projeto Resgate GFTeam IAPC de Irajá - BJJ Digital", align="C")

    # Salvar PDF
    os.makedirs("relatorios", exist_ok=True)
    caminho_pdf = os.path.abspath(f"relatorios/Certificado_{usuario}_{faixa}.pdf")
    pdf.output(caminho_pdf)
    return caminho_pdf
# =========================================
# MODO EXAME DE FAIXA (MENSAGEM PERSONALIZADA)
# =========================================
def modo_exame():
    st.markdown("<h1 style='color:#FFD700;'>🏁 Exame de Faixa</h1>", unsafe_allow_html=True)
    faixas = ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
    faixa = st.selectbox("Selecione a faixa:", faixas)
    usuario = st.text_input("Nome do aluno:")
    professor = st.text_input("Nome do professor responsável:")
    tema = "regras"

    if "exame_iniciado" not in st.session_state:
        st.session_state.exame_iniciado = False
        st.session_state.respostas = {}

    if not st.session_state.exame_iniciado:
        if st.button("Iniciar Exame"):
            questoes = carregar_questoes(tema)
            random.shuffle(questoes)
            st.session_state.questoes = questoes[:5]
            st.session_state.exame_iniciado = True
            st.rerun()

    if st.session_state.exame_iniciado:
        questoes = st.session_state.questoes
        total = len(questoes)

        for i, q in enumerate(questoes, 1):
            st.markdown(f"### {i}. {q['pergunta']}")
            resp = st.radio("Escolha:", q["opcoes"], key=f"resp_{i}", index=None)
            st.session_state.respostas[f"resp_{i}"] = resp

        if st.button("Finalizar Exame"):
            pontuacao = sum(
                1 for i, q in enumerate(questoes, 1)
                if st.session_state.respostas[f"resp_{i}"].startswith(q["resposta"])
            )
            codigo = gerar_codigo_unico()
            salvar_resultado(usuario, "Exame", tema, faixa, pontuacao, "00:05:00", codigo)
            exportar_certificados_json()
            caminho_pdf = gerar_pdf(usuario, faixa, pontuacao, total, codigo, professor)

            percentual = int((pontuacao / total) * 100)
            if pontuacao >= (total * 0.6):
                st.success(f"🎉 Parabéns, {usuario}! Você foi **APROVADO**, acertando {pontuacao}/{total} questões e obtendo {percentual}% de aproveitamento!")
            else:
                st.error(f"{usuario}, você acertou {pontuacao}/{total} questões ({percentual}%). Continue se preparando para alcançar a próxima faixa!")

            with open(caminho_pdf, "rb") as f:
                st.download_button("📄 Baixar Certificado", f, file_name=os.path.basename(caminho_pdf))

# =========================================
# HISTÓRICO DE CERTIFICADOS
# =========================================
def painel_certificados():
    st.markdown("<h1 style='color:#FFD700;'>📜 Histórico de Certificados</h1>", unsafe_allow_html=True)
    nome = st.text_input("Digite seu nome completo:")
    if st.button("🔍 Buscar"):
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM resultados ORDER BY data DESC", conn)
        conn.close()
        df = df[df["usuario"].str.contains(nome, case=False, na=False)]
        if df.empty:
            st.info("Nenhum certificado encontrado.")
        else:
            st.success(f"Foram encontrados {len(df)} registro(s).")
            st.dataframe(df[["usuario","faixa","pontuacao","data","codigo_verificacao"]])

# =========================================
# DASHBOARD DO PROFESSOR
# =========================================
def dashboard_professor():
    st.markdown("<h1 style='color:#FFD700;'>📈 Dashboard do Professor</h1>", unsafe_allow_html=True)
    abas = st.tabs(["📊 Indicadores", "📋 Histórico"])

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

    with abas[1]:
        st.markdown("### 📋 Histórico de Exames")
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT usuario, faixa, pontuacao, data, codigo_verificacao FROM resultados", conn)
        conn.close()
        st.dataframe(df)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("📤 Exportar CSV", csv, "relatorio_exames.csv", "text/csv")

# =========================================
# MENU PRINCIPAL
# =========================================
def main():
    st.sidebar.image("assets/logo.png", use_container_width=True)
    st.sidebar.markdown("<h3 style='color:#FFD700;'>Plataforma BJJ Digital</h3>", unsafe_allow_html=True)
    menu = st.sidebar.radio("Navegar:", [
        "🏁 Exame de Faixa",
        "📜 Histórico de Certificados",
        "📈 Dashboard do Professor"
    ])
    if menu == "🏁 Exame de Faixa":
        modo_exame()
    elif menu == "📜 Histórico de Certificados":
        painel_certificados()
    elif menu == "📈 Dashboard do Professor":
        dashboard_professor()

if __name__ == "__main__":
    main()
