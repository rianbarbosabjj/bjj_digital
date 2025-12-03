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
from urllib.parse import quote
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fpdf import FPDF
from database import get_db
from firebase_admin import firestore, storage 

# =========================================
# FUNÇÃO 1: UPLOAD DE IMAGEM
# =========================================
def fazer_upload_imagem(arquivo):
    if not arquivo: 
        return None
    
    try:
        bucket = storage.bucket()
        if not bucket.name:
            st.error("Erro: Bucket não configurado no secrets.toml")
            return None

        # 1. Define nome do arquivo
        ext = arquivo.name.split('.')[-1]
        blob_name = f"questoes/{uuid.uuid4()}.{ext}"
        blob = bucket.blob(blob_name)
        
        # 2. Upload
        arquivo.seek(0)
        blob.upload_from_file(arquivo, content_type=arquivo.type)
        
        # 3. Token de Acesso
        access_token = str(uuid.uuid4())
        metadata = {"firebaseStorageDownloadTokens": access_token}
        blob.metadata = metadata
        blob.patch()

        # 4. Monta URL
        blob_path_encoded = quote(blob_name, safe='') 
        final_url = f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/{blob_path_encoded}?alt=media&token={access_token}"
        
        return final_url
    except Exception as e:
        st.error(f"Erro no Upload: {e}")
        return None

# =========================================
# FUNÇÃO 2: QUESTÕES
# =========================================
def carregar_todas_questoes():
    try:
        db = get_db()
        docs = db.collection('questoes').where('status', '==', 'aprovada').stream()
        return [doc.to_dict() for doc in docs]
    except:
        return []

def salvar_questoes(tema, questoes):
    pass # Função legada mantida para compatibilidade

def carregar_questoes(tema):
    return [] # Função legada mantida para compatibilidade

# =========================================
# FUNÇÃO 3: FORMATAÇÃO E VALIDAÇÃO
# =========================================
def normalizar_nome(nome):
    if not nome: return "sem_nome"
    return "_".join(unicodedata.normalize("NFKD", nome).encode("ASCII", "ignore").decode().split()).lower()

def formatar_e_validar_cpf(cpf):
    if not cpf: return None
    cpf_limpo = re.sub(r'\D', '', str(cpf))
    if len(cpf_limpo) != 11: return None
    
    # Validação simples de dígitos iguais
    if cpf_limpo == cpf_limpo[0] * 11: return None
    
    return f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"

def formatar_cep(cep):
    if not cep: return None
    c = ''.join(filter(str.isdigit, cep))
    return c if len(c) == 8 else None

def buscar_cep(cep):
    c = formatar_cep(cep)
    if not c: return None
    try:
        r = requests.get(f"https://viacep.com.br/ws/{c}/json/", timeout=3)
        if r.status_code == 200:
            d = r.json()
            if "erro" not in d:
                return {
                    "logradouro": d.get("logradouro", "").upper(),
                    "bairro": d.get("bairro", "").upper(),
                    "cidade": d.get("localidade", "").upper(),
                    "uf": d.get("uf", "").upper()
                }
    except: pass
    return None

# =========================================
# FUNÇÃO 4: SEGURANÇA E EMAIL
# =========================================
def gerar_senha_temporaria(tamanho=8):
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(tamanho))

def enviar_email_recuperacao(email_destino, nova_senha):
    # Simplificado para evitar erros de SMTP
    try:
        sender = st.secrets.get("EMAIL_SENDER")
        pwd = st.secrets.get("EMAIL_PASSWORD")
        if not sender or not pwd: return False
        
        msg = MIMEMultipart()
        msg['Subject'] = "Nova Senha BJJ"
        msg['From'] = sender
        msg['To'] = email_destino
        msg.attach(MIMEText(f"Senha: {nova_senha}", 'html'))
        
        s = smtplib.SMTP("smtp.gmail.com", 587)
        s.starttls()
        s.login(sender, pwd)
        s.sendmail(sender, email_destino, msg.as_string())
        s.quit()
        return True
    except: return False

# =========================================
# FUNÇÃO 5: PDF E CÓDIGOS
# =========================================
def gerar_codigo_verificacao():
    return f"BJJ-{datetime.now().year}-{random.randint(10000,99999)}"

def gerar_qrcode(codigo):
    return None

@st.cache_data(show_spinner=False)
def gerar_pdf(usuario_nome, faixa, pontuacao, total, codigo, professor=None):
    try:
        pdf = FPDF("L", "mm", "A4")
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 24)
        pdf.cell(0, 20, "CERTIFICADO", ln=True, align="C")
        pdf.set_font("Helvetica", "", 16)
        pdf.ln(10)
        pdf.cell(0, 10, f"Certificamos que {usuario_nome} passou para {faixa}", ln=True, align="C")
        return pdf.output(dest='S').encode('latin-1'), "certificado.pdf"
    except: return None, None

# =========================================
# FUNÇÃO 6: REGRAS DO EXAME
# =========================================
def verificar_elegibilidade_exame(usuario_data):
    status = usuario_data.get('status_exame', 'pendente')
    if status == 'aprovado': return False, "Aprovado."
    if status == 'bloqueado': return False, "Bloqueado."
    if status == 'reprovado':
        ult = usuario_data.get('data_ultimo_exame')
        if ult:
            try:
                if isinstance(ult, str): d_ult = datetime.fromisoformat(ult.replace('Z',''))
                else: d_ult = ult
                diff = datetime.utcnow() - d_ult.replace(tzinfo=None)
                if diff.total_seconds() < 72*3600: return False, "Aguarde 72h."
            except: pass
    return True, "OK"

def registrar_inicio_exame(uid):
    try: get_db().collection('usuarios').document(uid).update({"status_exame": "em_andamento", "inicio_exame_temp": datetime.utcnow().isoformat()})
    except: pass

def registrar_fim_exame(uid, aprovado):
    try:
        stt = "aprovado" if aprovado else "reprovado"
        dados = {"status_exame": stt, "data_ultimo_exame": datetime.utcnow().isoformat(), "status_exame_em_andamento": False}
        if aprovado: dados["exame_habilitado"] = firestore.DELETE_FIELD
        get_db().collection('usuarios').document(uid).update(dados)
    except: pass

def bloquear_por_abandono(uid):
    try: get_db().collection('usuarios').document(uid).update({"status_exame": "bloqueado", "motivo_bloqueio": "Anti-Cola", "data_ultimo_exame": datetime.utcnow().isoformat()})
    except: pass
