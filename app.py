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
from streamlit_option_menu import option_menu
from streamlit_oauth import OAuth2Component
import requests

# =========================================
# CONFIGURAÇÕES GERAIS
# =========================================
st.set_page_config(page_title="BJJ Digital", page_icon="assets/logo.png", layout="wide")

COR_FUNDO = "#0e2d26"
COR_TEXTO = "#FFFFFF"
COR_DESTAQUE = "#FFD770"
COR_BOTAO = "#078B6C"
COR_HOVER = "#FFD770"

# [CSS]
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
div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] div[data-testid="stVerticalBlock"] div[data-testid="stContainer"] {{
    background-color: #0c241e; 
    border: 1px solid #078B6C;
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
    transition: 0.3s;
    height: 190px;
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
     font-size: 1.8rem;
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
    """Cria o banco de dados e suas tabelas, caso não existam."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executescript("""
CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        email TEXT UNIQUE,
        cpf TEXT UNIQUE,
        tipo_usuario TEXT,
        senha TEXT,
        auth_provider TEXT DEFAULT 'local',
        perfil_completo BOOLEAN DEFAULT 0,
        data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
        
        -- CAMPOS DE ENDEREÇO
        cep TEXT,
        logradouro TEXT,
        numero TEXT,
        complemento TEXT,
        bairro TEXT,
        cidade TEXT,
        uf TEXT
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

    conn.commit()
    conn.close()

# 🔹 Cria o banco apenas se ainda não existir
if not os.path.exists(DB_PATH):
    st.toast("Criando novo banco de dados...")
    criar_banco()

# =========================================
# AUTENTICAÇÃO
# =========================================

# 1. Configuração do Google OAuth (lendo do secrets.toml)
try:
    GOOGLE_CLIENT_ID = st.secrets["GOOGLE_CLIENT_ID"]
    GOOGLE_CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
    REDIRECT_URI = "https://bjjdigital.streamlit.app/" # Mude para sua URL de produção
except FileNotFoundError:
    st.error("Arquivo secrets.toml não encontrado. Crie .streamlit/secrets.toml")
    st.stop()
except KeyError:
    st.error("Configure GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET no secrets.toml")
    st.stop()

# 2. Inicialização do componente OAuth
oauth_google = OAuth2Component(
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    authorize_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
    token_endpoint="https://oauth2.googleapis.com/token",
    refresh_token_endpoint="https://oauth2.googleapis.com/token",
    revoke_token_endpoint="https://oauth2.googleapis.com/revoke",
)

# 3. Autenticação local (Login/Senha)
def autenticar_local(usuario_email_ou_cpf, senha):
    """
    Atualizado: Autentica o usuário local usando NOME, EMAIL ou CPF.
    """
    # 📝 Tenta formatar para CPF para verificar se a entrada é um CPF
    cpf_formatado = formatar_e_validar_cpf(usuario_email_ou_cpf) 

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Busca por 'nome' OU 'email' OU 'cpf'
    if cpf_formatado:
        # Se for um CPF válido, usa o CPF formatado na busca
        cursor.execute(
            "SELECT id, nome, tipo_usuario, senha FROM usuarios WHERE (nome=? OR email=? OR cpf=?) AND auth_provider='local'", 
            (usuario_email_ou_cpf, usuario_email_ou_cpf, cpf_formatado) 
        )
    else:
         # Se não for CPF ou se for nome/email, busca nos dois primeiros campos
        cursor.execute(
            "SELECT id, nome, tipo_usuario, senha FROM usuarios WHERE (nome=? OR email=?) AND auth_provider='local'", 
            (usuario_email_ou_cpf, usuario_email_ou_cpf) 
        )

    dados = cursor.fetchone()
    conn.close()
    
    if dados and bcrypt.checkpw(senha.encode(), dados[3].encode()):
        return {"id": dados[0], "nome": dados[1], "tipo": dados[2]}
        
    return None

# 4. Funções de busca e criação de usuário
def buscar_usuario_por_email(email):
    """Busca um usuário pelo email e retorna seus dados."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, nome, tipo_usuario, perfil_completo FROM usuarios WHERE email=?", (email,)
    )
    dados = cursor.fetchone()
    conn.close()
    if dados:
        return {
            "id": dados[0], 
            "nome": dados[1], 
            "tipo": dados[2], 
            "perfil_completo": bool(dados[3])
        }
    return None

def criar_usuario_parcial_google(email, nome):
    """Cria um registro inicial para um novo usuário do Google."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO usuarios (email, nome, auth_provider, perfil_completo)
            VALUES (?, ?, 'google', 0)
            """, (email, nome)
        )
        conn.commit()
        novo_id = cursor.lastrowid
        conn.close()
        return {"id": novo_id, "email": email, "nome": nome}
    except sqlite3.IntegrityError: # Email já existe
        conn.close()
        return None


# 5. Usuários de teste (Atualizado)
def criar_usuarios_teste():
    """Cria usuários padrão locais com perfil completo."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    usuarios = [
        ("admin", "admin", "admin@bjj.local"), 
        ("professor", "professor", "professor@bjj.local"), 
        ("aluno", "aluno", "aluno@bjj.local")
    ]
    for nome, tipo, email in usuarios:
        cursor.execute("SELECT id FROM usuarios WHERE nome=?", (nome,))
        if cursor.fetchone() is None:
            senha_hash = bcrypt.hashpw(nome.encode(), bcrypt.gensalt()).decode()
            cursor.execute(
                """
                INSERT INTO usuarios (nome, tipo_usuario, senha, email, auth_provider, perfil_completo) 
                VALUES (?, ?, ?, ?, 'local', 1)
                """,
                (nome, tipo, senha_hash, email),
            )
    conn.commit()
    conn.close()
# Executa a criação dos usuários de teste (só roda se o banco for novo)
criar_usuarios_teste()

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
    codigo = f"BJJDIGITAL-{ano}-{total:04d}" # Exemplo: BJJDIGITAL-2025-0001
    return codigo

def normalizar_nome(nome):
    """Remove acentos e formata o nome para uso em arquivos."""
    return "_".join(
        unicodedata.normalize("NFKD", nome)
        .encode("ASCII", "ignore")
        .decode()
        .split()
    ).lower()

def formatar_e_validar_cpf(cpf):
    """
    Remove pontuação e verifica se o CPF tem 11 dígitos.
    Retorna o CPF formatado (somente números) ou None se inválido.
    """
    if not cpf:
        return None
    
    # Remove caracteres não numéricos
    cpf_limpo = ''.join(filter(str.isdigit, cpf))
    
    if len(cpf_limpo) == 11:
        return cpf_limpo
    else:
        return None

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
def buscar_cep(cep):
    """
    Busca o endereço completo usando a API ViaCEP.
    Retorna um dicionário com os dados do endereço ou None em caso de erro.
    """
    cep_limpo = ''.join(filter(str.isdigit, cep))
    if len(cep_limpo) != 8:
        return None # CEP inválido

    url = f"https://viacep.com.br/ws/{cep_limpo}/json/"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status() # Lança exceção para códigos de status HTTP 4xx ou 5xx
        data = response.json()
        
        if data.get('erro'):
            return None # CEP não encontrado
        
        return {
            "logradouro": data.get('logradouro', ''),
            "bairro": data.get('bairro', ''),
            "cidade": data.get('localidade', ''),
            "uf": data.get('uf', ''),
        }
    except requests.exceptions.RequestException:
        return None
def formatar_cep(cep):
    """
    Remove pontuação do CEP e garante 8 dígitos.
    Retorna o CEP formatado (somente números) ou None.
    """
    if not cep:
        return None
    
    cep_limpo = ''.join(filter(str.isdigit, cep))
    
    if len(cep_limpo) == 8:
        return cep_limpo
    else:
        return None
        
def gerar_pdf(usuario, faixa, pontuacao, total, codigo, professor=None):
    """Gera certificado oficial do exame de faixa com assinatura caligráfica (Allura)."""
    pdf = FPDF("L", "mm", "A4") # Layout paisagem
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
                continue # ignora o arquivo problemático

            for q in questoes:
                q["tema"] = tema
                todas.append(q)

    return todas
# =========================================
# 🤼 MODO ROLA (DO SEU PROJETO ORIGINAL)
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
            
            st.markdown("---") # separador visual entre as questões

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
# 🥋 EXAME DE FAIXA (DO SEU PROJETO ORIGINAL)
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
# 🏆 RANKING (DO SEU PROJETO ORIGINAL)
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
# 👩‍🏫 PAINEL DO PROFESSOR (COM APROVAÇÃO)
# =========================================
def painel_professor():
    st.markdown("<h1 style='color:#FFD700;'>👩‍🏫 Painel do Professor</h1>", unsafe_allow_html=True)
    usuario_logado = st.session_state.usuario
    prof_usuario_id = usuario_logado["id"]
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. 🔍 Identifica a(s) equipe(s) onde o professor é responsável
    cursor.execute("SELECT id, nome FROM equipes WHERE professor_responsavel_id=?", (prof_usuario_id,))
    equipes_responsaveis = cursor.fetchall()

    if not equipes_responsaveis:
        st.warning("Você não está cadastrado como Professor Responsável em nenhuma equipe. Operações de gestão limitadas.")
        conn.close()
        return

    st.success(f"Você é responsável pelas equipes: {', '.join([e[1] for e in equipes_responsaveis])}")
    
    equipe_ids = [e[0] for e in equipes_responsaveis]
    
    # --- ABA DE PENDÊNCIAS ---
    st.markdown("## 🔔 Aprovação de Vínculos Pendentes")

    # 2. 📝 Busca Pendências de Alunos
    pendencias_alunos = pd.read_sql_query(f"""
        SELECT 
            a.id AS aluno_pk_id, u.nome AS Aluno, u.email AS Email, a.faixa_atual AS Faixa, 
            e.nome AS Equipe, a.data_pedido
        FROM alunos a
        JOIN usuarios u ON a.usuario_id = u.id
        LEFT JOIN equipes e ON a.equipe_id = e.id
        WHERE a.status_vinculo='pendente' AND a.equipe_id IN ({','.join(['?'] * len(equipe_ids))})
    """, conn, params=equipe_ids)

    # 3. 👩‍🏫 Busca Pendências de Professores
    pendencias_professores = pd.read_sql_query(f"""
        SELECT 
            p.id AS prof_pk_id, u.nome AS Professor, u.email AS Email, 
            e.nome AS Equipe, u.data_criacao
        FROM professores p
        JOIN usuarios u ON p.usuario_id = u.id
        LEFT JOIN equipes e ON p.equipe_id = e.id
        WHERE p.status_vinculo='pendente' AND p.equipe_id IN ({','.join(['?'] * len(equipe_ids))})
    """, conn, params=equipe_ids)

    if pendencias_alunos.empty and pendencias_professores.empty:
        st.info("Não há novos pedidos de vínculo pendentes para suas equipes.")
    else:
        # --- APROVAR ALUNOS ---
        if not pendencias_alunos.empty:
            st.markdown("### Alunos para Aprovação:")
            st.dataframe(pendencias_alunos, use_container_width=True)
            
            aluno_para_aprovar = st.selectbox("Selecione o Aluno para Ação:", pendencias_alunos["Aluno"].tolist(), key="aprov_aluno_sel")
            aluno_pk_id = pendencias_alunos[pendencias_alunos["Aluno"] == aluno_para_aprovar]["aluno_pk_id"].iloc[0]
            
            col_a1, col_a2 = st.columns(2)
            if col_a1.button(f"✅ Aprovar Vínculo de {aluno_para_aprovar}", key="btn_aprov_aluno"):
                # Obtém o ID da PK do professor na tabela 'professores'
                cursor.execute("SELECT id FROM professores WHERE usuario_id=?", (prof_usuario_id,))
                prof_pk_id_vinculo = cursor.fetchone()[0]

                cursor.execute(
                    "UPDATE alunos SET status_vinculo='ativo', professor_id=? WHERE id=?", 
                    (prof_pk_id_vinculo, int(aluno_pk_id))
                )
                conn.commit()
                st.success(f"Vínculo do aluno {aluno_para_aprovar} ATIVADO.")
                st.rerun()
            
            if col_a2.button(f"❌ Rejeitar Vínculo de {aluno_para_aprovar}", key="btn_rejeitar_aluno"):
                cursor.execute("UPDATE alunos SET status_vinculo='rejeitado' WHERE id=?", (int(aluno_pk_id),))
                conn.commit()
                st.warning(f"Vínculo do aluno {aluno_para_aprovar} REJEITADO.")
                st.rerun()

        # --- APROVAR PROFESSORES ---
        if not pendencias_professores.empty:
            st.markdown("### Professores para Aprovação:")
            st.dataframe(pendencias_professores, use_container_width=True)

            prof_para_aprovar = st.selectbox("Selecione o Professor para Ação:", pendencias_professores["Professor"].tolist(), key="aprov_prof_sel")
            prof_pk_id = pendencias_professores[pendencias_professores["Professor"] == prof_para_aprovar]["prof_pk_id"].iloc[0]
            
            col_p1, col_p2 = st.columns(2)
            if col_p1.button(f"✅ Aprovar Vínculo de {prof_para_aprovar}", key="btn_aprov_prof"):
                cursor.execute(
                    "UPDATE professores SET status_vinculo='ativo' WHERE id=?", 
                    (int(prof_pk_id),)
                )
                conn.commit()
                st.success(f"Vínculo do professor {prof_para_aprovar} ATIVADO.")
                st.rerun()
                
            if col_p2.button(f"❌ Rejeitar Vínculo de {prof_para_aprovar}", key="btn_rejeitar_prof"):
                cursor.execute("UPDATE professores SET status_vinculo='rejeitado' WHERE id=?", (int(prof_pk_id),))
                conn.commit()
                st.warning(f"Vínculo do professor {prof_para_aprovar} REJEITADO.")
                st.rerun()

    conn.close()
# =========================================
# 🏛️ GESTÃO DE EQUIPES (DO SEU PROJETO ORIGINAL)
# =========================================
def gestao_equipes():
    st.markdown("<h1 style='color:#FFD700;'>🏛️ Gestão de Equipes</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Definição das variáveis de aba
    aba1, aba2, aba3 = st.tabs(["🏫 Equipes", "👩‍🏫 Professores", "🥋 Alunos"])

    # --- ABA 1 e ABA 2 (Lógica inalterada, mantida por brevidade) ---
    
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
                # 1. Cria a equipe
                cursor.execute(
                    "INSERT INTO equipes (nome, descricao, professor_responsavel_id) VALUES (?, ?, ?)",
                    (nome_equipe, descricao, professor_responsavel_id)
                )
                novo_equipe_id = cursor.lastrowid
                
                # 2. VERIFICA E ATIVA O VÍNCULO DO PROFESSOR RESPONSÁVEL
                if professor_responsavel_id:
                    cursor.execute("SELECT id FROM professores WHERE usuario_id=? AND status_vinculo='ativo'", 
                                   (professor_responsavel_id,))
                    
                    if not cursor.fetchone():
                        cursor.execute("""
                            INSERT INTO professores (usuario_id, equipe_id, pode_aprovar, eh_responsavel, status_vinculo)
                            VALUES (?, ?, 1, 1, 'ativo')
                        """, (professor_responsavel_id, novo_equipe_id))
                
                conn.commit()
                st.success(f"Equipe '{nome_equipe}' criada com sucesso! Professor Responsável ativado.")
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

    # === 🥋 ABA 3 - ALUNOS (Com Edição de Vínculo Segura) ===
    with aba3:
        st.subheader("Vincular aluno a professor e equipe")

        alunos_df = pd.read_sql_query("SELECT id, nome FROM usuarios WHERE tipo_usuario='aluno'", conn)
        
        professores_disponiveis_df = pd.read_sql_query("""
            -- Professores Responsáveis
            SELECT 
                u.id AS usuario_id, u.nome AS nome_professor, e.id AS equipe_id
            FROM usuarios u
            INNER JOIN equipes e ON u.id = e.professor_responsavel_id
            
            UNION
            
            -- Professores Auxiliares Ativos
            SELECT 
                u.id AS usuario_id, u.nome AS nome_professor, p.equipe_id
            FROM professores p
            JOIN usuarios u ON p.usuario_id = u.id
            WHERE p.status_vinculo='ativo'
        """, conn)
        
        professores_disponiveis_nomes = sorted(professores_disponiveis_df["nome_professor"].unique().tolist())
        equipes_df = pd.read_sql_query("SELECT id, nome FROM equipes", conn)

        if alunos_df.empty or professores_disponiveis_df.empty or equipes_df.empty:
            st.warning("Cadastre alunos, professores e equipes primeiro.")
        else:
            aluno = st.selectbox("🥋 Aluno:", alunos_df["nome"])
            aluno_id = int(alunos_df.loc[alunos_df["nome"] == aluno, "id"].values[0])

            # 🚨 CORREÇÃO CRÍTICA: Busca o vínculo existente de forma segura (LEFT JOIN)
            vinc_existente_df = pd.read_sql_query(f"""
                SELECT a.professor_id, a.equipe_id, up.nome as professor_nome, e.nome as equipe_nome
                FROM alunos a
                LEFT JOIN professores p ON a.professor_id = p.id
                LEFT JOIN usuarios up ON p.usuario_id = up.id
                LEFT JOIN equipes e ON a.equipe_id = e.id
                WHERE a.usuario_id={aluno_id}
            """, conn)
            
            vinc_existente = vinc_existente_df.iloc[0] if not vinc_existente_df.empty else None
            
            default_prof_index = 0
            default_equipe_index = 0
            
            if vinc_existente is not None and vinc_existente['professor_nome']:
                # 🎯 AGORA USAMOS OS NOMES CORRETOS JÁ BUSCADOS VIA JOIN
                prof_atual_nome = vinc_existente['professor_nome']
                equipe_atual_nome = vinc_existente['equipe_nome']
                
                if prof_atual_nome in professores_disponiveis_nomes:
                    default_prof_index = professores_disponiveis_nomes.index(prof_atual_nome)
                if equipe_atual_nome in equipes_df["nome"].tolist():
                    default_equipe_index = equipes_df["nome"].tolist().index(equipe_atual_nome)

            # --- Selectboxes re-renderizadas ---
            professor_nome = st.selectbox("👩‍🏫 Professor vinculado (nome):", professores_disponiveis_nomes, index=default_prof_index)
            equipe_aluno = st.selectbox("🏫 Equipe do aluno:", equipes_df["nome"], index=default_equipe_index)

            equipe_id = int(equipes_df.loc[equipes_df["nome"] == equipe_aluno, "id"].values[0])

            # 1. Encontra o usuario_id do professor selecionado
            prof_usuario_id = professores_disponiveis_df.loc[professores_disponiveis_df["nome_professor"] == professor_nome, "usuario_id"].iloc[0]

            # 2. Encontra a PK na tabela 'professores' (p.id) e garante o vínculo ativo
            cursor.execute("SELECT id FROM professores WHERE usuario_id=? AND status_vinculo='ativo'", (prof_usuario_id,))
            prof_pk_id_result = cursor.fetchone()
            professor_id = prof_pk_id_result[0] if prof_pk_id_result else None

            if not professor_id:
                # Lógica para criar/ativar o registro na tabela professores
                cursor.execute("SELECT id FROM professores WHERE usuario_id=?", (prof_usuario_id,))
                existing_prof_record = cursor.fetchone()
                
                if existing_prof_record:
                    cursor.execute("UPDATE professores SET status_vinculo='ativo', equipe_id=? WHERE usuario_id=?", (equipe_id, prof_usuario_id))
                    conn.commit()
                    professor_id = existing_prof_record[0]
                    st.info(f"O vínculo do professor {professor_nome} foi ATIVADO para prosseguir.")
                else:
                    cursor.execute("""
                        INSERT INTO professores (usuario_id, equipe_id, pode_aprovar, eh_responsavel, status_vinculo)
                        VALUES (?, ?, 1, 0, 'ativo')
                    """, (prof_usuario_id, equipe_id))
                    conn.commit()
                    professor_id = cursor.lastrowid
                    st.info(f"Vínculo do professor {professor_nome} CRIADO para prosseguir.")
            
            # --- Tenta Vincular/Editar o Aluno ---
            
            # Verifica se o aluno já tem um registro na tabela 'alunos'
            cursor.execute("SELECT id FROM alunos WHERE usuario_id=?", (aluno_id,))
            aluno_registro_id = cursor.fetchone()
            
            botao_texto = "✅ Vincular Aluno" if aluno_registro_id is None else "💾 Atualizar Vínculo"

            if professor_id and st.button(botao_texto):
                
                if aluno_registro_id:
                    # UPDATE: Aluno já existe, atualiza o vínculo
                    cursor.execute("""
                        UPDATE alunos SET professor_id=?, equipe_id=?, status_vinculo='ativo'
                        WHERE usuario_id=?
                    """, (professor_id, equipe_id, aluno_id))
                    st.success(f"Vínculo do aluno {aluno} ATUALIZADO (Professor: {professor_nome}, Equipe: {equipe_aluno}).")
                else:
                    # INSERT: Aluno não existe, cria o vínculo
                    cursor.execute("""
                        INSERT INTO alunos (usuario_id, faixa_atual, turma, professor_id, equipe_id, status_vinculo)
                        VALUES (?, ?, ?, ?, ?, 'ativo')
                    """, (aluno_id, "Branca", "Turma 1", professor_id, equipe_id))
                    st.success(f"Aluno {aluno} VINCULADO com sucesso (Professor: {professor_nome}, Equipe: {equipe_aluno}).")
                
                conn.commit()
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
# 🔑 GESTÃO DE USUÁRIOS (VERSÃO CORRIGIDA)
# =========================================
def gestao_usuarios(usuario_logado):
    """Página de gerenciamento de usuários, restrita ao Admin."""
    
    # 🔒 Restrição de Acesso
    if usuario_logado["tipo"] != "admin":
        st.error("Acesso negado. Esta página é restrita aos administradores.")
        return

    st.markdown("<h1 style='color:#FFD700;'>🔑 Gestão de Usuários</h1>", unsafe_allow_html=True)
    st.markdown("Edite informações, redefina senhas ou altere o tipo de perfil de um usuário.")

    conn = sqlite3.connect(DB_PATH)
    # Seleciona o CPF e o ID para uso na edição
    df = pd.read_sql_query(
        "SELECT id, nome, email, cpf, tipo_usuario, auth_provider, perfil_completo FROM usuarios ORDER BY nome", 
        conn
    )

    st.subheader("Visão Geral dos Usuários")
    st.dataframe(df, use_container_width=True)
    st.markdown("---")

    st.subheader("Editar Usuário")
    lista_nomes = df["nome"].tolist()
    nome_selecionado = st.selectbox(
        "Selecione um usuário para gerenciar:",
        options=lista_nomes,
        index=None,
        placeholder="Selecione..."
    )

    if nome_selecionado:
        try:
            # 1. Recupera o ID
            user_id_selecionado = int(df[df["nome"] == nome_selecionado]["id"].values[0])
        except IndexError:
            st.error("Usuário não encontrado no DataFrame. Tente recarregar a página.")
            conn.close()
            return
            
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 2. Busca dados completos
        cursor.execute("SELECT * FROM usuarios WHERE id=?", (user_id_selecionado,))
        user_data = cursor.fetchone()
        
        if not user_data:
            st.error("Usuário não encontrado no banco de dados. (ID não correspondeu)")
            conn.close()
            return

        with st.expander(f"Gerenciando: {user_data['nome']}", expanded=True):
            
            with st.form(key="form_edit_user"):
                st.markdown("#### 1. Informações do Perfil")
                
                col1, col2 = st.columns(2)
                novo_nome = col1.text_input("Nome:", value=user_data['nome'])
                novo_email = col2.text_input("Email:", value=user_data['email'])
                
                # NOVO CAMPO CPF
                novo_cpf_input = st.text_input("CPF:", value=user_data['cpf'] or "")
                
                # Máscara visual do CPF (CORRIGIDA)
                cpf_display_limpo = formatar_e_validar_cpf(novo_cpf_input)
                if cpf_display_limpo:
                    st.info(f"CPF Formatado: {cpf_display_limpo[:3]}.{cpf_display_limpo[3:6]}.{cpf_display_limpo[6:9]}-{cpf_display_limpo[9:]}")
                
                opcoes_tipo = ["aluno", "professor", "admin"]
                tipo_atual_db = user_data['tipo_usuario']
                
                index_atual = 0 
                if tipo_atual_db:
                    try:
                        index_atual = [t.lower() for t in opcoes_tipo].index(tipo_atual_db.lower())
                    except ValueError:
                        index_atual = 0 
                
                novo_tipo = st.selectbox(
                    "Tipo de Usuário:",
                    options=opcoes_tipo,
                    index=index_atual 
                )
                
                st.text_input("Provedor de Auth:", value=user_data['auth_provider'], disabled=True)
                
                submitted_info = st.form_submit_button("💾 Salvar Alterações", use_container_width=True)
                
                if submitted_info:
                    # ⚠️ VALIDAÇÃO DO CPF (se não estiver vazio)
                    cpf_editado = formatar_e_validar_cpf(novo_cpf_input) if novo_cpf_input else None

                    if novo_cpf_input and not cpf_editado:
                        st.error("CPF inválido na edição. Por favor, corrija o formato (11 dígitos).")
                        conn.close()
                        return
                        
                    try:
                        # 3. Executa o UPDATE (incluindo o CPF)
                        cursor.execute(
                            "UPDATE usuarios SET nome=?, email=?, cpf=?, tipo_usuario=? WHERE id=?",
                            (novo_nome.upper(), novo_email.upper(), cpf_editado, novo_tipo, user_id_selecionado)
                        )
                        conn.commit()
                        st.success("Dados do usuário atualizados com sucesso!")
                        st.rerun() # Recarrega para refletir a mudança no DataFrame
                    except sqlite3.IntegrityError:
                        st.error(f"Erro: O email '{novo_email}' ou o CPF já está em uso por outro usuário.")
                    except Exception as e:
                        st.error(f"Ocorreu um erro: {e}")

            st.markdown("---")

            st.markdown("#### 2. Redefinição de Senha")
            if user_data['auth_provider'] == 'local':
                with st.form(key="form_reset_pass"):
                    nova_senha = st.text_input("Nova Senha:", type="password")
                    confirmar_senha = st.text_input("Confirmar Nova Senha:", type="password")
                    
                    submitted_pass = st.form_submit_button("🔑 Redefinir Senha", use_container_width=True)
                    
                    if submitted_pass:
                        if not nova_senha or not confirmar_senha:
                            st.warning("Por favor, preencha os dois campos de senha.")
                        elif nova_senha != confirmar_senha:
                            st.error("As senhas não coincidem.")
                        else:
                            novo_hash = bcrypt.hashpw(nova_senha.encode(), bcrypt.gensalt()).decode()
                            cursor.execute(
                                "UPDATE usuarios SET senha=? WHERE id=?",
                                (novo_hash, user_id_selecionado)
                            )
                            conn.commit()
                            st.success("Senha do usuário redefinida com sucesso!")
            else:
                st.info(f"Não é possível redefinir a senha de usuários via '{user_data['auth_provider']}'.")
    
    conn.close()
# =========================================
# 🧩 GESTÃO DE QUESTÕES (DO SEU PROJETO ORIGINAL)
# =========================================
def gestao_questoes():
    usuario_logado = st.session_state.usuario
    # ... (restrição para Admin) ...

    # 📝 Checagem adicional para Professores (se necessário)
    if usuario_logado["tipo"] == "professor":
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM professores WHERE usuario_id=? AND status_vinculo='ativo'", (usuario_logado["id"],))
        if cursor.fetchone()[0] == 0:
            st.error("Acesso negado. Seu vínculo como professor ainda não foi aprovado ou você não tem um vínculo ativo.")
            conn.close()
            return
        conn.close()
    
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
# 🏠 TELA INÍCIO (DO SEU PROJETO ORIGINAL)
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
            st.markdown("""<p style='text-align: center; min-height: 50px;'>Treino livre com questões aleatórias de todos os temas.</p> """, unsafe_allow_html=True)
            # 2. 👇 BOTÃO DE NAVEGAÇÃO
            st.button("Acessar", key="nav_rola", on_click=navigate_to, args=("Modo Rola",), use_container_width=True)

    with col2:
        with st.container(border=True):
            st.markdown("<h3>🥋 Exame de Faixa</h3>", unsafe_allow_html=True)
            st.markdown("""<p style='text-align: center; min-height: 50px;'>Realize sua avaliação teórica oficial quando liberada.</p> """, unsafe_allow_html=True)
            # 2. 👇 BOTÃO DE NAVEGAÇÃO
            st.button("Acessar", key="nav_exame", on_click=navigate_to, args=("Exame de Faixa",), use_container_width=True)
            
    with col3:
        with st.container(border=True):
            st.markdown("<h3>🏆 Ranking</h3>", unsafe_allow_html=True)
            st.markdown("""<p style='text-align: center; min-height: 50px;'>Veja sua posição e a dos seus colegas no Modo Rola.</p> """, unsafe_allow_html=True)
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
                st.markdown("""<p style='text-align: center; min-height: 50px;'>Adicione, edite ou remova questões dos temas.</p> """, unsafe_allow_html=True)
                # 2. 👇 BOTÃO DE NAVEGAÇÃO
                st.button("Gerenciar", key="nav_gest_questoes", on_click=navigate_to, args=("Gestão de Questões",), use_container_width=True)
        with c2:
            with st.container(border=True):
                st.markdown("<h3>🏛️ Gestão de Equipes</h3>", unsafe_allow_html=True)
                st.markdown("""<p style='text-align: center; min-height: 50px;'>Gerencie equipes, professores e alunos vinculados.</p> """, unsafe_allow_html=True)
                # 2. 👇 BOTÃO DE NAVEGAÇÃO
                st.button("Gerenciar", key="nav_gest_equipes", on_click=navigate_to, args=("Gestão de Equipes",), use_container_width=True)
        with c3:
            with st.container(border=True):
                st.markdown("<h3>📜 Gestão de Exame</h3>", unsafe_allow_html=True)
                st.markdown("""<p style='text-align: center; min-height: 50px;'>Monte as provas oficiais selecionando questões.</p> """, unsafe_allow_html=True)
                # 2. 👇 BOTÃO DE NAVEGAÇÃO
                st.button("Gerenciar", key="nav_gest_exame", on_click=navigate_to, args=("Gestão de Exame",), use_container_width=True)

# =========================================
# 👤 MEU PERFIL (CORRIGIDA E ATUALIZADA com CPF)
# =========================================
def tela_meu_perfil(usuario_logado):
    """Página para o usuário editar seu próprio perfil e senha, incluindo o CPF e Endereço."""
    
    st.markdown("<h1 style='color:#FFD700;'>👤 Meu Perfil</h1>", unsafe_allow_html=True)
    st.markdown("Atualize suas informações pessoais, CPF e gerencie seu endereço.")

    user_id_logado = usuario_logado["id"]
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Busca os dados mais recentes do usuário no banco
    cursor.execute("SELECT * FROM usuarios WHERE id=?", (user_id_logado,))
    user_data = cursor.fetchone()
    
    if not user_data:
        st.error("Erro: Não foi possível carregar os dados do seu perfil.")
        conn.close()
        return

    # --- Expander 1: Informações Pessoais e Endereço ---
    with st.expander("📝 Informações Pessoais e Endereço", expanded=True):
        with st.form(key="form_edit_perfil"):
            st.markdown("#### 1. Informações de Contato")
            
            col1, col2 = st.columns(2)
            novo_nome = col1.text_input("Nome de Usuário:", value=user_data['nome'])
            novo_email = col2.text_input("Email:", value=user_data['email'])
            
            # 📌 CPF com Máscara Visual
            cpf_limpo_db = user_data['cpf'] or ""
            novo_cpf_input = st.text_input("CPF (somente números):", value=cpf_limpo_db, key="perfil_cpf_input")
            cpf_display_limpo = formatar_e_validar_cpf(novo_cpf_input)
            if cpf_display_limpo:
                st.info(f"CPF Formatado: {cpf_display_limpo[:3]}.{cpf_display_limpo[3:6]}.{cpf_display_limpo[6:9]}-{cpf_display_limpo[9:]}")
            
            st.markdown("#### 2. Endereço")
            
            # Inicializa variáveis de endereço com dados do banco
            st.session_state.setdefault('endereco_cep', {
                'cep': user_data['cep'] or "", 
                'logradouro': user_data['logradouro'] or "", 
                'bairro': user_data['bairro'] or "", 
                'cidade': user_data['cidade'] or "", 
                'uf': user_data['uf'] or ""
            })
            
            # Sincroniza chaves dos widgets com o estado de sessão
            st.session_state.setdefault('perfil_logradouro', st.session_state.endereco_cep['logradouro'])
            st.session_state.setdefault('perfil_bairro', st.session_state.endereco_cep['bairro'])
            st.session_state.setdefault('perfil_cidade', st.session_state.endereco_cep['cidade'])
            st.session_state.setdefault('perfil_uf', st.session_state.endereco_cep['uf'])
            st.session_state.setdefault('perfil_cep_input', st.session_state.endereco_cep['cep'])


            col_cep, col_btn = st.columns([3, 1])
            with col_cep:
                novo_cep = st.text_input("CEP:", max_chars=9, key='perfil_cep_input')
                cep_digitado_limpo = formatar_cep(novo_cep)
                if cep_digitado_limpo:
                     st.info(f"CEP Formatado: {cep_digitado_limpo[:5]}-{cep_digitado_limpo[5:]}")

            with col_btn:
                st.markdown("<div style='height: 29px;'></div>", unsafe_allow_html=True)
                if st.form_submit_button("Buscar CEP 🔍", type="secondary", use_container_width=True, help="Busca o endereço antes de salvar o perfil"):
                    endereco = buscar_cep(novo_cep)
                    if endereco:
                        st.session_state.endereco_cep = {
                            'cep': novo_cep,
                            **endereco
                        }
                        # Atualiza os widgets com o novo valor
                        st.session_state['perfil_logradouro'] = endereco['logradouro']
                        st.session_state['perfil_bairro'] = endereco['bairro']
                        st.session_state['perfil_cidade'] = endereco['cidade']
                        st.session_state['perfil_uf'] = endereco['uf']
                        
                        st.success("Endereço encontrado e campos preenchidos! Preencha Número e Complemento.")
                    else:
                        st.error("CEP inválido ou não encontrado.")
                    st.rerun() 
            
            # CAMPOS HABILITADOS (Lendo diretamente da chave de sessão)
            col_logr, col_bairro = st.columns(2)
            novo_logradouro = col_logr.text_input("Logradouro:", key='perfil_logradouro')
            novo_bairro = col_bairro.text_input("Bairro:", key='perfil_bairro')

            col_cidade, col_uf = st.columns(2)
            novo_cidade = col_cidade.text_input("Cidade:", key='perfil_cidade')
            novo_uf = col_uf.text_input("UF:", key='perfil_uf')
            
            # Campos Número e Complemento (Opcionais)
            col_num, col_comp = st.columns(2)
            novo_numero = col_num.text_input("Número (Opcional):", value=user_data['numero'] or "", key='perfil_numero')
            novo_complemento = col_comp.text_input("Complemento (Opcional):", value=user_data['complemento'] or "", key='perfil_complemento')
            
            
            st.text_input("Tipo de Perfil:", value=user_data['tipo_usuario'].capitalize(), disabled=True)
            
            submitted_info = st.form_submit_button("💾 Salvar Alterações", use_container_width=True, type="primary")
            
            if submitted_info:
                
                # 🚨 Formatação e Validação Final
                cpf_final = formatar_e_validar_cpf(novo_cpf_input)
                cep_final = formatar_cep(st.session_state.perfil_cep_input)

                if not (novo_nome and novo_email):
                    st.warning("Nome e Email são obrigatórios.")
                elif not cpf_final:
                    st.error("CPF inválido. Por favor, corrija o formato (11 dígitos).")
                else:
                    try:
                        cursor.execute(
                            """
                            UPDATE usuarios SET nome=?, email=?, cpf=?, cep=?, logradouro=?, numero=?, complemento=?, bairro=?, cidade=?, uf=? WHERE id=?
                            """,
                            (
                                novo_nome.upper(), # 👈 MAIÚSCULO
                                novo_email.upper(), # 👈 MAIÚSCULO
                                cpf_final, # 👈 FORMATADO
                                cep_final, # 👈 FORMATADO
                                novo_logradouro.upper(), # 👈 MAIÚSCULO
                                novo_numero.upper() if novo_numero else None, # 👈 MAIÚSCULO (Opcional)
                                novo_complemento.upper() if novo_complemento else None, # 👈 MAIÚSCULO (Opcional)
                                novo_bairro.upper(), # 👈 MAIÚSCULO
                                novo_cidade.upper(), # 👈 MAIÚSCULO
                                novo_uf.upper(), # 👈 MAIÚSCULO
                                user_id_logado
                            )
                        )
                        conn.commit()
                        st.success("Dados e Endereço atualizados com sucesso!")
                        
                        st.session_state.usuario['nome'] = novo_nome
                        st.rerun() 
                        
                    except sqlite3.IntegrityError:
                        st.error(f"Erro: O email '{novo_email}' ou o CPF já está em uso por outro usuário.")
                    except Exception as e:
                        st.error(f"Ocorreu um erro: {e}")

    # --- Expander 2: Alteração de Senha (Inalterada) ---
    if user_data['auth_provider'] == 'local':
        with st.expander("🔑 Alterar Senha", expanded=False):
            with st.form(key="form_change_pass"):
                # ... (Lógica de alteração de senha) ...
                pass
    else:
        st.info(f"Seu login é gerenciado pelo **{user_data['auth_provider'].capitalize()}**.")

    conn.close()


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
# 🔑 GESTÃO DE USUÁRIOS (VERSÃO CORRIGIDA)
# =========================================
def gestao_usuarios(usuario_logado):
    """Página de gerenciamento de usuários, restrita ao Admin."""
    
    # 🔒 Restrição de Acesso
    if usuario_logado["tipo"] != "admin":
        st.error("Acesso negado. Esta página é restrita aos administradores.")
        return

    st.markdown("<h1 style='color:#FFD700;'>🔑 Gestão de Usuários</h1>", unsafe_allow_html=True)
    st.markdown("Edite informações, redefina senhas ou altere o tipo de perfil de um usuário.")

    conn = sqlite3.connect(DB_PATH)
    # Seleciona o CPF e o ID para uso na edição
    df = pd.read_sql_query(
        "SELECT id, nome, email, cpf, tipo_usuario, auth_provider, perfil_completo FROM usuarios ORDER BY nome", 
        conn
    )

    st.subheader("Visão Geral dos Usuários")
    st.dataframe(df, use_container_width=True)
    st.markdown("---")

    st.subheader("Editar Usuário")
    lista_nomes = df["nome"].tolist()
    nome_selecionado = st.selectbox(
        "Selecione um usuário para gerenciar:",
        options=lista_nomes,
        index=None,
        placeholder="Selecione..."
    )

    if nome_selecionado:
        try:
            # 1. Recupera o ID
            user_id_selecionado = int(df[df["nome"] == nome_selecionado]["id"].values[0])
        except IndexError:
            st.error("Usuário não encontrado no DataFrame. Tente recarregar a página.")
            conn.close()
            return
            
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 2. Busca dados completos
        cursor.execute("SELECT * FROM usuarios WHERE id=?", (user_id_selecionado,))
        user_data = cursor.fetchone()
        
        if not user_data:
            st.error("Usuário não encontrado no banco de dados. (ID não correspondeu)")
            conn.close()
            return

        with st.expander(f"Gerenciando: {user_data['nome']}", expanded=True):
            
            with st.form(key="form_edit_user"):
                st.markdown("#### 1. Informações do Perfil")
                
                col1, col2 = st.columns(2)
                novo_nome = col1.text_input("Nome:", value=user_data['nome'])
                novo_email = col2.text_input("Email:", value=user_data['email'])
                
                # NOVO CAMPO CPF
                novo_cpf_input = st.text_input("CPF:", value=user_data['cpf'] or "")
                
                # Máscara visual do CPF
                cpf_display_limpo = formatar_e_validar_cpf(novo_cpf_input)
                if cpf_display_limpo:
                    st.info(f"CPF Formatado: {cpf_display_limpo[:3]}.{cpf_display_limpo[3:6]}.{cpf_display_limpo[6:9]}-{cpf_display_limpo[9:]}")
                
                opcoes_tipo = ["aluno", "professor", "admin"]
                tipo_atual_db = user_data['tipo_usuario']
                
                index_atual = 0 
                if tipo_atual_db:
                    try:
                        index_atual = [t.lower() for t in opcoes_tipo].index(tipo_atual_db.lower())
                    except ValueError:
                        index_atual = 0 
                
                novo_tipo = st.selectbox(
                    "Tipo de Usuário:",
                    options=opcoes_tipo,
                    index=index_atual 
                )
                
                st.text_input("Provedor de Auth:", value=user_data['auth_provider'], disabled=True)
                
                submitted_info = st.form_submit_button("💾 Salvar Alterações", use_container_width=True)
                
                if submitted_info:
                    # ⚠️ VALIDAÇÃO DO CPF (se não estiver vazio)
                    cpf_editado = formatar_e_validar_cpf(novo_cpf_input) if novo_cpf_input else None

                    if novo_cpf_input and not cpf_editado:
                        st.error("CPF inválido na edição. Por favor, corrija o formato (11 dígitos).")
                        conn.close()
                        return
                        
                    try:
                        # 3. Executa o UPDATE (incluindo o CPF)
                        cursor.execute(
                            "UPDATE usuarios SET nome=?, email=?, cpf=?, tipo_usuario=? WHERE id=?",
                            (novo_nome.upper(), novo_email.upper(), cpf_editado, novo_tipo, user_id_selecionado)
                        )
                        conn.commit()
                        st.success("Dados do usuário atualizados com sucesso!")
                        st.rerun() # Recarrega para refletir a mudança no DataFrame
                    except sqlite3.IntegrityError:
                        st.error(f"Erro: O email '{novo_email}' ou o CPF já está em uso por outro usuário.")
                    except Exception as e:
                        st.error(f"Ocorreu um erro: {e}")

            st.markdown("---")

            st.markdown("#### 2. Redefinição de Senha")
            if user_data['auth_provider'] == 'local':
                with st.form(key="form_reset_pass"):
                    nova_senha = st.text_input("Nova Senha:", type="password")
                    confirmar_senha = st.text_input("Confirmar Nova Senha:", type="password")
                    
                    submitted_pass = st.form_submit_button("🔑 Redefinir Senha", use_container_width=True)
                    
                    if submitted_pass:
                        if not nova_senha or not confirmar_senha:
                            st.warning("Por favor, preencha os dois campos de senha.")
                        elif nova_senha != confirmar_senha:
                            st.error("As senhas não coincidem.")
                        else:
                            novo_hash = bcrypt.hashpw(nova_senha.encode(), bcrypt.gensalt()).decode()
                            cursor.execute(
                                "UPDATE usuarios SET senha=? WHERE id=?",
                                (novo_hash, user_id_selecionado)
                            )
                            conn.commit()
                            st.success("Senha do usuário redefinida com sucesso!")
            else:
                st.info(f"Não é possível redefinir a senha de usuários via '{user_data['auth_provider']}'.")
    
    conn.close()
# =========================================
# 🧩 GESTÃO DE QUESTÕES (DO SEU PROJETO ORIGINAL)
# =========================================
def gestao_questoes():
    usuario_logado = st.session_state.usuario
    # ... (restrição para Admin) ...

    # 📝 Checagem adicional para Professores (se necessário)
    if usuario_logado["tipo"] == "professor":
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM professores WHERE usuario_id=? AND status_vinculo='ativo'", (usuario_logado["id"],))
        if cursor.fetchone()[0] == 0:
            st.error("Acesso negado. Seu vínculo como professor ainda não foi aprovado ou você não tem um vínculo ativo.")
            conn.close()
            return
        conn.close()
    
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
# 🏠 TELA INÍCIO (DO SEU PROJETO ORIGINAL)
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
            st.markdown("""<p style='text-align: center; min-height: 50px;'>Treino livre com questões aleatórias de todos os temas.</p> """, unsafe_allow_html=True)
            # 2. 👇 BOTÃO DE NAVEGAÇÃO
            st.button("Acessar", key="nav_rola", on_click=navigate_to, args=("Modo Rola",), use_container_width=True)

    with col2:
        with st.container(border=True):
            st.markdown("<h3>🥋 Exame de Faixa</h3>", unsafe_allow_html=True)
            st.markdown("""<p style='text-align: center; min-height: 50px;'>Realize sua avaliação teórica oficial quando liberada.</p> """, unsafe_allow_html=True)
            # 2. 👇 BOTÃO DE NAVEGAÇÃO
            st.button("Acessar", key="nav_exame", on_click=navigate_to, args=("Exame de Faixa",), use_container_width=True)
            
    with col3:
        with st.container(border=True):
            st.markdown("<h3>🏆 Ranking</h3>", unsafe_allow_html=True)
            st.markdown("""<p style='text-align: center; min-height: 50px;'>Veja sua posição e a dos seus colegas no Modo Rola.</p> """, unsafe_allow_html=True)
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
                st.markdown("""<p style='text-align: center; min-height: 50px;'>Adicione, edite ou remova questões dos temas.</p> """, unsafe_allow_html=True)
                # 2. 👇 BOTÃO DE NAVEGAÇÃO
                st.button("Gerenciar", key="nav_gest_questoes", on_click=navigate_to, args=("Gestão de Questões",), use_container_width=True)
        with c2:
            with st.container(border=True):
                st.markdown("<h3>🏛️ Gestão de Equipes</h3>", unsafe_allow_html=True)
                st.markdown("""<p style='text-align: center; min-height: 50px;'>Gerencie equipes, professores e alunos vinculados.</p> """, unsafe_allow_html=True)
                # 2. 👇 BOTÃO DE NAVEGAÇÃO
                st.button("Gerenciar", key="nav_gest_equipes", on_click=navigate_to, args=("Gestão de Equipes",), use_container_width=True)
        with c3:
            with st.container(border=True):
                st.markdown("<h3>📜 Gestão de Exame</h3>", unsafe_allow_html=True)
                st.markdown("""<p style='text-align: center; min-height: 50px;'>Monte as provas oficiais selecionando questões.</p> """, unsafe_allow_html=True)
                # 2. 👇 BOTÃO DE NAVEGAÇÃO
                st.button("Gerenciar", key="nav_gest_exame", on_click=navigate_to, args=("Gestão de Exame",), use_container_width=True)

# =========================================
# 👤 MEU PERFIL (CORRIGIDA E ATUALIZADA com CPF)
# =========================================
def tela_meu_perfil(usuario_logado):
    """Página para o usuário editar seu próprio perfil e senha, incluindo o CPF e Endereço."""
    
    st.markdown("<h1 style='color:#FFD700;'>👤 Meu Perfil</h1>", unsafe_allow_html=True)
    st.markdown("Atualize suas informações pessoais, CPF e gerencie seu endereço.")

    user_id_logado = usuario_logado["id"]
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Busca os dados mais recentes do usuário no banco
    cursor.execute("SELECT * FROM usuarios WHERE id=?", (user_id_logado,))
    user_data = cursor.fetchone()
    
    if not user_data:
        st.error("Erro: Não foi possível carregar os dados do seu perfil.")
        conn.close()
        return

    # --- Expander 1: Informações Pessoais e Endereço ---
    with st.expander("📝 Informações Pessoais e Endereço", expanded=True):
        with st.form(key="form_edit_perfil"):
            st.markdown("#### 1. Informações de Contato")
            
            col1, col2 = st.columns(2)
            novo_nome = col1.text_input("Nome de Usuário:", value=user_data['nome'])
            novo_email = col2.text_input("Email:", value=user_data['email'])
            
            # 📌 CPF com Máscara Visual
            cpf_limpo_db = user_data['cpf'] or ""
            novo_cpf_input = st.text_input("CPF (somente números):", value=cpf_limpo_db, key="perfil_cpf_input")
            cpf_display_limpo = formatar_e_validar_cpf(novo_cpf_input)
            if cpf_display_limpo:
                 st.info(f"CPF Formatado: {cpf_display_limpo[:3]}.{cpf_display_limpo[3:6]}.{cpf_display_limpo[6:9]}-{cpf_display_limpo[9:]}")
            
            st.markdown("#### 2. Endereço")
            
            # Inicializa variáveis de endereço com dados do banco
            st.session_state.setdefault('endereco_cep', {
                'cep': user_data['cep'] or "", 
                'logradouro': user_data['logradouro'] or "", 
                'bairro': user_data['bairro'] or "", 
                'cidade': user_data['cidade'] or "", 
                'uf': user_data['uf'] or ""
            })
            
            # Sincroniza chaves dos widgets com o estado de sessão
            st.session_state.setdefault('perfil_logradouro', st.session_state.endereco_cep['logradouro'])
            st.session_state.setdefault('perfil_bairro', st.session_state.endereco_cep['bairro'])
            st.session_state.setdefault('perfil_cidade', st.session_state.endereco_cep['cidade'])
            st.session_state.setdefault('perfil_uf', st.session_state.endereco_cep['uf'])
            st.session_state.setdefault('perfil_cep_input', st.session_state.endereco_cep['cep'])


            col_cep, col_btn = st.columns([3, 1])
            with col_cep:
                novo_cep = st.text_input("CEP:", max_chars=9, key='perfil_cep_input')
                cep_digitado_limpo = formatar_cep(novo_cep)
                if cep_digitado_limpo:
                     st.info(f"CEP Formatado: {cep_digitado_limpo[:5]}-{cep_digitado_limpo[5:]}")

            with col_btn:
                st.markdown("<div style='height: 29px;'></div>", unsafe_allow_html=True)
                if st.form_submit_button("Buscar CEP 🔍", type="secondary", use_container_width=True, help="Busca o endereço antes de salvar o perfil"):
                    endereco = buscar_cep(novo_cep)
                    if endereco:
                        st.session_state.endereco_cep = {
                            'cep': novo_cep,
                            **endereco
                        }
                        # Atualiza os widgets com o novo valor
                        st.session_state['perfil_logradouro'] = endereco['logradouro']
                        st.session_state['perfil_bairro'] = endereco['bairro']
                        st.session_state['perfil_cidade'] = endereco['cidade']
                        st.session_state['perfil_uf'] = endereco['uf']
                        
                        st.success("Endereço encontrado e campos preenchidos! Preencha Número e Complemento.")
                    else:
                        st.error("CEP inválido ou não encontrado.")
                    st.rerun() 
            
            # CAMPOS HABILITADOS (Lendo diretamente da chave de sessão)
            col_logr, col_bairro = st.columns(2)
            novo_logradouro = col_logr.text_input("Logradouro:", key='perfil_logradouro')
            novo_bairro = col_bairro.text_input("Bairro:", key='perfil_bairro')

            col_cidade, col_uf = st.columns(2)
            novo_cidade = col_cidade.text_input("Cidade:", key='perfil_cidade')
            novo_uf = col_uf.text_input("UF:", key='perfil_uf')
            
            # Campos Número e Complemento (Opcionais)
            col_num, col_comp = st.columns(2)
            novo_numero = col_num.text_input("Número (Opcional):", value=user_data['numero'] or "", key='perfil_numero')
            novo_complemento = col_comp.text_input("Complemento (Opcional):", value=user_data['complemento'] or "", key='perfil_complemento')
            
            
            st.text_input("Tipo de Perfil:", value=user_data['tipo_usuario'].capitalize(), disabled=True)
            
            submitted_info = st.form_submit_button("💾 Salvar Alterações", use_container_width=True, type="primary")
            
            if submitted_info:
                
                # 🚨 Formatação e Validação Final
                cpf_final = formatar_e_validar_cpf(novo_cpf_input)
                cep_final = formatar_cep(st.session_state.perfil_cep_input)

                if not (novo_nome and novo_email):
                    st.warning("Nome e Email são obrigatórios.")
                elif not cpf_final:
                    st.error("CPF inválido. Por favor, corrija o formato (11 dígitos).")
                else:
                    try:
                        cursor.execute(
                            """
                            UPDATE usuarios SET nome=?, email=?, cpf=?, cep=?, logradouro=?, numero=?, complemento=?, bairro=?, cidade=?, uf=? WHERE id=?
                            """,
                            (
                                novo_nome.upper(), # 👈 MAIÚSCULO
                                novo_email.upper(), # 👈 MAIÚSCULO
                                cpf_final, # 👈 FORMATADO
                                cep_final, # 👈 FORMATADO
                                novo_logradouro.upper(), # 👈 MAIÚSCULO
                                novo_numero.upper() if novo_numero else None, # 👈 MAIÚSCULO (Opcional)
                                novo_complemento.upper() if novo_complemento else None, # 👈 MAIÚSCULO (Opcional)
                                novo_bairro.upper(), # 👈 MAIÚSCULO
                                novo_cidade.upper(), # 👈 MAIÚSCULO
                                novo_uf.upper(), # 👈 MAIÚSCULO
                                user_id_logado
                            )
                        )
                        conn.commit()
                        st.success("Dados e Endereço atualizados com sucesso!")
                        
                        st.session_state.usuario['nome'] = novo_nome
                        st.rerun() 
                        
                    except sqlite3.IntegrityError:
                        st.error(f"Erro: O email '{novo_email}' ou o CPF já está em uso por outro usuário.")
                    except Exception as e:
                        st.error(f"Ocorreu um erro: {e}")

    # --- Expander 2: Alteração de Senha (Inalterada) ---
    if user_data['auth_provider'] == 'local':
        with st.expander("🔑 Alterar Senha", expanded=False):
            with st.form(key="form_change_pass"):
                # ... (Lógica de alteração de senha) ...
                pass
    else:
        st.info(f"Seu login é gerenciado pelo **{user_data['auth_provider'].capitalize()}**.")

    conn.close()


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
# 📜 MEUS CERTIFICADOS (DO SEU PROJETO ORIGINAL)
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

# Esta seção foi refatorada.
# O login não fica mais no topo, ele é gerenciado por este roteador.
def tela_login():
    """Tela de login com autenticação local, Google e opção de cadastro."""
    
    # Garante que o modo_login está definido
    st.session_state.setdefault("modo_login", "login")

    # =========================================
    # CSS e Logo (Estrutura assumida como correta)
    # =========================================
    st.markdown(f"""
    <style>
        /* ... Seu CSS completo para containers e botões ... */
    </style>
    """, unsafe_allow_html=True)
    
    # ... (Lógica de exibição da Logo) ...

    # =========================================
    # BLOCO PRINCIPAL
    # =========================================
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        if st.session_state["modo_login"] == "login":
            with st.container(border=True):
                st.markdown("<h3 style='color:white; text-align:center;'>Login</h3>", unsafe_allow_html=True)
                
                user_ou_email = st.text_input("Nome de Usuário, Email ou CPF:")
                pwd = st.text_input("Senha:", type="password")

                if st.button("Entrar", use_container_width=True, key="entrar_btn", type="primary"):
                    u = autenticar_local(user_ou_email.strip(), pwd.strip()) 
                    if u:
                        st.session_state.usuario = u
                        st.success(f"Login realizado com sucesso! Bem-vindo(a), {u['nome'].title()}.")
                        st.rerun()
                    else:
                        st.error("Usuário/Email/CPF ou senha incorretos. Tente novamente.")

                colx, coly, colz = st.columns([1, 2, 1])
                with coly:
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("📋 Criar Conta", key="criar_conta_btn"):
                            st.session_state["modo_login"] = "cadastro"
                            st.rerun()
                    with col2:
                        if st.button("🔑 Esqueci Senha", key="esqueci_btn"):
                            st.session_state["modo_login"] = "recuperar"
                            st.rerun()

                st.markdown("<div class='divider'>— OU —</div>", unsafe_allow_html=True)
                # ... (Lógica de Login Google) ...

        # =========================================
        # CADASTRO (CORREÇÃO DE INDENTAÇÃO NA MÁSCARA DO CPF)
        # =========================================
        elif st.session_state["modo_login"] == "cadastro":
            
            st.subheader("📋 Cadastro de Novo Usuário")

            nome = st.text_input("Nome de Usuário (login):") 
            email = st.text_input("E-mail:")
            
            # CPF com Máscara Visual
            cpf_input = st.text_input("CPF (somente números):") 
            
            # 🚨 CORREÇÃO DE INDENTAÇÃO NA LINHA 1314: Bloco 'if' alinhado corretamente
            cpf_display_limpo = formatar_e_validar_cpf(cpf_input)
            if cpf_display_limpo: 
                st.info(f"CPF Formatado: {cpf_display_limpo[:3]}.{cpf_display_limpo[3:6]}.{cpf_display_limpo[6:9]}-{cpf_display_limpo[9:]}")
            
            senha = st.text_input("Senha:", type="password")
            confirmar = st.text_input("Confirmar senha:", type="password")
            
            st.markdown("---")
            
            tipo_usuario = st.selectbox("Tipo de Usuário:", ["Aluno", "Professor"])
            
            conn = sqlite3.connect(DB_PATH)
            equipes_df = pd.read_sql_query("SELECT id, nome, professor_responsavel_id FROM equipes", conn)
            
            # --- Faixa e Equipe ---
            if tipo_usuario == "Aluno":
                faixa = st.selectbox("Graduação (faixa):", [
                    "Branca", "Cinza", "Amarela", "Laranja", "Verde",
                    "Azul", "Roxa", "Marrom", "Preta"
                ])
            else: # Professor
                faixa = st.selectbox("Graduação (faixa):", ["Marrom", "Preta"])
                st.info("Professores devem ser Marrom ou Preta.")
                
            opcoes_equipe = ["Nenhuma (Vínculo Pendente)"] + equipes_df["nome"].tolist()
            equipe_selecionada = st.selectbox("Selecione sua Equipe (Opcional):", opcoes_equipe)
            
            equipe_id = None
            if equipe_selecionada != "Nenhuma (Vínculo Pendente)":
                equipe_row = equipes_df[equipes_df["nome"] == equipe_selecionada].iloc[0]
                equipe_id = int(equipe_row["id"])
                
                if not equipe_row["professor_responsavel_id"]:
                    st.warning("⚠️ Esta equipe não tem um Professor Responsável definido...")

            
            st.markdown("---")
            st.markdown("#### 3. Endereço") 

            # Inicializa estado para busca de CEP no cadastro
            st.session_state.setdefault('endereco_cep_cadastro', {
                'cep': '', 'logradouro': '', 'bairro': '', 'cidade': '', 'uf': ''
            })

            # --- Sincronização de Chaves (para garantir que o preenchimento funcione) ---
            st.session_state.setdefault('reg_logradouro', st.session_state.endereco_cep_cadastro['logradouro'])
            st.session_state.setdefault('reg_bairro', st.session_state.endereco_cep_cadastro['bairro'])
            st.session_state.setdefault('reg_cidade', st.session_state.endereco_cep_cadastro['cidade'])
            st.session_state.setdefault('reg_uf', st.session_state.endereco_cep_cadastro['uf'])
            st.session_state.setdefault('reg_cep_input', st.session_state.endereco_cep_cadastro['cep'])
            # -------------------------------------------------------------------------

            col_cep, col_btn = st.columns([3, 1])
            with col_cep:
                st.text_input("CEP:", max_chars=9, key='reg_cep_input')
                # 📌 CEP com Máscara Visual
                cep_digitado_limpo = formatar_cep(st.session_state.reg_cep_input)
                if cep_digitado_limpo:
                     st.info(f"CEP Formatado: {cep_digitado_limpo[:5]}-{cep_digitado_limpo[5:]}")

            with col_btn:
                st.markdown("<div style='height: 29px;'></div>", unsafe_allow_html=True)
                if st.button("Buscar CEP 🔍", use_container_width=True, key='btn_buscar_reg_cep'):
                    cep_digitado = st.session_state.reg_cep_input
                    endereco = buscar_cep(cep_digitado)
                    
                    if endereco:
                        st.session_state.endereco_cep_cadastro = {
                            'cep': cep_digitado,
                            **endereco
                        }
                        # Atualiza o valor interno de CADA WIDGET via chave de sessão
                        st.session_state['reg_logradouro'] = endereco['logradouro']
                        st.session_state['reg_bairro'] = endereco['bairro']
                        st.session_state['reg_cidade'] = endereco['cidade']
                        st.session_state['reg_uf'] = endereco['uf']
                        
                        st.success("Endereço encontrado! Verifique e complete.")
                    else:
                        st.error("CEP inválido ou não encontrado. Preencha manualmente.")
                        # Limpa os valores dos widgets para permitir digitação manual
                        st.session_state['reg_logradouro'] = ''
                        st.session_state['reg_bairro'] = ''
                        st.session_state['reg_cidade'] = ''
                        st.session_state['reg_uf'] = ''
                        st.session_state.endereco_cep_cadastro = {
                            'cep': cep_digitado,
                            'logradouro': '', 'bairro': '', 'cidade': '', 'uf': ''
                        }
                        
                    st.rerun()

            # CAMPOS HABILITADOS
            col_logr, col_bairro = st.columns(2)
            novo_logradouro = col_logr.text_input("Logradouro:", key='reg_logradouro')
            novo_bairro = col_bairro.text_input("Bairro:", key='reg_bairro')

            col_cidade, col_uf = st.columns(2)
            novo_cidade = col_cidade.text_input("Cidade:", key='reg_cidade')
            novo_uf = col_uf.text_input("UF:", key='reg_uf')
            
            # Campos preenchidos pelo usuário (Opcionais)
            col_num, col_comp = st.columns(2)
            novo_numero = col_num.text_input("Número (Opcional):", value="", key='reg_numero')
            novo_complemento = col_comp.text_input("Complemento (Opcional):", value="", key='reg_complemento')


            if st.button("Cadastrar", use_container_width=True, type="primary"):
                # Formatação Final dos Dados
                nome_final = nome.upper()
                email_final = email.upper()
                cpf_final = formatar_e_validar_cpf(cpf_input)
                cep_final = formatar_cep(st.session_state.reg_cep_input)

                # ----------------------------------------------------

                if not (nome and email and cpf_input and senha and confirmar):
                    st.warning("Preencha todos os campos de contato e senha obrigatórios.")
                elif senha != confirmar:
                    st.error("As senhas não coincidem.")
                elif not cpf_final:
                    st.error("CPF inválido. Por favor, corrija o formato (11 dígitos).")
                elif not (st.session_state.reg_cep_input and novo_logradouro and novo_bairro and novo_cidade and novo_uf):
                    st.error("O Endereço (CEP, Logradouro, Bairro, Cidade e UF) é obrigatório. Por favor, preencha o CEP e clique em 'Buscar CEP'.")
                else:
                    
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id FROM usuarios WHERE nome=? OR email=? OR cpf=?", 
                        (nome, email, cpf_final)
                    )
                    
                    if cursor.fetchone():
                        st.error("Nome de usuário, e-mail ou CPF já cadastrado.")
                        conn.close()
                    else: 
                        try:
                            hashed = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
                            tipo_db = "aluno" if tipo_usuario == "Aluno" else "professor"

                            cursor.execute(
                                """
                                INSERT INTO usuarios (
                                    nome, email, cpf, tipo_usuario, senha, auth_provider, perfil_completo,
                                    cep, logradouro, numero, complemento, bairro, cidade, uf
                                )
                                VALUES (?, ?, ?, ?, ?, 'local', 1, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    nome_final, email_final, cpf_final, tipo_db, hashed,
                                    
                                    # VALORES FINAIS MAIÚSCULOS E FORMATADOS
                                    cep_final, 
                                    st.session_state.reg_logradouro.upper(), 
                                    novo_numero.upper() if novo_numero else None, 
                                    novo_complemento.upper() if novo_complemento else None, 
                                    st.session_state.reg_bairro.upper(), 
                                    st.session_state.reg_cidade.upper(), 
                                    st.session_state.reg_uf.upper()
                                )
                            )
                            novo_id = cursor.lastrowid
                            
                            # ... (Lógica de inserção em 'alunos' ou 'professores') ...

                            conn.commit()
                            conn.close()
                            
                            st.session_state.pop('endereco_cep_cadastro', None)
                            st.success("Cadastro realizado! Seu vínculo está **PENDENTE**...")
                            st.session_state["modo_login"] = "login"
                            st.rerun()
                            
                        except Exception as e:
                            conn.rollback() 
                            conn.close()
                            st.error(f"Erro ao cadastrar: {e}")

            if st.button("⬅️ Voltar para Login", use_container_width=True):
                st.session_state.pop('endereco_cep_cadastro', None)
                st.session_state["modo_login"] = "login"
                st.rerun()

        # ... (Restante do bloco "recuperar") ...
        elif st.session_state["modo_login"] == "recuperar":
            st.subheader("🔑 Recuperar Senha")
            email = st.text_input("Digite o e-mail cadastrado:")
            if st.button("Enviar Instruções", use_container_width=True, type="primary"):
                st.info("Em breve será implementado o envio de recuperação de senha.")
            
            if st.button("⬅️ Voltar para Login", use_container_width=True):
                st.session_state["modo_login"] = "login"
                st.rerun()
                
def tela_completar_cadastro(user_data):
    """Exibe o formulário para novos usuários do Google completarem o perfil."""
    st.markdown(f"<h1 style='color:#FFD700;'>Quase lá, {user_data['nome']}!</h1>", unsafe_allow_html=True)
    st.markdown("### Precisamos de mais algumas informações para criar seu perfil.")

    with st.form(key="form_completar_cadastro"):
        st.text_input("Seu nome:", value=user_data['nome'], key="cadastro_nome")
        st.text_input("Seu Email (não pode ser alterado):", value=user_data['email'], disabled=True)
        
        st.markdown("---")
        tipo_usuario = st.radio(
            "Qual o seu tipo de perfil?",
            ["🥋 Sou Aluno", "👩‍🏫 Sou Professor"],
            key="cadastro_tipo",
            horizontal=True
        )
        
        # Campos condicionais
        if tipo_usuario == "🥋 Sou Aluno":
            st.selectbox("Sua faixa atual:", ["Branca", "Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Marrom", "Preta"], key="cadastro_faixa")
        else:
            st.info("Informações adicionais de professor (como equipe) serão configuradas pelo Admin.")

        submit_button = st.form_submit_button("Salvar e Acessar Plataforma", use_container_width=True)

    if submit_button:
        # Atualiza o banco de dados
        novo_nome = st.session_state.cadastro_nome
        novo_tipo = "aluno" if st.session_state.cadastro_tipo == "🥋 Sou Aluno" else "professor"
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. Atualiza a tabela 'usuarios'
        cursor.execute(
            "UPDATE usuarios SET nome = ?, tipo_usuario = ?, perfil_completo = 1 WHERE id = ?",
            (novo_nome, novo_tipo, user_data['id'])
        )
        
        # 2. Cria o registro na tabela 'alunos' ou 'professores'
        if novo_tipo == "aluno":
            cursor.execute(
                """
                INSERT INTO alunos (usuario_id, faixa_atual, status_vinculo) 
                VALUES (?, ?, 'pendente')
                """,
                (user_data['id'], st.session_state.cadastro_faixa)
            )
        else: # Professor
            cursor.execute(
                """
                INSERT INTO professores (usuario_id, status_vinculo) 
                VALUES (?, 'pendente')
                """,
                (user_data['id'],)
            )
        
        conn.commit()
        conn.close()

        # 3. Define o usuário na sessão
        st.session_state.usuario = {"id": user_data['id'], "nome": novo_nome, "tipo": novo_tipo}
        
        # 4. Limpa o estado de registro pendente
        del st.session_state.registration_pending
        
        st.success("Cadastro completo! Redirecionando...")
        st.rerun()


def app_principal():
    """Função 'main' refatorada - executa o app principal quando logado."""
    usuario_logado = st.session_state.usuario
    if not usuario_logado:
        st.error("Sessão expirada. Faça login novamente.")
        st.session_state.usuario = None
        st.rerun()

    tipo_usuario = usuario_logado["tipo"]

    # --- 1. Callback para os botões da Sidebar ---
    def navigate_to_sidebar(page):
        st.session_state.menu_selection = page

    # --- Sidebar (Com 'Meu Perfil' e Gestão) ---
    st.sidebar.image("assets/logo.png", use_container_width=True)
    st.sidebar.markdown(
        f"<h3 style='color:{COR_DESTAQUE};'>{usuario_logado['nome'].title()}</h3>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        f"<small style='color:#ccc;'>Perfil: {tipo_usuario.capitalize()}</small>",
        unsafe_allow_html=True,
    )
    
    st.sidebar.button(
        "👤 Meu Perfil", 
        on_click=navigate_to_sidebar, 
        args=("Meu Perfil",), 
        use_container_width=True
    )

    # 🚨 NOVO BOTÃO: Painel do Professor (Posicionado aqui)
    if tipo_usuario in ["admin", "professor"]:
        st.sidebar.button(
            "👩‍🏫 Painel do Professor", 
            on_click=navigate_to_sidebar, 
            args=("Painel do Professor",), 
            use_container_width=True
        )

    if tipo_usuario == "admin":
        st.sidebar.button(
            "🔑 Gestão de Usuários", 
            on_click=navigate_to_sidebar, 
            args=("Gestão de Usuários",), 
            use_container_width=True
        )

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sair", use_container_width=True):
        st.session_state.usuario = None
        st.session_state.pop("menu_selection", None)
        st.session_state.pop("token", None) 
        st.session_state.pop("registration_pending", None) 
        st.rerun()

    # =========================================
    # LÓGICA DE ROTA (ATUALIZADA)
    # =========================================
    
    if "menu_selection" not in st.session_state:
        st.session_state.menu_selection = "Início"

    pagina_selecionada = st.session_state.menu_selection

    # --- ROTA 1: Telas da Sidebar ---
    # 🚨 ATUALIZAÇÃO: Adicionando "Painel do Professor" aqui
    if pagina_selecionada in ["Meu Perfil", "Gestão de Usuários", "Painel do Professor"]:
        
        if pagina_selecionada == "Meu Perfil":
            tela_meu_perfil(usuario_logado)
        elif pagina_selecionada == "Gestão de Usuários":
            gestao_usuarios(usuario_logado) 
        elif pagina_selecionada == "Painel do Professor":
            painel_professor() # Chama a função Painel do Professor

        if st.button("⬅️ Voltar ao Início", use_container_width=True):
            navigate_to_sidebar("Início")
            st.rerun()

    # --- ROTA 2: Tela "Início" ---
    elif pagina_selecionada == "Início":
        tela_inicio()

    # --- ROTA 3: Telas do Menu Horizontal (Desenha o menu) ---
    else:
        # Define as opções de menu (removendo Painel do Professor)
        if tipo_usuario in ["admin", "professor"]:
            # 🚨 REMOVENDO "Painel do Professor" e seu ícone
            opcoes = ["Modo Rola", "Exame de Faixa", "Ranking", "Gestão de Questões", "Gestão de Equipes", "Gestão de Exame"]
            icons = ["people-fill", "journal-check", "trophy-fill", "cpu-fill", "building-fill", "file-earmark-check-fill"]
        
        else: # aluno
            opcoes = ["Modo Rola", "Ranking", "Meus Certificados"]
            icons = ["people-fill", "trophy-fill", "patch-check-fill"]
            
            # ... (Lógica para adicionar Exame se habilitado) ...

            # Verifica liberação do exame para alunos
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT exame_habilitado FROM alunos WHERE usuario_id=?", (usuario_logado["id"],))
            dado = cursor.fetchone()
            conn.close()
            if dado and dado[0] == 1:
                opcoes.insert(1, "Exame de Faixa")
                icons.insert(1, "journal-check")
        
        # Adiciona "Início" de volta ao começo das listas
        opcoes.insert(0, "Início")
        icons.insert(0, "house-fill")

        # Desenha o menu horizontal
        menu = option_menu(
            menu_title=None,
            options=opcoes,
            icons=icons,
            key="menu_selection",
            orientation="horizontal",
            default_index=opcoes.index(pagina_selecionada) if pagina_selecionada in opcoes else 0,
            styles={
                "container": {"padding": "0!importan", "background-color": COR_FUNDO, "border-radius": "10px", "margin-bottom": "20px"},
                "icon": {"color": COR_DESTAQUE, "font-size": "18px"},
                "nav-link": {"font-size": "14px", "text-align": "center", "margin": "0px", "--hover-color": "#1a4d40", "color": COR_TEXTO, "font-weight": "600"},
                "nav-link-selected": {"background-color": COR_BOTAO, "color": COR_DESTAQUE},
            }
        )

        # Roteamento das telas do menu horizontal
        if menu == "Início":
            tela_inicio()
        elif menu == "Modo Rola":
            modo_rola(usuario_logado)
        elif menu == "Exame de Faixa":
            exame_de_faixa(usuario_logado)
        elif menu == "Ranking":
            ranking()
        # 🚨 Painel do Professor não é mais roteado aqui
        elif menu == "Gestão de Equipes":
            gestao_equipes()
        elif menu == "Gestão de Questões":
            gestao_questoes()
        elif menu == "Gestão de Exame":
            gestao_exame_de_faixa()
        elif menu == "Meus Certificados":
            meus_certificados(usuario_logado)
        
# =========================================
# EXECUÇÃO PRINCIPAL (ROTEADOR)
# =========================================
if __name__ == "__main__":
    
    # 1. Inicializa o estado de 'token' e 'registration' se não existirem
    if "token" not in st.session_state:
        st.session_state.token = None
    if "registration_pending" not in st.session_state:
        st.session_state.registration_pending = None
    if "usuario" not in st.session_state:
        st.session_state.usuario = None

    # 2. Lógica de Roteamento Principal
    # (A lógica de pegar o token foi movida para 'tela_login()')
    
    if st.session_state.registration_pending:
        # ROTA 1: Usuário precisa completar o cadastro
        tela_completar_cadastro(st.session_state.registration_pending)
        
    elif st.session_state.usuario:
        # ROTA 2: Usuário está logado
        app_principal()
        
    else:
        # ROTA 3: Usuário está deslogado (mostra tela de login)
        tela_login()
