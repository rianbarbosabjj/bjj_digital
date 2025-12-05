import os
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
# CONFIGURAÇÃO DE CORES DAS FAIXAS (RGB)
# =========================================
CORES_FAIXAS = {
    "CINZA E BRANCA": (128, 128, 128), "CINZA": (128, 128, 128), "CINZA E PRETA": (128, 128, 128), 
    "AMARELA E BRANCA": (204, 169, 0), "AMARELA": (204, 169, 0), "AMARELA E PRETA": (204, 169, 0),
    "LARANJA E BRANCA": (255, 140, 0), "LARANJA": (255, 140, 0), "LARANJA E PRETA": (255, 140, 0),
    "VERDE e BRANCA": (0, 100, 0), "VERDE": (0, 100, 0), "VERDE E PRETA": (0, 100, 0),
    "AZUL": (0, 0, 139), "ROXA": (128, 0, 128), "MARROM": (101, 67, 33), "PRETA": (0, 0, 0)
}

def get_cor_faixa(nome_faixa):
    for chave, cor in CORES_FAIXAS.items():
        if chave in nome_faixa.upper():
            return cor
    return (0, 0, 0) 

# =========================================
# FUNÇÕES DE MÍDIA E UPLOAD
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
        return f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/{blob_path_encoded}?alt=media&token={access_token}"
    except Exception as e:
        st.error(f"Erro Upload: {e}")
        return None

# =========================================
# IA ANTI-DUPLICIDADE (SAFE MODE)
# =========================================
# Tenta importar as bibliotecas de IA. Se falhar, usa função dummy.
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    
    @st.cache_resource
    def carregar_modelo_ia():
        return SentenceTransformer('all-MiniLM-L6-v2')

    def verificar_duplicidade_ia(nova_pergunta, lista_existentes, threshold=0.85):
        if not lista_existentes: return False, None
        try:
            model = carregar_modelo_ia()
            embedding_novo = model.encode([nova_pergunta])
            
            textos_existentes = [str(q.get('pergunta', '')) for q in lista_existentes]
            if not textos_existentes: return False, None
            
            embeddings_existentes = model.encode(textos_existentes)
            scores = cosine_similarity(embedding_novo, embeddings_existentes)[0]
            
            max_score = np.max(scores)
            idx_max = np.argmax(scores)
            
            if max_score >= threshold:
                return True, f"{textos_existentes[idx_max]} ({max_score*100:.1f}%)"
            return False, None
        except Exception as e:
            print(f"Erro IA: {e}")
            return False, None

except ImportError:
    # Fallback caso não tenha as bibliotecas instaladas
    def verificar_duplicidade_ia(n, l, t=0.85): 
        return False, None

# =========================================
# DEMAIS FUNÇÕES (LEGACY & TOOLS)
# =========================================
def carregar_todas_questoes(): return []
def salvar_questoes(t, q): pass

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

def gerar_codigo_verificacao():
    try:
        db = get_db()
        aggregate_query = db.collection('resultados').count()
        snapshots = aggregate_query.get()
        total_existente = int(snapshots[0][0].value)
        proximo_num = total_existente + 1
        return f"BJJDIGITAL-{datetime.now().year}-{proximo_num:04d}"
    except:
        return f"BJJDIGITAL-{datetime.now().year}-{random.randint(1000,9999)}"

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

@st.cache_data(show_spinner=False)
def gerar_pdf(usuario_nome, faixa, pontuacao, total, codigo, professor=None):
    try:
        pdf = FPDF("L", "mm", "A4")
        pdf.add_page()
        CF, CV, CD = (255, 255, 252), (14, 45, 38), (218, 165, 32)
        pdf.set_fill_color(*CF); pdf.rect(0,0,297,210,"F")
        pdf.set_fill_color(*CV); pdf.rect(0,0,35,210,"F")
        pdf.set_fill_color(*CD); pdf.rect(35,0,2,210,"F")
        pdf.set_draw_color(*CD); pdf.set_line_width(1); pdf.rect(10,10,277,190)
        
        def find_img(name):
            if os.path.exists(f"assets/{name}"): return f"assets/{name}"
            if os.path.exists(name): return name
            return None

        logo = find_img("logo.jpg") or find_img("logo.png")
        if logo: pdf.image(logo, x=45, y=20, w=30)

        qr = gerar_qrcode(codigo)
        if qr and os.path.exists(qr):
            pdf.image(qr, x=250, y=26, w=20)

        pdf.set_y(50); pdf.set_left_margin(45)
        pdf.set_font("Helvetica", "B", 36); pdf.set_text_color(*CV)
        pdf.cell(0, 15, "CERTIFICADO", ln=True, align="C")
        pdf.set_font("Helvetica", "", 14); pdf.set_text_color(80,80,80)
        pdf.cell(0, 10, "DE CONCLUSÃO DE EXAME TEÓRICO", ln=True, align="C")
        pdf.ln(10)

        pdf.set_font("Helvetica", "", 16); pdf.set_text_color(0,0,0)
        pdf.cell(0, 10, "Certificamos que o aluno(a)", ln=True, align="C")
        
        pdf.ln(5)
        try: nm = usuario_nome.upper().encode('latin-1','replace').decode('latin-1')
        except: nm = str(usuario_nome).upper()
        
        pdf.set_font("Helvetica", "B", 30)
        pdf.set_text_color(*CD); pdf.cell(0, 15, nm, ln=True, align="C")
        
        pdf.ln(5); pdf.set_font("Helvetica", "", 16); pdf.set_text_color(0,0,0)
        pdf.cell(0, 10, "Concluiu com êxito a avaliação para a faixa", ln=True, align="C")
        pdf.ln(5)
        pdf.set_text_color(*get_cor_faixa(faixa))
        pdf.set_font("Helvetica", "B", 32)
        pdf.cell(0, 15, faixa.upper(), ln=True, align="C")

        pdf.ln(10); pdf.set_font("Helvetica", "", 11); pdf.set_text_color(100,100,100)
        pdf.cell(0, 8, f"Emissão: {datetime.now().strftime('%d/%m/%Y')} | Nota: {pontuacao:.1f}%", ln=True, align="C")

        return pdf.output(dest='S').encode('latin-1'), f"Certificado.pdf"
    except: return None, None

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
