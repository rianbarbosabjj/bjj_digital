import streamlit as st
from PIL import Image
import sqlite3
import json
import random
import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import qrcode

# =========================================
# CONFIGURAÇÕES GERAIS
# =========================================
st.set_page_config(
    page_title="BJJ Digital",
    page_icon="🥋",
    layout="wide",
)

# Paleta de cores (baseada na GFTeam IAPC)
COR_FUNDO = "#0e2d26"        # verde escuro
COR_TEXTO = "#FFFFFF"
COR_DESTAQUE = "#FFD700"     # dourado
COR_BOTAO = "#078B6C"        # verde GFTeam
COR_HOVER = "#FFD700"

# CSS global
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
        pontuacao INTEGER,
        tempo TEXT,
        data DATETIME DEFAULT CURRENT_TIMESTAMP
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

def salvar_resultado(usuario, modo, tema, pontuacao, tempo):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO resultados (usuario, modo, tema, pontuacao, tempo) VALUES (?, ?, ?, ?, ?)",
                   (usuario, modo, tema, pontuacao, tempo))
    conn.commit()
    conn.close()

def mostrar_cabecalho(titulo):
    st.markdown(f"<h1>{titulo}</h1>", unsafe_allow_html=True)
    topo_path = "assets/topo.png"
    if os.path.exists(topo_path):
        st.image(topo_path, use_container_width=True)

# =========================================
# GERAÇÃO DE RELATÓRIO PDF
# =========================================
def gerar_relatorio_pdf(aluno, faixa, pontuacao, total, tempo, professor, aprovado):
    os.makedirs("output", exist_ok=True)
    codigo = f"RESGATE-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    qrcode_path = f"output/{codigo}_qrcode.png"
    pdf_path = f"output/{codigo}_relatorio.pdf"

    qr = qrcode.make(f"BJJ Digital - Código de verificação: {codigo}")
    qr.save(qrcode_path)

    faixas = ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
    try:
        proxima_faixa = faixas[faixas.index(faixa) + 1]
    except:
        proxima_faixa = faixa

    dados = {
        "aluno": aluno,
        "faixa": faixa,
        "pontuacao": pontuacao,
        "total": total,
        "tempo": tempo,
        "data": datetime.now().strftime("%d/%m/%Y"),
        "professor": professor,
        "qrcode_path": qrcode_path,
        "codigo": codigo,
        "aprovado": aprovado,
        "proxima_faixa": proxima_faixa
    }

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("relatorio.html")
    html_content = template.render(**dados)

    HTML(string=html_content, base_url=".").write_pdf(pdf_path)

    return pdf_path

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

        respostas = {}
        for i, q in enumerate(questoes[:5], 1):
            if "video" in q and q["video"]:
                st.video(q["video"])
            if "imagem" in q and q["imagem"]:
                st.image(q["imagem"], use_container_width=True)

            st.subheader(f"{i}. {q['pergunta']}")
            resposta = st.radio("Escolha uma opção:", q["opcoes"], key=f"q{i}", index=None)
            respostas[f"q{i}"] = resposta

        if st.button("Finalizar Exame"):
            for i, q in enumerate(questoes[:5], 1):
                resp = respostas.get(f"q{i}")
                if resp and resp.startswith(q["resposta"]):
                    pontuacao += 1

            aprovado = pontuacao >= 3
            salvar_resultado(usuario, "Exame", faixa, pontuacao, "00:05:00")

            if aprovado:
                st.success(f"✅ {usuario}, você foi aprovado para a faixa {faixa}!")
            else:
                st.error(f"❌ {usuario}, você não atingiu a pontuação mínima. Tente novamente em 3 dias.")

            professor = "Professor Responsável - GFTeam IAPC de Irajá"
            pdf_path = gerar_relatorio_pdf(usuario, faixa, pontuacao, total, "00:05:00", professor, aprovado)

            with open(pdf_path, "rb") as pdf_file:
                st.download_button(
                    label="📄 Baixar Relatório do Exame (PDF)",
                    data=pdf_file,
                    file_name=os.path.basename(pdf_path),
                    mime="application/pdf"
                )

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

        respostas = {}
        for i, q in enumerate(questoes[:5], 1):
            if "video" in q and q["video"]:
                st.video(q["video"])
            if "imagem" in q and q["imagem"]:
                st.image(q["imagem"], use_container_width=True)

            st.write(f"**{i}. {q['pergunta']}**")
            resposta = st.radio("", q["opcoes"], key=f"rola{i}", index=None)
            respostas[f"rola{i}"] = resposta

        if st.button("Finalizar Rola"):
            for i, q in enumerate(questoes[:5], 1):
                resp = respostas.get(f"rola{i}")
                if resp and resp.startswith(q["resposta"]):
                    pontos += 1

            salvar_resultado(usuario, "Rola", tema, pontos, "00:04:00")
            st.success(f"🎯 Resultado: {pontos}/{total} acertos")

# =========================================
# RANKING
# =========================================
def ranking():
    mostrar_cabecalho("🏆 Ranking Geral")

    conn = sqlite3.connect(DB_PATH)
    dados = conn.execute("SELECT usuario, modo, tema, pontuacao, data FROM resultados ORDER BY pontuacao DESC LIMIT 20").fetchall()
    conn.close()

    if dados:
        st.dataframe(dados, use_container_width=True)
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
