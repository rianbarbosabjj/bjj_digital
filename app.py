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

    CREATE TABLE IF NOT EXISTS rola_resultados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        faixa TEXT,
        tema TEXT,
        acertos INTEGER,
        total INTEGER,
        percentual REAL,
        data DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    conn.close()

criar_banco()

# =========================================
# AUTENTICAÇÃO
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
    usuarios = [("admin", "admin"), ("professor", "professor"), ("aluno", "aluno")]
    for nome, tipo in usuarios:
        cursor.execute("SELECT id FROM usuarios WHERE nome=?", (nome,))
        if cursor.fetchone() is None:
            senha_hash = bcrypt.hashpw(nome.encode(), bcrypt.gensalt()).decode()
            cursor.execute("INSERT INTO usuarios (nome, tipo_usuario, senha) VALUES (?, ?, ?)", (nome, tipo, senha_hash))
    conn.commit()
    conn.close()

criar_usuarios_teste()

# =========================================
# LOGIN
# =========================================
if "usuario" not in st.session_state:
    st.session_state.usuario = None

if st.session_state.usuario is None:
    st.markdown("""
        <div style='display:flex;justify-content:center;align-items:center;'>
            <img src='assets/logo.png' style='width:25%;max-width:180px;height:auto;'/>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center;color:#FFD700;'>Bem-vindo(a) ao BJJ Digital</h2>", unsafe_allow_html=True)
    user = st.text_input("Usuário:")
    pwd = st.text_input("Senha:", type="password")
    if st.button("Entrar"):
        u = autenticar(user.strip(), pwd.strip())
        if u:
            st.session_state.usuario = u
            st.success(f"Login realizado com sucesso! Bem-vindo(a), {u['nome'].title()}.")
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos. Tente novamente.")
    st.stop()

usuario_logado = st.session_state.get("usuario", None)
tipo_usuario = usuario_logado["tipo"] if usuario_logado else "aluno"

# =========================================
# FUNÇÕES AUXILIARES
# =========================================
def carregar_questoes(tema):
    path = f"questions/{tema}.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# =========================================
# 🤼 MODO ROLA
# =========================================
def modo_rola():
    st.markdown("<h1 style='color:#FFD700;'>🤼 Modo Rola - Treino Livre</h1>", unsafe_allow_html=True)
    temas = [f.replace(".json","") for f in os.listdir("questions") if f.endswith(".json")]
    temas.append("Todos os Temas")
    tema = st.selectbox("Selecione o tema:", temas)
    faixa = st.selectbox("Sua faixa:", ["Branca","Cinza","Amarela","Laranja","Verde","Azul","Roxa","Marrom","Preta"])

    if st.button("Iniciar Treino 🤼"):
        if tema == "Todos os Temas":
            questoes = []
            for arquivo in os.listdir("questions"):
                with open(f"questions/{arquivo}", "r", encoding="utf-8") as f:
                    questoes += json.load(f)
        else:
            questoes = carregar_questoes(tema)

        if not questoes:
            st.error("Nenhuma questão disponível.")
            return

        random.shuffle(questoes)
        acertos = 0
        total = len(questoes)

        for i, q in enumerate(questoes, 1):
            st.markdown(f"### {i}. {q['pergunta']}")
            if q.get("imagem"): st.image(q["imagem"], use_container_width=True)
            if q.get("video"): st.video(q["video"])
            resposta = st.radio("Escolha a alternativa:", q["opcoes"], key=f"rola_{i}")
            if st.button(f"Confirmar resposta {i}", key=f"confirma_{i}"):
                if resposta.startswith(q["resposta"]):
                    acertos += 1
                    st.success("✅ Correto!")
                else:
                    st.error(f"❌ Incorreto. Resposta correta: {q['resposta']}")

        percentual = int((acertos / total) * 100)
        st.markdown(f"## Resultado Final: {percentual}% de acertos ({acertos}/{total})")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO rola_resultados (usuario, faixa, tema, acertos, total, percentual)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (usuario_logado["nome"], faixa, tema, acertos, total, percentual))
        conn.commit()
        conn.close()
        st.success("Resultado salvo com sucesso! 🏆")

# =========================================
# 🏆 RANKING
# =========================================
def ranking():
    st.markdown("<h1 style='color:#FFD700;'>🏆 Ranking do Modo Rola</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM rola_resultados", conn)
    conn.close()

    if df.empty:
        st.info("Nenhum resultado disponível no ranking ainda.")
        return

    filtro_faixa = st.selectbox("Filtrar por faixa:", ["Todas"] + sorted(df["faixa"].unique().tolist()))
    if filtro_faixa != "Todas":
        df = df[df["faixa"] == filtro_faixa]

    ranking_df = df.groupby("usuario", as_index=False).agg(
        media_percentual=("percentual","mean"),
        total_treinos=("id","count")
    ).sort_values(by="media_percentual", ascending=False)

    ranking_df["Posição"] = range(1, len(ranking_df)+1)
    st.dataframe(ranking_df[["Posição","usuario","media_percentual","total_treinos"]], use_container_width=True)

    fig = px.bar(ranking_df.head(10), x="usuario", y="media_percentual",
                 text_auto=True, title="Top 10 - Modo Rola",
                 color="media_percentual", color_continuous_scale="YlOrBr")
    st.plotly_chart(fig, use_container_width=True)

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
            fig = px.line(df, x="data", y="pontuacao", color="faixa", title="Evolução das Notas")
            st.plotly_chart(fig, use_container_width=True)
    conn.close()

# =========================================
# MENU
# =========================================
def tela_inicio():
    st.image("assets/logo.png", use_container_width=True)
    st.markdown("<h2 style='text-align:center;color:#FFD700;'>Bem-vindo(a) ao Sistema BJJ Digital</h2>", unsafe_allow_html=True)
    st.write("Selecione uma das opções no menu lateral para começar.")

def main():
    st.sidebar.image("assets/logo.png", use_container_width=True)
    st.sidebar.markdown(f"<h3 style='color:{COR_DESTAQUE};'>Usuário: {usuario_logado['nome'].title()}</h3>", unsafe_allow_html=True)
    st.sidebar.markdown(f"<small style='color:#ccc;'>Perfil: {usuario_logado['tipo'].capitalize()}</small>", unsafe_allow_html=True)
    st.sidebar.markdown("---")

    if tipo_usuario == "admin":
        opcoes = ["🏠 Início", "🤼 Modo Rola", "🏆 Ranking", "👩‍🏫 Painel do Professor"]
    elif tipo_usuario == "professor":
        opcoes = ["🏠 Início", "🤼 Modo Rola", "🏆 Ranking", "👩‍🏫 Painel do Professor"]
    else:
        opcoes = ["🏠 Início", "🤼 Modo Rola", "🏆 Ranking"]

    menu = st.sidebar.radio("Navegar:", opcoes)

    if menu == "🏠 Início":
        tela_inicio()
    elif menu == "🤼 Modo Rola":
        modo_rola()
    elif menu == "🏆 Ranking":
        ranking()
    elif menu == "👩‍🏫 Painel do Professor":
        painel_professor()

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.usuario = None
        st.rerun()

if __name__ == "__main__":
    main()
