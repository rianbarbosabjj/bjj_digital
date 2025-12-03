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
import qrcode  # Biblioteca necessária para o QR Code
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
    if not url: return None
    try:
        if "shorts/" in url:
            base = url.split("shorts/")[1]
            video_id = base.split("?")[0]
            return f"https://www.youtube.com/watch?v={video_id}"
        elif "youtu.be/" in url:
            base = url.split("youtu.be/")[1]
            video_id = base.split("?")[0]
            return f"https://www.youtube.com/watch?v={video_id}"
        return url
    except: return url

# =========================================
# FUNÇÃO DE UPLOAD
# =========================================
def fazer_upload_midia(arquivo):
    if not arquivo: return None
    try:
        bucket = storage.bucket() 
        if not bucket.name:
            bucket_name = st.secrets.get("firebase", {}).get("storage_bucket")
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
# 4. CÓDIGOS E QR CODE (RECUPERADO)
# =========================================
def gerar_codigo_verificacao():
    return f"BJJ-{datetime.now().year}-{random.randint(10000,99999)}"

def gerar_qrcode(codigo):
    """Gera uma imagem de QR Code e salva temporariamente."""
    try:
        os.makedirs("temp", exist_ok=True)
        caminho_qr = f"temp/qr_{codigo}.png"
        
        # URL de validação (Exemplo)
        url_validacao = f"https://bjj-digital.streamlit.app/?validar={codigo}"
        
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(url_validacao)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(caminho_qr)
        return caminho_qr
    except Exception as e:
        print(f"Erro QR: {e}")
        return None

# =========================================
# 5. PDF PREMIUM (COM SELO E QR CODE)
# =========================================
@st.cache_data(show_spinner=False)
def gerar_pdf(usuario_nome, faixa, pontuacao, total, codigo, professor=None):
    try:
        pdf = FPDF("L", "mm", "A4")
        pdf.add_page()
        
        # --- CORES ---
        COR_FUNDO = (255, 255, 250)      # Creme muito suave
        COR_VERDE = (14, 45, 38)         # Verde BJJ Digital
        COR_DOURADO = (218, 165, 32)     # Dourado
        
        # Fundo
        pdf.set_fill_color(*COR_FUNDO)
        pdf.rect(0, 0, 297, 210, "F")
        
        # Barra Lateral Esquerda
        pdf.set_fill_color(*COR_VERDE)
        pdf.rect(0, 0, 35, 210, "F")
        
        # Linha Decorativa Dourada (Vertical)
        pdf.set_fill_color(*COR_DOURADO)
        pdf.rect(35, 0, 2, 210, "F")
        
        # Moldura de Borda
        pdf.set_draw_color(*COR_DOURADO)
        pdf.set_line_width(1)
        pdf.rect(10, 10, 277, 190)
        
        # --- IMAGENS ---
        # 1. Logo (na barra lateral)
        if os.path.exists("assets/logo.jpg"):
            pdf.image("assets/logo.jpg", x=5, y=20, w=25)
        elif os.path.exists("assets/logo.png"):
             pdf.image("assets/logo.png", x=5, y=20, w=25)
             
        # 2. Selo Dourado (Canto Inferior Direito)
        if os.path.exists("assets/selo_dourado.jpg"):
            pdf.image("assets/selo_dourado.jpg", x=235, y=130, w=40)
            
        # 3. QR Code (Canto Superior Direito)
        qr_path = gerar_qrcode(codigo)
        if qr_path and os.path.exists(qr_path):
            pdf.image(qr_path, x=250, y=20, w=25)
            pdf.set_xy(245, 45)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(35, 5, "Verificar Autenticidade", align="C")

        # --- CONTEÚDO ---
        # Ajuste de margem para pular a barra lateral
        margem_esq = 40
        largura_util = 297 - margem_esq - 10
        
        pdf.set_left_margin(margem_esq)
        
        # Título
        pdf.set_y(40)
        pdf.set_font("Helvetica", "B", 36)
        pdf.set_text_color(*COR_VERDE)
        pdf.cell(0, 15, "CERTIFICADO", ln=True, align="C")
        
        pdf.set_font("Helvetica", "", 14)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 10, "DE CONCLUSÃO DE EXAME TEÓRICO", ln=True, align="C")
        
        pdf.ln(15)
        
        # Corpo
        pdf.set_font("Helvetica", "", 16)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, "Certificamos que o aluno(a)", ln=True, align="C")
        
        # Nome do Aluno
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 32)
        pdf.set_text_color(*COR_DOURADO)
        try: nome_limpo = usuario_nome.upper().encode('latin-1', 'replace').decode('latin-1')
        except: nome_limpo = usuario_nome.upper()
        pdf.cell(0, 15, nome_limpo, ln=True, align="C")
        
        pdf.ln(5)
        
        # Faixa
        pdf.set_font("Helvetica", "", 16)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, "Concluiu com êxito a avaliação técnica para a faixa", ln=True, align="C")
        
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 26)
        pdf.set_text_color(*COR_VERDE)
        pdf.cell(0, 15, faixa.upper(), ln=True, align="C")
        
        # Detalhes (Data, Nota, Código)
        pdf.ln(15)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(80, 80, 80)
        data_hoje = datetime.now().strftime("%d/%m/%Y")
        info = f"Data de Emissão: {data_hoje}   |   Nota Final: {pontuacao:.1f}%   |   Código: {codigo}"
        pdf.cell(0, 8, info, ln=True, align="C")
        
        # Assinatura
        pdf.ln(15)
        y_linha = pdf.get_y()
        pdf.set_draw_color(50, 50, 50)
        pdf.line(margem_esq + 40, y_linha, 297 - 40, y_linha) # Linha centralizada na área útil
        
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(*COR_VERDE)
        pdf.cell(0, 6, "COORDENAÇÃO TÉCNICA - BJJ DIGITAL", ln=True, align="C")
        
        return pdf.output(dest='S').encode('latin-1'), f"Certificado_{nome_limpo.split()[0]}.pdf"
    except Exception as e:
        print(f"Erro PDF: {e}")
        return None, None

# =========================================
# 6. REGRAS DO EXAME
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
