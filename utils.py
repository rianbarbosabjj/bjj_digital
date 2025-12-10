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
import json
from urllib.parse import quote
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fpdf import FPDF
# Se você tiver um arquivo database.py, mantenha essa linha. 
# Caso contrário, certifique-se de que get_db está definido neste arquivo.
from database import get_db 
from firebase_admin import firestore, storage 

# =========================================
# CONFIGURAÇÃO DE CORES E FAIXAS
# =========================================
CORES_FAIXAS = {
    "CINZA E BRANCA": (150, 150, 150), "CINZA": (128, 128, 128), "CINZA E PRETA": (100, 100, 100), 
    "AMARELA E BRANCA": (240, 230, 140), "AMARELA": (255, 215, 0), "AMARELA E PRETA": (184, 134, 11),
    "LARANJA E BRANCA": (255, 160, 122), "LARANJA": (255, 140, 0), "LARANJA E PRETA": (200, 100, 0),
    "VERDE e BRANCA": (144, 238, 144), "VERDE": (0, 128, 0), "VERDE E PRETA": (0, 100, 0),
    "AZUL": (0, 0, 205), "ROXA": (128, 0, 128), "MARROM": (139, 69, 19), "PRETA": (0, 0, 0)
}

# --- ADIÇÕES NECESSÁRIAS PARA O PROFESSOR.PY ---
# Lista completa para os selects
FAIXAS_COMPLETAS = [
    "Branca", 
    "Cinza e Branca", "Cinza", "Cinza e Preta",
    "Amarela e Branca", "Amarela", "Amarela e Preta",
    "Laranja e Branca", "Laranja", "Laranja e Preta",
    "Verde e Branca", "Verde", "Verde e Preta",
    "Azul", "Roxa", "Marrom", "Preta"
]

NIVEIS_DIFICULDADE = [1, 2, 3, 4]

MAPA_NIVEIS = {
    1: "Fácil", 
    2: "Médio", 
    3: "Difícil", 
    4: "Mestre"
}
# -----------------------------------------------

def get_cor_faixa(nome_faixa):
    for chave, cor in CORES_FAIXAS.items():
        if chave in str(nome_faixa).upper():
            return cor
    return (0, 0, 0) 

def get_badge_nivel(nivel):
    """Retorna um ícone visual para o nível da questão"""
    badges = {1: "🟢", 2: "🟡", 3: "🔴", 4: "💀"}
    return badges.get(nivel, "⚪")

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
# IA ANTI-DUPLICIDADE
# =========================================
IA_ATIVADA = False 
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    IA_ATIVADA = True
    @st.cache_resource
    def carregar_modelo_ia():
        return SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    def verificar_duplicidade_ia(nova_pergunta, lista_existentes, threshold=0.75):
        try:
            if not lista_existentes: return False, None
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
        except: return False, None
except ImportError:
    IA_ATIVADA = False
    def verificar_duplicidade_ia(n, l, t=0.75): return False, "IA não instalada"

# =========================================
# FUNÇÕES GERAIS E DB
# =========================================
def carregar_todas_questoes(): return []
def salvar_questoes(t, q): pass

def auditoria_ia_questao(p, a, c): return "Indisponível"
def auditoria_ia_openai(p, a, c): return "Indisponível"

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
        if r.status_code == 200:
            d = r.json()
            if "erro" not in d:
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
        msg['Subject'] = "Recuperação de Senha - BJJ Digital"
        msg['From'] = s_email
        msg['To'] = dest
        corpo = f"<html><body><h2>Recuperação</h2><p>Senha: <b>{senha}</b></p></body></html>"
        msg.attach(MIMEText(corpo, 'html'))
        server = smtplib.SMTP("smtp.zoho.com", 587)
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
        total = int(snapshots[0][0].value)
        return f"BJJDIGITAL-{datetime.now().year}-{total+1:04d}"
    except:
        return f"BJJDIGITAL-{datetime.now().year}-{random.randint(1000,9999)}"

# =================================
# GERA O CERTIFICADO
# =================================
def gerar_qrcode(codigo):
    import qrcode
    import os

    pasta = "qrcodes"
    os.makedirs(pasta, exist_ok=True)

    caminho = f"{pasta}/{codigo}.png"

    # Novo link de validação
    url = f"https://bjjdigital.com.br/verificar.html?codigo={codigo}"

    # Gera apenas se ainda não existir
    if not os.path.exists(caminho):
        img = qrcode.make(url)
        img.save(caminho)

    return caminho

@st.cache_data(show_spinner=False)
def gerar_pdf(usuario_nome, faixa, pontuacao, total, codigo, professor="Professor(a) Responsavel"):
    
    def limpa(txt):
        # Remove acentos para evitar erros com fontes padrão do FPDF (Arial/Helvetica)
        if not txt: return ""
        return unicodedata.normalize('NFKD', str(txt)).encode('ASCII', 'ignore').decode('ASCII')

    # ==========================
    # CONFIGURAÇÃO DO PDF
    # ==========================
    pdf = FPDF("L", "mm", "A4")
    pdf.set_auto_page_break(False)
    pdf.add_page()

    L, H = 297, 210  # Dimensões A4 Paisagem

    # Cores (ainda usadas em textos, não no fundo)
    C_BRANCO_GELO = (252, 252, 252)  # fallback se não achar o PNG
    C_DOURADO = (218, 165, 32)
    C_CINZA = (100, 100, 100)
    C_TEXTO = (50, 50, 50)

    # ===== FUNDO COM Borda + Metálico (PNG gerado do SVG) =====
    bg_path = None
    if os.path.exists("assets/fundo_certificado_bjj.png"):
        bg_path = "assets/fundo_certificado_bjj.png"
    elif os.path.exists("assets/fundo_certificado_bjj.jpg"):
        bg_path = "assets/fundo_certificado_bjj.jpg"

    if bg_path:
        # imagem ocupa toda a página A4 paisagem
        pdf.image(bg_path, x=0, y=0, w=L, h=H)
    else:
        # fallback: fundo liso se a imagem não for encontrada
        pdf.set_fill_color(*C_BRANCO_GELO)
        pdf.rect(0, 0, L, H, "F")

    # (Não desenhamos mais bordas aqui – já estão no fundo)

    # ===== TÍTULO (Com efeito de sombra) =====
    titulo = "CERTIFICADO DE EXAME TEORICO"
    
    # Sombra do título
    pdf.set_y(28)
    pdf.set_font("Helvetica", "B", 32)
    pdf.set_text_color(200, 180, 100)  # Sombra clara
    pdf.cell(0, 16, titulo, ln=False, align="C")

    # Título principal
    pdf.set_y(26.8)
    pdf.set_text_color(*C_DOURADO)
    pdf.cell(0, 16, titulo, ln=True, align="C")

    # ===== LOGO =====
    if os.path.exists("assets/logo.png"):
        pdf.image("assets/logo.png", x=(L/2)-18, y=52, w=36)
    
    # ===== TEXTO INTRODUTÓRIO =====
    pdf.set_y(90)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(*C_TEXTO)
    pdf.cell(0, 8, "Certificamos que o aluno(a):", ln=True, align="C")

    # ===== NOME DO ALUNO =====
    nome = limpa(usuario_nome.upper().strip())
    
    # Ajuste dinâmico do tamanho da fonte para nomes longos
    size = 42
    pdf.set_font("Helvetica", "B", size)
    while pdf.get_string_width(nome) > 240 and size > 16:
        size -= 2
        pdf.set_font("Helvetica", "B", size)
    
    pdf.set_text_color(*C_DOURADO)
    pdf.cell(0, 20, nome, ln=True, align="C")

    # ===== TEXTO DE FAIXA =====
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(*C_TEXTO)
    pdf.cell(0, 8, "foi aprovado(a) no exame teórico para a faixa:", ln=True, align="C")

    # ===== NOME DA FAIXA =====
    pdf.ln(4)
    cor_fx = get_cor_faixa(faixa)
    
    pdf.set_font("Helvetica", "B", 38)
    pdf.set_text_color(*cor_fx)
    pdf.cell(0, 18, limpa(faixa.upper()), ln=True, align="C")

    # ===== RODAPÉ =====
    y_base = 151

    # Selo Dourado
    selo = "assets/selo_dourado.png"
    if os.path.exists(selo):
        pdf.image(selo, x=32, y=y_base, w=32)
        pdf.set_xy(25, y_base + 33)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*C_CINZA)
        pdf.cell(45, 4, "Certificacao Oficial", align="C")

    # Assinatura
    pdf.set_xy(0, y_base + 4)
    
    # Tenta carregar fonte manuscrita, senão usa itálico padrão
    font_ass = "Helvetica"
    style_ass = "I"  # Italic
    
    if os.path.exists("assets/Allura-Regular.ttf"):
        try:
            pdf.add_font("Allura", "", "assets/Allura-Regular.ttf", uni=True)
            font_ass = "Allura"
            style_ass = ""
        except:
            pass
            
    pdf.set_font(font_ass, style_ass, 28 if font_ass == "Allura" else 20)
    pdf.set_text_color(*C_DOURADO)
    pdf.cell(0, 14, limpa(professor), ln=True, align="C")

    # Linha da assinatura
    pdf.set_draw_color(60, 60, 60)
    pdf.set_line_width(0.4)
    x_line_start = (L/2) - 40
    x_line_end = (L/2) + 40
    y_line = pdf.get_y() + 1
    pdf.line(x_line_start, y_line, x_line_end, y_line)

    pdf.ln(4)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*C_CINZA)
    pdf.cell(0, 5, "Professor(a) Responsavel", align="C")

    # QR Code + Info Lateral
    qr_path = gerar_qrcode(codigo)
    if qr_path and os.path.exists(qr_path):
        pdf.image(qr_path, x=L-56, y=y_base, w=32)
        
    pdf.set_xy(L-64, y_base + 32)
    pdf.set_font("Courier", "", 8)
    pdf.set_text_color(*C_CINZA)
    pdf.cell(45, 4, f"Ref: {codigo}", align="C")
    
    pdf.set_xy(L-64, y_base + 36)
    pdf.cell(45, 4, f"{datetime.now().strftime('%d/%m/%Y')}", align="C")

    return pdf.output(dest="S").encode("latin-1"), f"Certificado_{nome.split()[0]}.pdf"


# =========================================
# LÓGICA DE EXAME E DB
# =========================================
def verificar_elegibilidade_exame(dados_usuario):
    status = dados_usuario.get('status_exame', 'pendente')
    if status == 'bloqueado': return False, "Exame bloqueado. Contate o professor."
    if status == 'reprovado':
        try:
            last = dados_usuario.get('data_ultimo_exame')
            if last:
                dt_last = last.replace(tzinfo=None) if hasattr(last, 'date') else datetime.fromisoformat(str(last).replace('Z',''))
                if (datetime.now() - dt_last).days < 3: return False, "Aguarde 3 dias para tentar novamente."
        except: pass
    return True, "Autorizado"

def registrar_inicio_exame(uid):
    try: get_db().collection('usuarios').document(uid).update({"status_exame": "em_andamento", "inicio_exame_temp": datetime.now().isoformat(), "status_exame_em_andamento": True})
    except: pass

def registrar_fim_exame(uid, aprovado):
    try:
        stt = "aprovado" if aprovado else "reprovado"
        get_db().collection('usuarios').document(uid).update({"status_exame": stt, "exame_habilitado": False, "data_ultimo_exame": firestore.SERVER_TIMESTAMP, "status_exame_em_andamento": False})
        return True
    except: return False

def bloquear_por_abandono(uid):
    try: get_db().collection('usuarios').document(uid).update({"status_exame": "bloqueado", "exame_habilitado": False, "status_exame_em_andamento": False})
    except: pass
