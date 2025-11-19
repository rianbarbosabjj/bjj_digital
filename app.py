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
from datetime import datetime, date, timedelta
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

# [CSS (sem alterações)]
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;700&display=swap');

/* --- CORREÇÃO CRÍTICA: GARANTE QUE O BACKGROUND E O CONTEÚDO APAREÇAM --- */

/* Aplica cor de fundo ao corpo principal do Streamlit (resolve tela preta) */
[data-testid="stAppViewContainer"] > .main {{
    background-color: {COR_FUNDO} !important;
    color: {COR_TEXTO} !important;
    min-height: 100vh; /* Garante que a tela tenha altura total */
}}

/* Força a barra lateral a ter a mesma cor de fundo */
[data-testid="stSidebar"] {{
    background-color: #0c241e !important;
}}

/* --- ESTILOS ORIGINAIS --- */

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
# BANCO DE DADOS E MIGRAÇÃO
# =========================================
DB_PATH = os.path.expanduser("~/bjj_digital.db")

def criar_banco():
    """Cria o banco de dados e suas tabelas, caso não existam."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tabela 'usuarios' COMPLETA
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        email TEXT UNIQUE,
        cpf TEXT UNIQUE, -- NOVO: CPF, único e obrigatório para login local
        tipo_usuario TEXT,
        senha TEXT, -- Nulo para logins sociais
        auth_provider TEXT DEFAULT 'local', -- 'local', 'google', etc.
        perfil_completo BOOLEAN DEFAULT 0, -- 0 = Incompleto, 1 = Completo
        cep TEXT, -- Endereço
        logradouro TEXT, -- Endereço
        numero TEXT, -- NOVO: Número do endereço
        bairro TEXT, -- Endereço
        cidade TEXT, -- Endereço
        estado TEXT, -- Endereço
        data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
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
        exame_habilitado BOOLEAN DEFAULT 0,
        data_inicio_exame TEXT, -- NOVO: Período de exame
        data_fim_exame TEXT -- NOVO: Período de exame
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


def migrar_db():
    """Garante que todas as colunas existam nas tabelas, adicionando se necessário."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. MIGRAÇÃO DA TABELA USUARIOS
    colunas_novas_usuarios = {
        'cpf': 'TEXT UNIQUE', 'cep': 'TEXT', 'logradouro': 'TEXT', 'bairro': 'TEXT', 
        'cidade': 'TEXT', 'estado': 'TEXT', 'numero': 'TEXT'
    }
    for coluna, tipo in colunas_novas_usuarios.items():
        try:
            cursor.execute(f"SELECT {coluna} FROM usuarios LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {coluna} {tipo}")
            conn.commit()
            st.toast(f"Coluna {coluna} (usuarios) adicionada.")
            
    # 2. MIGRAÇÃO DA TABELA ALUNOS (Datas de exame)
    try:
        cursor.execute("SELECT data_inicio_exame FROM alunos LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE alunos ADD COLUMN data_inicio_exame TEXT")
        cursor.execute("ALTER TABLE alunos ADD COLUMN data_fim_exame TEXT")
        conn.commit()
        st.toast("Campos de Data de Exame adicionados à tabela 'alunos'.")
            
    conn.close()

# 5. Usuários de teste (Atualizado)
def criar_usuarios_teste():
    """Cria usuários padrão locais com perfil completo."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    usuarios = [
        ("Admin User", "admin", "admin@bjj.local", "00000000000"), 
        ("Professor User", "professor", "professor@bjj.local", "11111111111"), 
        ("Aluno User", "aluno", "aluno@bjj.local", "22222222222")
    ]
    for nome, tipo, email, cpf in usuarios:
        cursor.execute("SELECT id FROM usuarios WHERE email=? OR cpf=?", (email, cpf))
        if cursor.fetchone() is None:
            senha_hash = bcrypt.hashpw(nome.encode(), bcrypt.gensalt()).decode()
            cursor.execute(
                """
                INSERT INTO usuarios (nome, tipo_usuario, senha, email, cpf, auth_provider, perfil_completo) 
                VALUES (?, ?, ?, ?, ?, 'local', 1)
                """,
                (nome, tipo, senha_hash, email, cpf),
            )
    conn.commit()
    conn.close()

# 🔹 Lógica de inicialização do topo do script
if not os.path.exists(DB_PATH):
    st.toast("Criando novo banco de dados...")
    criar_banco()
    criar_usuarios_teste() 

# Sempre execute a migração se o DB existir
migrar_db()

# =========================================
# FUNÇÕES DE UTILIDADE E AUTENTICAÇÃO
# =========================================

def validar_cpf(cpf):
    """Verifica se o CPF tem 11 dígitos e se os dígitos verificadores são válidos."""
    # 1. Limpar e verificar o tamanho
    cpf = ''.join(filter(str.isdigit, cpf))
    if len(cpf) != 11:
        return False
    # 2. Verificar CPFs com todos os dígitos iguais
    if len(set(cpf)) == 1:
        return False
    # 3. Cálculo e validação do 1º dígito verificador
    soma = 0
    for i in range(9):
        soma += int(cpf[i]) * (10 - i)
    resto = soma % 11
    digito_1 = 0 if resto < 2 else 11 - resto
    if int(cpf[9]) != digito_1:
        return False
    # 4. Cálculo e validação do 2º dígito verificador
    soma = 0
    for i in range(10):
        soma += int(cpf[i]) * (11 - i)
    resto = soma % 11
    digito_2 = 0 if resto < 2 else 11 - resto
    if int(cpf[10]) != digito_2:
        return False
    return True

def buscar_endereco_por_cep(cep):
    """Busca endereço usando a API ViaCEP."""
    cep = ''.join(filter(str.isdigit, cep))
    if len(cep) != 8:
        return None
    url = f"https://viacep.com.br/ws/{cep}/json/"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status() 
        data = response.json()
        if data.get('erro'):
            return None
        return {
            "logradouro": data.get("logradouro", ""),
            "bairro": data.get("bairro", ""),
            "cidade": data.get("localidade", ""),
            "estado": data.get("uf", "")
        }
    except requests.exceptions.RequestException as e:
        st.error(f"Erro na comunicação com a API de CEP: {e}")
        return None
    except Exception as e:
        st.error(f"Erro desconhecido ao buscar CEP: {e}")
        return None

# 3. Autenticação local (Login/Senha)
def autenticar_local(usuario_ou_email, senha):
    """
    Atualizado: Autentica o usuário local usando EMAIL ou CPF.
    """
    conn = sqlite3.connect(DB_PATH) 
    cursor = conn.cursor()
    dados = None
    
    try:
        # Busca por 'email' OU 'cpf' (O nome completo não é mais usado para login)
        cursor.execute(
            "SELECT id, nome, tipo_usuario, senha FROM usuarios WHERE (email=? OR cpf=?) AND auth_provider='local'", 
            (usuario_ou_email, usuario_ou_email)
        )
        dados = cursor.fetchone()
        
        if dados is not None and dados[3]: # dados[3] é 'senha'
            # Se a senha existe e é válida
            if bcrypt.checkpw(senha.encode(), dados[3].encode()):
                return {"id": dados[0], "nome": dados[1], "tipo": dados[2]}
            
    except Exception as e:
        st.error(f"Erro de autenticação no DB: {e}")
        
    finally:
        conn.close() 
        
    return None

# 4. Funções de busca e criação de usuário
def buscar_usuario_por_email(email):
    """Busca um usuário pelo email e retorna seus dados."""
    conn = sqlite3.connect(DB_PATH) 
    cursor = conn.cursor()
    dados = None
    
    try:
        cursor.execute(
            "SELECT id, nome, tipo_usuario, perfil_completo FROM usuarios WHERE email=?", (email,)
        )
        dados = cursor.fetchone()
        
        if dados:
            return {
                "id": dados[0], 
                "nome": dados[1], 
                "tipo": dados[2], 
                "perfil_completo": bool(dados[3])
            }
    finally:
        conn.close()
        
    return None

def criar_usuario_parcial_google(email, nome):
    """Cria um registro inicial para um novo usuário do Google."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    novo_id = None
    
    try:
        cursor.execute(
            """
            INSERT INTO usuarios (email, nome, auth_provider, perfil_completo)
            VALUES (?, ?, 'google', 0)
            """, (email, nome)
        )
        conn.commit()
        novo_id = cursor.lastrowid
        
    except sqlite3.IntegrityError: # Email já existe
        pass
        
    finally:
        conn.close()
        
    if novo_id:
        return {"id": novo_id, "email": email, "nome": nome}
    return None

def buscar_equipes():
    """Retorna uma lista de tuplas (id, nome) de todas as equipes ativas."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    equipes = cursor.execute("SELECT id, nome FROM equipes WHERE ativo=1").fetchall()
    conn.close()
    return equipes

# --- FUNÇÕES DE GESTÃO DO PROFESSOR ---

def get_professor_team_id(usuario_id):
    """Busca o ID da equipe principal do professor ativo."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    team_id = None
    try:
        # Busca a equipe onde o professor está ativo
        cursor.execute(
            "SELECT equipe_id FROM professores WHERE usuario_id=? AND status_vinculo='ativo' LIMIT 1",
            (usuario_id,)
        )
        result = cursor.fetchone()
        if result:
            team_id = result[0]
    finally:
        conn.close()
    return team_id

def get_alunos_by_equipe(equipe_id):
    """Busca todos os alunos (e seus status de exame) de uma equipe."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    alunos = []
    try:
        cursor.execute(
            """
            SELECT 
                a.id as aluno_id, 
                u.nome as nome_aluno, 
                u.email, 
                a.faixa_atual, 
                a.status_vinculo,
                a.exame_habilitado,
                a.data_inicio_exame, 
                a.data_fim_exame 
            FROM alunos a
            JOIN usuarios u ON a.usuario_id = u.id
            WHERE a.equipe_id=?
            """,
            (equipe_id,)
        )
        alunos = cursor.fetchall()
    finally:
        conn.close()
    return alunos

def habilitar_exame_aluno(aluno_id, data_inicio_str, data_fim_str):
    """Habilita o exame e define o período na tabela alunos."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE alunos 
            SET exame_habilitado=1, data_inicio_exame=?, data_fim_exame=?
            WHERE id=?
            """,
            (data_inicio_str, data_fim_str, aluno_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao habilitar exame: {e}")
        return False
    finally:
        conn.close()


# =========================================
# FUNÇÕES DE TELA E ROTEAMENTO
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

# ------------------------------------

# 3. Autenticação local (Login/Senha)
def autenticar_local(usuario_ou_email, senha):
    """
    Atualizado: Autentica o usuário local usando EMAIL ou CPF.
    (Conexão fechada após a operação)
    """
    conn = sqlite3.connect(DB_PATH) 
    cursor = conn.cursor()
    dados = None
    
    try:
        # Busca por 'email' OU 'cpf' (O nome completo não é mais usado para login)
        cursor.execute(
            "SELECT id, nome, tipo_usuario, senha FROM usuarios WHERE (email=? OR cpf=?) AND auth_provider='local'", 
            (usuario_ou_email, usuario_ou_email)
        )
        dados = cursor.fetchone()
        
        if dados is not None and dados[3]: # dados[3] é 'senha'
            # Se a senha existe e é válida
            if bcrypt.checkpw(senha.encode(), dados[3].encode()):
                return {"id": dados[0], "nome": dados[1], "tipo": dados[2]}
            
    except Exception as e:
        st.error(f"Erro de autenticação no DB: {e}")
        
    finally:
        conn.close() 
        
    return None

# 4. Funções de busca e criação de usuário
def buscar_usuario_por_email(email):
    """Busca um usuário pelo email e retorna seus dados."""
    conn = sqlite3.connect(DB_PATH) 
    cursor = conn.cursor()
    dados = None
    
    try:
        cursor.execute(
            "SELECT id, nome, tipo_usuario, perfil_completo FROM usuarios WHERE email=?", (email,)
        )
        dados = cursor.fetchone()
        
        if dados:
            return {
                "id": dados[0], 
                "nome": dados[1], 
                "tipo": dados[2], 
                "perfil_completo": bool(dados[3])
            }
    finally:
        conn.close()
        
    return None

def criar_usuario_parcial_google(email, nome):
    """Cria um registro inicial para um novo usuário do Google."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    novo_id = None
    
    try:
        cursor.execute(
            """
            INSERT INTO usuarios (email, nome, auth_provider, perfil_completo)
            VALUES (?, ?, 'google', 0)
            """, (email, nome)
        )
        conn.commit()
        novo_id = cursor.lastrowid
        
    except sqlite3.IntegrityError: # Email já existe
        pass
        
    finally:
        conn.close()
        
    if novo_id:
        return {"id": novo_id, "email": email, "nome": nome}
    return None

def buscar_equipes():
    """Retorna uma lista de tuplas (id, nome) de todas as equipes ativas."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    equipes = cursor.execute("SELECT id, nome FROM equipes WHERE ativo=1").fetchall()
    conn.close()
    return equipes

# --- FUNÇÕES DE GESTÃO DO PROFESSOR (INCLUÍDAS) ---

def get_professor_team_id(usuario_id):
    """Busca o ID da equipe principal do professor ativo."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    team_id = None
    try:
        # Busca a equipe onde o professor está ativo
        cursor.execute(
            "SELECT equipe_id FROM professores WHERE usuario_id=? AND status_vinculo='ativo' LIMIT 1",
            (usuario_id,)
        )
        result = cursor.fetchone()
        if result:
            team_id = result[0]
    finally:
        conn.close()
    return team_id

def get_alunos_by_equipe(equipe_id):
    """Busca todos os alunos (e seus status de exame) de uma equipe."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    alunos = []
    try:
        cursor.execute(
            """
            SELECT 
                a.id as aluno_id, 
                u.nome as nome_aluno, 
                u.email, 
                a.faixa_atual, 
                a.status_vinculo,
                a.exame_habilitado,
                a.data_inicio_exame, 
                a.data_fim_exame 
            FROM alunos a
            JOIN usuarios u ON a.usuario_id = u.id
            WHERE a.equipe_id=?
            """,
            (equipe_id,)
        )
        alunos = cursor.fetchall()
    finally:
        conn.close()
    return alunos

def habilitar_exame_aluno(aluno_id, data_inicio_str, data_fim_str):
    """Habilita o exame e define o período na tabela alunos."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE alunos 
            SET exame_habilitado=1, data_inicio_exame=?, data_fim_exame=?
            WHERE id=?
            """,
            (data_inicio_str, data_fim_str, aluno_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao habilitar exame: {e}")
        return False
    finally:
        conn.close()


# =========================================
# TELAS DO APP
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

def exame_de_faixa(usuario_logado):
    st.markdown("<h1 style='color:#FFD700;'>🥋 Exame de Faixa</h1>", unsafe_allow_html=True)

    # Verifica se o aluno foi liberado para o exame
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT exame_habilitado, data_inicio_exame, data_fim_exame FROM alunos WHERE usuario_id=?", (usuario_logado["id"],))
    dado = cursor.fetchone()
    conn.close()

    # 🔒 Apenas alunos precisam de liberação
    if usuario_logado["tipo"] not in ["admin", "professor"]:
        if not dado or dado[0] == 0:
            st.warning("🚫 Seu exame de faixa ainda não foi liberado. Aguarde a autorização do professor.")
            return
        
        # Verifica o período do exame
        if dado[0] == 1:
            data_inicio = datetime.strptime(dado[1], '%Y-%m-%d').date() if dado[1] else date.min
            data_fim = datetime.strptime(dado[2], '%Y-%m-%d').date() if dado[2] else date.max
            hoje = date.today()
            
            if hoje < data_inicio:
                st.info(f"O período do seu exame começa em **{data_inicio.strftime('%d/%m/%Y')}**. Aguarde a data de início.")
                return
            if hoje > data_fim:
                st.error(f"Seu prazo para realizar o exame terminou em **{data_fim.strftime('%d/%m/%Y')}**. Contate seu professor para solicitar uma nova liberação.")
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

def painel_professor():
    st.title("🥋 Painel do Professor")
    
    # 1. ABRIR CONEXÃO ÚNICA NO INÍCIO
    conn = sqlite3.connect(DB_PATH) 
    cursor = conn.cursor()
    
    professor_id = st.session_state.usuario['id']
    usuario_tipo = st.session_state.usuario['tipo']
    
    # Busca a equipe onde o professor LOGADO é o RESPONSÁVEL
    equipe_responsavel = cursor.execute(
        "SELECT id, nome FROM equipes WHERE professor_responsavel_id=?", 
        (professor_id,)
    ).fetchone()
    
    equipe_id_responsavel = equipe_responsavel[0] if equipe_responsavel else None
    equipe_nome_responsavel = equipe_responsavel[1] if equipe_responsavel else 'N/A'
    
    if not equipe_id_responsavel and usuario_tipo != 'admin':
        st.warning("Você ainda não é o Professor Responsável por uma equipe. Esta seção não está disponível.")
        conn.close()
        return

    # --- TABS DE GESTÃO ---
    tab_alunos, tab_aprovacao = st.tabs(["Alunos da Equipe", "Solicitações Pendentes (Professores)"])

    # 1. GESTÃO DE ALUNOS (Listagem e Habilitação de Exame)
    with tab_alunos:
        equipe_id = equipe_id_responsavel if equipe_id_responsavel else 0 # Use o ID da equipe

        if equipe_id == 0:
             st.info("Você não é responsável por nenhuma equipe. Use a Gestão de Equipes para visualização completa.")
        else:
            st.header(f"Lista de Alunos da Equipe: {equipe_nome_responsavel}")
            
            dados_alunos = get_alunos_by_equipe(equipe_id)
            df_alunos = pd.DataFrame(dados_alunos)
            
            if df_alunos.empty:
                st.info("Nenhum aluno ativo ou pendente encontrado para sua equipe.")
            else:
                # 3. HABILITAR PERÍODO DE EXAME
                st.subheader("Liberar Período de Exame de Faixa")
                
                alunos_ativos = df_alunos[df_alunos['status_vinculo'] == 'ativo'].copy()
                
                if alunos_ativos.empty:
                    st.info("Não há alunos ativos para habilitar exames.")
                else:
                    alunos_para_selecao = {
                        f"{row['nome_aluno']} ({row['faixa_atual']})": row['aluno_id'] 
                        for index, row in alunos_ativos.iterrows()
                    }
                    
                    with st.form("form_habilitar_exame", clear_on_submit=True):
                        col1, col2 = st.columns(2)
                        aluno_selecionado_str = col1.selectbox("Selecione o Aluno",list(alunos_para_selecao.keys()),key="aluno_select")
                        aluno_id_selecionado = alunos_para_selecao.get(aluno_selecionado_str)
                        aluno_info = alunos_ativos[alunos_ativos['aluno_id'] == aluno_id_selecionado]
                        aluno_email = aluno_info['email'].iloc[0] if not aluno_info.empty else "Email não encontrado"

                        hoje = date.today()
                        data_inicio = col1.date_input("Data de Início do Exame", hoje)
                        data_fim = col2.date_input("Data Limite para o Exame", hoje + timedelta(days=14))
                        
                        if data_fim <= data_inicio:
                            st.error("A Data Limite deve ser posterior ou igual à Data de Início.")
                            submetido = False
                        else:
                            submetido = st.form_submit_button("Habilitar Exame e Agendar Alerta")
                        
                        if submetido:
                            data_inicio_str = data_inicio.strftime('%Y-%m-%d')
                            data_fim_str = data_fim.strftime('%Y-%m-%d')
                            
                            if habilitar_exame_aluno(aluno_id_selecionado, data_inicio_str, data_fim_str):
                                # Lógica de Notificação Simulada
                                data_alerta = data_fim - timedelta(days=3)
                                if data_alerta <= hoje:
                                    data_alerta = hoje + timedelta(days=1)
                                start_date_str = data_alerta.strftime('%Y-%m-%d')
                                
                                st.success(f"Exame habilitado para **{aluno_selecionado_str}** de **{data_inicio_str}** até **{data_fim_str}**!")
                                st.info(f"O Alerta de Prazo Final será verificado e enviado automaticamente em: **{start_date_str}**.")
                                st.session_state["refresh_professor_panel"] = True 
                            else:
                                st.error("Erro ao salvar no banco de dados. Tente novamente.")

                # Exibição Final da Tabela
                if "refresh_professor_panel" in st.session_state and st.session_state["refresh_professor_panel"]:
                    st.session_state["refresh_professor_panel"] = False
                    dados_alunos = get_alunos_by_equipe(equipe_id)
                    df_alunos = pd.DataFrame(dados_alunos)
                    
                df_display = df_alunos.copy()
                df_display['Data Início'] = df_display['data_inicio_exame'].fillna('N/A')
                df_display['Data Limite'] = df_display['data_fim_exame'].fillna('N/A')
                df_display['Habilitado'] = df_display['exame_habilitado'].apply(lambda x: '✅ Sim' if x else '❌ Não')
                
                st.markdown("---")
                st.subheader("Situação dos Exames")
                
                st.dataframe(
                    df_display[['nome_aluno', 'faixa_atual', 'status_vinculo', 'Habilitado', 'Data Início', 'Data Limite']],
                    column_config={
                        "nome_aluno": "Aluno",
                        "faixa_atual": "Faixa",
                        "status_vinculo": "Status Vínculo",
                        "Habilitado": "Exame Habilitado",
                    },
                    hide_index=True
                )


    # 2. APROVAÇÃO DE PROFESSORES (NOVA LÓGICA)
    with tab_aprovacao:
        if equipe_id_responsavel is None and usuario_tipo != 'admin':
            st.warning("Apenas o Professor Responsável ou Admin pode aprovar solicitações.")
            
        else:
            st.header("Solicitações de Ingresso de Professores")
            
            # 2.1 Buscar solicitações pendentes (USANDO conn ABERTO)
            query = """
                SELECT 
                    p.id, u.nome, u.email, e.nome AS equipe_nome
                FROM professores p
                JOIN usuarios u ON p.usuario_id = u.id
                JOIN equipes e ON p.equipe_id = e.id
                WHERE p.status_vinculo = 'pendente' 
            """
            params = ()
            
            if usuario_tipo == 'professor':
                query += " AND p.equipe_id = ?"
                params = (equipe_id_responsavel,)
            
            # USANDO O 'conn' ABERTO AQUI
            professores_pendentes = pd.read_sql_query(query, conn, params=params)
            
            if professores_pendentes.empty:
                st.info("Nenhuma solicitação de professor pendente para aprovação.")
            else:
                st.dataframe(professores_pendentes, use_container_width=True)
                
                st.markdown("---")
                st.subheader("Aprovar/Rejeitar")
                
                for index, row in professores_pendentes.iterrows():
                    prof_id = row['id'] # ID da linha na tabela 'professores'
                    
                    with st.container(border=True):
                        st.markdown(f"**Professor:** {row['nome']} ({row['email']})")
                        st.markdown(f"**Equipe Solicitada:** {row['equipe_nome']}")
                        
                        col_aprov, col_rejeita = st.columns(2)
                        
                        if col_aprov.button("✅ Aprovar Ingresso", key=f"aprov_{prof_id}"):
                            cursor.execute("UPDATE professores SET status_vinculo='ativo' WHERE id=?", (prof_id,))
                            conn.commit()
                            st.success(f"Professor {row['nome']} aprovado com sucesso! ✅")
                            st.rerun()
                            
                        if col_rejeita.button("❌ Rejeitar Ingresso", key=f"rejeita_{prof_id}"):
                            cursor.execute("UPDATE professores SET status_vinculo='rejeitado' WHERE id=?", (prof_id,))
                            conn.commit()
                            st.warning(f"Professor {row['nome']} rejeitado.")
                            st.rerun()

    # 3. FECHAMENTO DA CONEXÃO
    # 🚨 PONTO CRÍTICO: Fechar a conexão apenas no final, após todas as operações de banco.
    conn.close() 

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

def gestao_usuarios(usuario_logado):
    """Página de gerenciamento de usuários, restrita ao Admin."""
    
    if usuario_logado["tipo"] != "admin":
        st.error("Acesso negado. Esta página é restrita aos administradores.")
        return

    st.markdown("<h1 style='color:#FFD700;'>🔑 Gestão de Usuários</h1>", unsafe_allow_html=True)
    st.markdown("Edite informações, redefina senhas ou altere o tipo de perfil de um usuário.")

    conn = sqlite3.connect(DB_PATH)
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
            user_id_selecionado = int(df[df["nome"] == nome_selecionado]["id"].values[0])
        except IndexError:
            st.error("Usuário não encontrado no DataFrame. Tente recarregar a página.")
            conn.close()
            return
            
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
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
                novo_cpf = st.text_input("CPF:", value=user_data['cpf'] or "", help="Necessário para usuários locais.")
                
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
                    if user_data['auth_provider'] == 'local' and not validar_cpf(novo_cpf):
                        st.error("CPF inválido. Por favor, corrija.")
                        st.stop()
                    
                    try:
                        cursor.execute(
                            "UPDATE usuarios SET nome=?, email=?, cpf=?, tipo_usuario=? WHERE id=?",
                            (novo_nome, novo_email, novo_cpf, novo_tipo, user_id_selecionado)
                        )
                        conn.commit()
                        st.success("Dados do usuário atualizados com sucesso!")
                    except sqlite3.IntegrityError:
                        st.error(f"Erro: O email '{novo_email}' ou CPF '{novo_cpf}' já está em uso por outro usuário.")
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
            <p style='color:{COR_TEXTO};text-align:center;font-size:1.1em;'>Bem-vindo(a), {st.session_state.usuario['nome'].title()}! Use a navegação acima ou os cartões abaixo.</p>
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

def tela_meu_perfil(usuario_logado):
    """Página para o usuário editar seu próprio perfil e senha."""
    
    st.markdown("<h1 style='color:#FFD700;'>👤 Meu Perfil</h1>", unsafe_allow_html=True)
    st.markdown("Atualize suas informações pessoais e gerencie sua senha de acesso.")

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

    # --- Expander 1: Informações Pessoais ---
    with st.expander("📝 Informações Pessoais", expanded=True):
        with st.form(key="form_edit_perfil"):
            st.markdown("#### Editar Informações")
            
            novo_nome = st.text_input("Nome Completo:", value=user_data['nome'])
            novo_email = st.text_input("Email:", value=user_data['email'])
            
            if user_data['auth_provider'] == 'local':
                novo_cpf = st.text_input("CPF:", value=user_data['cpf'] or "", help="Obrigatório para usuários de login local.")
            else:
                novo_cpf = user_data['cpf'] # Mantém o valor
                st.text_input("CPF:", value=user_data['cpf'] or "Não aplicável (Login Google)", disabled=True)
            
            st.text_input("Tipo de Perfil:", value=user_data['tipo_usuario'].capitalize(), disabled=True)
            
            submitted_info = st.form_submit_button("💾 Salvar Alterações", use_container_width=True)
            
            if submitted_info:
                if not novo_nome or not novo_email:
                    st.warning("Nome e Email são obrigatórios.")
                elif user_data['auth_provider'] == 'local' and not validar_cpf(novo_cpf):
                    st.error("CPF inválido. Por favor, corrija.")
                else:
                    try:
                        cursor.execute(
                            "UPDATE usuarios SET nome=?, email=?, cpf=? WHERE id=?",
                            (novo_nome, novo_email, novo_cpf, user_id_logado)
                        )
                        conn.commit()
                        st.success("Dados atualizados com sucesso!")
                        
                        # ATUALIZA A SESSÃO para refletir o novo nome
                        st.session_state.usuario['nome'] = novo_nome
                        st.rerun() # Recarrega a página
                        
                    except sqlite3.IntegrityError:
                        st.error(f"Erro: O email '{novo_email}' ou CPF '{novo_cpf}' já está em uso por outro usuário.")
                    except Exception as e:
                        st.error(f"Ocorreu um erro: {e}")

    # --- Expander 2: Alteração de Senha (Somente para 'local') ---
    if user_data['auth_provider'] == 'local':
        with st.expander("🔑 Alterar Senha", expanded=False):
            with st.form(key="form_change_pass"):
                st.markdown("#### Redefinir Senha")
                
                senha_atual = st.text_input("Senha Atual:", type="password")
                nova_senha = st.text_input("Nova Senha:", type="password")
                confirmar_senha = st.text_input("Confirmar Nova Senha:", type="password")
                
                submitted_pass = st.form_submit_button("🔑 Alterar Senha", use_container_width=True)
                
                if submitted_pass:
                    if not senha_atual or not nova_senha or not confirmar_senha:
                        st.warning("Por favor, preencha todos os campos de senha.")
                    elif nova_senha != confirmar_senha:
                        st.error("As novas senhas não coincidem.")
                    else:
                        # Verifica a senha atual
                        hash_atual_db = user_data['senha']
                        if bcrypt.checkpw(senha_atual.encode(), hash_atual_db.encode()):
                            # Se a senha atual estiver correta, atualiza
                            novo_hash = bcrypt.hashpw(nova_senha.encode(), bcrypt.gensalt()).decode()
                            cursor.execute(
                                "UPDATE usuarios SET senha=? WHERE id=?",
                                (novo_hash, user_id_logado)
                            )
                            conn.commit()
                            st.success("Senha alterada com sucesso!")
                        else:
                            st.error("A 'Senha Atual' está incorreta.")
    else:
        # Mostra esta mensagem para usuários do Google
        st.info(f"Seu login é gerenciado pelo **{user_data['auth_provider'].capitalize()}**. Para alterar sua senha, você deve fazê-lo diretamente na sua conta Google.")

    # --- Expander 3: Endereço ---
    with st.expander("📍 Endereço (Opcional)", expanded=False):
        with st.form(key="form_edit_endereco"):
            # Preenche com dados da sessão para edição
            cep_val = st.text_input("CEP:", value=user_data['cep'] or "", key="edit_cep_input")
            
            # Botão de busca de CEP com callback para atualizar o cache e o estado da aplicação
            def handle_cep_search():
                endereco = buscar_endereco_por_cep(st.session_state.edit_cep_input)
                if endereco:
                    st.session_state["endereco_cache"] = endereco
                    st.session_state.logradouro_val = endereco.get('logradouro', '')
                    st.session_state.bairro_val = endereco.get('bairro', '')
                    st.session_state.cidade_val = endereco.get('localidade', '')
                    st.session_state.estado_val = endereco.get('uf', '')
                    # Reinicializa o número com o valor do DB, a busca não muda o número
                    st.session_state.numero_val = user_data['numero'] or "" 
                    st.success("Endereço encontrado! Lembre-se de clicar em 'Salvar Endereço' no final.")
                else:
                    st.error("CEP não encontrado ou inválido.")

            st.button("🔍 Buscar CEP", type="secondary", on_click=handle_cep_search)

            # Inicializa estados de sessão para campos de edição (usado para persistir o resultado do CEP)
            if 'logradouro_val' not in st.session_state:
                st.session_state.logradouro_val = user_data['logradouro'] or ""
            if 'numero_val' not in st.session_state: # NOVO CAMPO
                st.session_state.numero_val = user_data['numero'] or ""
            if 'bairro_val' not in st.session_state:
                st.session_state.bairro_val = user_data['bairro'] or ""
            if 'cidade_val' not in st.session_state:
                st.session_state.cidade_val = user_data['cidade'] or ""
            if 'estado_val' not in st.session_state:
                st.session_state.estado_val = user_data['estado'] or ""

            
            novo_logradouro = st.text_input("Logradouro (Rua/Av):", value=st.session_state.logradouro_val)
            col_num, col_comp = st.columns(2)
            # NOVO CAMPO: Número do endereço
            novo_numero = col_num.text_input("Número:", value=st.session_state.numero_val) 
            novo_complemento = col_comp.text_input("Complemento:", value="") # Não salvo no DB atualmente

            novo_bairro = st.text_input("Bairro:", value=st.session_state.bairro_val)
            col_cid, col_est = st.columns(2)
            novo_cidade = col_cid.text_input("Cidade:", value=st.session_state.cidade_val)
            novo_estado = col_est.text_input("Estado (UF):", value=st.session_state.estado_val)


            if st.form_submit_button("💾 Salvar Endereço", type="primary"):
                cep_final = st.session_state.edit_cep_input.strip()
                cursor.execute(
                    "UPDATE usuarios SET cep=?, logradouro=?, numero=?, bairro=?, cidade=?, estado=? WHERE id=?",
                    (cep_final, novo_logradouro, novo_numero, novo_bairro, novo_cidade, novo_estado, user_id_logado)
                )
                conn.commit()
                # Limpa o cache após salvar
                if "endereco_cache" in st.session_state: del st.session_state["endereco_cache"]
                # Força a atualização dos estados para refletir o DB
                st.session_state.logradouro_val = novo_logradouro
                st.session_state.numero_val = novo_numero # Atualiza o estado
                st.session_state.bairro_val = novo_bairro
                st.session_state.cidade_val = novo_cidade
                st.session_state.estado_val = novo_estado

                st.success("Endereço salvo com sucesso!")
                st.rerun()

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

def tela_login():
    """Tela de login com autenticação local, Google e opção de cadastro."""
    st.session_state.setdefault("modo_login", "login")
    # Inicializa o cache de endereço se não existir
    st.session_state.setdefault("cadastro_endereco_cache", {})


    # =========================================
    # CSS
    # ... (o CSS permanece o mesmo) ...
    # =========================================
    st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"] {
            height: 100%;
            overflow-y: auto;
        }

        [data-testid="stAppViewContainer"] > .main {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            min-height: 95vh;
        }
        div[data-testid="stContainer"] > div[style*="border"] {
            background-color: #0c241e !important;
            border: 1px solid #078B6C !important;
            border-radius: 12px !important;
            padding: 25px 35px !important;
            max-width: 400px !important;
            margin: 0 auto !important;
            box-shadow: 0px 0px 8px rgba(0,0,0,0.3);
        }
        .stButton>button[kind="primary"] {
            background: linear-gradient(90deg, #078B6C, #056853) !important;
            color: white !important;
            font-weight: bold !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.6em 1.2em !important;
            width: 100% !important;
            transition: 0.3s;
        }
        .stButton>button[kind="primary"]:hover {
            background: #FFD770 !important;
            color: #0c241e !important;
            transform: scale(1.02);
        }
        .divider {
            text-align: center;
            color: gray;
            font-size: 13px;
            margin: 12px 0;
        }
    </style>
    """, unsafe_allow_html=True)

    # =========================================
    # LOGO CENTRALIZADA
    # ... (o código da logo permanece o mesmo) ...
    # =========================================
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode()
        logo_html = f"<img src='data:image/png;base64,{logo_base64}' style='width:140px;height:auto;margin-bottom:5px;'/>"
    else:
        logo_html = "<p style='color:red;'>Logo não encontrada.</p>"

    st.markdown(f"""
        <div style='display:flex;flex-direction:column;align-items:center;justify-content:center;margin-top:-20px;'>
            {logo_html}
            <h2 style='color:#FFD700;text-align:center;'>Bem-vindo(a) ao BJJ Digital</h2>
        </div>
    """, unsafe_allow_html=True)

    # =========================================
    # BLOCO DE LOGIN
    # =========================================
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2: # <--- TUDO DEVE ESTAR DENTRO DESTE BLOCO!
        if st.session_state["modo_login"] == "login":
            with st.container(border=True):
                st.markdown("<h3 style='color:white; text-align:center;'>Login</h3>", unsafe_allow_html=True)
                
                # Login agora aceita Email ou CPF
                user_ou_cpf = st.text_input("Email ou CPF para Login:")
                pwd = st.text_input("Senha:", type="password")

                if st.button("Entrar", use_container_width=True, key="entrar_btn", type="primary"):
                    u = autenticar_local(user_ou_cpf.strip(), pwd.strip()) 
                    if u:
                        st.session_state.usuario = u
                        st.success(f"Login realizado com sucesso! Bem-vindo(a), {u['nome'].title()}.")
                        st.rerun()
                    else:
                        st.error("Email/CPF ou senha incorretos. Tente novamente.")

                # Botões Criar Conta / Esqueci Senha
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

                # Botão Google
                st.markdown("<div class='divider'>— OU —</div>", unsafe_allow_html=True)
                token = oauth_google.authorize_button(
                    name="Entrar com o Google",
                    icon="https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png",
                    use_container_width=True,
                    scope="email profile",
                    key="google_login",
                    redirect_uri=REDIRECT_URI,
                )
                
                # Lógica do token Google
                if token and "access_token" in token:
                    st.session_state.token = token
                    access_token = token["access_token"]
                    headers = {"Authorization": f"Bearer {access_token}"}
                    try:
                        resp = requests.get("https://www.googleapis.com/oauth2/v3/userinfo", headers=headers, timeout=5)
                        resp.raise_for_status()
                        info = resp.json()
                        email, nome = info.get("email"), info.get("name")
                    except Exception as e:
                        st.error(f"Erro ao autenticar com Google: {e}")
                        email, nome = None, None
                    if email:
                        usuario_db = buscar_usuario_por_email(email)
                        if usuario_db:
                            st.session_state.usuario = usuario_db
                        else:
                            novo = criar_usuario_parcial_google(email, nome)
                            st.session_state.registration_pending = novo
                        st.rerun()

        # =========================================
        # CADASTRO (Professor se vincula à equipe)
        # =========================================
        elif st.session_state["modo_login"] == "cadastro":
            
            # --- Buscar equipes para o selectbox ---
            equipes_disponiveis = buscar_equipes()
            equipe_map = {nome: id for id, nome in equipes_disponiveis}
            lista_equipes = ["Nenhuma (Professor será vinculado pelo Admin)"] + list(equipe_map.keys())
            
            with st.container(border=True):
                st.markdown("<h3 style='color:white; text-align:center;'>📋 Cadastro de Novo Usuário (Local)</h3>", unsafe_allow_html=True)
                
                with st.form(key="form_cadastro_local"):
                    
                    def handle_cadastro_cep_search_form():
                        cep_digitado = st.session_state.cadastro_cep_input
                        if not cep_digitado:
                            st.warning("Por favor, digite um CEP para buscar.")
                            return
                        
                        endereco = buscar_endereco_por_cep(cep_digitado)
                        if endereco:
                            endereco["cep_original"] = cep_digitado
                            st.session_state["cadastro_endereco_cache"] = endereco
                            st.success("Endereço encontrado e campos preenchidos. Complete o restante, se necessário.")
                        else:
                            st.error("CEP não encontrado ou inválido.")

                    # Dados Pessoais
                    st.markdown("#### Informações de Acesso")
                    nome = st.text_input("Nome Completo:") 
                    email = st.text_input("E-mail:")
                    cpf = st.text_input("CPF:", help="Apenas números. Será usado para login e identificação única.")
                    senha = st.text_input("Senha:", type="password")
                    confirmar = st.text_input("Confirmar senha:", type="password")
                    
                    st.markdown("---")
                    st.markdown("#### Classificação")
                    tipo_usuario = st.selectbox("Tipo de Usuário:", ["Aluno", "Professor"])
                    
                    equipe_sel = None
                    if tipo_usuario == "Aluno":
                        faixa = st.selectbox("Graduação (faixa):", [
                            "Branca", "Cinza", "Amarela", "Laranja", "Verde",
                            "Azul", "Roxa", "Marrom", "Preta"
                        ])
                    else:
                        faixa = "Preta" 
                        st.info("O vínculo de professor requer aprovação do responsável pela equipe.")
                        
                        # NOVO CAMPO: Seleção de Equipe para Professor
                        equipe_nome_sel = st.selectbox("Selecione a Equipe:", lista_equipes)
                        if equipe_nome_sel != lista_equipes[0]:
                             equipe_sel = equipe_map[equipe_nome_sel]

                    
                    st.markdown("---")
                    st.markdown("#### Endereço (Opcional)")
                    
                    # Campo CEP com o botão auxiliar
                    col_cep, col_btn_cep = st.columns([3, 1])
                    cep_input = col_cep.text_input("CEP:", key="cadastro_cep_input", value=st.session_state["cadastro_endereco_cache"].get("cep_original", ""))
                    
                    col_btn_cep.form_submit_button(
                        "🔍 Buscar", 
                        key="buscar_cep_btn", 
                        on_click=handle_cadastro_cep_search_form
                    )

                    # Preenchimento automático ou manual usando o cache
                    cache = st.session_state["cadastro_endereco_cache"]
                    
                    logradouro = st.text_input("Logradouro (Rua/Av):", value=cache.get('logradouro', ""))
                    col_num, col_comp = st.columns(2) # Colunas para Número e Complemento
                    numero = col_num.text_input("Número:", value="", help="O número do endereço.") 
                    col_comp.text_input("Complemento:", value="") 

                    bairro = st.text_input("Bairro:", value=cache.get('bairro', ""))
                    col_cid, col_est = st.columns(2)
                    cidade = col_cid.text_input("Cidade:", value=cache.get('cidade', ""))
                    estado = col_est.text_input("Estado (UF):", value=cache.get('uf', ""))
                    
                    # Botão Final de Cadastro (Submit button principal)
                    submitted = st.form_submit_button("Cadastrar", use_container_width=True, type="primary")

                    if submitted:
                        # Validações
                        if not (nome and email and senha and confirmar and cpf):
                            st.error("Preencha todos os campos obrigatórios: Nome Completo, Email, Senha e CPF.")
                            st.stop()
                        elif senha != confirmar:
                            st.error("As senhas não coincidem.")
                            st.stop()
                        elif not validar_cpf(cpf):
                            st.error("CPF inválido. Por favor, verifique o número.")
                            st.stop()
                        
                        # Lógica de salvar no DB
                        conn = sqlite3.connect(DB_PATH) 
                        cursor = conn.cursor()
                        
                        # Verifica duplicidade de Email ou CPF 
                        cursor.execute("SELECT id FROM usuarios WHERE email=? OR cpf=?", (email, cpf))
                        if cursor.fetchone():
                            st.error("Email ou CPF já cadastrado. Use outro ou faça login.")
                            conn.close()
                            st.stop()
                        else:
                            try:
                                hashed = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
                                tipo_db = "aluno" if tipo_usuario == "Aluno" else "professor"
                                
                                # Usa o valor atual do input do CEP
                                cep_final = cep_input 
                                
                                # 1. Salva na tabela 'usuarios'
                                cursor.execute(
                                    """
                                    INSERT INTO usuarios (nome, email, cpf, tipo_usuario, senha, auth_provider, perfil_completo, cep, logradouro, numero, bairro, cidade, estado)
                                    VALUES (?, ?, ?, ?, ?, 'local', 1, ?, ?, ?, ?, ?, ?)
                                    """,
                                    (nome, email, cpf, tipo_db, hashed, cep_final, logradouro, numero, bairro, cidade, estado)
                                )
                                novo_id = cursor.lastrowid
                                
                                # 2. Salva na tabela 'alunos' ou 'professores'
                                if tipo_db == "aluno":
                                    cursor.execute(
                                        """
                                        INSERT INTO alunos (usuario_id, faixa_atual, status_vinculo) 
                                        VALUES (?, ?, 'pendente')
                                        """,
                                        (novo_id, faixa) 
                                    )
                                else: # Professor
                                    # Salva equipe_id (se selecionada) e status PENDENTE
                                    status = 'pendente'
                                    cursor.execute(
                                        """
                                        INSERT INTO professores (usuario_id, equipe_id, status_vinculo) 
                                        VALUES (?, ?, ?)
                                        """,
                                        (novo_id, equipe_sel, status) 
                                    )
                                
                                conn.commit()
                                conn.close()
                                st.success("Usuário cadastrado com sucesso! Faça login para continuar.")
                                
                                if tipo_db == "professor" and equipe_sel:
                                     st.info("Seu cadastro como professor está **pendente de aprovação** pelo responsável da equipe.")

                                st.session_state["modo_login"] = "login"
                                # Limpa o cache após o cadastro
                                if "cadastro_endereco_cache" in st.session_state: del st.session_state["cadastro_endereco_cache"]
                                st.rerun()
                                
                            except Exception as e:
                                conn.rollback() 
                                conn.close()
                                st.error(f"Erro ao cadastrar: {e}")

            if st.button("⬅️ Voltar para Login", use_container_width=True):
                st.session_state["modo_login"] = "login"
                if "cadastro_endereco_cache" in st.session_state: del st.session_state["cadastro_endereco_cache"]
                st.rerun()

        # =========================================
        # RECUPERAÇÃO DE SENHA
        # =========================================
        elif st.session_state["modo_login"] == "recuperar":
            with st.container(border=True):
                st.markdown("<h3 style='color:white; text-align:center;'>🔑 Recuperar Senha</h3>", unsafe_allow_html=True)
                email = st.text_input("Digite o e-mail cadastrado:")
                if st.button("Enviar Instruções", use_container_width=True, type="primary"):
                    st.info("Em breve será implementado o envio de recuperação de senha.")
                
                if st.button("⬅️ Voltar para Login", use_container_width=True):
                    st.session_state["modo_login"] = "login"
                    st.rerun()
