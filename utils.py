import os
import json
import re
import requests
import streamlit as st
import smtplib
import secrets
import string
import unicodedata
import random
import uuid
import qrcode
from urllib.parse import quote
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fpdf import FPDF
from database import get_db
from firebase_admin import firestore, storage 

# =========================================
# CORES FAIXAS
# =========================================
CORES_FAIXAS = {
    "BRANCA": (50, 50, 50), "CINZA": (128, 128, 128), "AMARELA": (204, 169, 0),
    "LARANJA": (255, 140, 0), "VERDE": (0, 100, 0), "AZUL": (0, 0, 139),
    "ROXA": (128, 0, 128), "MARROM": (101, 67, 33), "PRETA": (0, 0, 0)
}
def get_cor_faixa(nome):
    for k, v in CORES_FAIXAS.items():
        if k in nome.upper(): return v
    return (0, 0, 0)

# =========================================
# UPLOAD E VÍDEO
# =========================================
def normalizar_link_video(url):
    if not url: return None
    try:
        if "shorts/" in url: return f"https://www.youtube.com/watch?v={url.split('shorts/')[1].split('?')[0]}"
        elif "youtu.be/" in url: return f"https://www.youtube.com/watch?v={url.split('youtu.be/')[1].split('?')[0]}"
        return url
    except: return url

def fazer_upload_midia(arquivo):
    if not arquivo: return None
    try:
        bucket = storage.bucket()
        if not bucket.name:
            bn = st.secrets.get("firebase", {}).get("storage_bucket")
            if not bn: bn = st.secrets.get("storage_bucket")
            if not bn: return None
        
        ext = arquivo.name.split('.')[-1]
        blob = bucket.blob(f"questoes/{uuid.uuid4()}.{ext}")
        arquivo.seek(0)
        blob.upload_from_file(arquivo, content_type=arquivo.type)
        
        token = str(uuid.uuid4())
        blob.metadata = {"firebaseStorageDownloadTokens": token}
        blob.patch()
        return f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/{quote(blob.name, safe='')}?alt=media&token={token}"
    except Exception as e:
        st.error(f"Erro Upload: {e}"); return None

# =========================================
# QUESTÕES
# =========================================
def carregar_todas_questoes():
    try:
        docs = get_db().collection('questoes').where('status', '==', 'aprovada').stream()
        return [d.to_dict() for d in docs]
    except: return []
def carregar_questoes(t): return []
def salvar_questoes(t, q): pass

# =========================================
# UTILITÁRIOS
# =========================================
def normalizar_nome(n): return "_".join(unicodedata.normalize("NFKD", n).encode("ASCII","ignore").decode().split()).lower() if n else "sem_nome"
def formatar_e_validar_cpf(c): return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}" if c and len(re.sub(r'\D','',str(c)))==11 else None
def formatar_cep(c): return ''.join(filter(str.isdigit,c)) if c else None
def buscar_cep(cep):
    try:
        r = requests.get(f"https://viacep.com.br/ws/{formatar_cep(cep)}/json/", timeout=3)
        if r.ok and "erro" not in r.json(): return r.json()
    except: pass
    return None
def gerar_senha_temporaria(t=8): return ''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(t))
def enviar_email_recuperacao(d, s): return False 

# =========================================
# CÓDIGO SEQUENCIAL E QR CODE
# =========================================
def gerar_codigo_verificacao():
    """Gera BJJDIGITAL-{ANO}-{SEQUENCIA} consultando o banco."""
    try:
        # Tenta contar documentos para gerar sequencia
        count = get_db().collection('resultados').count().get()[0][0].value
        seq = int(count) + 1
    except:
        seq = random.randint(1000, 9999)
    return f"BJJDIGITAL-{datetime.now().year}-{seq:04d}"

def gerar_qrcode(codigo):
    try:
        os.makedirs("temp", exist_ok=True)
        path = f"temp/qr_{codigo}.png"
        qr = qrcode.QRCode(box_size=10, border=1)
        qr.add_data(f"https://bjjdigital.streamlit.app/?validar={codigo}")
        qr.make(fit=True)
        qr.make_image(fill_color="black", back_color="white").save(path)
        return path
    except: return None

# =========================================
# GERADOR DE PDF BLINDADO
# =========================================
@st.cache_data(show_spinner=False)
def gerar_pdf(usuario_nome, faixa, pontuacao, total, codigo, professor=None):
    try:
        pdf = FPDF("L", "mm", "A4")
        pdf.add_page()
        
        # Cores
        CF, CV, CD = (255, 255, 252), (14, 45, 38), (218, 165, 32)
        
        # Fundo e Bordas
        pdf.set_fill_color(*CF); pdf.rect(0,0,297,210,"F")
        pdf.set_fill_color(*CV); pdf.rect(0,0,35,210,"F")
        pdf.set_fill_color(*CD); pdf.rect(35,0,2,210,"F")
        pdf.set_draw_color(*CD); pdf.set_line_width(1); pdf.rect(10,10,277,190)
        pdf.set_line_width(0.3); pdf.rect(37,12,248,186)

        # Helper para achar imagens
        def find_img(name):
            if os.path.exists(f"assets/{name}"): return f"assets/{name}"
            if os.path.exists(name): return name
            return None

        # Logo
        logo = find_img("logo.jpg") or find_img("logo.png")
        if logo: pdf.image(logo, x=45, y=20, w=30)

        # QR Code
        qr = gerar_qrcode(codigo)
        if qr and os.path.exists(qr):
            pdf.set_xy(240, 20)
            pdf.set_font("Helvetica", "B", 8); pdf.set_text_color(100,100,100)
            pdf.cell(40, 5, "Autenticidade", align="C")
            pdf.image(qr, x=250, y=26, w=20)
            pdf.set_xy(240, 47); pdf.set_font("Courier", "B", 9); pdf.set_text_color(0,0,0)
            pdf.cell(40, 5, codigo, align="C")

        # Título
        pdf.set_y(50); pdf.set_left_margin(45)
        pdf.set_font("Helvetica", "B", 36); pdf.set_text_color(*CV)
        pdf.cell(0, 15, "CERTIFICADO", ln=True, align="C")
        pdf.set_font("Helvetica", "", 14); pdf.set_text_color(80,80,80)
        pdf.cell(0, 10, "DE CONCLUSÃO DE EXAME TEÓRICO", ln=True, align="C")
        pdf.ln(10)

        # Texto
        pdf.set_font("Helvetica", "", 16); pdf.set_text_color(0,0,0)
        pdf.cell(0, 10, "Certificamos que o aluno(a)", ln=True, align="C")
        
        # Nome
        pdf.ln(5)
        try: nm = usuario_nome.upper().encode('latin-1','replace').decode('latin-1')
        except: nm = str(usuario_nome).upper()
        
        sz = 32
        pdf.set_font("Helvetica", "B", sz)
        while pdf.get_string_width(nm) > 230 and sz > 12:
            sz -= 2; pdf.set_font("Helvetica", "B", sz)
            
        pdf.set_text_color(*CD); pdf.cell(0, 15, nm, ln=True, align="C")
        
        # Faixa
        pdf.ln(5); pdf.set_font("Helvetica", "", 16); pdf.set_text_color(0,0,0)
        pdf.cell(0, 10, "Concluiu com êxito a avaliação para a faixa", ln=True, align="C")
        pdf.ln(5)
        pdf.set_text_color(*get_cor_faixa(faixa))
        pdf.set_font("Helvetica", "B", 32)
        pdf.cell(0, 15, faixa.upper(), ln=True, align="C")

        # Dados
        pdf.ln(10); pdf.set_font("Helvetica", "", 11); pdf.set_text_color(100,100,100)
        pdf.cell(0, 8, f"Emissão: {datetime.now().strftime('%d/%m/%Y')}  |  Nota: {pontuacao:.1f}%", ln=True, align="C")

        # Assinatura
        pdf.ln(15); y = pdf.get_y()
        pdf.set_draw_color(50,50,50); pdf.set_line_width(0.5)
        pdf.line(100, y, 200, y)
        pdf.ln(2); pdf.set_font("Helvetica", "B", 11); pdf.set_text_color(*CV)
        pdf.cell(0, 6, "COORDENAÇÃO TÉCNICA - BJJ DIGITAL", align="C")

        # Selo
        selo = find_img("selo_dourado.jpg")
        if selo: pdf.image(selo, x=245, y=155, w=35)

        # Retorno seguro de Bytes
        return pdf.output(dest='S').encode('latin-1'), f"Certificado_{nm.split()[0]}.pdf"

    except Exception as e:
        print(f"Erro PDF: {e}")
        return None, None

# =========================================
# 6. REGRAS
# =========================================
def verificar_elegibilidade_exame(ud):
    stt = ud.get('status_exame','pendente')
    if stt=='aprovado': return False, "Aprovado."
    if stt=='bloqueado': return False, "Bloqueado."
    if stt=='reprovado':
        u = ud.get('data_ultimo_exame')
        if u:
            try:
                dt = datetime.fromisoformat(u.replace('Z','')) if isinstance(u,str) else u
                if (datetime.utcnow()-dt.replace(tzinfo=None)).total_seconds() < 72*3600: return False, "Aguarde 72h."
            except: pass
    return True, "OK"

def registrar_inicio_exame(uid):
    try: get_db().collection('usuarios').document(uid).update({"status_exame":"em_andamento", "inicio_exame_temp":datetime.utcnow().isoformat()})
    except: pass

def registrar_fim_exame(uid, apr):
    try:
        s = "aprovado" if apr else "reprovado"
        d = {"status_exame":s, "data_ultimo_exame":datetime.utcnow().isoformat(), "status_exame_em_andamento":False}
        if apr: d.update({"exame_habilitado":firestore.DELETE_FIELD, "exame_inicio":firestore.DELETE_FIELD, "exame_fim":firestore.DELETE_FIELD})
        get_db().collection('usuarios').document(uid).update(d)
    except: pass

def bloquear_por_abandono(uid):
    try: get_db().collection('usuarios').document(uid).update({"status_exame":"bloqueado", "motivo_bloqueio":"Anti-Cola", "data_ultimo_exame":datetime.utcnow().isoformat()})
    except: pass
