import streamlit as st
from fpdf import FPDF
from PIL import Image
import sqlite3
import json
import random
import os
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
        data DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def atualizar_banco():
    """Adiciona a coluna codigo_verificacao se ainda não existir."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Verifica se a coluna já existe
    cursor.execute("PRAGMA table_info(resultados)")
    colunas = [col[1] for col in cursor.fetchall()]

    if "codigo_verificacao" not in colunas:
        cursor.execute("ALTER TABLE resultados ADD COLUMN codigo_verificacao TEXT")
        conn.commit()
        print("✅ Coluna 'codigo_verificacao' adicionada com sucesso.")
    else:
        print("✅ Coluna 'codigo_verificacao' já existe.")

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

def salvar_resultado(usuario, modo, tema, faixa, pontuacao, tempo):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO resultados (usuario, modo, tema, faixa, pontuacao, tempo)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (usuario, modo, tema, faixa, pontuacao, tempo))
    conn.commit()
    conn.close()

def gerar_pdf(usuario, faixa, pontuacao, total):
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
    pdf.cell(0, 10, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
    pdf.ln(15)

    pdf.set_font("Helvetica", "B", 16)
    resultado = "✅ APROVADO" if pontuacao >= (total * 0.6) else "❌ NÃO APROVADO"
    pdf.set_text_color(*dourado)
    pdf.cell(0, 15, resultado, ln=True, align="C")

    pdf.ln(30)
    pdf.set_text_color(*branco)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, "Assinatura do Professor:", ln=True, align="C")
    pdf.line(70, pdf.get_y() + 5, 140, pdf.get_y() + 5)

    pdf.set_y(-30)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(*dourado)
    pdf.cell(0, 10, "Projeto Resgate GFTeam IAPC de Irajá - BJJ Digital", ln=True, align="C")

    os.makedirs("relatorios", exist_ok=True)
    caminho_pdf = f"relatorios/Relatorio_{usuario}_{faixa}.pdf"
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
    tema = "regras"

    if st.button("Iniciar Exame"):
        questoes = carregar_questoes(tema)
        random.shuffle(questoes)
        pontuacao = 0
        total = len(questoes[:5])

        for i, q in enumerate(questoes[:5], 1):
            if "video" in q and q["video"]:
                st.video(q["video"])
            if "imagem" in q and q["imagem"]:
                st.image(q["imagem"], use_container_width=True)
            st.subheader(f"{i}. {q['pergunta']}")
            resposta = st.radio("Escolha uma opção:", q["opcoes"], key=f"q{i}", index=None)
            if resposta and resposta.startswith(q["resposta"]):
                pontuacao += 1

        if st.button("Finalizar Exame"):
            salvar_resultado(usuario, "Exame", tema, faixa, pontuacao, "00:05:00")
            caminho_pdf = gerar_pdf(usuario, faixa, pontuacao, total)
            with open(caminho_pdf, "rb") as file:
                st.download_button(
                    label="📄 Baixar Relatório PDF",
                    data=file,
                    file_name=os.path.basename(caminho_pdf),
                    mime="application/pdf"
                )
            st.success(f"✅ {usuario}, você fez {pontuacao}/{total} pontos.")
            st.info(f"Resultado salvo para a faixa {faixa}.")

# =========================================
# MODO ESTUDO
# =========================================
def modo_estudo():
    mostrar_cabecalho("📘 Estudo Interativo")

    temas = ["regras", "graduacoes", "historia"]
    tema = st.selectbox("Escolha um tema:", temas)

    questoes = carregar_questoes(tema)
    if not questoes:
        st.warning("Nenhuma questão encontrada.")
        return

    q = random.choice(questoes)
    if "video" in q and q["video"]:
        st.video(q["video"])
    if "imagem" in q and q["imagem"]:
        st.image(q["imagem"], use_container_width=True)

    st.subheader(q["pergunta"])
    resposta = st.radio("Escolha a alternativa:", q["opcoes"], index=None)
    if st.button("Verificar"):
        if resposta and resposta.startswith(q["resposta"]):
            st.success("✅ Correto!")
        else:
            st.error(f"❌ Errado! A resposta certa era: {q['resposta']}")

# =========================================
# MODO TREINO (ROLA)
# =========================================
def modo_rola():
    mostrar_cabecalho("🤼‍♂️ Rola (Modo Treino)")

    usuario = st.text_input("Digite seu nome:")
    tema = st.selectbox("Selecione o tema:", ["regras", "graduacoes", "historia"])

    if st.button("Iniciar Rola"):
        questoes = carregar_questoes(tema)
        random.shuffle(questoes)
        pontos = 0
        total = len(questoes[:5])

        for i, q in enumerate(questoes[:5], 1):
            if "video" in q and q["video"]:
                st.video(q["video"])
            if "imagem" in q and q["imagem"]:
                st.image(q["imagem"], use_container_width=True)
            st.write(f"**{i}. {q['pergunta']}**")
            resposta = st.radio("", q["opcoes"], key=f"rola{i}", index=None)
            if resposta and resposta.startswith(q["resposta"]):
                pontos += 1

        if st.button("Finalizar Rola"):
            salvar_resultado(usuario, "Rola", tema, None, pontos, "00:04:00")
            st.success(f"🎯 Resultado: {pontos}/{total} acertos")

# =========================================
# RANKING
# =========================================
def ranking():
    mostrar_cabecalho("🏆 Ranking Geral")

    conn = sqlite3.connect(DB_PATH)
    dados = conn.execute("SELECT usuario, modo, tema, faixa, pontuacao, data FROM resultados ORDER BY pontuacao DESC LIMIT 20").fetchall()
    conn.close()

    if dados:
        st.dataframe(dados)
    else:
        st.info("Nenhum resultado registrado ainda.")

# =========================================
# MENU PRINCIPAL
# =========================================
def main():
    st.sidebar.image("assets/logo.png", use_container_width=True)
    st.sidebar.markdown("<h3 style='color:#FFD700;'>Plataforma BJJ Digital</h3>", unsafe_allow_html=True)
    menu = st.sidebar.radio("Navegar:", ["🏁 Exame de Faixa", "📘 Estudo", "🤼‍♂️ Rola (Modo Treino)", "🏆 Ranking"])

    if menu == "🏁 Exame de Faixa":
        modo_exame()
    elif menu == "📘 Estudo":
        modo_estudo()
    elif menu == "🤼‍♂️ Rola (Modo Treino)":
        modo_rola()
    elif menu == "🏆 Ranking":
        ranking()

if __name__ == "__main__":
    main()
