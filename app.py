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
import math
import time

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

    conn.commit()
    conn.close()

try:
    criar_banco()
except Exception as e:
    st.error(f"Erro ao criar o banco de dados: {e}")

# =========================================
# FUNÇÕES AUXILIARES
# =========================================
def carregar_questoes(tema):
    path = f"questions/{tema}.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def gerar_codigo_unico():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM resultados")
    total = cursor.fetchone()[0] + 1
    conn.close()
    ano = datetime.now().year
    return f"BJJDIGITAL-{ano}-{total:05d}"

def salvar_resultado(usuario, modo, tema, faixa, pontuacao, tempo, codigo):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO resultados (usuario, modo, tema, faixa, pontuacao, tempo, codigo_verificacao)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (usuario, modo, tema, faixa, pontuacao, tempo, codigo))
    conn.commit()
    conn.close()

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

def normalizar_nome(nome):
    nfkd = unicodedata.normalize("NFKD", nome)
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower().replace(" ", "_")

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
    pdf.set_xy(0,25)
    pdf.cell(297,10,"CERTIFICADO DE EXAME TEÓRICO DE FAIXA",align="C")
    pdf.set_draw_color(*dourado)
    pdf.line(30,35,268,35)
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        pdf.image(logo_path,x=133,y=40,w=32)
    pdf.set_text_color(*preto)
pdf.set_font("Helvetica", "", 16)
pdf.cell(0, 10, "Certificamos que o(a) aluno(a)", align="C")
pdf.ln(15) # Adiciona 15mm de espaço vertical

# --- Bloco 2: Nome do Aluno (Destaque Principal) ---
pdf.set_text_color(*dourado)
pdf.set_font("Helvetica", "B", 24) # Fonte maior para o nome
pdf.cell(0, 10, usuario.upper(), align="C")
pdf.ln(20) # Mais espaço após o nome

# --- Bloco 3: "Concluiu o exame..." ---
pdf.set_text_color(*preto)
pdf.set_font("Helvetica", "", 16) # Fonte menor que o nome (era 20)
pdf.cell(0, 8, "concluiu o exame teórico para a faixa", align="C")
pdf.ln(12) # Espaço

# --- Bloco 4: Faixa (com cor) ---
cores_faixa = {
    "Cinza": (169, 169, 169), "Amarela": (255, 215, 0), "Laranja": (255, 140, 0),
    "Verde": (0, 128, 0), "Azul": (30, 144, 255), "Roxa": (128, 0, 128),
    "Marrom": (139, 69, 19), "Preta": (0, 0, 0)
}
cor_faixa = cores_faixa.get(faixa, preto)
pdf.set_text_color(*cor_faixa)
pdf.set_font("Helvetica", "B", 20) # Fonte maior para a faixa (era 16)
pdf.cell(0, 8, faixa.upper(), align="C")
pdf.ln(25) # Espaço maior antes do status

# --- Bloco 5: Status "APROVADO" (Destaque Secundário) ---
pdf.set_text_color(*dourado)
pdf.set_font("Helvetica", "B", 22) # Fonte grande para o status (era 16)
pdf.cell(0, 8, "APROVADO", align="C")
    selo_path="assets/selo_dourado.png"
    if os.path.exists(selo_path):
        pdf.image(selo_path,x=23,y=155,w=30)
    caminho_qr=gerar_qrcode(codigo)
    pdf.image(caminho_qr,x=245,y=155,w=25)
    pdf.set_text_color(*preto)
    pdf.set_font("Helvetica","I",8)
    pdf.set_xy(220,180)
    pdf.cell(60,6,f"Código: {codigo}",align="R")
    if professor:
        assinatura_path=f"assets/assinaturas/{normalizar_nome(professor)}.png"
        if os.path.exists(assinatura_path):
            pdf.image(assinatura_path,x=118,y=160,w=60)
    pdf.set_text_color(*preto)
    pdf.set_font("Helvetica","",10)
    pdf.set_xy(0,175)
    pdf.cell(297,6,"Assinatura do Professor Responsável",align="C")
    pdf.set_draw_color(*dourado)
    pdf.line(100,173,197,173)
    pdf.line(30,190,268,190)
    pdf.set_text_color(*dourado)
    pdf.set_font("Helvetica","I",9)
    pdf.set_xy(0,190)
    pdf.cell(297,6,"Plataforma BJJ Digital",align="C")
    os.makedirs("relatorios",exist_ok=True)
    caminho_pdf=os.path.abspath(f"relatorios/Certificado_{usuario}_{faixa}.pdf")
    pdf.output(caminho_pdf)
    return caminho_pdf
# =========================================
# MODO EXAME DE FAIXA (ATUALIZADO)
# =========================================
def modo_exame():
    st.markdown("<h1 style='color:#FFD700;'>🏁 Exame de Faixa</h1>", unsafe_allow_html=True)
    faixas=["Cinza","Amarela","Laranja","Verde","Azul","Roxa","Marrom","Preta"]
    faixa=st.selectbox("Selecione a faixa:",faixas)
    usuario=st.text_input("Nome do aluno:")
    professor=st.text_input("Nome do professor responsável:")
    tema="regras"

    if "exame_iniciado" not in st.session_state:
        st.session_state.exame_iniciado=False
        st.session_state.respostas={}
        st.session_state.certificado_path=None

    if not st.session_state.exame_iniciado:
        if st.button("Iniciar Exame"):
            questoes=carregar_questoes(tema)
            if not questoes:
                st.error("Nenhuma questão encontrada para o tema selecionado.")
                return
            random.shuffle(questoes)
            st.session_state.questoes=questoes[:5]
            st.session_state.exame_iniciado=True
            st.rerun()

    if st.session_state.exame_iniciado:
        questoes=st.session_state.questoes
        total=len(questoes)
        for i,q in enumerate(questoes,1):
            st.markdown(f"### {i}. {q['pergunta']}")
            if q.get("imagem"):
                st.image(q["imagem"],use_container_width=True)
            if q.get("video"):
                st.video(q["video"])
            resp=st.radio("Escolha:",q["opcoes"],key=f"resp_{i}",index=None)
            st.session_state.respostas[f"resp_{i}"]=resp

        if st.button("Finalizar Exame"):
            pontuacao=sum(1 for i,q in enumerate(questoes,1)
                          if st.session_state.respostas.get(f"resp_{i}","").startswith(q["resposta"]))
            codigo=gerar_codigo_unico()
            salvar_resultado(usuario,"Exame",tema,faixa,pontuacao,"00:05:00",codigo)
            caminho_pdf=gerar_pdf(usuario,faixa,pontuacao,total,codigo,professor)
            st.session_state.certificado_path=caminho_pdf
            st.rerun()

    if st.session_state.get("certificado_path"):
        caminho_pdf=st.session_state.certificado_path
        with open(caminho_pdf,"rb") as f:
            st.download_button("📄 Baixar Certificado",f,
                               file_name=os.path.basename(caminho_pdf),
                               mime="application/pdf")
# =========================================
# FINALIZAR EXAME (VERSÃO FIXA)
# =========================================
def finalizar_exame(usuario, faixa, professor, tema):
    questoes = st.session_state.questoes
    total = len(questoes)

    pontuacao = sum(
        1 for i, q in enumerate(questoes, 1)
        if st.session_state.respostas.get(f"resp_{i}", "").startswith(q["resposta"])
    )
    percentual = int((pontuacao / total) * 100)
    aprovado = pontuacao >= (total * 0.6)
    status = "APROVADO" if aprovado else "REPROVADO"

    codigo = gerar_codigo_unico()
    salvar_resultado(usuario, "Exame", tema, faixa, pontuacao, "00:05:00", codigo)
    caminho_pdf = gerar_pdf(usuario, faixa, pontuacao, total, codigo, professor)
    st.session_state.certificado_path = caminho_pdf
    st.session_state.exame_finalizado = True
    st.session_state.exame_iniciado = False

    if aprovado:
        st.success(f"🎉 Parabéns, {usuario}! Você foi **{status}** e obteve {percentual}% de acertos!")
        with open(caminho_pdf, "rb") as f:
            st.download_button(
                label="📄 Baixar Certificado",
                data=f,
                file_name=os.path.basename(caminho_pdf),
                mime="application/pdf",
                use_container_width=True
            )
    else:
        st.error(f"❌ {usuario}, você **não obteve o percentual mínimo de acerto para aprovação** ({percentual}%). "
                 f"Tente novamente em 3 dias e continue se preparando!")
# =========================================
# PAINEL DO PROFESSOR
# =========================================
def painel_professor():
    st.markdown("<h1 style='color:#FFD700;'>👩‍🏫 Painel do Professor</h1>", unsafe_allow_html=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    aba1, aba2 = st.tabs(["➕ Cadastrar Aluno", "📋 Alunos Cadastrados"])

    with aba1:
        with st.form("cadastro_aluno"):
            nome = st.text_input("Nome completo do aluno:")
            faixa = st.selectbox("Faixa atual:", ["Branca","Cinza","Amarela","Laranja","Verde","Azul","Roxa","Marrom","Preta"])
            turma = st.text_input("Turma:")
            professor = st.text_input("Professor responsável:")
            observacoes = st.text_area("Observações (opcional):")
            submitted = st.form_submit_button("💾 Salvar Aluno")
            if submitted and nome.strip():
                cursor.execute("""
                    INSERT INTO alunos (nome, faixa_atual, turma, professor, observacoes)
                    VALUES (?, ?, ?, ?, ?)
                """, (nome, faixa, turma, professor, observacoes))
                conn.commit()
                st.success(f"Aluno(a) **{nome}** cadastrado(a) com sucesso!")

    with aba2:
        df = pd.read_sql_query("SELECT * FROM alunos ORDER BY nome ASC", conn)
        if df.empty: st.info("Nenhum aluno cadastrado.")
        else:
            st.dataframe(df,use_container_width=True)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("📤 Exportar CSV", csv, "alunos.csv", "text/csv")
    conn.close()

# =========================================
# BANCO DE QUESTÕES
# =========================================
def banco_questoes_professor():
    st.markdown("<h1 style='color:#FFD700;'>🧩 Banco de Questões (Professor)</h1>", unsafe_allow_html=True)
    conn=sqlite3.connect(DB_PATH)
    cursor=conn.cursor()
    aba1,aba2=st.tabs(["➕ Criar Nova Questão","📚 Minhas Questões"])
    with aba1:
        with st.form("nova_questao"):
            faixa=st.selectbox("Faixa:",["Cinza","Amarela","Laranja","Verde","Azul","Roxa","Marrom","Preta"])
            tema=st.text_input("Tema:")
            pergunta=st.text_area("Pergunta:")
            autor=st.text_input("Professor (autor):")
            midia_tipo=st.radio("Deseja adicionar mídia?",["Nenhum","Imagem","Vídeo"])
            midia_caminho=None
            if midia_tipo=="Imagem":
                imagem=st.file_uploader("Envie uma imagem:",type=["jpg","jpeg","png"])
                if imagem:
                    os.makedirs("questions/assets",exist_ok=True)
                    nome_arquivo=f"q_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
                    caminho_final=os.path.join("questions/assets",nome_arquivo)
                    with open(caminho_final,"wb") as f: f.write(imagem.read())
                    midia_caminho=caminho_final
                    st.image(caminho_final,use_container_width=True)
                    midia_tipo="imagem"
            elif midia_tipo=="Vídeo":
                midia_caminho=st.text_input("Cole o link do vídeo:")
                if midia_caminho: st.video(midia_caminho)
            opcoes=[st.text_input(f"Opção {i+1}:") for i in range(4)]
            resposta=st.selectbox("Resposta correta:",[o for o in opcoes if o])
            enviar=st.form_submit_button("💾 Enviar Questão")
            if enviar:
                cursor.execute("""INSERT INTO questoes
                    (faixa,tema,pergunta,opcoes_json,resposta,autor,midia_tipo,midia_caminho,status)
                    VALUES (?,?,?,?,?,?,?,?,'pendente')
                """,(faixa,tema,pergunta,json.dumps(opcoes),resposta,autor,midia_tipo.lower(),midia_caminho))
                conn.commit()
                st.success("Questão enviada para aprovação!")
    with aba2:
        df=pd.read_sql_query("SELECT id,faixa,tema,pergunta,status FROM questoes ORDER BY data_criacao DESC",conn)
        if df.empty: st.info("Nenhuma questão criada ainda.")
        else: st.dataframe(df,use_container_width=True)
    conn.close()

# =========================================
# PAINEL ADMIN
# =========================================
def painel_admin_questoes():
    st.markdown("<h1 style='color:#FFD700;'>🏛️ Aprovação de Questões</h1>", unsafe_allow_html=True)
    conn=sqlite3.connect(DB_PATH)
    cursor=conn.cursor()
    df=pd.read_sql_query("SELECT * FROM questoes WHERE status='pendente' ORDER BY data_criacao DESC",conn)
    if df.empty: st.info("Nenhuma questão pendente.")
    else:
        for _,row in df.iterrows():
            st.markdown(f"### 🧠 Questão #{row['id']} – {row['faixa']} | {row['tema']}")
            st.write(row["pergunta"])
            opcoes=json.loads(row["opcoes_json"])
            for i,op in enumerate(opcoes): st.write(f"{chr(65+i)}) {op}")
            if row["midia_tipo"]=="imagem" and row["midia_caminho"]: st.image(row["midia_caminho"])
            elif row["midia_tipo"]=="video" and row["midia_caminho"]: st.video(row["midia_caminho"])
            c1,c2=st.columns(2)
            with c1:
                if st.button(f"✅ Aprovar {row['id']}"):
                    cursor.execute("UPDATE questoes SET status='aprovada' WHERE id=?",(row["id"],))
                    conn.commit(); st.success("Aprovada!"); st.rerun()
            with c2:
                if st.button(f"❌ Rejeitar {row['id']}"):
                    cursor.execute("UPDATE questoes SET status='rejeitada' WHERE id=?",(row["id"],))
                    conn.commit(); st.warning("Rejeitada."); st.rerun()
    conn.close()

# =========================================
# MENU PRINCIPAL
# =========================================
def main():
    st.sidebar.image("assets/logo.png", use_container_width=True)
    st.sidebar.markdown("<h3 style='color:#FFD700;'>Plataforma BJJ Digital</h3>", unsafe_allow_html=True)
    menu=st.sidebar.radio("Navegar:",[
        "🏁 Exame de Faixa",
        "👩‍🏫 Painel do Professor",
        "🧩 Banco de Questões (Professor)",
        "🏛️ Aprovação de Questões (Admin)"
    ])
    if menu=="🏁 Exame de Faixa": modo_exame()
    elif menu=="👩‍🏫 Painel do Professor": painel_professor()
    elif menu=="🧩 Banco de Questões (Professor)": banco_questoes_professor()
    elif menu=="🏛️ Aprovação de Questões (Admin)": painel_admin_questoes()

if __name__=="__main__":
    main()
