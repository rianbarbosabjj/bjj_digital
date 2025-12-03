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
from urllib.parse import quote, urlparse, parse_qs
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fpdf import FPDF
from database import get_db
from firebase_admin import firestore, storage 

# =========================================
# FUNÇÃO NOVA: CORRIGIR LINK DO YOUTUBE
# =========================================
def normalizar_link_video(url):
    """
    Converte links de YouTube Shorts ou Mobile para o formato padrão 'watch?v='.
    Isso garante que o st.video consiga reproduzir.
    """
    if not url: return None
    
    try:
        # Se for link de Shorts
        if "shorts/" in url:
            # Ex: https://youtube.com/shorts/ID_DO_VIDEO?feature=share
            # Vira: https://youtube.com/watch?v=ID_DO_VIDEO
            base = url.split("shorts/")[1]
            video_id = base.split("?")[0] # Remove parâmetros extras
            return f"https://www.youtube.com/watch?v={video_id}"
        
        # Se for link mobile (youtu.be)
        elif "youtu.be/" in url:
            base = url.split("youtu.be/")[1]
            video_id = base.split("?")[0]
            return f"https://www.youtube.com/watch?v={video_id}"
            
        # Se já for normal, retorna como está
        return url
    except:
        return url

# =========================================
# FUNÇÃO DE UPLOAD (LINK PÚBLICO FIREBASE)
# =========================================
def fazer_upload_midia(arquivo):
    if not arquivo: return None
    try:
        bucket = storage.bucket() 
        if not bucket.name:
            bucket_name = st.secrets.get("firebase", {}).get("storage_bucket")
            # Fallback para ler direto da raiz se não achar no dict
            if not bucket_name: bucket_name = st.secrets.get("storage_bucket")
            
            if not bucket_name: return None
        
        ext = arquivo.name.split('.')[-1]
        blob_name = f"questoes/{uuid.uuid4()}.{ext}"
        blob = bucket.blob(blob_name)
        
        arquivo.seek(0)
        blob.upload_from_file(arquivo, content_type=arquivo.type)
        
        access_token = str(uuid.uuid4())
        metadata = {"firebaseStorageDownloadTokens": access_token}
        blob.metadata = metadata
        blob.patch() 

        blob_path_encoded = quote(blob_name, safe='') 
        final_url = f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/{blob_path_encoded}?alt=media&token={access_token}"
        
        return final_url
    except Exception as e:
        st.error(f"Erro Upload: {e}")
        return None

# =========================================
# 1. FUNÇÕES DE QUESTÕES
# =========================================
def carregar_todas_questoes():
    try:
        db = get_db()
        docs = db.collection('questoes').where('status', '==', 'aprovada').stream()
        return [doc.to_dict() for doc in docs]
    except: return []

def carregar_questoes(t): return [] 
def salvar_questoes(t, q): pass

# =========================================
# 2. FUNÇÕES GERAIS
# =========================================
def normalizar_nome(nome):
    if not nome: return "sem_nome"
    return "_".join(unicodedata.normalize("NFKD", nome).encode("ASCII", "ignore").decode().split()).lower()

def formatar_e_validar_cpf(cpf):
    if not cpf: return None
    c = re.sub(r'\D', '', str(cpf))
    if len(c) != 11 or c == c[0]*11: return None
    return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}"

def formatar_cep(cep):
    if not cep: return None
    c = ''.join(filter(str.isdigit, cep))
    return c if len(c) == 8 else None

def buscar_cep(cep):
    c = formatar_cep(cep)
    if not c: return None
    try:
        r = requests.get(f"https://viacep.com.br/ws/{c}/json/", timeout=3)
        if r.status_code == 200 and "erro" not in r.json():
            d = r.json()
            return {"logradouro": d.get("logradouro","").upper(), "bairro": d.get("bairro","").upper(), "cidade": d.get("localidade","").upper(), "uf": d.get("uf","").upper()}
    except: pass
    return None

# =========================================
# 3. SEGURANÇA
# =========================================
def gerar_senha_temporaria(t=8):
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(t))

def enviar_email_recuperacao(dest, senha):
    try:
        s_email = st.secrets.get("EMAIL_SENDER")
        s_pwd = st.secrets.get("EMAIL_PASSWORD")
        if not s_email or not s_pwd: return False
        msg = MIMEMultipart()
        msg['Subject'] = "Recuperação BJJ"
        msg['From'] = s_email
        msg['To'] = dest
        msg.attach(MIMEText(f"Senha: {senha}", 'html'))
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(s_email, s_pwd)
        server.sendmail(s_email, dest, msg.as_string())
        server.quit()
        return True
    except: return False

# =========================================
# 4. PDF E CÓDIGOS
# =========================================
def gerar_codigo_verificacao():
    return f"BJJ-{datetime.now().year}-{random.randint(10000,99999)}"

def gerar_qrcode(c): return None

@st.cache_data(show_spinner=False)
def gerar_pdf(nome, faixa, pont, tot, cod, prof=None):
    try:
        pdf = FPDF("L", "mm", "A4")
        pdf.add_page()
        pdf.set_fill_color(252, 252, 250); pdf.rect(0,0,297,210,"F")
        pdf.set_fill_color(25, 25, 25); pdf.rect(0,0,25,210,"F")
        pdf.set_font("Helvetica", "B", 24); pdf.set_xy(30,40); pdf.cell(0,20,"CERTIFICADO",ln=True,align="C")
        pdf.set_font("Helvetica", "", 16); pdf.ln(10); pdf.set_x(30)
        pdf.cell(0,10,f"Certificamos que {nome}",ln=True,align="C")
        pdf.set_x(30); pdf.cell(0,10,f"Aprovado para {faixa.upper()}",ln=True,align="C")
        return pdf.output(dest='S').encode('latin-1'), "certificado.pdf"
    except: return None, None

# =========================================
# 5. REGRAS
# =========================================
def verificar_elegibilidade_exame(ud):
    stt = ud.get('status_exame','pendente')
    if stt == 'aprovado': return False, "Aprovado."
    if stt == 'bloqueado': return False, "Bloqueado."
    if stt == 'reprovado':
        ult = ud.get('data_ultimo_exame')
        if ult:
            try:
                d = datetime.fromisoformat(ult.replace('Z','')) if isinstance(ult,str) else ult
                if (datetime.utcnow()-d.replace(tzinfo=None)).total_seconds() < 72*3600: return False, "Aguarde 72h."
            except: pass
    return True, "OK"

def registrar_inicio_exame(uid):
    try: get_db().collection('usuarios').document(uid).update({"status_exame":"em_andamento", "inicio_exame_temp":datetime.utcnow().isoformat()})
    except: pass

def registrar_fim_exame(uid, apr):
    try:
        stt = "aprovado" if apr else "reprovado"
        d = {"status_exame":stt, "data_ultimo_exame":datetime.utcnow().isoformat(), "status_exame_em_andamento":False}
        if apr: d["exame_habilitado"] = firestore.DELETE_FIELD
        get_db().collection('usuarios').document(uid).update(d)
    except: pass

def bloquear_por_abandono(uid):
    try: get_db().collection('usuarios').document(uid).update({"status_exame":"bloqueado", "motivo_bloqueio":"Anti-Cola", "data_ultimo_exame":datetime.utcnow().isoformat()})
    except: pass
