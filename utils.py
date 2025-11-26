import os
import json
import unicodedata
import qrcode
import requests
from datetime import datetime
from fpdf import FPDF
from firebase_admin import firestore
from database import get_db 
import streamlit as st

# =========================================
# FUNÇÕES DE QUESTÕES (FALLBACK)
# =========================================
def carregar_questoes(tema):
    path = f"questions/{tema}.json"
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f: return json.load(f)
        except: return []
    return []

def salvar_questoes(tema, questoes):
    os.makedirs("questions", exist_ok=True)
    with open(f"questions/{tema}.json", "w", encoding="utf-8") as f:
        json.dump(questoes, f, indent=4, ensure_ascii=False)

def carregar_todas_questoes():
    todas = []
    if not os.path.exists("questions"): return []
    for f in os.listdir("questions"):
        if f.endswith(".json"):
            try:
                tema = f.replace(".json", "")
                q_list = carregar_questoes(tema)
                for q in q_list:
                    q['tema'] = tema
                    todas.append(q)
            except: continue
    return todas

# =========================================
# FUNÇÕES GERAIS
# =========================================

def gerar_codigo_verificacao():
    db = get_db()
    total = 0
    try:
        docs = db.collection('resultados').stream()
        total = len(list(docs))
    except Exception as e:
        print(f"Erro ao contar resultados: {e}")
        import random
        total = random.randint(1000, 9999)

    sequencial = total + 1
    ano = datetime.now().year
    codigo = f"BJJDIGITAL-{ano}-{sequencial:04d}" 
    return codigo

def normalizar_nome(nome):
    if not nome: return "sem_nome"
    return "_".join(unicodedata.normalize("NFKD", nome).encode("ASCII", "ignore").decode().split()).lower()

def formatar_e_validar_cpf(cpf):
    if not cpf: return None
    cpf_limpo = ''.join(filter(str.isdigit, cpf))
    return cpf_limpo if len(cpf_limpo) == 11 else None

def formatar_cep(cep):
    if not cep: return None
    cep_limpo = ''.join(filter(str.isdigit, cep))
    return cep_limpo if len(cep_limpo) == 8 else None

def buscar_cep(cep):
    cep_fmt = formatar_cep(cep)
    if not cep_fmt: return None
    try:
        resp = requests.get(f"https://viacep.com.br/ws/{cep_fmt}/json/", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            if "erro" not in data:
                return {
                    "logradouro": data.get("logradouro", ""),
                    "bairro": data.get("bairro", ""),
                    "cidade": data.get("localidade", ""),
                    "uf": data.get("uf", "")
                }
    except: pass
    return None

def gerar_qrcode(codigo):
    """Gera QR Code apontando para a página estática verificar.html."""
    os.makedirs("temp_qr", exist_ok=True)
    caminho_qr = f"temp_qr/{codigo}.png"
    
    if os.path.exists(caminho_qr):
        return caminho_qr
        
    # LINK CORRETO: Aponta para a página HTML específica
    link = f"https://bjjdigital.com.br/verificar.html?code={codigo}"
    
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(caminho_qr)
    return caminho_qr

# =========================================
# GERADOR DE PDF
# =========================================
@st.cache_data(show_spinner=False)
def gerar_pdf(usuario, faixa, pontuacao, total, codigo, professor=None):
    """Gera certificado PDF oficial."""
    pdf = FPDF("L", "mm", "A4")
    pdf.set_auto_page_break(False)
    pdf.add_page()

    dourado, preto, branco = (218, 165, 32), (40, 40, 40), (255, 255, 255)
    percentual = int((pontuacao / total) * 100) if total > 0 else 0
    data_hora = datetime.now().strftime("%d/%m/%Y")

    pdf.set_fill_color(*branco)
    pdf.rect(0, 0, 297, 210, "F")
    pdf.set_draw_color(*dourado)
    pdf.set_line_width(2)
    pdf.rect(10, 10, 277, 190)
    pdf.set_line_width(0.5)
    pdf.rect(13, 13, 271, 184)

    if os.path.exists("assets/logo.png"):
        pdf.image("assets/logo.png", x=130, y=20, w=35)

    pdf.set_text_color(*dourado)
    pdf.set_font("Helvetica", "B", 36)
    pdf.set_xy(0, 60)
    pdf.cell(297, 15, "CERTIFICADO DE CONCLUSÃO", align="C")
    
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(*preto)
    pdf.set_xy(0, 80)
    pdf.cell(297, 10, "Certificamos que", align="C")

    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(*dourado)
    pdf.set_xy(0, 95)
    try:
        nome_display = usuario.upper().encode('latin-1', 'replace').decode('latin-1')
    except:
        nome_display = usuario.upper()
    pdf.cell(297, 15, nome_display, align="C")

    cores_faixa = {
        "Cinza": (169, 169, 169), "Amarela": (255, 215, 0),
        "Laranja": (255, 140, 0), "Verde": (0, 128, 0),
        "Azul": (30, 144, 255), "Roxa": (128, 0, 128),
        "Marrom": (139, 69, 19), "Preta": (0, 0, 0),
    }
    r, g, b = cores_faixa.get(faixa, preto)

    pdf.set_font("Helvetica", "", 16)
    pdf.set_text_color(*preto)
    pdf.set_xy(0, 115)
    pdf.cell(297, 10, f"concluiu com êxito o Exame Teórico para a faixa", align="C")
    
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(r, g, b)
    pdf.set_xy(0, 125)
    try: f_disp = faixa.upper().encode('latin-1', 'replace').decode('latin-1')
    except: f_disp = faixa.upper()
    pdf.cell(297, 10, f_disp, align="C")

    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(*preto)
    pdf.set_xy(0, 135)
    pdf.cell(297, 10, f"Aproveitamento: {percentual}% | Data: {data_hora}", align="C")

    pdf.set_font("Courier", "", 10)
    pdf.set_xy(20, 175)
    pdf.cell(100, 5, f"Código: {codigo}", align="L")
    
    try:
        caminho_qr = gerar_qrcode(codigo)
        pdf.image(caminho_qr, x=250, y=155, w=25)
    except: pass

    if os.path.exists("assets/selo_dourado.png"):
        pdf.image("assets/selo_dourado.png", x=20, y=150, w=30)

    if professor:
        try: prof_nome = professor.encode('latin-1', 'replace').decode('latin-1')
        except: prof_nome = professor
        
        fonte_ass = "assets/fonts/Allura-Regular.ttf"
        if os.path.exists(fonte_ass):
            try:
                pdf.add_font("Assinatura", "", fonte_ass, uni=True)
                pdf.set_font("Assinatura", "", 30)
            except: pdf.set_font("Helvetica", "I", 18)
        else: pdf.set_font("Helvetica", "I", 18)

        pdf.set_text_color(*preto)
        pdf.set_y(155)
        pdf.cell(0, 10, prof_nome, align="C")
        
        pdf.set_draw_color(*dourado)
        pdf.line(100, 168, 197, 168)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_y(170)
        pdf.cell(0, 5, "Professor Responsável", align="C")

    pdf.set_draw_color(*dourado)
    pdf.line(30, 190, 268, 190)
    pdf.set_text_color(*dourado)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_y(192)
    pdf.cell(0, 5, "Plataforma BJJ Digital - bjjdigital.com.br", align="C")

    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    nome_arquivo = f"Certificado_{normalizar_nome(usuario)}_{normalizar_nome(faixa)}.pdf"
    
    return pdf_bytes, nome_arquivo
