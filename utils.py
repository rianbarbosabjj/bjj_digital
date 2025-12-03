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
# CONFIGURAÇÃO DE CORES DAS FAIXAS (RGB)
# =========================================
CORES_FAIXAS = {
    "BRANCA": (50, 50, 50),      # Cinza Escuro (para ler no papel branco)
    "CINZA": (128, 128, 128),    # Cinza
    "AMARELA": (204, 169, 0),    # Amarelo Escuro (Ouro)
    "LARANJA": (255, 140, 0),    # Laranja
    "VERDE": (0, 100, 0),        # Verde Escuro
    "AZUL": (0, 0, 139),         # Azul Escuro
    "ROXA": (128, 0, 128),       # Roxo
    "MARROM": (101, 67, 33),     # Marrom
    "PRETA": (0, 0, 0)           # Preto
}

def get_cor_faixa(nome_faixa):
    """Retorna a tupla RGB baseada no nome da faixa."""
    for chave, cor in CORES_FAIXAS.items():
        if chave in nome_faixa.upper():
            return cor
    return (0, 0, 0) # Default Preto

# =========================================
# FUNÇÃO: NORMALIZAR VÍDEO
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
# FUNÇÃO: UPLOAD DE MÍDIA
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
        return f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/{blob_path_encoded}?alt=media&token={access_token}"
    except Exception as e:
        st.error(f"Erro Upload: {e}")
        return None

# =========================================
# FUNÇÕES DE BANCO DE QUESTÕES (LEGADO/ADMIN)
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
# FUNÇÕES GERAIS
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
# SEGURANÇA
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
# CÓDIGOS E QR CODE
# =========================================
def gerar_codigo_verificacao():
    return f"BJJ-{datetime.now().year}-{random.randint(10000,99999)}"

def gerar_qrcode(codigo):
    try:
        os.makedirs("temp", exist_ok=True)
        caminho_qr = f"temp/qr_{codigo}.png"
        # Link para validar (exemplo)
        url_validacao = f"https://bjjdigital.streamlit.app/?validar={codigo}"
        
        qr = qrcode.QRCode(version=1, box_size=10, border=1)
        qr.add_data(url_validacao)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(caminho_qr)
        return caminho_qr
    except: return None

# =========================================
# GERADOR DE PDF (NOVO LAYOUT)
# =========================================
@st.cache_data(show_spinner=False)
def gerar_pdf(usuario_nome, faixa, pontuacao, total, codigo, professor=None):
    try:
        pdf = FPDF("L", "mm", "A4")
        pdf.add_page()
        
        # --- CONFIGURAÇÃO DE CORES ---
        COR_FUNDO = (255, 255, 252)      # Papel levemente creme
        COR_VERDE = (14, 45, 38)         # Verde BJJ
        COR_DOURADO = (218, 165, 32)     # Dourado Metálico
        COR_PRETO = (30, 30, 30)
        
        # Fundo
        pdf.set_fill_color(*COR_FUNDO)
        pdf.rect(0, 0, 297, 210, "F")
        
        # Barra Lateral Esquerda
        pdf.set_fill_color(*COR_VERDE)
        pdf.rect(0, 0, 25, 210, "F")
        pdf.set_fill_color(*COR_DOURADO)
        pdf.rect(25, 0, 2, 210, "F") # Linha fina dourada separando
        
        # Borda Dupla Dourada no Corpo
        pdf.set_draw_color(*COR_DOURADO)
        pdf.set_line_width(1)
        pdf.rect(35, 10, 252, 190) # Borda externa
        pdf.set_line_width(0.3)
        pdf.rect(37, 12, 248, 186) # Borda interna fina

        margem_conteudo = 45
        largura_util = 297 - margem_conteudo - 15
        centro_x = margem_conteudo + (largura_util / 2)

        # --- CABEÇALHO (LOGO E QR CODE) ---
        y_topo = 20
        
        # 1. Logo (Esquerda, alinhado com QR Code)
        logo_path = None
        if os.path.exists("assets/logo.jpg"): logo_path = "assets/logo.jpg"
        elif os.path.exists("assets/logo.png"): logo_path = "assets/logo.png"
        
        if logo_path:
            pdf.image(logo_path, x=margem_conteudo, y=y_topo, w=30)
        
        # 2. Bloco de Autenticidade (Direita)
        qr_path = gerar_qrcode(codigo)
        if qr_path and os.path.exists(qr_path):
            # Texto "Verificar Autenticidade" (EM CIMA)
            pdf.set_xy(240, y_topo)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(40, 5, "Verificar Autenticidade", align="C")
            
            # Imagem QR Code (MEIO)
            pdf.image(qr_path, x=250, y=y_topo + 6, w=20)
            
            # Código escrito (EMBAIXO)
            pdf.set_xy(240, y_topo + 27)
            pdf.set_font("Courier", "B", 9)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(40, 5, codigo, align="C")

        # --- TÍTULO PRINCIPAL ---
        pdf.set_y(50)
        pdf.set_x(margem_conteudo)
        pdf.set_font("Helvetica", "B", 38)
        pdf.set_text_color(*COR_VERDE)
        pdf.cell(largura_util, 15, "CERTIFICADO", ln=True, align="C")
        
        pdf.set_font("Helvetica", "", 14)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(largura_util, 10, "DE CONCLUSÃO DE EXAME TEÓRICO", ln=True, align="C")
        
        pdf.ln(10)
        
        # --- CORPO DO TEXTO ---
        pdf.set_font("Helvetica", "", 16)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(largura_util, 10, "Certificamos que o aluno(a)", ln=True, align="C")
        
        # --- NOME DO ALUNO (ADAPTÁVEL) ---
        try: nome_limpo = usuario_nome.upper().encode('latin-1', 'replace').decode('latin-1')
        except: nome_limpo = usuario_nome.upper()
        
        # Lógica para reduzir fonte se nome for grande
        tam_fonte = 34
        pdf.set_font("Helvetica", "B", tam_fonte)
        largura_texto = pdf.get_string_width(nome_limpo)
        
        while largura_texto > (largura_util - 20) and tam_fonte > 12:
            tam_fonte -= 1
            pdf.set_font("Helvetica", "B", tam_fonte)
            largura_texto = pdf.get_string_width(nome_limpo)
        
        pdf.set_text_color(*COR_DOURADO)
        pdf.cell(largura_util, 20, nome_limpo, ln=True, align="C")
        
        # --- CONTINUAÇÃO TEXTO ---
        pdf.set_font("Helvetica", "", 16)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(largura_util, 10, "Concluiu com êxito a avaliação técnica e está apto à faixa", ln=True, align="C")
        
        # --- FAIXA (COLORIDA) ---
        pdf.ln(5)
        cor_faixa = get_cor_faixa(faixa)
        pdf.set_text_color(*cor_faixa)
        pdf.set_font("Helvetica", "B", 32)
        pdf.cell(largura_util, 15, faixa.upper(), ln=True, align="C")
        
        # --- DETALHES FINAIS ---
        pdf.ln(10)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(100, 100, 100)
        data_hoje = datetime.now().strftime("%d/%m/%Y")
        info = f"Data de Emissão: {data_hoje}   |   Aproveitamento: {pontuacao:.1f}%"
        pdf.cell(largura_util, 8, info, ln=True, align="C")
        
        # --- ASSINATURA ---
        pdf.ln(15)
        y_assinatura = pdf.get_y()
        
        # Linha da assinatura
        pdf.set_draw_color(50, 50, 50)
        pdf.set_line_width(0.5)
        x_line_start = centro_x - 60
        x_line_end = centro_x + 60
        pdf.line(x_line_start, y_assinatura, x_line_end, y_assinatura)
        
        pdf.set_xy(x_line_start, y_assinatura + 2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*COR_VERDE)
        pdf.cell(120, 6, "COORDENAÇÃO TÉCNICA - BJJ DIGITAL", align="C")
        
        # --- SELO DOURADO (INFERIOR DIREITO) ---
        if os.path.exists("assets/selo_dourado.jpg"):
            # Posicionado no canto inferior direito, dentro da margem
            pdf.image("assets/selo_dourado.jpg", x=245, y=155, w=35)

        return pdf.output(dest='S').encode('latin-1'), f"Certificado_{nome_limpo.split()[0]}.pdf"
    except Exception as e:
        print(f"Erro PDF: {e}")
        return None, None

# =========================================
# REGRAS DO EXAME
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
