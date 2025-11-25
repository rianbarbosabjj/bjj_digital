import os
import json
import unicodedata
import qrcode
import requests
from datetime import datetime
from fpdf import FPDF
from firebase_admin import firestore
from database import get_db 
import streamlit as st  # Necessário para o cache

# =========================================
# FUNÇÕES DE QUESTÕES
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
    except:
        import random
        total = random.randint(1000, 9999)
    sequencial = total + 1
    ano = datetime.now().year
    return f"BJJDIGITAL-{ano}-{sequencial:04d}"

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
    os.makedirs("temp_qr", exist_ok=True)
    caminho_qr = f"temp_qr/{codigo}.png"
    # Pequeno cache de arquivo para o QR Code (evita recriar imagem se já existe)
    if os.path.exists(caminho_qr):
        return caminho_qr
        
    link = f"https://bjjdigital.com.br/validar?code={codigo}"
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(caminho_qr)
    return caminho_qr

# =========================================
# GERADOR DE PDF (COM CACHE)
# =========================================
@st.cache_data(show_spinner=False)
def gerar_pdf(usuario, faixa, pontuacao, total, codigo, professor=None):
    """
    Gera certificado PDF oficial.
    Retorna (bytes, nome_arquivo).
    """
    pdf = FPDF("L", "mm", "A4")
    pdf.set_auto_page_break(False)
    pdf.add_page()

    # Cores
    dourado, preto, branco = (218, 165, 32), (40, 40, 40), (255, 255, 255)
    percentual = int((pontuacao / total) * 100) if total > 0 else 0
    data_hora = datetime.now().strftime("%d/%m/%Y")

    # Fundo e Borda
    pdf.set_fill_color(*branco)
    pdf.rect(0, 0, 297, 210, "F")
    pdf.set_draw_color(*dourado)
    pdf.set_line_width(2)
    pdf.rect(10, 10, 277, 190)
    pdf.set_line_width(0.5)
    pdf.rect(13, 13, 271, 184)

    # Logo
    if os.path.exists("assets/logo.png"):
        pdf.image("assets/logo.png", x=130, y=20, w=35)

    # Título
    pdf.set_text_color(*dourado)
    pdf.set_font("Helvetica", "B", 36)
    pdf.set_xy(0, 60)
    pdf.cell(297, 15, "CERTIFICADO DE CONCLUSÃO", align="C")
    
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(*preto)
    pdf.set_xy(0, 80)
    pdf.cell(297, 10, "Certificamos que", align="C")

    # Nome do Aluno
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(*dourado)
    pdf.set_xy(0, 95)
    pdf.cell(297, 15, usuario.upper(), align="C")

    # Texto Central
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(*preto)
    pdf.set_xy(0, 115)
    pdf.cell(297, 10, f"concluiu com êxito o Exame Teórico para a faixa {faixa}", align="C")
    
    pdf.set_xy(0, 125)
    pdf.cell(297, 10, f"Aproveitamento: {percentual}% | Data: {data_hora}", align="C")

    # Código e QR Code
    pdf.set_font("Courier", "", 10)
    pdf.set_xy(20, 175)
    pdf.cell(100, 5, f"Código de Autenticidade: {codigo}", align="L")
    
    try:
        qr_path = gerar_qrcode(codigo)
        pdf.image(qr_path, x=250, y=160, w=25)
    except: pass

    # Assinatura
    if professor:
        fonte_assinatura = "assets/fonts/Allura-Regular.ttf"
        if os.path.exists(fonte_assinatura):
            try:
                pdf.add_font("Assinatura", "", fonte_assinatura, uni=True)
                pdf.set_font("Assinatura", "", 30)
            except: pdf.set_font("Helvetica", "I", 18)
        else: pdf.set_font("Helvetica", "I", 18)

        pdf.set_text_color(*preto)
        pdf.set_y(158)
        pdf.cell(0, 12, professor, align="C")
        pdf.set_draw_color(*dourado)
        pdf.line(100, 173, 197, 173)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_y(175)
        pdf.cell(0, 6, "Assinatura do Professor Responsável", align="C")

    # Rodapé
    pdf.set_draw_color(*dourado)
    pdf.line(30, 190, 268, 190)
    pdf.set_text_color(*dourado)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_y(190)
    pdf.cell(0, 6, "Plataforma BJJ Digital", align="C")

    # Retorna bytes diretamente (MUITO MAIS RÁPIDO)
    # .encode('latin-1') é o padrão do FPDF para output binário
    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    nome_arquivo = f"Certificado_{normalizar_nome(usuario)}_{normalizar_nome(faixa)}.pdf"
    
    return pdf_bytes, nome_arquivo
