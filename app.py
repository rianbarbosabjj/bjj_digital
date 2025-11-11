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
import base64

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
DB_PATH = os.path.expanduser("~/bjj_digital.db")

def criar_banco():
    """Cria o banco de dados e suas tabelas, caso não existam."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
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
        eh_responsavel BOOLEAN DEFAULT 0,
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
        data_pedido DATETIME DEFAULT CURRENT_TIMESTAMP,
        exame_habilitado BOOLEAN DEFAULT 0
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

# 🔹 Cria o banco apenas se ainda não existir
if not os.path.exists(DB_PATH):
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
    """Cria usuários padrão: admin, professor e aluno."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    usuarios = [("admin", "admin"), ("professor", "professor"), ("aluno", "aluno")]
    for nome, tipo in usuarios:
        cursor.execute("SELECT id FROM usuarios WHERE nome=?", (nome,))
        if cursor.fetchone() is None:
            senha_hash = bcrypt.hashpw(nome.encode(), bcrypt.gensalt()).decode()
            cursor.execute(
                "INSERT INTO usuarios (nome, tipo_usuario, senha) VALUES (?, ?, ?)",
                (nome, tipo, senha_hash),
            )
    conn.commit()
    conn.close()

criar_usuarios_teste()

# =========================================
# LOGIN
# =========================================
if "usuario" not in st.session_state:
    st.session_state.usuario = None

if st.session_state.usuario is None:
    # Exibe logo centralizado (igual à tela inicial)
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode()
        logo_html = f"<img src='data:image/png;base64,{logo_base64}' style='width:180px;max-width:200px;height:auto;margin-bottom:10px;'/>"
    else:
        logo_html = "<p style='color:red;'>Logo não encontrada.</p>"

    st.markdown(f"""
        <div style='display:flex;flex-direction:column;align-items:center;justify-content:center;margin-top:40px;'>
            {logo_html}
            <h2 style='color:#FFD700;text-align:center;'>Bem-vindo(a) ao BJJ Digital</h2>
        </div>
    """, unsafe_allow_html=True)

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


# =========================================
# FUNÇÕES AUXILIARES
# =========================================
def carregar_questoes(tema):
    """Carrega as questões do arquivo JSON correspondente."""
    path = f"questions/{tema}.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def salvar_questoes(tema, questoes):
    """Salva lista de questões no arquivo JSON."""
    os.makedirs("questions", exist_ok=True)
    with open(f"questions/{tema}.json", "w", encoding="utf-8") as f:
        json.dump(questoes, f, indent=4, ensure_ascii=False)


def gerar_codigo_verificacao():
    """Gera código de verificação único no formato BJJDIGITAL-ANO-XXXX."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Conta quantos certificados já foram gerados
    cursor.execute("SELECT COUNT(*) FROM resultados")
    total = cursor.fetchone()[0] + 1
    conn.close()

    ano = datetime.now().year
    codigo = f"BJJDIGITAL-{ano}-{total:04d}"  # Exemplo: BJJDIGITAL-2025-0001
    return codigo
# =========================================
# 🤼 MODO ROLA (versão aprimorada – layout limpo)
# =========================================
def modo_rola(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>🤼 Modo Rola - Treino Livre</h1>", unsafe_allow_html=True)

    temas = [f.replace(".json", "") for f in os.listdir("questions") if f.endswith(".json")]
    temas.append("Todos os Temas")

    tema = st.selectbox("Selecione o tema:", temas)
    faixa = st.selectbox("Sua faixa:", ["Branca", "Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"])

    if st.button("Iniciar Treino 🤼"):
        # 🔹 Carrega questões conforme seleção
        if tema == "Todos os Temas":
            questoes = []
            for arquivo in os.listdir("questions"):
                if arquivo.endswith(".json"):
                    caminho = f"questions/{arquivo}"
                    try:
                        with open(caminho, "r", encoding="utf-8") as f:
                            questoes += json.load(f)
                    except json.JSONDecodeError:
                        st.warning(f"⚠️ Arquivo '{arquivo}' ignorado (erro de formatação).")
                        continue
        else:
            questoes = carregar_questoes(tema)

        if not questoes:
            st.error("Nenhuma questão disponível para este tema.")
            return

        random.shuffle(questoes)
        acertos = 0
        total = len(questoes)

        st.markdown(f"### 🧩 Total de questões: {total}")

        for i, q in enumerate(questoes, 1):
            st.markdown(f"### {i}. {q['pergunta']}")

            # 🔹 Exibe imagem (somente se existir e for válida)
            if q.get("imagem"):
                imagem_path = q["imagem"].strip()
                if imagem_path and os.path.exists(imagem_path):
                    st.image(imagem_path, use_container_width=True)
                elif imagem_path:
                    st.warning(f"⚠️ Imagem não encontrada: {imagem_path}")
            # (Sem else — espaço oculto se não houver imagem)

            # 🔹 Exibe vídeo (somente se existir)
            if q.get("video"):
                try:
                    st.video(q["video"])
                except Exception:
                    st.warning("⚠️ Não foi possível carregar o vídeo associado a esta questão.")
            # (Sem else — espaço oculto se não houver vídeo)

            resposta = st.radio("Escolha a alternativa:", q["opcoes"], key=f"rola_{i}")

            if st.button(f"Confirmar resposta {i}", key=f"confirma_{i}"):
                if resposta.startswith(q["resposta"]):
                    acertos += 1
                    st.success("✅ Correto!")
                else:
                    st.error(f"❌ Incorreto. Resposta correta: {q['resposta']}")
            
            st.markdown("---")  # separador visual entre as questões

        percentual = int((acertos / total) * 100)
        st.markdown(f"## Resultado Final: {percentual}% de acertos ({acertos}/{total})")

        # 🔹 Salva resultado no banco
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
# 🥋 EXAME DE FAIXA (versão integrada com certificado profissional)
# =========================================
def exame_de_faixa(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>🥋 Exame de Faixa</h1>", unsafe_allow_html=True)

    # Verifica se o aluno foi liberado para o exame
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT exame_habilitado FROM alunos WHERE usuario_id=?", (usuario_logado["id"],))
    dado = cursor.fetchone()
    conn.close()

    # 🔒 Apenas alunos precisam de liberação
    if usuario_logado["tipo"] not in ["admin", "professor"]:
        if not dado or dado[0] == 0:
            st.warning("🚫 Seu exame de faixa ainda não foi liberado. Aguarde a autorização do professor.")
            return

    faixa = st.selectbox(
        "Selecione sua faixa:",
        ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
    )

    exame_path = f"exames/faixa_{faixa.lower()}.json"
    if not os.path.exists(exame_path):
        st.error("Nenhum exame cadastrado para esta faixa ainda.")
        return

    # 🔍 Tenta carregar o exame
    try:
        with open(exame_path, "r", encoding="utf-8") as f:
            exame = json.load(f)
    except json.JSONDecodeError:
        st.error(f"⚠️ O arquivo '{exame_path}' está corrompido. Verifique o formato JSON.")
        return

    questoes = exame.get("questoes", [])
    if not questoes:
        st.info("Ainda não há questões cadastradas para esta faixa.")
        return

    st.markdown(f"### 🧩 Total de questões: {len(questoes)}")

    respostas = {}
    for i, q in enumerate(questoes, 1):
        st.markdown(f"### {i}. {q['pergunta']}")

        # 🔹 Exibe imagem somente se existir e for válida
        if q.get("imagem"):
            imagem_path = q["imagem"].strip()
            if imagem_path and os.path.exists(imagem_path):
                st.image(imagem_path, use_container_width=True)
            elif imagem_path:
                st.warning(f"⚠️ Imagem não encontrada: {imagem_path}")

        # 🔹 Exibe vídeo somente se existir
        if q.get("video"):
            try:
                st.video(q["video"])
            except Exception:
                st.warning("⚠️ Não foi possível carregar o vídeo associado a esta questão.")

        # 🔹 Corrigido: nenhuma alternativa vem pré-selecionada
        respostas[i] = st.radio(
            "Escolha a alternativa:",
            q["opcoes"],
            key=f"exame_{i}",
            index=None
        )

        st.markdown("---")

    # 🔘 Botão para finalizar o exame
    finalizar = st.button("Finalizar Exame 🏁")

    if finalizar:
        acertos = sum(
            1 for i, q in enumerate(questoes, 1)
            if respostas.get(i, "") and respostas[i].startswith(q["resposta"])
        )

        total = len(questoes)
        percentual = int((acertos / total) * 100)
        st.markdown(f"## Resultado Final: {percentual}% de acertos ({acertos}/{total})")

        # 🔹 Reseta variáveis antes de definir novo estado
        st.session_state["certificado_pronto"] = False

        if percentual >= 70:
            st.success("🎉 Parabéns! Você foi aprovado(a) no Exame de Faixa! 👏")

            codigo = gerar_codigo_verificacao()
            st.session_state["certificado_pronto"] = True
            st.session_state["dados_certificado"] = {
                "usuario": usuario_logado["nome"],
                "faixa": faixa,
                "acertos": acertos,
                "total": total,
                "codigo": codigo
            }

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO resultados (usuario, modo, faixa, pontuacao, data, codigo_verificacao)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (usuario_logado["nome"], "Exame de Faixa", faixa, percentual, datetime.now(), codigo))
            conn.commit()
            conn.close()

        else:
            st.error("😞 Você não atingiu a pontuação mínima (70%). Continue treinando e tente novamente! 💪")

    # 🔘 Exibição do botão de download — somente após clique e aprovação
    if st.session_state.get("certificado_pronto") and finalizar:
        dados = st.session_state["dados_certificado"]
        caminho_pdf = gerar_pdf(
            dados["usuario"],
            dados["faixa"],
            dados["acertos"],
            dados["total"],
            dados["codigo"]
        )

        st.info("Clique abaixo para gerar e baixar seu certificado.")
        with open(caminho_pdf, "rb") as f:
            st.download_button(
                label="📥 Baixar Certificado de Exame",
                data=f.read(),
                file_name=os.path.basename(caminho_pdf),
                mime="application/pdf"
            )

        st.success("Certificado gerado com sucesso! 🥋")

# =========================================
# GERAÇÃO DE CERTIFICADO
# =========================================
def normalizar_nome(nome):
    """Remove acentos e formata o nome para uso em arquivos."""
    return "_".join(
        unicodedata.normalize("NFKD", nome)
        .encode("ASCII", "ignore")
        .decode()
        .split()
    ).lower()


def gerar_qrcode(codigo):
    """Gera QR Code com link de verificação oficial do BJJ Digital."""
    os.makedirs("temp_qr", exist_ok=True)
    caminho_qr = f"temp_qr/{codigo}.png"

    # URL de verificação oficial
    base_url = "https://bjjdigital.netlify.app/verificar"
    link_verificacao = f"{base_url}?codigo={codigo}"

    # Criação do QR
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4,
        error_correction=qrcode.constants.ERROR_CORRECT_H
    )
    qr.add_data(link_verificacao)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(caminho_qr)

    return caminho_qr


def gerar_pdf(usuario, faixa, pontuacao, total, codigo, professor=None):
    """Gera certificado oficial do exame de faixa."""
    pdf = FPDF("L", "mm", "A4")  # Layout Paisagem (297x210)
    pdf.set_auto_page_break(False)
    pdf.add_page()

    # Cores principais
    dourado, preto, branco = (218, 165, 32), (40, 40, 40), (255, 255, 255)
    percentual = int((pontuacao / total) * 100)
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Fundo branco e moldura dourada dupla
    pdf.set_fill_color(*branco)
    pdf.rect(0, 0, 297, 210, "F")
    pdf.set_draw_color(*dourado)
    pdf.set_line_width(2)
    pdf.rect(8, 8, 281, 194)
    pdf.set_line_width(0.8)
    pdf.rect(11, 11, 275, 188)

    # Cabeçalho
    pdf.set_text_color(*dourado)
    pdf.set_font("Helvetica", "BI", 30)
    pdf.set_y(25)
    pdf.cell(0, 10, "CERTIFICADO DE EXAME TEÓRICO DE FAIXA", align="C")
    pdf.set_draw_color(*dourado)
    pdf.line(30, 35, 268, 35)

    # Logo
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=133, y=40, w=32)

    # ---------------------------------------------------
    # BLOCO CENTRAL (Texto Hierarquizado e Equilibrado)
    # ---------------------------------------------------
    pdf.set_text_color(*preto)
    pdf.set_font("Helvetica", "", 16)
    pdf.set_y(80)
    pdf.cell(0, 10, "Certificamos que o(a) aluno(a)", align="C")

    pdf.set_text_color(*dourado)
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_y(92)
    pdf.cell(0, 10, usuario.upper(), align="C")

    cores_faixa = {
        "Cinza": (169, 169, 169),
        "Amarela": (255, 215, 0),
        "Laranja": (255, 140, 0),
        "Verde": (0, 128, 0),
        "Azul": (30, 144, 255),
        "Roxa": (128, 0, 128),
        "Marrom": (139, 69, 19),
        "Preta": (0, 0, 0),
    }
    cor_faixa = cores_faixa.get(faixa, preto)

    pdf.set_text_color(*preto)
    pdf.set_font("Helvetica", "", 16)
    pdf.set_y(108)
    pdf.cell(0, 8, "concluiu o exame teórico para a faixa", align="C")

    pdf.set_text_color(*cor_faixa)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_y(118)
    pdf.cell(0, 8, faixa.upper(), align="C")

    pdf.set_text_color(*dourado)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_y(132)
    pdf.cell(0, 8, "APROVADO", align="C")

    pdf.set_text_color(*preto)
    pdf.set_font("Helvetica", "", 14)
    texto_final = f"obtendo {percentual}% de aproveitamento, realizado em {data_hora}."
    pdf.set_y(142)
    pdf.cell(0, 6, texto_final, align="C")

    # ---------------------------------------------------
    # SEL0, QR CODE E ASSINATURA
    # ---------------------------------------------------
    selo_path = "assets/selo_dourado.png"
    if os.path.exists(selo_path):
        pdf.image(selo_path, x=23, y=155, w=30)

    caminho_qr = gerar_qrcode(codigo)
    pdf.image(caminho_qr, x=245, y=155, w=25)

    pdf.set_text_color(*preto)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_xy(220, 180)
    pdf.cell(60, 6, f"Código: {codigo}", align="R")

    if professor:
        assinatura_path = f"assets/assinaturas/{normalizar_nome(professor)}.png"
        if os.path.exists(assinatura_path):
            pdf.image(assinatura_path, x=118, y=160, w=60)
        pdf.set_text_color(*preto)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_y(175)
        pdf.cell(0, 6, "Assinatura do Professor Responsável", align="C")
        pdf.set_draw_color(*dourado)
        pdf.line(100, 173, 197, 173)

    # Rodapé
    pdf.set_draw_color(*dourado)
    pdf.line(30, 190, 268, 190)
    pdf.set_text_color(*dourado)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_y(190)
    pdf.cell(0, 6, "Plataforma BJJ Digital", align="C")

    # ---------------------------------------------------
    # EXPORTAÇÃO
    # ---------------------------------------------------
    os.makedirs("relatorios", exist_ok=True)
    caminho_pdf = os.path.abspath(f"relatorios/Certificado_{usuario}_{faixa}.pdf")
    pdf.output(caminho_pdf)
    return caminho_pdf
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
        media_percentual=("percentual", "mean"),
        total_treinos=("id", "count")
    ).sort_values(by="media_percentual", ascending=False)

    ranking_df["Posição"] = range(1, len(ranking_df) + 1)
    st.dataframe(ranking_df[["Posição", "usuario", "media_percentual", "total_treinos"]], use_container_width=True)

    fig = px.bar(
        ranking_df.head(10),
        x="usuario",
        y="media_percentual",
        text_auto=True,
        title="Top 10 - Modo Rola",
        color="media_percentual",
        color_continuous_scale="YlOrBr",
    )
    st.plotly_chart(fig, use_container_width=True)
# =========================================
# 👩‍🏫 PAINEL DO PROFESSOR
# =========================================
def painel_professor():
    st.markdown("<h1 style='color:#FFD700;'>👩‍🏫 Painel do Professor</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    aba1, aba2, aba3 = st.tabs(["📋 Gerenciar Alunos", "⚙️ Gestão da Equipe", "🏛️ Gestão de Equipes"])

    # --- 📋 ABA 1: Gerenciar alunos e habilitar exame ---
    with aba1:
        st.markdown("### 👥 Alunos cadastrados")
        df = pd.read_sql_query("SELECT * FROM alunos", conn)
        if df.empty:
            st.info("Nenhum aluno cadastrado ainda.")
        else:
            df["Exame Habilitado"] = df["exame_habilitado"].apply(lambda x: "Sim" if x else "Não")
            st.dataframe(df[["id", "faixa_atual", "turma", "status_vinculo", "Exame Habilitado"]], use_container_width=True)

            aluno_id = st.number_input("ID do aluno:", min_value=1, step=1)
            col1, col2 = st.columns(2)
            if col1.button("✅ Habilitar Exame"):
                cursor.execute("UPDATE alunos SET exame_habilitado=1 WHERE id=?", (aluno_id,))
                conn.commit()
                st.success(f"Exame habilitado para o aluno ID {aluno_id}.")
                st.rerun()
            if col2.button("❌ Desabilitar Exame"):
                cursor.execute("UPDATE alunos SET exame_habilitado=0 WHERE id=?", (aluno_id,))
                conn.commit()
                st.warning(f"Exame desabilitado para o aluno ID {aluno_id}.")
                st.rerun()

    # --- ⚙️ ABA 2: Professores da equipe ---
    with aba3:
        st.markdown("### 🏛️ Equipes Cadastradas")

        df_eq = pd.read_sql_query("SELECT * FROM equipes", conn)
        if df_eq.empty:
            st.info("Nenhuma equipe cadastrada ainda.")
        else:
            for i, row in df_eq.iterrows():
                unique_key = f"equipe_{row['id']}_{i}"
                with st.expander(f"🏋️ {row['nome']} (ID {row['id']})", expanded=False):
                    st.markdown(f"**Descrição:** {row['descricao'] or 'Sem descrição.'}")
                    st.markdown(f"**Professor Responsável (ID):** {row['professor_responsavel_id'] or 'Não definido'}")
                    st.markdown(f"**Ativa:** {'✅ Sim' if row['ativo'] else '❌ Não'}")

                    col1, col2 = st.columns(2)

                    # --- Botão de edição ---
                    if col1.button(f"✏️ Editar", key=f"editar_{unique_key}"):
                        st.session_state[f"editando_{row['id']}"] = True

                    if st.session_state.get(f"editando_{row['id']}", False):
                        with st.form(f"form_editar_{unique_key}"):
                            novo_nome = st.text_input("Nome da equipe:", value=row['nome'], key=f"nome_{unique_key}")
                            nova_descricao = st.text_area("Descrição:", value=row['descricao'] or "", key=f"desc_{unique_key}")
                            novo_prof = st.number_input("ID do Professor Responsável:", 
                                                        value=row['professor_responsavel_id'] or 0, min_value=0, key=f"prof_{unique_key}")
                            ativo = st.checkbox("Equipe Ativa", value=bool(row['ativo']), key=f"ativo_{unique_key}")

                            salvar = st.form_submit_button("💾 Salvar Alterações", key=f"salvar_{unique_key}")
                            if salvar:
                                cursor.execute("""
                                    UPDATE equipes
                                    SET nome=?, descricao=?, professor_responsavel_id=?, ativo=?
                                    WHERE id=?
                                """, (novo_nome, nova_descricao, novo_prof, ativo, row['id']))
                                conn.commit()
                                st.success(f"Equipe '{novo_nome}' atualizada com sucesso! ✅")
                                st.session_state[f"editando_{row['id']}"] = False
                                st.rerun()

                    # --- Botão de exclusão ---
                    if col2.button(f"🗑️ Excluir", key=f"excluir_{unique_key}"):
                        st.session_state[f"confirmar_exclusao_{row['id']}"] = True

                    if st.session_state.get(f"confirmar_exclusao_{row['id']}", False):
                        st.warning(f"⚠️ Tem certeza que deseja excluir a equipe **{row['nome']}**?", icon="⚠️")
                        conf1, conf2 = st.columns(2)
                        if conf1.button(f"✅ Confirmar Exclusão", key=f"confirma_{unique_key}"):
                            cursor.execute("DELETE FROM equipes WHERE id=?", (row['id'],))
                            conn.commit()
                            st.error(f"Equipe '{row['nome']}' foi excluída com sucesso.")
                            st.session_state[f"confirmar_exclusao_{row['id']}"] = False
                            st.rerun()
                        if conf2.button("❌ Cancelar", key=f"cancelar_{unique_key}"):
                            st.session_state[f"confirmar_exclusao_{row['id']}"] = False
                            st.info("Exclusão cancelada.")
                            st.rerun()

        st.markdown("---")
        st.markdown("### ➕ Cadastrar Nova Equipe")
        with st.form("nova_equipe_form"):
            nome_eq = st.text_input("Nome da Equipe:", key="novo_nome_eq")
            descricao_eq = st.text_area("Descrição:", key="nova_desc_eq")
            prof_resp = st.number_input("ID do Professor Responsável:", min_value=0, key="novo_prof_eq")
            ativo_eq = st.checkbox("Ativa", value=True, key="novo_ativo_eq")
            salvar_eq = st.form_submit_button("💾 Criar Equipe", key="criar_eq_btn")

            if salvar_eq and nome_eq.strip():
                cursor.execute("""
                    INSERT INTO equipes (nome, descricao, professor_responsavel_id, ativo)
                    VALUES (?, ?, ?, ?)
                """, (nome_eq.strip(), descricao_eq.strip(), prof_resp, ativo_eq))
                conn.commit()
                st.success(f"Equipe '{nome_eq}' criada com sucesso! 🎉")
                st.rerun()
    conn.close()
# =========================================
# 🧩 GESTÃO DE QUESTÕES
# =========================================
def gestao_questoes():
    st.markdown("<h1 style='color:#FFD700;'>🧠 Gestão de Questões</h1>", unsafe_allow_html=True)

    temas_existentes = [f.replace(".json", "") for f in os.listdir("questions") if f.endswith(".json")]
    tema_selecionado = st.selectbox("Tema:", ["Novo Tema"] + temas_existentes)

    if tema_selecionado == "Novo Tema":
        tema = st.text_input("Digite o nome do novo tema:")
    else:
        tema = tema_selecionado

    questoes = carregar_questoes(tema) if tema else []

    st.markdown("### ✍️ Adicionar nova questão")
    pergunta = st.text_area("Pergunta:")
    opcoes = [st.text_input(f"Alternativa {letra}:", key=f"opt_{letra}") for letra in ["A", "B", "C", "D", "E"]]
    resposta = st.selectbox("Resposta correta:", ["A", "B", "C", "D", "E"])
    imagem = st.text_input("Caminho da imagem (opcional):")
    video = st.text_input("URL do vídeo (opcional):")

    if st.button("💾 Salvar Questão"):
        if pergunta.strip():
            nova = {
                "pergunta": pergunta.strip(),
                "opcoes": [f"{letra}) {txt}" for letra, txt in zip(["A", "B", "C", "D", "E"], opcoes) if txt.strip()],
                "resposta": resposta,
                "imagem": imagem.strip(),
                "video": video.strip(),
            }
            questoes.append(nova)
            salvar_questoes(tema, questoes)
            st.success("Questão adicionada com sucesso! ✅")
            st.rerun()
        else:
            st.error("A pergunta não pode estar vazia.")

    st.markdown("### 📚 Questões cadastradas")
    if not questoes:
        st.info("Nenhuma questão cadastrada ainda.")
    else:
        for i, q in enumerate(questoes, 1):
            st.markdown(f"**{i}. {q['pergunta']}**")
            for alt in q["opcoes"]:
                st.markdown(f"- {alt}")
            st.markdown(f"**Resposta:** {q['resposta']}")
            if st.button(f"🗑️ Excluir questão {i}", key=f"del_{i}"):
                questoes.pop(i - 1)
                salvar_questoes(tema, questoes)
                st.warning("Questão removida.")
                st.rerun()


# =========================================
# 🏠 MENU PRINCIPAL
# =========================================
def tela_inicio():
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode()
        logo_html = f"<img src='data:image/png;base64,{logo_base64}' style='width:180px;max-width:200px;height:auto;margin-bottom:10px;'/>"
    else:
        logo_html = "<p style='color:red;'>Logo não encontrada.</p>"

    st.markdown(f"""
        <div style='display:flex;flex-direction:column;align-items:center;justify-content:center;margin-top:40px;'>
            {logo_html}
            <h2 style='color:#FFD700;text-align:center;'>Bem-vindo(a) ao BJJ Digital</h2>
            <p style='color:#FFFFFF;text-align:center;font-size:1.1em;'>Selecione uma opção no menu lateral para começar o treino 💪</p>
        </div>
    """, unsafe_allow_html=True)


# =========================================
# 🚀 MAIN
# =========================================
def main():
    usuario_logado = st.session_state.usuario
    if not usuario_logado:
        st.error("Sessão expirada. Faça login novamente.")
        st.session_state.usuario = None
        st.rerun()

    tipo_usuario = usuario_logado["tipo"]

    st.sidebar.image("assets/logo.png", use_container_width=True)
    st.sidebar.markdown(
        f"<h3 style='color:{COR_DESTAQUE};'>Usuário: {usuario_logado['nome'].title()}</h3>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        f"<small style='color:#ccc;'>Perfil: {tipo_usuario.capitalize()}</small>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("---")

    # =========================================
    # Menu dinâmico conforme perfil
    # =========================================
    if tipo_usuario in ["admin", "professor"]:
        opcoes = [
            "🏠 Início",
            "🤼 Modo Rola",
            "🥋 Exame de Faixa",
            "🏆 Ranking",
            "👩‍🏫 Painel do Professor",
            "🧠 Gestão de Questões",
            "🏛️ Gestão de Equipes",  # 👈 NOVA OPÇÃO
            "🥋 Gestão de Exame de Faixa"
        ]
    else:  # aluno
        opcoes = ["🏠 Início", "🤼 Modo Rola", "🏆 Ranking", "📜 Meus Certificados"]

        # Checa se exame está habilitado pelo professor
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT exame_habilitado FROM alunos WHERE usuario_id=?", (usuario_logado["id"],))
        dado = cursor.fetchone()
        conn.close()
        if dado and dado[0] == 1:
            opcoes.insert(2, "🥋 Exame de Faixa")

    # =========================================
    # Navegação entre módulos
    # =========================================
    menu = st.sidebar.radio("Navegar:", opcoes)

    if menu == "🏠 Início":
        tela_inicio()
    elif menu == "🤼 Modo Rola":
        modo_rola(usuario_logado)
    elif menu == "🥋 Exame de Faixa":
        exame_de_faixa(usuario_logado)
    elif menu == "🏆 Ranking":
        ranking()
    elif menu == "👩‍🏫 Painel do Professor":
        painel_professor()
    elif menu == "🏛️ Gestão de Equipes":
        gestao_equipes()
    elif menu == "🧠 Gestão de Questões":
        gestao_questoes()
    elif menu == "🥋 Gestão de Exame de Faixa":
        gestao_exame_de_faixa()
    elif menu == "📜 Meus Certificados":
        meus_certificados(usuario_logado)

    # =========================================
    # Botão de logout
    # =========================================
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.usuario = None
        st.rerun()
# =========================================
# 🥋 GESTÃO DE EXAME DE FAIXA (modo híbrido)
# =========================================
def carregar_todas_questoes():
    """Carrega todas as questões de todos os temas, adicionando o campo 'tema'."""
    todas = []
    os.makedirs("questions", exist_ok=True)

    for arquivo in os.listdir("questions"):
        if arquivo.endswith(".json"):
            tema = arquivo.replace(".json", "")
            caminho = f"questions/{arquivo}"

            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    questoes = json.load(f)
            except json.JSONDecodeError as e:
                st.error(f"⚠️ Erro ao carregar o arquivo '{arquivo}'. Verifique o formato JSON.")
                st.code(str(e))
                continue  # ignora o arquivo problemático

            for q in questoes:
                q["tema"] = tema
                todas.append(q)

    return todas


def gestao_exame_de_faixa():
    st.markdown("<h1 style='color:#FFD700;'>🥋 Gestão de Exame de Faixa</h1>", unsafe_allow_html=True)

    os.makedirs("exames", exist_ok=True)
    faixas = ["Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"]
    faixa = st.selectbox("Selecione a faixa:", faixas)

    exame_path = f"exames/faixa_{faixa.lower()}.json"
    if os.path.exists(exame_path):
        with open(exame_path, "r", encoding="utf-8") as f:
            exame = json.load(f)
    else:
        exame = {
            "faixa": faixa,
            "ultima_atualizacao": datetime.now().strftime("%Y-%m-%d"),
            "criado_por": st.session_state.usuario["nome"],
            "temas_incluidos": [],
            "questoes": []
        }

    # 🔹 Carrega todas as questões disponíveis
    todas_questoes = carregar_todas_questoes()
    if not todas_questoes:
        st.warning("Nenhuma questão cadastrada nos temas até o momento.")
        return

    # 🔹 Filtro por tema
    temas_disponiveis = sorted(list(set(q["tema"] for q in todas_questoes)))
    tema_filtro = st.selectbox("Filtrar questões por tema:", ["Todos"] + temas_disponiveis)

    # 🔹 Exibição com filtro
    if tema_filtro != "Todos":
        questoes_filtradas = [q for q in todas_questoes if q["tema"] == tema_filtro]
    else:
        questoes_filtradas = todas_questoes

    st.markdown("### ✅ Selecione as questões que farão parte do exame")
    selecao = []
    for i, q in enumerate(questoes_filtradas, 1):
        st.markdown(f"**{i}. ({q['tema']}) {q['pergunta']}**")
        if st.checkbox(f"Adicionar esta questão ({q['tema']})", key=f"{faixa}_{q['tema']}_{i}"):
            selecao.append(q)

    # 🔘 Botão para inserir as selecionadas
    if selecao and st.button("➕ Inserir Questões Selecionadas"):
        for q in selecao:
            if not any(q["pergunta"] == ex_q["pergunta"] for ex_q in exame["questoes"]):
                exame["questoes"].append(q)
        exame["temas_incluidos"] = sorted(list(set(exame.get("temas_incluidos", []) + [q["tema"] for q in selecao])))
        exame["ultima_atualizacao"] = datetime.now().strftime("%Y-%m-%d")
        st.success(f"{len(selecao)} questão(ões) adicionada(s) ao exame da faixa {faixa}.")
        with open(exame_path, "w", encoding="utf-8") as f:
            json.dump(exame, f, indent=4, ensure_ascii=False)
        st.rerun()

    # 🔘 Botão para salvar tudo
    if st.button("💾 Salvar Exame Completo"):
        exame["ultima_atualizacao"] = datetime.now().strftime("%Y-%m-%d")
        exame["criado_por"] = st.session_state.usuario["nome"]
        with open(exame_path, "w", encoding="utf-8") as f:
            json.dump(exame, f, indent=4, ensure_ascii=False)
        st.success(f"Exame da faixa {faixa} salvo com sucesso! 🥋")

    st.markdown("---")
    st.markdown("### 📋 Questões já incluídas no exame atual:")
    if not exame["questoes"]:
        st.info("Nenhuma questão adicionada ainda.")
    else:
        for i, q in enumerate(exame["questoes"], 1):
            st.markdown(f"**{i}. ({q['tema']}) {q['pergunta']}**")
            st.markdown(f"<small>Resposta correta: {q['resposta']}</small>", unsafe_allow_html=True)

    if st.button("🗑️ Excluir exame desta faixa"):
        os.remove(exame_path)
        st.warning(f"O exame da faixa {faixa} foi excluído.")
        st.rerun()

def meus_certificados(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>📜 Meus Certificados</h1>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT faixa, pontuacao, data, codigo_verificacao
        FROM resultados
        WHERE usuario = ? AND modo = 'Exame de Faixa'
        ORDER BY data DESC
    """, (usuario_logado["nome"],))
    certificados = cursor.fetchall()
    conn.close()

    if not certificados:
        st.info("Você ainda não possui certificados emitidos. Complete um exame de faixa para conquistá-los! 🥋")
        return

    for i, (faixa, pontuacao, data, codigo) in enumerate(certificados, 1):
        st.markdown(f"### 🥋 {i}. Faixa {faixa}")
        st.markdown(f"- **Aproveitamento:** {pontuacao}%")
        st.markdown(f"- **Data:** {data}")
        st.markdown(f"- **Código de Verificação:** `{codigo}`")

        caminho_pdf = f"relatorios/Certificado_{usuario_logado['nome']}_{faixa}.pdf"

        # 🔹 Se o certificado não estiver salvo, ele será recriado automaticamente
        if not os.path.exists(caminho_pdf):
            caminho_pdf = gerar_pdf(
                usuario_logado["nome"],
                faixa,
                int((pontuacao / 100) * 10),  # dummy proporcional
                10,
                codigo
            )

        with open(caminho_pdf, "rb") as f:
            st.download_button(
                label=f"📥 Baixar Certificado - Faixa {faixa}",
                data=f.read(),
                file_name=os.path.basename(caminho_pdf),
                mime="application/pdf",
                key=f"baixar_{i}"
            )

        st.markdown("---")
def gestao_equipes():
    st.markdown("<h1 style='color:#FFD700;'>🏛️ Gestão de Equipes</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    aba1, aba2, aba3 = st.tabs(["🏫 Equipes", "👩‍🏫 Professores", "🥋 Alunos"])

    # ============================================================
    # 🏫 ABA 1 - EQUIPES
    # ============================================================
    with aba1:
        st.subheader("Cadastrar nova equipe")

        # 🔹 Campo de nome e descrição
        nome_equipe = st.text_input("Nome da equipe:")
        descricao = st.text_area("Descrição:")

        # 🔹 Seleciona o professor responsável
        professores_disp = pd.read_sql_query(
            "SELECT id, nome FROM usuarios WHERE tipo_usuario='professor'", conn
        )
        professor_responsavel = None
        if professores_disp.empty:
            st.warning("⚠️ Nenhum professor cadastrado. Cadastre um professor primeiro.")
        else:
            nome_prof = st.selectbox(
                "Professor responsável:", professores_disp["nome"]
            )
            professor_responsavel = professores_disp.loc[
                professores_disp["nome"] == nome_prof, "id"
            ].values[0]

        # 🔘 Botão para criar equipe
        if st.button("➕ Criar Equipe"):
            if not nome_equipe.strip():
                st.error("O nome da equipe é obrigatório.")
            elif professor_responsavel is None:
                st.error("Selecione um professor responsável.")
            else:
                cursor.execute(
                    """
                    INSERT INTO equipes (nome, descricao, professor_responsavel_id, ativo)
                    VALUES (?, ?, ?, 1)
                    """,
                    (nome_equipe, descricao, professor_responsavel),
                )
                conn.commit()
                st.success(f"Equipe '{nome_equipe}' criada com sucesso! 🥋")
                st.rerun()

        st.markdown("---")
        st.subheader("Equipes existentes")

        equipes = pd.read_sql_query(
            """
            SELECT e.id, e.nome, e.descricao, u.nome AS professor_responsavel, e.ativo
            FROM equipes e
            LEFT JOIN usuarios u ON e.professor_responsavel_id = u.id
            """,
            conn,
        )

        if equipes.empty:
            st.info("Nenhuma equipe cadastrada.")
        else:
            st.dataframe(equipes, use_container_width=True)

    # ============================================================
    # 👩‍🏫 ABA 2 - PROFESSORES
    # ============================================================
    with aba2:
        st.subheader("Vincular professor a uma equipe")

        professores = pd.read_sql_query("SELECT id, nome FROM usuarios WHERE tipo_usuario='professor'", conn)
        equipes = pd.read_sql_query("SELECT id, nome FROM equipes", conn)

        if professores.empty or equipes.empty:
            st.warning("Cadastre pelo menos uma equipe e um professor primeiro.")
        else:
            prof = st.selectbox("Professor:", professores["nome"])
            equipe = st.selectbox("Equipe:", equipes["nome"])

            prof_id = professores.loc[professores["nome"] == prof, "id"].values[0]
            equipe_id = equipes.loc[equipes["nome"] == equipe, "id"].values[0]

            if st.button("📎 Vincular Professor"):
                cursor.execute(
                    "INSERT INTO professores (usuario_id, equipe_id, pode_aprovar, status_vinculo) VALUES (?, ?, ?, ?)",
                    (prof_id, equipe_id, 1, "ativo"),
                )
                conn.commit()
                st.success(f"Professor {prof} vinculado à equipe {equipe}! ✅")
                st.rerun()

        st.markdown("---")
        st.subheader("Professores vinculados")
        profs = pd.read_sql_query(
            """
            SELECT p.id, u.nome AS professor, e.nome AS equipe, p.status_vinculo, p.data_vinculo
            FROM professores p
            LEFT JOIN usuarios u ON p.usuario_id = u.id
            LEFT JOIN equipes e ON p.equipe_id = e.id
            """,
            conn,
        )
        if profs.empty:
            st.info("Nenhum professor vinculado.")
        else:
            st.dataframe(profs, use_container_width=True)

    # ============================================================
    # 🥋 ABA 3 - ALUNOS
    # ============================================================
    with aba3:
        st.subheader("Vincular aluno a professor e equipe")

        alunos = pd.read_sql_query("SELECT id, nome FROM usuarios WHERE tipo_usuario='aluno'", conn)
        professores = pd.read_sql_query("SELECT id, usuario_id, equipe_id FROM professores WHERE status_vinculo='ativo'", conn)
        equipes = pd.read_sql_query("SELECT id, nome FROM equipes", conn)

        if alunos.empty or professores.empty or equipes.empty:
            st.warning("Cadastre alunos, professores e equipes antes de vincular.")
        else:
            aluno = st.selectbox("Aluno:", alunos["nome"])
            professor_id = st.selectbox("Professor (ID da tabela professores):", professores["id"])
            equipe = st.selectbox("Equipe:", equipes["nome"])

            aluno_id = alunos.loc[alunos["nome"] == aluno, "id"].values[0]
            equipe_id = equipes.loc[equipes["nome"] == equipe, "id"].values[0]

            if st.button("✅ Vincular Aluno"):
                cursor.execute(
                    """
                    INSERT INTO alunos (usuario_id, faixa_atual, turma, professor_id, equipe_id, status_vinculo)
                    VALUES (?, ?, ?, ?, ?, 'ativo')
                    """,
                    (aluno_id, "Branca", "Turma 1", professor_id, equipe_id),
                )
                conn.commit()
                st.success(f"Aluno {aluno} vinculado com sucesso! 🥋")
                st.rerun()

        st.markdown("---")
        st.subheader("Alunos vinculados")
        alunos_vinc = pd.read_sql_query(
            """
            SELECT a.id, u.nome AS aluno, e.nome AS equipe, a.faixa_atual, a.turma, a.status_vinculo
            FROM alunos a
            LEFT JOIN usuarios u ON a.usuario_id = u.id
            LEFT JOIN equipes e ON a.equipe_id = e.id
            """,
            conn,
        )
        if alunos_vinc.empty:
            st.info("Nenhum aluno vinculado ainda.")
        else:
            st.dataframe(alunos_vinc, use_container_width=True)

    conn.close()


# =========================================
# EXECUÇÃO
# =========================================
if __name__ == "__main__":
    main()
