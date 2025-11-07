import streamlit as st
from PIL import Image
import sqlite3
import json
import random
import os
import time

# =========================================
# CONFIGURAÇÕES GERAIS
# =========================================
st.set_page_config(
    page_title="BJJ Digital",
    page_icon="🥋",
    layout="wide",
)

# =========================================
# ESTILO VISUAL RESPONSIVO
# =========================================
COR_FUNDO = "#0e2d26"
COR_TEXTO = "#FFFFFF"
COR_DESTAQUE = "#FFD700"
COR_BOTAO = "#078B6C"
COR_HOVER = "#FFD700"

st.markdown(f"""
    <style>
    html, body {{
        background-color: {COR_FUNDO};
        color: {COR_TEXTO};
        font-family: 'Poppins', sans-serif;
    }}
    [data-testid="stAppViewContainer"] {{
        background-color: {COR_FUNDO};
    }}
    h1, h2, h3, h4 {{
        color: {COR_DESTAQUE};
        text-align: center;
        font-weight: 700;
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
    .question-box {{
        background-color: rgba(255, 255, 255, 0.05);
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin-top: 20px;
    }}
    @media (max-width: 768px) {{
        .stButton>button {{
            width: 100%;
            font-size: 0.9em;
        }}
        h1 {{
            font-size: 1.8em;
        }}
        h2 {{
            font-size: 1.3em;
        }}
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
        topo_img = Image.open(topo_path)
        st.image(topo_img, use_container_width=True)

# =========================================
# MODO EXAME DE FAIXA (só exibe quando ativo)
# =========================================
def modo_exame():
    mostrar_cabecalho("🏁 Exame de Faixa")
    faixas = ["Branca", "Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
    faixa = st.selectbox("Selecione a faixa para o exame:", faixas)
    usuario = st.text_input("Nome do aluno:")
    tema = "regras"

    if st.button("Iniciar Exame"):
        questoes = carregar_questoes(tema)
        random.shuffle(questoes)
        total = len(questoes[:5])
        pontuacao = 0

        st.session_state["inicio_tempo"] = time.time()

        for i, q in enumerate(questoes[:5]):
            st.markdown(f"<div class='question-box'><h3>{i+1}. {q['pergunta']}</h3></div>", unsafe_allow_html=True)

            if q.get("imagem"):
                st.image(q["imagem"], use_container_width=True)
            if q.get("video"):
                st.video(q["video"])

            resposta = st.radio("Escolha a alternativa:", q["opcoes"], key=f"exam_q{i}", index=None)
            if resposta and resposta.startswith(q["resposta"]):
                pontuacao += 1

        if st.button("Finalizar Exame"):
            tempo_total = round(time.time() - st.session_state["inicio_tempo"])
            salvar_resultado(usuario, "Exame", faixa, pontuacao, f"{tempo_total}s")
            st.success(f"✅ {usuario}, você fez {pontuacao}/{total} pontos em {tempo_total} segundos.")

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

    if "indice_q" not in st.session_state:
        st.session_state["indice_q"] = 0
        st.session_state["acertos"] = 0

    q = questoes[st.session_state["indice_q"]]

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if q.get("imagem"):
            st.image(q["imagem"], use_container_width=True)
        if q.get("video"):
            st.video(q["video"])
        st.markdown(f"<div class='question-box'><h3>{q['pergunta']}</h3></div>", unsafe_allow_html=True)
        resposta = st.radio("Escolha a alternativa:", q["opcoes"], key=f"estudo_{st.session_state['indice_q']}", index=None)

        if st.button("Verificar resposta"):
            if resposta and resposta.startswith(q["resposta"]):
                st.success("✅ Correto!")
                st.session_state["acertos"] += 1
            else:
                st.error(f"❌ Errado! A resposta certa era: {q['resposta']}")
            if st.session_state["indice_q"] < len(questoes) - 1:
                st.session_state["indice_q"] += 1
                st.experimental_rerun()
            else:
                st.info(f"Fim do estudo! Você acertou {st.session_state['acertos']}/{len(questoes)} questões.")
                st.session_state.clear()

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
        total = len(questoes[:5])
        pontuacao = 0

        for i, q in enumerate(questoes[:5]):
            st.markdown(f"<div class='question-box'><h3>{i+1}. {q['pergunta']}</h3></div>", unsafe_allow_html=True)
            if q.get("imagem"):
                st.image(q["imagem"], use_container_width=True)
            if q.get("video"):
                st.video(q["video"])

            resposta = st.radio("Escolha a alternativa:", q["opcoes"], key=f"rola{i}", index=None)
            if resposta and resposta.startswith(q["resposta"]):
                pontuacao += 1

        if st.button("Finalizar Rola"):
            salvar_resultado(usuario, "Rola", tema, pontuacao, "00:04:00")
            st.success(f"🎯 Resultado: {pontuacao}/{total} acertos")

# =========================================
# RANKING
# =========================================
def ranking():
    mostrar_cabecalho("🏆 Ranking Geral")
    conn = sqlite3.connect(DB_PATH)
    dados = conn.execute("SELECT usuario, modo, tema, pontuacao, data FROM resultados ORDER BY pontuacao DESC LIMIT 20").fetchall()
    conn.close()

    if dados:
        st.markdown("### 🥇 Melhores Desempenhos")
        st.markdown(
            f"""
            <style>
            table {{
                width: 100%;
                text-align: center;
                border-collapse: collapse;
            }}
            th {{
                color: {COR_DESTAQUE};
                font-weight: bold;
                padding: 8px;
            }}
            td {{
                color: {COR_TEXTO};
                padding: 6px;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
        st.table(dados)
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
