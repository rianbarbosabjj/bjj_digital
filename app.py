import streamlit as st
from fpdf import FPDF
from PIL import Image
import sqlite3
import json
import random
import os
import qrcode
import unicodedata
from datetime import datetime

# =========================================
# CONFIGURAÇÕES GERAIS
# =========================================
st.set_page_config(
    page_title="BJJ Digital",
    page_icon="🥋",
    layout="wide",
)

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
    conn.commit()
    conn.close()

def atualizar_banco():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(resultados)")
    colunas = [col[1] for col in cursor.fetchall()]
    if "codigo_verificacao" not in colunas:
        cursor.execute("ALTER TABLE resultados ADD COLUMN codigo_verificacao TEXT")
        conn.commit()
    conn.close()

criar_banco()
atualizar_banco()

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

def gerar_qrcode(codigo):
    os.makedirs("relatorios/qrcodes", exist_ok=True)
    caminho_qr = os.path.abspath(f"relatorios/qrcodes/{codigo}.png")
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=8,
        border=2,
    )
    qr.add_data(f"Código de verificação: {codigo}")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(caminho_qr)
    return caminho_qr

def normalizar_nome(nome):
    nfkd = unicodedata.normalize("NFKD", nome)
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower().replace(" ", "_")

def gerar_pdf(usuario, faixa, pontuacao, total, codigo, professor=None):
    pdf = FPDF()
    pdf.add_page()

    verde_escuro = (14, 45, 38)
    dourado = (255, 215, 0)
    branco = (255, 255, 255)

    pdf.set_fill_color(*verde_escuro)
    pdf.rect(0, 0, 210, 297, "F")

    pdf.set_text_color(*dourado)
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(0, 20, "Relatório de Exame de Faixa", ln=True, align="C")

    pdf.set_draw_color(*dourado)
    pdf.set_line_width(1)
    pdf.line(10, 30, 200, 30)

    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=85, y=35, w=40)

    pdf.ln(60)
    pdf.set_text_color(*branco)
    pdf.set_font("Helvetica", "", 14)
    pdf.cell(0, 10, f"Aluno: {usuario}", ln=True, align="C")
    pdf.cell(0, 10, f"Faixa Avaliada: {faixa}", ln=True, align="C")
    pdf.cell(0, 10, f"Pontuação: {pontuacao}/{total}", ln=True, align="C")
    pdf.cell(0, 10, f"Código: {codigo}", ln=True, align="C")
    pdf.cell(0, 10, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
    pdf.ln(15)

    pdf.set_font("Helvetica", "B", 16)
    resultado = "✅ APROVADO" if pontuacao >= (total * 0.6) else "❌ NÃO APROVADO"
    pdf.set_text_color(*dourado)
    pdf.cell(0, 15, resultado, ln=True, align="C")
    pdf.ln(20)

    # QR Code
    caminho_qr = gerar_qrcode(codigo)
    if os.path.exists(caminho_qr):
        try:
            pdf.image(caminho_qr, x=85, y=200, w=40)
        except Exception as e:
            print(f"⚠️ Erro ao inserir QR Code: {e}")

    pdf.ln(45)

    # Assinatura Digital
    pdf.set_text_color(*branco)
    pdf.set_font("Helvetica", "", 12)
    if professor:
        nome_normalizado = normalizar_nome(professor)
        assinatura_path = f"assets/assinaturas/{nome_normalizado}.png"
        if os.path.exists(assinatura_path):
            pdf.image(assinatura_path, x=75, y=pdf.get_y() - 5, w=60)
        else:
            pdf.cell(0, 10, "(Assinatura digital não encontrada)", ln=True, align="C")

    pdf.cell(0, 15, "Assinatura do Professor:", ln=True, align="C")
    pdf.line(70, pdf.get_y() + 5, 140, pdf.get_y() + 5)

    pdf.set_y(-30)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(*dourado)
    pdf.cell(0, 10, "Projeto Resgate GFTeam IAPC de Irajá - BJJ Digital", ln=True, align="C")

    os.makedirs("relatorios", exist_ok=True)
    caminho_pdf = os.path.abspath(f"relatorios/Relatorio_{usuario}_{faixa}.pdf")
    pdf.output(caminho_pdf)
    return caminho_pdf

def mostrar_cabecalho(titulo):
    st.markdown(f"<h1>{titulo}</h1>", unsafe_allow_html=True)
    topo_path = "assets/topo.webp"
    if os.path.exists(topo_path):
        topo_img = Image.open(topo_path)
        st.image(topo_img, use_container_width=True)

# =========================================
# MODO EXAME DE FAIXA
# =========================================
def modo_exame():
    mostrar_cabecalho("🏁 Exame de Faixa")

    faixas = ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
    faixa = st.selectbox("Selecione a faixa para o exame:", faixas)
    usuario = st.text_input("Nome do aluno:")
    professor = st.text_input("Nome do professor responsável:")
    tema = "regras"

    # Inicializa variáveis persistentes
    if "exame_iniciado" not in st.session_state:
        st.session_state.exame_iniciado = False
        st.session_state.questoes_exame = []
        st.session_state.respostas_exame = {}
        st.session_state.pontuacao_exame = 0

    # Inicia o exame
    if not st.session_state.exame_iniciado:
        if st.button("Iniciar Exame"):
            questoes = carregar_questoes(tema)
            random.shuffle(questoes)
            st.session_state.questoes_exame = questoes[:5]
            st.session_state.exame_iniciado = True
            st.session_state.respostas_exame = {}
            st.session_state.pontuacao_exame = 0
            st.experimental_rerun()

    # Mostra as questões (sem recarregar)
    if st.session_state.exame_iniciado:
        questoes = st.session_state.questoes_exame
        total = len(questoes)

        st.markdown("### Responda todas as questões abaixo:")

        for i, q in enumerate(questoes, 1):
            st.markdown(f"---")
            st.markdown(f"### {i}. {q['pergunta']}")
            if "video" in q and q["video"]:
                st.video(q["video"])
            if "imagem" in q and q["imagem"]:
                st.image(q["imagem"], use_container_width=True)

            key_resp = f"resposta_{i}"
            resposta = st.radio(
                "Escolha uma opção:",
                q["opcoes"],
                key=key_resp,
                index=None
            )

            if resposta:
                st.session_state.respostas_exame[key_resp] = resposta

        # Contabiliza pontuação
        pontuacao = 0
        for i, q in enumerate(questoes, 1):
            key_resp = f"resposta_{i}"
            if key_resp in st.session_state.respostas_exame:
                resposta = st.session_state.respostas_exame[key_resp]
                if resposta.startswith(q["resposta"]):
                    pontuacao += 1
        st.session_state.pontuacao_exame = pontuacao

        # Exibe botão de finalização apenas após todas as respostas
        if len(st.session_state.respostas_exame) == total:
            st.success("✅ Todas as questões foram respondidas.")
            if st.button("Finalizar Exame"):
                codigo = gerar_codigo_unico()
                salvar_resultado(usuario, "Exame", tema, faixa, pontuacao, "00:05:00", codigo)
                caminho_pdf = gerar_pdf(usuario, faixa, pontuacao, total, codigo, professor)

                with open(caminho_pdf, "rb") as file:
                    st.download_button(
                        label="📄 Baixar Relatório PDF",
                        data=file,
                        file_name=os.path.basename(caminho_pdf),
                        mime="application/pdf"
                    )

                st.success(f"✅ {usuario}, você fez {pontuacao}/{total} pontos.")
                st.info(f"Código de verificação: {codigo}")

                # Reset
                for key in ["exame_iniciado", "questoes_exame", "respostas_exame", "pontuacao_exame"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.experimental_rerun()

# =========================================
# MENU PRINCIPAL
# =========================================
def main():
    st.sidebar.image("assets/logo.png", use_container_width=True)
    st.sidebar.markdown("<h3 style='color:#FFD700;'>Plataforma BJJ Digital</h3>", unsafe_allow_html=True)
    menu = st.sidebar.radio("Navegar:", ["🏁 Exame de Faixa"])

    if menu == "🏁 Exame de Faixa":
        modo_exame()

if __name__ == "__main__":
    main()
