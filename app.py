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
st.set_page_config(page_title="BJJ Digital", page_icon="🥋", layout="wide")

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

def criar_banco_geral():
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

    cursor.execute('''CREATE TABLE IF NOT EXISTS alunos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        faixa_atual TEXT,
        turma TEXT,
        professor TEXT,
        observacoes TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS questoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        faixa TEXT,
        tema TEXT,
        pergunta TEXT,
        opcoes_json TEXT,
        resposta TEXT,
        autor TEXT,
        midia_tipo TEXT CHECK(midia_tipo IN ('imagem', 'video', 'nenhum')) DEFAULT 'nenhum',
        midia_caminho TEXT,
        status TEXT CHECK(status IN ('aprovada', 'pendente', 'rejeitada')) DEFAULT 'pendente',
        data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # NOVAS TABELAS DE USUÁRIOS E EQUIPES
    cursor.execute('''CREATE TABLE IF NOT EXISTS equipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE NOT NULL,
        professor_responsavel TEXT NOT NULL,
        data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        data_nasc DATE,
        email TEXT UNIQUE NOT NULL,
        equipe TEXT,
        professor_responsavel TEXT,
        tipo_usuario TEXT CHECK(tipo_usuario IN ('admin', 'professor', 'aluno')),
        senha TEXT,
        data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()
    conn.close()

criar_banco_geral()


# =========================================
# FUNÇÕES AUXILIARES
# =========================================
def hash_senha(senha):
    return bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def gerar_qrcode(codigo):
    os.makedirs("certificados/qrcodes", exist_ok=True)
    caminho_qr = os.path.abspath(f"certificados/qrcodes/{codigo}.png")
    url_verificacao = f"https://bjjdigital.netlify.app/verificar?codigo={codigo}"
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=8, border=2)
    qr.add_data(url_verificacao)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img.save(caminho_qr)
    return caminho_qr


# =========================================
# CERTIFICADO
# =========================================
def gerar_pdf(usuario, faixa, pontuacao, total, codigo, professor=None):
    pdf = FPDF("L", "mm", "A4")
    pdf.set_auto_page_break(False)
    pdf.add_page()
    dourado, preto, branco = (218,165,32), (40,40,40), (255,255,255)
    percentual = int((pontuacao / total) * 100)
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")

    pdf.set_fill_color(*branco)
    pdf.rect(0,0,297,210,"F")
    pdf.set_draw_color(*dourado)
    pdf.set_line_width(2)
    pdf.rect(8,8,281,194)
    pdf.set_line_width(0.8)
    pdf.rect(11,11,275,188)
    pdf.set_text_color(*dourado)
    pdf.set_font("Helvetica","BI",30)
    pdf.set_y(25)
    pdf.cell(0,10,"CERTIFICADO DE EXAME TEÓRICO DE FAIXA",align="C")
    pdf.set_draw_color(*dourado)
    pdf.line(30,35,268,35)

    logo_path = "assets/logo.png"
    if os.path.exists(logo_path): pdf.image(logo_path,x=133,y=40,w=32)

    pdf.set_text_color(*preto)
    pdf.set_font("Helvetica","",16)
    pdf.set_y(80)
    pdf.cell(0,10,"Certificamos que o(a) aluno(a)",align="C")

    pdf.set_text_color(*dourado)
    pdf.set_font("Helvetica","B",24)
    pdf.set_y(92)
    pdf.cell(0,10,usuario.upper(),align="C")

    cores_faixa = {
        "Cinza":(169,169,169),"Amarela":(255,215,0),"Laranja":(255,140,0),
        "Verde":(0,128,0),"Azul":(30,144,255),"Roxa":(128,0,128),
        "Marrom":(139,69,19),"Preta":(0,0,0)
    }
    cor_faixa = cores_faixa.get(faixa,preto)

    pdf.set_text_color(*preto)
    pdf.set_font("Helvetica","",16)
    pdf.set_y(108)
    pdf.cell(0,8,"concluiu o exame teórico para a faixa",align="C")

    pdf.set_text_color(*cor_faixa)
    pdf.set_font("Helvetica","B",20)
    pdf.set_y(118)
    pdf.cell(0,8,faixa.upper(),align="C")

    pdf.set_text_color(*dourado)
    pdf.set_font("Helvetica","B",22)
    pdf.set_y(132)
    pdf.cell(0,8,"APROVADO",align="C")

    pdf.set_text_color(*preto)
    pdf.set_font("Helvetica","",14)
    texto_final = f"obtendo {percentual}% de aproveitamento, realizado em {data_hora}."
    pdf.set_y(142)
    pdf.cell(0,6,texto_final,align="C")

    selo_path="assets/selo_dourado.png"
    if os.path.exists(selo_path): pdf.image(selo_path,x=23,y=155,w=30)
    
    caminho_qr=gerar_qrcode(codigo)
    pdf.image(caminho_qr,x=245,y=155,w=25)
    
    pdf.set_text_color(*preto)
    pdf.set_font("Helvetica","I",8)
    pdf.set_xy(220,180)
    pdf.cell(60,6,f"Código: {codigo}",align="R")
    
    if professor:
        assinatura_path=f"assets/assinaturas/{professor.lower().replace(' ','_')}.png"
        if os.path.exists(assinatura_path): pdf.image(assinatura_path,x=118,y=160,w=60)
            
    pdf.set_text_color(*preto)
    pdf.set_font("Helvetica","",10)
    pdf.set_y(175)
    pdf.cell(0,6,"Assinatura do Professor Responsável",align="C")
    
    pdf.set_draw_color(*dourado)
    pdf.line(100,173,197,173)
    pdf.line(30,190,268,190)
    
    pdf.set_text_color(*dourado)
    pdf.set_font("Helvetica","I",9)
    pdf.set_y(190)
    pdf.cell(0,6,"Plataforma BJJ Digital",align="C")
    
    os.makedirs("relatorios",exist_ok=True)
    caminho_pdf=os.path.abspath(f"relatorios/Certificado_{usuario}_{faixa}.pdf")
    pdf.output(caminho_pdf)
    
    return caminho_pdf


# =========================================
# PAINEL ADMIN DE USUÁRIOS E EQUIPES
# =========================================
def painel_usuarios_admin(usuario_logado_tipo="admin"):
    st.markdown("<h1 style='color:#FFD700;'>👑 Gerenciamento de Usuários (Admin)</h1>", unsafe_allow_html=True)
    if usuario_logado_tipo != "admin":
        st.warning("Acesso restrito a administradores.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    aba1, aba2, aba3 = st.tabs(["➕ Cadastrar Usuário", "📋 Usuários", "🏫 Equipes"])

    # 1️⃣ Cadastrar Usuário
    with aba1:
        with st.form("novo_usuario"):
            nome = st.text_input("Nome completo:")
            data_nasc = st.date_input("Data de nascimento:")
            email = st.text_input("E-mail:")
            tipo = st.selectbox("Tipo de usuário:", ["aluno","professor","admin"])
            equipe, prof_resp = None, None
            equipes_df = pd.read_sql_query("SELECT nome FROM equipes", conn)
            if tipo in ["professor","aluno"]:
                if not equipes_df.empty:
                    equipe = st.selectbox("Equipe:", equipes_df["nome"].tolist())
                else:
                    st.info("Nenhuma equipe cadastrada.")
            if tipo == "aluno":
                profs = pd.read_sql_query("SELECT nome FROM usuarios WHERE tipo_usuario='professor'", conn)
                if not profs.empty:
                    prof_resp = st.selectbox("Professor responsável:", profs["nome"].tolist())
            senha = st.text_input("Senha (deixe em branco se OAuth):", type="password")
            enviar = st.form_submit_button("💾 Cadastrar")
            if enviar:
                senha_hash = hash_senha(senha) if senha else None
                try:
                    cursor.execute("""
                        INSERT INTO usuarios (nome, data_nasc, email, equipe, professor_responsavel, tipo_usuario, senha)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (nome, data_nasc, email, equipe, prof_resp, tipo, senha_hash))
                    conn.commit()
                    st.success(f"Usuário {nome} ({tipo}) cadastrado com sucesso!")
                except sqlite3.IntegrityError:
                    st.error("E-mail já cadastrado.")

    # 2️⃣ Listar Usuários
    with aba2:
        df = pd.read_sql_query("SELECT id, nome, email, tipo_usuario, equipe, professor_responsavel, data_criacao FROM usuarios ORDER BY nome", conn)
        if df.empty: st.info("Nenhum usuário cadastrado.")
        else:
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("📤 Exportar CSV", csv, "usuarios.csv", "text/csv")

    # 3️⃣ Gerenciar Equipes
    with aba3:
        with st.form("nova_equipe"):
            nome_equipe = st.text_input("Nome da equipe:")
            prof_resp = st.text_input("Professor responsável:")
            cadastrar = st.form_submit_button("💾 Cadastrar Equipe")
            if cadastrar:
                try:
                    cursor.execute("INSERT INTO equipes (nome, professor_responsavel) VALUES (?,?)",(nome_equipe,prof_resp))
                    conn.commit()
                    st.success("Equipe cadastrada com sucesso!")
                except sqlite3.IntegrityError:
                    st.error("Equipe já existe.")
        equipes_df = pd.read_sql_query("SELECT id, nome, professor_responsavel, data_criacao FROM equipes", conn)
        st.dataframe(equipes_df, use_container_width=True)
    conn.close()


# =========================================
# MENU PRINCIPAL
# =========================================
def main():
    st.sidebar.image("assets/logo.png", use_container_width=True)
    st.sidebar.markdown("<h3 style='color:#FFD700;'>Plataforma BJJ Digital</h3>", unsafe_allow_html=True)
    menu = st.sidebar.radio("Navegar:", [
        "🏁 Exame de Faixa",
        "👩‍🏫 Painel do Professor",
        "🧩 Banco de Questões (Professor)",
        "🏛️ Aprovação de Questões (Admin)",
        "👑 Gerenciamento de Usuários (Admin)"
    ])
    if menu == "👑 Gerenciamento de Usuários (Admin)":
        painel_usuarios_admin(usuario_logado_tipo="admin")
    else:
        st.info("Outros módulos mantidos — funcionalidade completa em versão estável 1.8.")

if __name__ == "__main__":
    main()
