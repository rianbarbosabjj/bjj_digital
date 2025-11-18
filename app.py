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

# =========================================
# CSS GLOBAL
# =========================================
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
</style>
""", unsafe_allow_html=True)


# =========================================
# BANCO DE DADOS (ATUALIZADO COM CPF + ENDEREÇO)
# =========================================
DB_PATH = os.path.expanduser("~/bjj_digital.db")

def criar_banco():
    """Cria o banco de dados com CPF único + endereço completo."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        email TEXT UNIQUE,
        tipo_usuario TEXT,
        senha TEXT,
        auth_provider TEXT DEFAULT 'local',
        perfil_completo BOOLEAN DEFAULT 0,
        data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,

        cpf TEXT UNIQUE,
        cep TEXT,
        endereco TEXT,
        numero TEXT,
        complemento TEXT,
        bairro TEXT,
        cidade TEXT,
        estado TEXT
    );
    """)

    cursor.executescript("""
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

    # Garantir colunas novas
    novas_colunas = {
        "cpf": "TEXT UNIQUE",
        "cep": "TEXT",
        "endereco": "TEXT",
        "numero": "TEXT",
        "complemento": "TEXT",
        "bairro": "TEXT",
        "cidade": "TEXT",
        "estado": "TEXT"
    }

    for coluna, tipo in novas_colunas.items():
        try:
            cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {coluna} {tipo}")
        except:
            pass

    conn.commit()
    conn.close()

if not os.path.exists(DB_PATH):
    st.toast("Criando banco...")
    criar_banco()


# =========================================
# 🔒 VALIDAÇÃO DE CPF
# =========================================
def limpar_cpf(cpf: str) -> str:
    return "".join(filter(str.isdigit, cpf or ""))

def validar_cpf(cpf: str) -> bool:
    cpf = limpar_cpf(cpf)
    if len(cpf) != 11:
        return False
    if cpf == cpf[0] * 11:
        return False

    soma1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
    dig1 = (soma1 * 10 % 11) % 10

    soma2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
    dig2 = (soma2 * 10 % 11) % 10

    return cpf[-2:] == f"{dig1}{dig2}"


# =========================================
# 🌐 BUSCA DE ENDEREÇO POR CEP (ViaCEP)
# =========================================
def buscar_endereco_por_cep(cep):
    cep = limpar_cpf(cep)
    if len(cep) != 8:
        return None

    url = f"https://viacep.com.br/ws/{cep}/json/"
    try:
        r = requests.get(url, timeout=5)
        data = r.json()

        if "erro" in data:
            return None

        return {
            "endereco": data.get("logradouro", ""),
            "bairro": data.get("bairro", ""),
            "cidade": data.get("localidade", ""),
            "estado": data.get("uf", "")
        }
    except:
        return None


# =========================================
# AUTENTICAÇÃO (LOGIN LOCAL + GOOGLE)
# =========================================
try:
    GOOGLE_CLIENT_ID = st.secrets["GOOGLE_CLIENT_ID"]
    GOOGLE_CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
    REDIRECT_URI = "https://bjjdigital.streamlit.app/"
except:
    GOOGLE_CLIENT_ID = GOOGLE_CLIENT_SECRET = REDIRECT_URI = None

oauth_google = OAuth2Component(
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    authorize_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
    token_endpoint="https://oauth2.googleapis.com/token"
)


# =========================================
# AUTENTICAÇÃO LOCAL
# =========================================
def autenticar_local(usuario_ou_email, senha):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, nome, tipo_usuario, senha FROM usuarios WHERE (nome=? OR email=?)",
        (usuario_ou_email, usuario_ou_email)
    )
    dados = cursor.fetchone()
    conn.close()

    if not dados:
        return None

    if bcrypt.checkpw(senha.encode(), dados[3].encode()):
        return {"id": dados[0], "nome": dados[1], "tipo": dados[2]}
    return None


# =========================================
# LOGIN + CADASTRO (CPF + ENDEREÇO INTEGRADO)
# =========================================
def tela_login():
    st.session_state.setdefault("modo_login", "login")

    st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"] { height: 100%; overflow-y: auto; }
        [data-testid="stAppViewContainer"] > .main {
            display: flex; flex-direction: column; justify-content: center; align-items: center;
            min-height: 95vh;
        }
    </style>
    """, unsafe_allow_html=True)

    # Logo
    if os.path.exists("assets/logo.png"):
        st.image("assets/logo.png", width=150)

    st.markdown("<h2 style='color:#FFD700;'>BJJ Digital</h2>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1.4, 1])
    with c2:
        # ============================
        # MODO LOGIN
        # ============================
        if st.session_state["modo_login"] == "login":
            with st.container(border=True):
                st.write("### Login")

                user_input = st.text_input("Usuário ou Email")
                pwd = st.text_input("Senha", type="password")

                if st.button("Entrar", use_container_width=True):
                    user = autenticar_local(user_input, pwd)
                    if user:
                        st.session_state.usuario = user
                        st.rerun()
                    else:
                        st.error("Credenciais inválidas.")

                colA, colB = st.columns(2)
                if colA.button("Criar Conta"):
                    st.session_state["modo_login"] = "cadastro"
                    st.rerun()

                if colB.button("Esqueci Senha"):
                    st.info("Funcionalidade em desenvolvimento.")

        # ============================
        # MODO CADASTRO (COM CPF + ENDEREÇO COMPLETO)
        # ============================
        elif st.session_state["modo_login"] == "cadastro":

            st.write("### Criar Conta")

            nome = st.text_input("Nome de Usuário")
            email = st.text_input("Email")
            senha = st.text_input("Senha", type="password")
            confirmar = st.text_input("Confirmar Senha", type="password")

            # CPF
            cpf_input = st.text_input("CPF (somente números)")
            cpf_limpo = limpar_cpf(cpf_input)

            # CEP + auto preenchimento
            cep_input = st.text_input("CEP")
            endereco = bairro = cidade = estado = ""

            if len(limpar_cpf(cep_input)) == 8:
                dados_cep = buscar_endereco_por_cep(cep_input)
                if dados_cep:
                    endereco = dados_cep["endereco"]
                    bairro = dados_cep["bairro"]
                    cidade = dados_cep["cidade"]
                    estado = dados_cep["estado"]
                else:
                    st.warning("CEP não encontrado.")

            endereco = st.text_input("Endereço", value=endereco)
            numero = st.text_input("Número")
            complemento = st.text_input("Complemento")
            bairro = st.text_input("Bairro", value=bairro)
            cidade = st.text_input("Cidade", value=cidade)
            estado = st.text_input("Estado", value=estado)

            tipo_usuario = st.selectbox("Tipo", ["Aluno", "Professor"])
            faixa = st.selectbox("Faixa", 
                                 ["Branca","Cinza","Amarela","Laranja","Verde","Azul","Roxa","Marrom","Preta"]
                                 if tipo_usuario=="Aluno" else ["Preta"])

            if st.button("Cadastrar", use_container_width=True):

                if not validar_cpf(cpf_limpo):
                    st.error("CPF inválido.")
                    st.stop()

                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()

                cursor.execute("SELECT id FROM usuarios WHERE cpf=?", (cpf_limpo,))
                if cursor.fetchone():
                    st.error("CPF já cadastrado.")
                    conn.close()
                    st.stop()

                if senha != confirmar:
                    st.error("As senhas não coincidem.")
                    st.stop()

                senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()

                cursor.execute(
                    """
                    INSERT INTO usuarios 
                    (nome,email,tipo_usuario,senha,auth_provider,perfil_completo,
                     cpf,cep,endereco,numero,complemento,bairro,cidade,estado)
                    VALUES (?,?,?,?,1,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        nome, email, tipo_usuario.lower(), senha_hash,
                        cpf_limpo, limpar_cpf(cep_input), endereco, numero, complemento,
                        bairro, cidade, estado
                    )
                )

                novo_id = cursor.lastrowid

                if tipo_usuario=="Aluno":
                    cursor.execute("INSERT INTO alunos (usuario_id, faixa_atual, status_vinculo) VALUES (?,?,?)",
                                   (novo_id, faixa, "pendente"))
                else:
                    cursor.execute("INSERT INTO professores (usuario_id, status_vinculo) VALUES (?,?)",
                                   (novo_id, "pendente"))

                conn.commit()
                conn.close()

                st.success("Conta criada com sucesso! Faça login.")
                st.session_state["modo_login"] = "login"
                st.rerun()


# =========================================
# ⚠ A PARTE 1 TERMINA AQUI
# =========================================
# =========================================
# MODO ROLA (quiz de rolagem)
# =========================================
def modo_rola(usuario_logado):
st.title("Modo Rola - Treinamento Técnico")
st.write("Selecione a faixa e o tema para iniciar o treino.")


conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()


cursor.execute("SELECT DISTINCT faixa FROM banco_questoes ORDER BY faixa")
faixas = [f[0] for f in cursor.fetchall()]


if not faixas:
st.warning("Nenhuma questão cadastrada.")
return


faixa_sel = st.selectbox("Faixa", faixas)


cursor.execute("SELECT DISTINCT tema FROM banco_questoes WHERE faixa=? ORDER BY tema", (faixa_sel,))
temas = [t[0] for t in cursor.fetchall()]


if not temas:
st.warning("Nenhum tema cadastrado para esta faixa.")
return


tema_sel = st.selectbox("Tema", temas)


if st.button("Iniciar Treino", use_container_width=True):
cursor.execute("SELECT pergunta, resposta FROM banco_questoes WHERE faixa=? AND tema=?", (faixa_sel, tema_sel))
questoes = cursor.fetchall()


if not questoes:
st.error("Nenhuma questão encontrada.")
return


q = random.choice(questoes)
pergunta, resposta = q


st.subheader("Pergunta:")
st.write(pergunta)


resposta_usuario = st.text_input("Sua resposta:")


if st.button("Verificar Resposta"):
if resposta_usuario.strip().lower() == resposta.strip().lower():
st.success("Acerto! Boa!")
percentual = 100
else:
st.error(f"Resposta incorreta. Correta seria: {resposta}")
percentual = 0


cursor.execute(
"INSERT INTO rola_resultados (usuario, faixa, tema, acertos, total, percentual) VALUES (?,?,?,?,?,?)",
(usuario_logado["nome"], faixa_sel, tema_sel, 1 if percentual==100 else 0, 1, percentual)
)
conn.commit()


conn.close()

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
# =========================================
# MODO ROLA (quiz de rolagem)
# =========================================
def modo_rola(usuario_logado):
st.title("Modo Rola - Treinamento Técnico")
st.write("Selecione a faixa e o tema para iniciar o treino.")


conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()


cursor.execute("SELECT DISTINCT faixa FROM banco_questoes ORDER BY faixa")
faixas = [f[0] for f in cursor.fetchall()]


if not faixas:
st.warning("Nenhuma questão cadastrada.")
return


faixa_sel = st.selectbox("Faixa", faixas)


cursor.execute("SELECT DISTINCT tema FROM banco_questoes WHERE faixa=? ORDER BY tema", (faixa_sel,))
temas = [t[0] for t in cursor.fetchall()]


if not temas:
st.warning("Nenhum tema cadastrado para esta faixa.")
return


tema_sel = st.selectbox("Tema", temas)


if st.button("Iniciar Treino", use_container_width=True):
cursor.execute("SELECT pergunta, resposta FROM banco_questoes WHERE faixa=? AND tema=?", (faixa_sel, tema_sel))
questoes = cursor.fetchall()


if not questoes:
st.error("Nenhuma questão encontrada.")
return


q = random.choice(questoes)
pergunta, resposta = q


st.subheader("Pergunta:")
st.write(pergunta)


resposta_usuario = st.text_input("Sua resposta:")


if st.button("Verificar Resposta"):
if resposta_usuario.strip().lower() == resposta.strip().lower():
st.success("Acerto! Boa!")
percentual = 100
else:
st.error(f"Resposta incorreta. Correta seria: {resposta}")
percentual = 0


cursor.execute(
"INSERT INTO rola_resultados (usuario, faixa, tema, acertos, total, percentual) VALUES (?,?,?,?,?,?)",
(usuario_logado["nome"], faixa_sel, tema_sel, 1 if percentual==100 else 0, 1, percentual)
)
conn.commit()


conn.close()
# =========================================
# 👤 TELA MEU PERFIL (com CPF e Endereço)
# =========================================
def tela_meu_perfil(usuario_logado):
st.markdown("<h1 style='color:#FFD700;'>👤 Meu Perfil</h1>", unsafe_allow_html=True)
st.markdown("Atualize suas informações pessoais, CPF e endereço.")


user_id = usuario_logado["id"]


conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT * FROM usuarios WHERE id=?", (user_id,))
user = cursor.fetchone()


if not user:
st.error("Erro ao carregar perfil.")
return


with st.form("perfil_form"):
st.subheader("Informações pessoais")
nome = st.text_input("Nome:", value=user["nome"])
email = st.text_input("Email:", value=user["email"])


st.subheader("CPF")
cpf_digitado = st.text_input("CPF:", value=user["cpf"] or "")


st.subheader("Endereço")
cep = st.text_input("CEP:", value=user["cep"] or "")
numero = st.text_input("Número:", value=user["numero"] or "")
complemento = st.text_input("Complemento:", value=user["complemento"] or "")
endereco = st.text_input("Endereço:", value=user["endereco"] or "")
bairro = st.text_input("Bairro:", value=user["bairro"] or "")
cidade = st.text_input("Cidade:", value=user["cidade"] or "")
estado = st.text_input("Estado:", value=user["estado"] or "")


submit = st.form_submit_button("Salvar alterações")


if submit:
cpf_limpo = limpar_cpf(cpf_digitado)
if not validar_cpf(cpf_limpo):
st.error("CPF inválido.")
return


cursor.execute("SELECT id FROM usuarios WHERE cpf=? AND id<>?", (cpf_limpo, user_id))
if cursor.fetchone():
st.error("Este CPF já está cadastrado.")
return


cursor.execute(
"""
UPDATE usuarios
SET nome=?, email=?, cpf=?, cep=?, endereco=?, numero=?, complemento=?, bairro=?, cidade=?, estado=?
WHERE id=?
""",
(nome, email, cpf_limpo, cep, endereco, numero, complemento, bairro, cidade, estado, user_id)
)
conn.commit()
conn.close()
st.success("Perfil atualizado!")
st.session_state.usuario["nome"] = nome
st.rerun()


# =========================================
# 🔑 GESTÃO DE USUÁRIOS (ADMIN) — com CPF e Endereço
# =========================================
def gestao_usuarios(usuario):
if usuario["tipo"] != "admin":
st.error("Acesso negado.")
return


st.markdown("<h1 style='color:#FFD700;'>🔑 Gestão de Usuários</h1>", unsafe_allow_html=True)


conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query("SELECT * FROM usuarios", conn)


st.dataframe(df, use_container_width=True)


user_selected = st.selectbox("Selecionar usuário:", df["nome"].tolist())
tela_login()
