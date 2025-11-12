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
from streamlit_option_menu import option_menu # 👈 NOVA IMPORTAÇÃO

# =========================================
# CONFIGURAÇÕES GERAIS
# =========================================
st.set_page_config(page_title="BJJ Digital", page_icon="assets/logo.png", layout="wide")

COR_FUNDO = "#0e2d26"
COR_TEXTO = "#FFFFFF"
COR_DESTAQUE = "#FFD770" # Ajustei para um dourado um pouco mais suave
COR_BOTAO = "#078B6C"
COR_HOVER = "#FFD770"

# CSS ATUALIZADO (Sugestão 3 e 1)
# 1. Importa a fonte 'Poppins'
# 2. Remove o 'body' (agora no config.toml)
# 3. Adiciona estilo para os "cards" do dashboard
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;700&display=swap');

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
    transform: scale(1.02);
}}
h1, h2, h3 {{
    color: {COR_DESTAQUE};
    text-align: center;
    font-weight: 700;
}}

/* Estilo para os cartões do dashboard (tela_inicio) */
div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] div[data-testid="stVerticalBlock"] div[data-testid="stContainer"] {{
    background-color: #0c241e; 
    border: 1px solid #078B6C;
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
    transition: 0.3s;
    height: 190px; /* Força uma altura uniforme */
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}}
div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] div[data-testid="stVerticalBlock"] div[data-testid="stContainer"]:hover {{
    transform: scale(1.03); 
    border-color: {COR_DESTAQUE};
    background-color: #1a4d40;
}}
div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] div[data-testid="stVerticalBlock"] div[data-testid="stContainer"] h3 {{
     color: {COR_DESTAQUE};
     margin-bottom: 10px;
     font-size: 1.8rem; /* Aumenta o ícone/título */
}}
div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] div[data-testid="stVerticalBlock"] div[data-testid="stContainer"] p {{
     color: {COR_TEXTO};
     font-size: 0.95rem;
}}
</style>
""", unsafe_allow_html=True)


# =========================================
# BANCO DE DADOS
# =========================================
DB_PATH = os.path.expanduser("~/bjj_digital.db")

def criar_banco():
    """Cria o banco de dados e todas as tabelas necessárias, atualizando se houver campos novos."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # =========================================
    # Criação das tabelas principais
    # =========================================
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        tipo_usuario TEXT,
        senha TEXT,
        perfil_completo INTEGER DEFAULT 0  -- indica se o cadastro foi concluído
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
        codigo_verificacao TEXT,
        acertos INTEGER,
        total_questoes INTEGER
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

    # =========================================
    # Atualizações retroativas (bancos antigos)
    # =========================================
    try:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN perfil_completo INTEGER DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        # A coluna já existe — ignorar
        pass

    try:
        cursor.execute("ALTER TABLE resultados ADD COLUMN acertos INTEGER")
        cursor.execute("ALTER TABLE resultados ADD COLUMN total_questoes INTEGER")
        conn.commit()
    except sqlite3.OperationalError:
        # Colunas já existem — ignorar
        pass

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

    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        user = st.text_input("Usuário:", key="login_user")
        pwd = st.text_input("Senha:", type="password", key="login_pwd")

        if st.button("Entrar", use_container_width=True):
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
    """Sava lista de questões no arquivo JSON."""
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
# 🤼 MODO ROLA
# =========================================
def modo_rola(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>🤼 Modo Rola - Treino Livre</h1>", unsafe_allow_html=True)

    temas = [f.replace(".json", "") for f in os.listdir("questions") if f.endswith(".json")]
    temas.append("Todos os Temas")

    col1, col2 = st.columns(2)
    with col1:
        tema = st.selectbox("Selecione o tema:", temas)
    with col2:
        faixa = st.selectbox("Sua faixa:", ["Branca", "Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"])

    if st.button("Iniciar Treino 🤼", use_container_width=True):
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
# 🥋 EXAME DE FAIXA
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
    finalizar = st.button("Finalizar Exame 🏁", use_container_width=True)

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
            # [BUGFIX] Salva acertos e total para recriação do PDF
            cursor.execute("""
                INSERT INTO resultados (usuario, modo, faixa, pontuacao, acertos, total_questoes, data, codigo_verificacao)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (usuario_logado["nome"], "Exame de Faixa", faixa, percentual, acertos, total, datetime.now(), codigo))
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
                mime="application/pdf",
                use_container_width=True
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
    """Gera certificado oficial do exame de faixa com assinatura caligráfica (Allura)."""
    pdf = FPDF("L", "mm", "A4")  # Layout paisagem
    pdf.set_auto_page_break(False)
    pdf.add_page()

    # 🎨 Cores e layout base
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
    # BLOCO CENTRAL
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
    # SELO E QR CODE
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

    # ---------------------------------------------------
    # ASSINATURA DO PROFESSOR (Allura)
    # ---------------------------------------------------
    if professor:
        fonte_assinatura = "assets/fonts/Allura-Regular.ttf"
        if os.path.exists(fonte_assinatura):
            try:
                pdf.add_font("Assinatura", "", fonte_assinatura, uni=True)
                pdf.set_font("Assinatura", "", 30)
            except Exception:
                pdf.set_font("Helvetica", "I", 18)
        else:
            pdf.set_font("Helvetica", "I", 18)

        pdf.set_text_color(*preto)
        pdf.set_y(158)
        pdf.cell(0, 12, professor, align="C")

        pdf.set_draw_color(*dourado)
        pdf.line(100, 173, 197, 173)

        pdf.set_font("Helvetica", "", 10)
        pdf.set_y(175)
        pdf.cell(0, 6, "Assinatura do Professor Responsável", align="C")

    # ---------------------------------------------------
    # RODAPÉ
    # ---------------------------------------------------
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
    nome_arquivo = f"Certificado_{normalizar_nome(usuario)}_{normalizar_nome(faixa)}.pdf"
    caminho_pdf = os.path.abspath(f"relatorios/{nome_arquivo}")
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

    if df.empty:
        st.info("Nenhum resultado para esta faixa.")
        return

    ranking_df = df.groupby("usuario", as_index=False).agg(
        media_percentual=("percentual", "mean"),
        total_treinos=("id", "count")
    ).sort_values(by="media_percentual", ascending=False).reset_index(drop=True)

    ranking_df["Posição"] = range(1, len(ranking_df) + 1)
    ranking_df["media_percentual"] = ranking_df["media_percentual"].round(2)
    
    st.dataframe(
        ranking_df[["Posição", "usuario", "media_percentual", "total_treinos"]], 
        use_container_width=True,
        column_config={"media_percentual": st.column_config.NumberColumn(format="%.2f%%")}
    )

    fig = px.bar(
        ranking_df.head(10),
        x="usuario",
        y="media_percentual",
        text_auto=True,
        title="Top 10 - Modo Rola (% Média de Acertos)",
        color="media_percentual",
        color_continuous_scale="YlOrBr",
    )
    fig.update_layout(xaxis_title="Usuário", yaxis_title="% Média de Acertos")
    st.plotly_chart(fig, use_container_width=True)

# =========================================
# 👩‍🏫 PAINEL DO PROFESSOR (Função 'dummy' - implementar)
# =========================================
def painel_professor():
    st.markdown("<h1 style='color:#FFD700;'>👩‍🏫 Painel do Professor</h1>", unsafe_allow_html=True)
    st.info("Esta área está em desenvolvimento. Use a 'Gestão de Equipes' e 'Gestão de Exames'.")
    # Aqui entraria a lógica de aprovar alunos, liberar exames, etc.

# =========================================
# 🏛️ GESTÃO DE EQUIPES
# =========================================
def gestao_equipes():
    st.markdown("<h1 style='color:#FFD700;'>🏛️ Gestão de Equipes</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    aba1, aba2, aba3 = st.tabs(["🏫 Equipes", "👩‍🏫 Professores", "🥋 Alunos"])

    # === 🏫 ABA 1 - EQUIPES ===
    with aba1:
        st.subheader("Cadastrar nova equipe")
        nome_equipe = st.text_input("Nome da nova equipe:")
        descricao = st.text_area("Descrição da nova equipe:")

        professores_df = pd.read_sql_query("SELECT id, nome FROM usuarios WHERE tipo_usuario='professor'", conn)
        professor_responsavel_id = None
        if not professores_df.empty:
            prof_resp_nome = st.selectbox(
                "👩‍🏫 Professor responsável:",
                ["Nenhum"] + professores_df["nome"].tolist()
            )
            if prof_resp_nome != "Nenhum":
                professor_responsavel_id = int(professores_df.loc[professores_df["nome"] == prof_resp_nome, "id"].values[0])

        if st.button("➕ Criar Equipe"):
            if nome_equipe.strip():
                cursor.execute(
                    "INSERT INTO equipes (nome, descricao, professor_responsavel_id) VALUES (?, ?, ?)",
                    (nome_equipe, descricao, professor_responsavel_id)
                )
                conn.commit()
                st.success(f"Equipe '{nome_equipe}' criada com sucesso!")
                st.rerun()
            else:
                st.error("O nome da equipe é obrigatório.")

        st.markdown("---")
        st.subheader("Equipes existentes")
        equipes_df = pd.read_sql_query("""
            SELECT e.id, e.nome, e.descricao, COALESCE(u.nome, 'Nenhum') AS professor_responsavel
            FROM equipes e
            LEFT JOIN usuarios u ON e.professor_responsavel_id = u.id
        """, conn)
        if equipes_df.empty:
            st.info("Nenhuma equipe cadastrada.")
        else:
            st.dataframe(equipes_df, use_container_width=True)
            st.markdown("### ✏️ Editar ou Excluir Equipe")

            equipe_lista = equipes_df["nome"].tolist()
            equipe_sel = st.selectbox("Selecione a equipe:", equipe_lista)
            equipe_id = int(equipes_df.loc[equipes_df["nome"] == equipe_sel, "id"].values[0])
            dados_equipe = equipes_df[equipes_df["id"] == equipe_id].iloc[0]

            with st.expander(f"Gerenciar {equipe_sel}", expanded=True):
                novo_nome = st.text_input("Novo nome da equipe:", value=dados_equipe["nome"])
                nova_desc = st.text_area("Descrição:", value=dados_equipe["descricao"] or "")

                prof_atual = dados_equipe["professor_responsavel"]
                prof_opcoes = ["Nenhum"] + professores_df["nome"].tolist()
                index_atual = prof_opcoes.index(prof_atual) if prof_atual in prof_opcoes else 0
                novo_prof = st.selectbox("👩‍🏫 Professor responsável:", prof_opcoes, index=index_atual)
                novo_prof_id = None
                if novo_prof != "Nenhum":
                    novo_prof_id = int(professores_df.loc[professores_df["nome"] == novo_prof, "id"].values[0])

                col1, col2 = st.columns(2)
                if col1.button("💾 Salvar Alterações"):
                    cursor.execute(
                        "UPDATE equipes SET nome=?, descricao=?, professor_responsavel_id=? WHERE id=?",
                        (novo_nome, nova_desc, novo_prof_id, equipe_id)
                    )
                    conn.commit()
                    st.success(f"Equipe '{novo_nome}' atualizada com sucesso! ✅")
                    st.rerun()

                if col2.button("🗑️ Excluir Equipe"):
                    cursor.execute("DELETE FROM equipes WHERE id=?", (equipe_id,))
                    conn.commit()
                    st.warning(f"Equipe '{equipe_sel}' excluída com sucesso.")
                    st.rerun()

    # === 👩‍🏫 ABA 2 - PROFESSORES (Apoio) ===
    with aba2:
        st.subheader("Vincular professor de apoio a uma equipe")

        professores_df = pd.read_sql_query("SELECT id, nome FROM usuarios WHERE tipo_usuario='professor'", conn)
        equipes_df = pd.read_sql_query("SELECT id, nome FROM equipes", conn)

        if professores_df.empty or equipes_df.empty:
            st.warning("Cadastre professores e equipes primeiro.")
        else:
            prof = st.selectbox("Professor de apoio:", professores_df["nome"])
            equipe_prof = st.selectbox("Equipe:", equipes_df["nome"])
            prof_id = int(professores_df.loc[professores_df["nome"] == prof, "id"].values[0])
            equipe_id = int(equipes_df.loc[equipes_df["nome"] == equipe_prof, "id"].values[0])

            if st.button("📎 Vincular Professor de Apoio"):
                cursor.execute("""
                    INSERT INTO professores (usuario_id, equipe_id, pode_aprovar, status_vinculo)
                    VALUES (?, ?, ?, ?)
                """, (prof_id, equipe_id, 0, "ativo"))
                conn.commit()
                st.success(f"Professor {prof} vinculado como apoio à equipe {equipe_prof}.")
                st.rerun()

        st.markdown("---")
        st.subheader("Professores vinculados")
        profs_df = pd.read_sql_query("""
            SELECT p.id, u.nome AS professor, e.nome AS equipe, p.status_vinculo
            FROM professores p
            JOIN usuarios u ON p.usuario_id = u.id
            JOIN equipes e ON p.equipe_id = e.id
        """, conn)
        if profs_df.empty:
            st.info("Nenhum professor vinculado ainda.")
        else:
            st.dataframe(profs_df, use_container_width=True)

    # === 🥋 ABA 3 - ALUNOS ===
    with aba3:
        st.subheader("Vincular aluno a professor e equipe")

        alunos_df = pd.read_sql_query("SELECT id, nome FROM usuarios WHERE tipo_usuario='aluno'", conn)
        professores_df = pd.read_sql_query("""
            SELECT p.id, u.nome AS nome_professor, p.equipe_id 
            FROM professores p 
            JOIN usuarios u ON p.usuario_id = u.id 
            WHERE p.status_vinculo='ativo'
        """, conn)
        equipes_df = pd.read_sql_query("SELECT id, nome FROM equipes", conn)

        if alunos_df.empty or professores_df.empty or equipes_df.empty:
            st.warning("Cadastre alunos, professores e equipes antes de vincular.")
        else:
            aluno = st.selectbox("🥋 Aluno:", alunos_df["nome"])
            professor_nome = st.selectbox("👩‍🏫 Professor vinculado (nome):", professores_df["nome_professor"])
            equipe_aluno = st.selectbox("🏫 Equipe do aluno:", equipes_df["nome"])

            aluno_id = int(alunos_df.loc[alunos_df["nome"] == aluno, "id"].values[0])
            professor_id = int(professores_df.loc[professores_df["nome_professor"] == professor_nome, "id"].values[0])
            equipe_id = int(equipes_df.loc[equipes_df["nome"] == equipe_aluno, "id"].values[0])

            if st.button("✅ Vincular Aluno"):
                cursor.execute("""
                    INSERT INTO alunos (usuario_id, faixa_atual, turma, professor_id, equipe_id, status_vinculo)
                    VALUES (?, ?, ?, ?, ?, 'ativo')
                """, (aluno_id, "Branca", "Turma 1", professor_id, equipe_id))
                conn.commit()
                st.success(f"Aluno {aluno} vinculado à equipe {equipe_aluno} sob orientação de {professor_nome}.")
                st.rerun()

        st.markdown("---")
        st.subheader("Alunos vinculados")
        alunos_vinc_df = pd.read_sql_query("""
            SELECT a.id, u.nome AS aluno, e.nome AS equipe, up.nome AS professor
            FROM alunos a
            JOIN usuarios u ON a.usuario_id = u.id
            JOIN equipes e ON a.equipe_id = e.id
            JOIN professores p ON a.professor_id = p.id
            JOIN usuarios up ON p.usuario_id = up.id
        """, conn)
        if alunos_vinc_df.empty:
            st.info("Nenhum aluno vinculado ainda.")
        else:
            st.dataframe(alunos_vinc_df, use_container_width=True)

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
    with st.expander("Expandir para adicionar questão", expanded=False):
        pergunta = st.text_area("Pergunta:")
        opcoes = [st.text_input(f"Alternativa {letra}:", key=f"opt_{letra}") for letra in ["A", "B", "C", "D", "E"]]
        resposta = st.selectbox("Resposta correta:", ["A", "B", "C", "D", "E"])
        imagem = st.text_input("Caminho da imagem (opcional):")
        video = st.text_input("URL do vídeo (opcional):")

        if st.button("💾 Salvar Questão"):
            if pergunta.strip() and tema.strip():
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
                st.error("A pergunta e o nome do tema não podem estar vazios.")

    st.markdown("### 📚 Questões cadastradas")
    if not questoes:
        st.info("Nenhuma questão cadastrada para este tema ainda.")
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
# 🏠 TELA INÍCIO (AGORA DASHBOARD - Sugestão 1)
# =========================================
# =========================================
# 🏠 TELA INÍCIO (AGORA COM CARTÕES CLICÁVEIS)
# =========================================
def tela_inicio():
    
    # 1. 👇 FUNÇÃO DE CALLBACK PARA NAVEGAÇÃO
    def navigate_to(page_name):
        st.session_state.menu_selection = page_name

    # Logo centralizado
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode()
        logo_html = f"<img src='data:image/png;base64,{logo_base64}' style='width:180px;max-width:200px;height:auto;margin-bottom:10px;'/>"
    else:
        logo_html = "<p style='color:red;'>Logo não encontrada.</p>"

    st.markdown(f"""
        <div style='display:flex;flex-direction:column;align-items:center;justify-content:center;margin-bottom:30px;'>
            {logo_html}
            <h2 style='color:{COR_DESTAQUE};text-align:center;'>Painel BJJ Digital</h2>
            <p style='color:{COR_TEXTO};text-align:center;font-size:1.1em;'>Bem-vindo(a), {st.session_state.usuario['nome'].title()}!</p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # --- Cartões Principais (Para todos) ---
    col1, col2, col3 = st.columns(3)

    with col1:
        with st.container(border=True):
            st.markdown("<h3>🤼 Modo Rola</h3>", unsafe_allow_html=True) 
            st.markdown("""<p style='text-align: center; min-height: 50px;'>Treino livre com questões aleatórias de todos os temas.</p>""", unsafe_allow_html=True)
            # 2. 👇 BOTÃO DE NAVEGAÇÃO
            st.button("Acessar", key="nav_rola", on_click=navigate_to, args=("Modo Rola",), use_container_width=True)

    with col2:
        with st.container(border=True):
            st.markdown("<h3>🥋 Exame de Faixa</h3>", unsafe_allow_html=True)
            st.markdown("""<p style='text-align: center; min-height: 50px;'>Realize sua avaliação teórica oficial quando liberada.</p>""", unsafe_allow_html=True)
            # 2. 👇 BOTÃO DE NAVEGAÇÃO
            st.button("Acessar", key="nav_exame", on_click=navigate_to, args=("Exame de Faixa",), use_container_width=True)
            
    with col3:
        with st.container(border=True):
            st.markdown("<h3>🏆 Ranking</h3>", unsafe_allow_html=True)
            st.markdown("""<p style='text-align: center; min-height: 50px;'>Veja sua posição e a dos seus colegas no Modo Rola.</p>""", unsafe_allow_html=True)
            # 2. 👇 BOTÃO DE NAVEGAÇÃO
            st.button("Acessar", key="nav_ranking", on_click=navigate_to, args=("Ranking",), use_container_width=True)

    # --- Cartões de Gestão (Admin/Professor) ---
    if st.session_state.usuario["tipo"] in ["admin", "professor"]:
        st.markdown("---")
        st.markdown(f"<h2 style='color:{COR_DESTAQUE};text-align:center; margin-top:30px;'>Painel de Gestão</h2>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            with st.container(border=True):
                st.markdown("<h3>🧠 Gestão de Questões</h3>", unsafe_allow_html=True)
                st.markdown("""<p style='text-align: center; min-height: 50px;'>Adicione, edite ou remova questões dos temas.</p>""", unsafe_allow_html=True)
                # 2. 👇 BOTÃO DE NAVEGAÇÃO
                st.button("Gerenciar", key="nav_gest_questoes", on_click=navigate_to, args=("Gestão de Questões",), use_container_width=True)
        with c2:
            with st.container(border=True):
                st.markdown("<h3>🏛️ Gestão de Equipes</h3>", unsafe_allow_html=True)
                st.markdown("""<p style='text-align: center; min-height: 50px;'>Gerencie equipes, professores e alunos vinculados.</p>""", unsafe_allow_html=True)
                # 2. 👇 BOTÃO DE NAVEGAÇÃO
                st.button("Gerenciar", key="nav_gest_equipes", on_click=navigate_to, args=("Gestão de Equipes",), use_container_width=True)
        with c3:
            with st.container(border=True):
                st.markdown("<h3>📜 Gestão de Exame</h3>", unsafe_allow_html=True)
                st.markdown("""<p style='text-align: center; min-height: 50px;'>Monte as provas oficiais selecionando questões.</p>""", unsafe_allow_html=True)
                # 2. 👇 BOTÃO DE NAVEGAÇÃO
                st.button("Gerenciar", key="nav_gest_exame", on_click=navigate_to, args=("Gestão de Exame",), use_container_width=True)

# =========================================
# 🚀 MAIN (COM MENU OCULTO NO INÍCIO)
# =========================================
def main():
    usuario_logado = st.session_state.usuario
    if not usuario_logado:
        st.error("Sessão expirada. Faça login novamente.")
        st.session_state.usuario = None
        st.rerun()

    tipo_usuario = usuario_logado["tipo"]

    # --- Sidebar (Info e Logout) ---
    st.sidebar.image("assets/logo.png", use_container_width=True)
    st.sidebar.markdown(
        f"<h3 style='color:{COR_DESTAQUE};'>{usuario_logado['nome'].title()}</h3>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        f"<small style='color:#ccc;'>Perfil: {tipo_usuario.capitalize()}</small>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sair", use_container_width=True):
        st.session_state.usuario = None
        st.session_state.pop("menu_selection", None) # Limpa o estado do menu
        st.rerun()

    # =========================================
    # Menu dinâmico (Horizontal)
    # =========================================

    # 1. Inicializa o estado de navegação
    if "menu_selection" not in st.session_state:
        st.session_state.menu_selection = "Início"

    # 🔹 Define opções e ícones com base no perfil
    if tipo_usuario in ["admin", "professor"]:
        opcoes = [
            "Início",
            "Modo Rola",
            "Exame de Faixa",
            "Ranking",
            "Painel do Professor",
            "Gestão de Questões",
            "Gestão de Equipes",
            "Gestão de Exame"
        ]
        icons = [
            "house-fill", 
            "people-fill", 
            "journal-check", 
            "trophy-fill", 
            "easel-fill", 
            "cpu-fill", 
            "building-fill", 
            "file-earmark-check-fill"
        ]
    else:  # aluno
        opcoes = ["Início", "Modo Rola", "Ranking", "Meus Certificados"]
        icons = ["house-fill", "people-fill", "trophy-fill", "patch-check-fill"]

        # Checa se exame está habilitado
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT exame_habilitado FROM alunos WHERE usuario_id=?", (usuario_logado["id"],))
        dado = cursor.fetchone()
        conn.close()
        if dado and dado[0] == 1:
            opcoes.insert(2, "Exame de Faixa")
            icons.insert(2, "journal-check")

    
    # 2. 👇 [MUDANÇA PRINCIPAL]
    #    SÓ EXIBE O MENU SE A PÁGINA ATUAL NÃO FOR "Início"
    if st.session_state.menu_selection != "Início":
        menu = option_menu(
            menu_title=None,
            options=opcoes,
            icons=icons,
            key="menu_selection", # Chave é a mesma
            orientation="horizontal",
            styles={
                "container": {"padding": "0!important", "background-color": COR_FUNDO, "border-radius": "10px", "margin-bottom": "20px"},
                "icon": {"color": COR_DESTAQUE, "font-size": "18px"},
                "nav-link": {
                    "font-size": "14px",
                    "text-align": "center",
                    "margin": "0px",
                    "--hover-color": "#1a4d40", 
                    "color": COR_TEXTO,
                    "font-weight": "600",
                },
                "nav-link-selected": {"background-color": COR_BOTAO, "color": COR_DESTAQUE},
            }
        )
    else:
        # Se estamos no "Início", o menu não é renderizado (pois o "if" falhou),
        # mas a variável 'menu' precisa ter o valor correto para o roteamento.
        menu = "Início" 

    # =========================================
    # Navegação entre módulos (Roteamento)
    # =========================================
    # (O roteamento abaixo continua funcionando perfeitamente)
    if menu == "Início":
        tela_inicio()
    elif menu == "Modo Rola":
        modo_rola(usuario_logado)
    elif menu == "Exame de Faixa":
        exame_de_faixa(usuario_logado)
    elif menu == "Ranking":
        ranking()
    elif menu == "Painel do Professor":
        painel_professor()
    elif menu == "Gestão de Equipes":
        gestao_equipes()
    elif menu == "Gestão de Questões":
        gestao_questoes()
    elif menu == "Gestão de Exame":
        gestao_exame_de_faixa()
    elif menu == "Meus Certificados":
        meus_certificados(usuario_logado)

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
        try:
            with open(exame_path, "r", encoding="utf-8") as f:
                exame = json.load(f)
        except json.JSONDecodeError:
            st.error("Arquivo de exame corrompido. Criando um novo.")
            exame = {} # Reseta
    else:
        exame = {}

    # Garante que a estrutura base exista
    if "questoes" not in exame:
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
        st.warning("Nenhuma questão cadastrada nos temas (pasta 'questions') até o momento.")
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
    
    # Filtra questões que JÁ ESTÃO no exame para evitar duplicatas
    perguntas_no_exame = set(q["pergunta"] for q in exame["questoes"])
    questoes_para_selecao = [q for q in questoes_filtradas if q["pergunta"] not in perguntas_no_exame]

    if not questoes_para_selecao:
        st.info(f"Todas as questões {('do tema ' + tema_filtro) if tema_filtro != 'Todos' else ''} já foram adicionadas ou não há questões disponíveis.")

    for i, q in enumerate(questoes_para_selecao, 1):
        st.markdown(f"**{i}. ({q['tema']}) {q['pergunta']}**")
        if st.checkbox(f"Adicionar esta questão ({q['tema']})", key=f"{faixa}_{q['tema']}_{i}"):
            selecao.append(q)

    # 🔘 Botão para inserir as selecionadas
    if selecao and st.button("➕ Inserir Questões Selecionadas"):
        exame["questoes"].extend(selecao)
        exame["temas_incluidos"] = sorted(list(set(q["tema"] for q in exame["questoes"])))
        exame["ultima_atualizacao"] = datetime.now().strftime("%Y-%m-%d")
        
        with open(exame_path, "w", encoding="utf-8") as f:
            json.dump(exame, f, indent=4, ensure_ascii=False)
        
        st.success(f"{len(selecao)} questão(ões) adicionada(s) ao exame da faixa {faixa}.")
        st.rerun()

    st.markdown("---")
    st.markdown("### 📋 Questões já incluídas no exame atual:")
    if not exame["questoes"]:
        st.info("Nenhuma questão adicionada ainda.")
    else:
        for i, q in enumerate(exame["questoes"], 1):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{i}. ({q['tema']}) {q['pergunta']}**")
                st.markdown(f"<small>Resposta correta: {q['resposta']}</small>", unsafe_allow_html=True)
            with col2:
                if st.button(f"Remover {i}", key=f"rem_{i}"):
                    exame["questoes"].pop(i - 1)
                    with open(exame_path, "w", encoding="utf-8") as f:
                        json.dump(exame, f, indent=4, ensure_ascii=False)
                    st.rerun()

    st.markdown("---")
    if st.button("🗑️ Excluir exame completo desta faixa", type="primary"):
        if os.path.exists(exame_path):
            os.remove(exame_path)
            st.warning(f"O exame da faixa {faixa} foi excluído.")
            st.rerun()
        else:
            st.error("O arquivo de exame não existe.")

# =========================================
# 📜 MEUS CERTIFICADOS (COM BUGFIX)
# =========================================
def meus_certificados(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>📜 Meus Certificados</h1>", unsafe_allow_html=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # [BUGFIX] Seleciona acertos e total_questoes
    cursor.execute("""
        SELECT faixa, pontuacao, data, codigo_verificacao, acertos, total_questoes
        FROM resultados
        WHERE usuario = ? AND modo = 'Exame de Faixa'
        ORDER BY data DESC
    """, (usuario_logado["nome"],))
    certificados = cursor.fetchall()
    conn.close()

    if not certificados:
        st.info("Você ainda não possui certificados emitidos. Complete um exame de faixa para conquistá-los! 🥋")
        return

    for i, (faixa, pontuacao, data, codigo, acertos, total) in enumerate(certificados, 1):
        st.markdown(f"### 🥋 {i}. Faixa {faixa}")
        st.markdown(f"- **Aproveitamento:** {pontuacao}%")
        st.markdown(f"- **Data:** {datetime.fromisoformat(data).strftime('%d/%m/%Y às %H:%M')}")
        st.markdown(f"- **Código de Verificação:** `{codigo}`")

        # Define um nome de arquivo padronizado
        nome_arquivo = f"Certificado_{normalizar_nome(usuario_logado['nome'])}_{normalizar_nome(faixa)}.pdf"
        caminho_pdf_esperado = f"relatorios/{nome_arquivo}"

        # 🔹 Se o certificado não estiver salvo, ele será recriado
        if not os.path.exists(caminho_pdf_esperado):
            
            # [BUGFIX] Usa os valores corretos do banco.
            # Se acertos ou total for NULO (de dados antigos), usa um fallback.
            acertos_pdf = acertos if acertos is not None else int((pontuacao / 100) * 10) # Fallback
            total_pdf = total if total is not None else 10 # Fallback

            caminho_pdf = gerar_pdf(
                usuario_logado["nome"],
                faixa,
                acertos_pdf,
                total_pdf,
                codigo
            )
        else:
            caminho_pdf = caminho_pdf_esperado
        
        try:
            with open(caminho_pdf, "rb") as f:
                st.download_button(
                    label=f"📥 Baixar Certificado - Faixa {faixa}",
                    data=f.read(),
                    file_name=os.path.basename(caminho_pdf),
                    mime="application/pdf",
                    key=f"baixar_{i}",
                    use_container_width=True
                )
        except FileNotFoundError:
            st.error(f"Erro ao tentar recarregar o certificado '{nome_arquivo}'. Tente novamente.")
            
        st.markdown("---")

# =========================================
# EXECUÇÃO
# =========================================
if __name__ == "__main__":
    main()
