import os
import json
import re
import requests
import streamlit as st
import smtplib
import secrets
import string
import unicodedata
import qrcode
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
# FUNÇÃO DE UPLOAD (LINK PÚBLICO FIREBASE)
# =========================================
def fazer_upload_imagem(arquivo):
    """
    Envia imagem para o Storage e gera um link público e persistente.
    """
    if not arquivo: return None
    
    try:
        bucket = storage.bucket() 
        if not bucket.name:
            # Tenta recuperar do secrets se o objeto bucket estiver sem nome
            bucket_name = st.secrets.get("firebase", {}).get("storage_bucket")
            if not bucket_name:
                st.error("Erro: Bucket não configurado.")
                return None
            # Reconecta com o nome explícito se necessário (raro)
            
        # 1. Define o caminho
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

        # 4. URL Manual
        blob_path_encoded = quote(blob_name, safe='') 
        final_url = f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/{blob_path_encoded}?alt=media&token={access_token}"
        
        return final_url
        
    except Exception as e:
        st.error(f"Erro Upload: {e}")
        return None

# =========================================
# 1. QUESTÕES
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
    try:
        db = get_db()
        docs = db.collection('questoes').where('status', '==', 'aprovada').stream()
        return [doc.to_dict() for doc in docs]
    except: return []

# =========================================
# 2. VALIDAÇÕES E FORMATAÇÃO (ESSENCIAL)
# =========================================
def normalizar_nome(nome):
    if not nome: return "sem_nome"
    return "_".join(unicodedata.normalize("NFKD", nome).encode("ASCII", "ignore").decode().split()).lower()

def formatar_e_validar_cpf(cpf):
    if not cpf: return None
    cpf_limpo = re.sub(r'\D', '', str(cpf))
    if len(cpf_limpo) != 11: return None
    if cpf_limpo == cpf_limpo[0] * 11: return None
    
    def calcular_digito(cpf_parcial):
        soma = 0
        peso = len(cpf_parcial) + 1
        for n in cpf_parcial:
            soma += int(n) * peso
            peso -= 1
        resto = soma % 11
        return '0' if resto < 2 else str(11 - resto)

    digito1 = calcular_digito(cpf_limpo[:9])
    digito2 = calcular_digito(cpf_limpo[:10])
    
    if cpf_limpo[-2:] == digito1 + digito2:
        return f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"
    return None

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
# 3. SEGURANÇA
# =========================================
def gerar_senha_temporaria(tamanho=8):
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(tamanho))

def enviar_email_recuperacao(email_destino, nova_senha):
    # Lógica de e-mail simplificada para evitar erros se não configurado
    try:
        sender = st.secrets.get("EMAIL_SENDER")
        pwd = st.secrets.get("EMAIL_PASSWORD")
        if not sender or not pwd: return False
        
        msg = MIMEMultipart()
        msg['Subject'] = "Recuperação BJJ Digital"
        msg['From'] = sender
        msg['To'] = email_destino
        msg.attach(MIMEText(f"Nova Senha: {nova_senha}", 'html'))
        
        server = smtplib.SMTP(st.secrets.get("EMAIL_SERVER", "smtp.gmail.com"), 587)
        server.starttls()
        server.login(sender, pwd)
        server.sendmail(sender, email_destino, msg.as_string())
        server.quit()
        return True
    except: return False

# =========================================
# 4. GERAÇÃO DE PDF E CÓDIGOS
# =========================================
def gerar_codigo_verificacao():
    return f"BJJ-{datetime.now().year}-{random.randint(10000,99999)}"

def gerar_qrcode(codigo):
    return None # Simplificado para evitar erros de path

@st.cache_data(show_spinner=False)
def gerar_pdf(usuario_nome, faixa, pontuacao, total, codigo, professor=None):
    try:
        pdf = FPDF("L", "mm", "A4")
        pdf.add_page()
        pdf.set_fill_color(252, 252, 250)
        pdf.rect(0, 0, 297, 210, "F")
        
        # Barra lateral
        pdf.set_fill_color(25, 25, 25)
        pdf.rect(0, 0, 25, 210, "F")
        
        pdf.set_font("Helvetica", "B", 24)
        pdf.cell(0, 20, "CERTIFICADO", ln=True, align="C")
        
        pdf.set_font("Helvetica", "", 16)
        pdf.ln(10)
        pdf.cell(0, 10, f"Certificamos que {usuario_nome}", ln=True, align="C")
        pdf.cell(0, 10, f"Foi aprovado para a faixa {faixa.upper()}", ln=True, align="C")
        
        return pdf.output(dest='S').encode('latin-1'), "certificado.pdf"
    except: return None, None

# =========================================
# 5. REGRAS DE EXAME
# =========================================
def verificar_elegibilidade_exame(usuario_data):
    # Lógica de bloqueio 72h
    status = usuario_data.get('status_exame', 'pendente')
    if status == 'aprovado': return False, "Aprovado."
    if status == 'bloqueado': return False, "Bloqueado."
    if status == 'reprovado':
        ult = usuario_data.get('data_ultimo_exame')
        if ult:
            try:
                # Tenta formatar data ISO
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
        get_db().collection('usuarios').document(uid).update({"status_exame": stt, "data_ultimo_exame": datetime.utcnow().isoformat(), "status_exame_em_andamento": False})
    except: pass

def bloquear_por_abandono(uid):
    try: get_db().collection('usuarios').document(uid).update({"status_exame": "bloqueado", "motivo_bloqueio": "Anti-Cola", "data_ultimo_exame": datetime.utcnow().isoformat()})
    except: pass
