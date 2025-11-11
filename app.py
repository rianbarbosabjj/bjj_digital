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

    # Resultados
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

    # Alunos
    cursor.execute('''CREATE TABLE IF NOT EXISTS alunos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        faixa_atual TEXT,
        turma TEXT,
        professor TEXT,
        observacoes TEXT
    )''')

    # Questões
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

    # Usuários
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        senha TEXT NOT NULL,
        perfil TEXT CHECK(perfil IN ('admin','professor','aluno')) NOT NULL,
        ativo INTEGER DEFAULT 1,
        data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # Cria admin padrão
    cursor.execute("SELECT * FROM usuarios WHERE email = 'admin@bjjdigital.com'")
    if not cursor.fetchone():
        senha_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute("""
            INSERT INTO usuarios (nome,email,senha,perfil)
            VALUES (?,?,?,?)
        """, ("Administrador", "admin@bjjdigital.com", senha_hash, "admin"))
        conn.commit()

    conn.close()

try:
    criar_banco()
except Exception as e:
    st.error(f"Erro ao criar o banco: {e}")

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
    url = f"https://bjjdigital.netlify.app/verificar?codigo={codigo}"
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img.save(caminho_qr)
    return caminho_qr

def normalizar_nome(nome):
    nfkd = unicodedata.normalize("NFKD", nome)
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower().replace(" ", "_")

# =========================================
# GERAÇÃO DE CERTIFICADO
# =========================================
def gerar_pdf(usuario, faixa, pontuacao, total, codigo, professor=None):
    pdf = FPDF("L", "mm", "A4")
    pdf.add_page()
    dourado, preto, branco = (218,165,32),(40,40,40),(255,255,255)
    percentual = int((pontuacao/total)*100)
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

    pdf.set_text_color(*preto)
    pdf.set_font("Helvetica","",16)
    pdf.set_y(80)
    pdf.cell(0,10,"Certificamos que o(a) aluno(a)",align="C")

    pdf.set_text_color(*dourado)
    pdf.set_font("Helvetica","B",24)
    pdf.set_y(92)
    pdf.cell(0,10,usuario.upper(),align="C")

    cores = {"Cinza":(169,169,169),"Amarela":(255,215,0),"Laranja":(255,140,0),
             "Verde":(0,128,0),"Azul":(30,144,255),"Roxa":(128,0,128),
             "Marrom":(139,69,19),"Preta":(0,0,0)}
    cor_faixa = cores.get(faixa,preto)
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
    texto = f"obtendo {percentual}% de aproveitamento, realizado em {data_hora}."
    pdf.set_y(142)
    pdf.cell(0,6,texto,align="C")

    selo="assets/selo_dourado.png"
    if os.path.exists(selo): pdf.image(selo,x=23,y=155,w=30)
    qr_path=gerar_qrcode(codigo)
    pdf.image(qr_path,x=245,y=155,w=25)
    pdf.set_font("Helvetica","I",8)
    pdf.set_xy(220,180)
    pdf.cell(60,6,f"Código: {codigo}",align="R")

    if professor:
        assinatura=f"assets/assinaturas/{normalizar_nome(professor)}.png"
        if os.path.exists(assinatura): pdf.image(assinatura,x=118,y=160,w=60)

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
    caminho=f"relatorios/Certificado_{usuario}_{faixa}.pdf"
    pdf.output(caminho)
    return caminho

# =========================================
# MODO EXAME COM TEMPORIZADOR
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
        st.session_state.tempo_inicio=None
        st.session_state.tempo_total=None
        st.session_state.certificado_path=None
        st.session_state.exame_finalizado=False

    # Início
    if not st.session_state.exame_iniciado and not st.session_state.exame_finalizado:
        st.markdown("### 🧩 Instruções: 5 questões, 3 minutos por questão (tempo total: 15 minutos).")
        if st.button("🎯 Iniciar Exame"):
            questoes=carregar_questoes(tema)
            if not questoes:
                st.error("Nenhuma questão encontrada.")
                return
            random.shuffle(questoes)
            st.session_state.questoes=questoes[:5]
            st.session_state.exame_iniciado=True
            st.session_state.exame_finalizado=False
            st.session_state.respostas={}
            st.session_state.tempo_inicio=time.time()
            st.session_state.tempo_total=len(st.session_state.questoes)*180
            st.rerun()
        return

    # Durante o exame
    tempo_decorrido=int(time.time()-st.session_state.tempo_inicio)
    tempo_restante=st.session_state.tempo_total-tempo_decorrido
    if tempo_restante<=0:
        st.warning("⏰ Tempo encerrado! Exame finalizado automaticamente.")
        finalizar_exame(usuario,faixa,professor,tema)
        return

    minutos,segundos=divmod(tempo_restante,60)
    st.markdown(f"### ⏰ Tempo restante: {minutos:02d}:{segundos:02d}")
    progresso=tempo_restante/st.session_state.tempo_total
    st.progress(progresso)

    questoes=st.session_state.questoes
    for i,q in enumerate(questoes,1):
        st.markdown(f"### {i}. {q['pergunta']}")
        if q.get("imagem"): st.image(q["imagem"],use_container_width=True)
        if q.get("video"): st.video(q["video"])
        resp=st.radio("Escolha:",q["opcoes"],key=f"resp_{i}",index=None)
        st.session_state.respostas[f"resp_{i}"]=resp

    if st.button("✅ Finalizar Exame"):
        finalizar_exame(usuario,faixa,professor,tema)
        return

    time.sleep(1)
    st.rerun()

# =========================================
# FINALIZAR EXAME
# =========================================
def finalizar_exame(usuario,faixa,professor,tema):
    questoes=st.session_state.questoes
    total=len(questoes)
    pontuacao=sum(1 for i,q in enumerate(questoes,1)
                  if st.session_state.respostas.get(f"resp_{i}","").startswith(q["resposta"]))
    percentual=int((pontuacao/total)*100)
    aprovado=pontuacao>=(total*0.6)
    status="APROVADO" if aprovado else "REPROVADO"
    codigo=gerar_codigo_unico()
    salvar_resultado(usuario,"Exame",tema,faixa,pontuacao,"00:05:00",codigo)
    caminho=gerar_pdf(usuario,faixa,pontuacao,total,codigo,professor)
    st.session_state.certificado_path=caminho
    st.session_state.exame_finalizado=True
    st.session_state.exame_iniciado=False

    if aprovado:
        st.success(f"🎉 Parabéns, {usuario}! Você foi **{status}** e obteve {percentual}% de acertos!")
        with open(caminho,"rb") as f:
            st.download_button("📄 Baixar Certificado",f,
                file_name=os.path.basename(caminho),mime="application/pdf",use_container_width=True)
    else:
        st.error(f"❌ {usuario}, você **não atingiu o percentual mínimo de acerto ({percentual}%)**. "
                 f"Tente novamente em 3 dias e continue se preparando!")

# =========================================
# PAINÉIS
# =========================================
def painel_professor():
    st.header("👩‍🏫 Painel do Professor")
    st.info("Gerencie seus alunos e turmas.")
    conn=sqlite3.connect(DB_PATH)
    cursor=conn.cursor()
    aba1,aba2=st.tabs(["➕ Cadastrar Aluno","📋 Alunos"])
    with aba1:
        with st.form("cadastro"):
            nome=st.text_input("Nome do aluno:")
            faixa=st.selectbox("Faixa atual:",["Branca","Cinza","Amarela","Laranja","Verde","Azul","Roxa","Marrom","Preta"])
            turma=st.text_input("Turma:")
            prof=st.text_input("Professor responsável:")
            obs=st.text_area("Observações:")
            sub=st.form_submit_button("Salvar")
            if sub and nome:
                cursor.execute("INSERT INTO alunos (nome,faixa_atual,turma,professor,observacoes) VALUES (?,?,?,?,?)",
                               (nome,faixa,turma,prof,obs))
                conn.commit()
                st.success(f"Aluno(a) {nome} cadastrado(a)!")
    with aba2:
        df=pd.read_sql_query("SELECT * FROM alunos ORDER BY nome",conn)
        if df.empty: st.info("Nenhum aluno cadastrado.")
        else: st.dataframe(df,use_container_width=True)
    conn.close()

def painel_admin_questoes():
    st.header("🏛️ Aprovação de Questões")
    conn=sqlite3.connect(DB_PATH)
    cursor=conn.cursor()
    df=pd.read_sql_query("SELECT * FROM questoes WHERE status='pendente' ORDER BY data_criacao DESC",conn)
    if df.empty:
        st.info("Nenhuma questão pendente.")
    else:
        for _,row in df.iterrows():
            st.markdown(f"### 🧠 Questão #{row['id']} – {row['faixa']} | {row['tema']}")
            st.write(row["pergunta"])
            for i,op in enumerate(json.loads(row["opcoes_json"])): st.write(f"{chr(65+i)}) {op}")
            if row["midia_tipo"]=="imagem": st.image(row["midia_caminho"])
            elif row["midia_tipo"]=="video": st.video(row["midia_caminho"])
            c1,c2=st.columns(2)
            with c1:
                if st.button(f"✅ Aprovar {row['id']}"):
                    cursor.execute("UPDATE questoes SET status='aprovada' WHERE id=?",(row["id"],))
                    conn.commit(); st.rerun()
            with c2:
                if st.button(f"❌ Rejeitar {row['id']}"):
                    cursor.execute("UPDATE questoes SET status='rejeitada' WHERE id=?",(row["id"],))
                    conn.commit(); st.rerun()
    conn.close()

# =========================================
# LOGIN
# =========================================
def autenticar_usuario(email,senha):
    conn=sqlite3.connect(DB_PATH)
    c=conn.cursor()
    c.execute("SELECT nome,senha,perfil FROM usuarios WHERE email=? AND ativo=1",(email,))
    user=c.fetchone()
    conn.close()
    if user and bcrypt.checkpw(senha.encode('utf-8'),user[1].encode('utf-8')):
        return {"nome":user[0],"perfil":user[2],"email":email}
    return None

def login_page():
    st.markdown("<h1 style='color:#FFD700;'>🔐 Login - BJJ Digital</h1>", unsafe_allow_html=True)
    email=st.text_input("Email:")
    senha=st.text_input("Senha:",type="password")
    if st.button("Entrar"):
        user=autenticar_usuario(email,senha)
        if user:
            st.session_state["usuario_logado"]=user
            st.rerun()
        else:
            st.error("Email ou senha incorretos.")
    st.markdown("<small>Admin padrão: admin@bjjdigital.com / admin123</small>", unsafe_allow_html=True)

def logout_button():
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sair"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# =========================================
# MENU PRINCIPAL
# =========================================
def main():
    user=st.session_state.get("usuario_logado")
    if not user:
        login_page()
        return
    st.sidebar.image("assets/logo.png",use_container_width=True)
    st.sidebar.markdown(f"👋 {user['nome']} ({user['perfil'].capitalize()})")
    logout_button()
    menu=[]
    if user["perfil"]=="admin":
        menu=["🏁 Exame de Faixa","👩‍🏫 Painel do Professor","🏛️ Aprovação de Questões"]
    elif user["perfil"]=="professor":
        menu=["🏁 Exame de Faixa","👩‍🏫 Painel do Professor"]
    elif user["perfil"]=="aluno":
        menu=["🏁 Exame de Faixa"]
    escolha=st.sidebar.radio("Navegar:",menu)
    if escolha=="🏁 Exame de Faixa": modo_exame()
    elif escolha=="👩‍🏫 Painel do Professor": painel_professor()
    elif escolha=="🏛️ Aprovação de Questões": painel_admin_questoes()

# =========================================
# EXECUÇÃO
# =========================================
if __name__=="__main__":
    main()
