import streamlit as st
from PIL import Image
import sqlite3
import json
import random
import os

# ==========================================================
# CONFIGURAÇÕES GERAIS
# ==========================================================
st.set_page_config(
    page_title="BJJ Digital",
    page_icon="🥋",
    layout="wide",
)

# Paleta de cores (GFTeam IAPC)
COR_FUNDO = "#0E2D26"       # verde escuro
COR_TEXTO = "#FFFFFF"
COR_DESTAQUE = "#FFD700"    # dourado
COR_BOTAO = "#078B6C"       # verde GFTeam
COR_HOVER = "#FFD700"

# Estilo CSS
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
        padding: 0.7em 1.4em;
        border-radius: 10px;
        transition: 0.3s;
        font-size: 1em;
    }}
    .stButton>button:hover {{
        background: {COR_HOVER};
        color: {COR_FUNDO};
        transform: scale(1.05);
    }}
    h1, h2, h3 {{
        color: {COR_DESTAQUE};
        text-align: center;
        font-weight: 700;
    }}
    .question {{
        background-color: #143D33;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }}
    </style>
""", unsafe_allow_html=True)

# ==========================================================
# BANCO DE DADOS
# ==========================================================
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
    cursor.execute('''CREATE TABLE IF NOT EXISTS exames_disponiveis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        equipe TEXT,
        faixa TEXT,
        questoes TEXT,
        ativo INTEGER DEFAULT 0
    )''')
    conn.commit()
    conn.close()

criar_banco()

# ==========================================================
# FUNÇÕES AUXILIARES
# ==========================================================
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

# ==========================================================
# MODO EXAME DE FAIXA (atualizado)
# ==========================================================
def modo_exame():
    mostrar_cabecalho("🏁 Exame de Faixa")

    exame_ativo = True  # futuramente controlado pelo professor

    if not exame_ativo:
        st.warning("⛔ O exame de faixa ainda não foi liberado pelo seu professor.")
        return

    usuario = st.text_input("Nome do aluno:")
    faixa = st.selectbox("Faixa em exame:", 
                         ["Branca", "Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"])

    st.info("📘 As questões foram selecionadas pelo seu professor.")

    tema = "regras"
    questoes = carregar_questoes(tema)

    if st.button("Iniciar Exame"):
        if not questoes:
            st.warning("❌ Nenhuma questão encontrada para este exame.")
            return

        random.shuffle(questoes)
        pontuacao = 0
        total = len(questoes[:5])

        for i, q in enumerate(questoes[:5], 1):
            st.markdown(f"### {i}. {q['pergunta']}")
            if "imagem" in q and q["imagem"] and os.path.exists(q["imagem"]):
                st.image(q["imagem"], use_container_width=True)
            if "video" in q and q["video"]:
                st.video(q["video"])

            resposta = st.radio("Escolha uma opção:", q["opcoes"], key=f"exame_{i}", index=None)
            if resposta and resposta.startswith(q["resposta"]):
                pontuacao += 1

        if st.button("Finalizar Exame"):
            salvar_resultado(usuario, "Exame", faixa, pontuacao, "00:05:00")
            if pontuacao >= total * 0.7:
                st.success(f"✅ Parabéns {usuario}! Você foi aprovado(a) com {pontuacao}/{total} acertos.")
            else:
                st.error(f"❌ {usuario}, infelizmente você não atingiu a pontuação mínima. Refaça em 3 dias.")
            st.info(f"Resultado salvo para a faixa {faixa}.")

# ==========================================================
# MODO ESTUDO
# ==========================================================
def modo_estudo():
    mostrar_cabecalho("📘 Estudo Interativo")

    temas = ["regras", "graduacoes", "historia"]
    tema = st.selectbox("Escolha um tema:", temas)

    questoes = carregar_questoes(tema)
    if not questoes:
        st.warning("Nenhuma questão encontrada para este tema.")
        return

    q = random.choice(questoes)
    st.markdown("<div class='question'>", unsafe_allow_html=True)

    if "imagem" in q and q["imagem"] and os.path.exists(q["imagem"]):
        st.image(q["imagem"], use_container_width=True)

    st.subheader(q["pergunta"])

    resposta = st.radio("Escolha a alternativa:", q["opcoes"], key="estudo", index=None)
    if st.button("Verificar"):
        if resposta and resposta.startswith(q["resposta"]):
            st.success("✅ Correto!")
        else:
            st.error(f"❌ Errado! A resposta certa era: {q['resposta']}")

    if "video" in q and q["video"]:
        st.video(q["video"])

    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================================
# MODO TREINO (ROLA)
# ==========================================================
def modo_rola():
    mostrar_cabecalho("🤼‍♂️ Rola (Modo Treino)")

    usuario = st.text_input("Digite seu nome:")
    tema = st.selectbox("Selecione o tema:", ["regras", "graduacoes", "historia"])

    if st.button("Iniciar Rola"):
        questoes = carregar_questoes(tema)
        if not questoes:
            st.warning("❌ Nenhuma questão encontrada para este tema.")
            return

        random.shuffle(questoes)
        pontos = 0
        total = len(questoes[:5])

        for i, q in enumerate(questoes[:5], 1):
            st.markdown(f"### {i}. {q['pergunta']}")
            if "imagem" in q and q["imagem"] and os.path.exists(q["imagem"]):
                st.image(q["imagem"], use_container_width=True)
            resposta = st.radio("", q["opcoes"], key=f"rola_{i}", index=None)
            if resposta and resposta.startswith(q["resposta"]):
                pontos += 1
            if "video" in q and q["video"]:
                st.video(q["video"])

        if st.button("Finalizar Rola"):
            salvar_resultado(usuario, "Rola", tema, pontos, "00:04:00")
            st.success(f"🎯 Resultado: {pontos}/{total} acertos")

# ==========================================================
# RANKING
# ==========================================================
def ranking():
    mostrar_cabecalho("🏆 Ranking Geral")

    conn = sqlite3.connect(DB_PATH)
    dados = conn.execute("SELECT usuario, modo, tema, pontuacao, data FROM resultados ORDER BY pontuacao DESC, data DESC LIMIT 20").fetchall()
    conn.close()

    if dados:
        st.markdown(
            f"""
            <style>
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            th {{
                background-color: {COR_DESTAQUE};
                color: {COR_FUNDO};
                padding: 10px;
                text-align: center;
            }}
            td {{
                background-color: #12382F;
                color: {COR_TEXTO};
                text-align: center;
                padding: 8px;
            }}
            </style>
            """, unsafe_allow_html=True
        )
        st.table(dados)
    else:
        st.info("Nenhum resultado registrado ainda.")

# ==========================================================
# MENU PRINCIPAL
# ==========================================================
def main():
    st.sidebar.image("assets/logo.png", use_container_width=True)
    st.sidebar.markdown("<h3 style='color:#FFD700;'>Plataforma BJJ Digital</h3>", unsafe_allow_html=True)

    exame_disponivel = True  # futuramente controlado por professor

    opcoes_menu = ["📘 Estudo", "🤼‍♂️ Rola", "🏆 Ranking"]
    if exame_disponivel:
        opcoes_menu.insert(0, "🏁 Exame de Faixa")

    menu = st.sidebar.radio("Navegar:", opcoes_menu)

    if menu == "🏁 Exame de Faixa":
        modo_exame()
    elif menu == "📘 Estudo":
        modo_estudo()
    elif menu == "🤼‍♂️ Rola":
        modo_rola()
    elif menu == "🏆 Ranking":
        ranking()

if __name__ == "__main__":
    main()
