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
    "CINZA E BRANCA": (150, 150, 150), "CINZA": (128, 128, 128), "CINZA E PRETA": (100, 100, 100), 
    "AMARELA E BRANCA": (240, 230, 140), "AMARELA": (255, 215, 0), "AMARELA E PRETA": (184, 134, 11),
    "LARANJA E BRANCA": (255, 160, 122), "LARANJA": (255, 140, 0), "LARANJA E PRETA": (200, 100, 0),
    "VERDE e BRANCA": (144, 238, 144), "VERDE": (0, 128, 0), "VERDE E PRETA": (0, 100, 0),
    "AZUL": (0, 0, 205), "ROXA": (128, 0, 128), "MARROM": (139, 69, 19), "PRETA": (0, 0, 0)
}

def get_cor_faixa(nome_faixa):
    for chave, cor in CORES_FAIXAS.items():
        if chave in nome_faixa.upper():
            return cor
    return (255, 255, 255)

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
    IA_ATIVADA = False
    def verificar_duplicidade_ia(n, l, t=0.75): 
        return False, "IA não instalada"

# =========================================
# DEMAIS FUNÇÕES
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
        total = int(snapshots[0][0].value)
        return f"BJJDIGITAL-{datetime.now().year}-{total+1:04d}"
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

# =========================================
# GERADOR DE PDF (CORRIGIDO)
# =========================================
@st.cache_data(show_spinner=False)
def gerar_pdf(usuario_nome, faixa, pontuacao, total, codigo, professor="Professor(a) Responsável"):
    try:
        # 1. Preparação
        # Limpa texto para evitar erros de encode latin-1
        def limpa(txt):
            if not txt: return ""
            return str(txt).encode('latin-1', 'replace').decode('latin-1')

        pdf = FPDF("L", "mm", "A4")
        pdf.add_page()
        
        # Cores
        C_BRANCO = (255, 255, 255)
        C_DOURADO = (218, 165, 32)
        C_FUNDO = (14, 45, 38) 

        # 2. Fundo
        fundo_ok = False
        for ext in [".jpg", ".png", ".jpeg"]:
            path = f"assets/fundo_certificado{ext}"
            if os.path.exists(path):
                pdf.image(path, x=0, y=0, w=297, h=210)
                fundo_ok = True
                break
        
        if not fundo_ok:
            # Fallback se não achar imagem
            pdf.set_fill_color(*C_FUNDO)
            pdf.rect(0,0,297,210,"F")
            pdf.set_draw_color(*C_DOURADO)
            pdf.set_line_width(2)
            pdf.rect(10,10,277,190)

        # 3. Fonte Assinatura
        fonte_ass = "Helvetica"
        if os.path.exists("assets/Allura-Regular.ttf"):
            try:
                # REMOVIDO o uni=True que causava erro
                pdf.add_font('Allura', '', 'assets/Allura-Regular.ttf', uni=True) 
                fonte_ass = 'Allura'
            except:
                # Se falhar (ex: versão lib), tenta sem uni=True ou fallback
                try: 
                    pdf.add_font('Allura', '', 'assets/Allura-Regular.ttf')
                    fonte_ass = 'Allura'
                except: pass

        # 4. Textos do Certificado (Coordenadas calibradas)
        
        # Cabeçalho
        pdf.set_y(40)
        pdf.set_font("Helvetica", "B", 32)
        pdf.set_text_color(*C_BRANCO)
        pdf.cell(0, 10, limpa("CERTIFICADO"), ln=True, align="C")
        
        pdf.set_font("Helvetica", "", 12)
        pdf.set_text_color(200, 200, 200)
        pdf.cell(0, 8, limpa("DE EXAME TEÓRICO DE FAIXA"), ln=True, align="C")
        
        # Texto "Certificamos que..."
        pdf.ln(15)
        pdf.set_font("Helvetica", "", 16)
        pdf.set_text_color(*C_BRANCO)
        pdf.cell(0, 10, limpa("Certificamos que o aluno(a)"), ln=True, align="C")

        # NOME DO ALUNO (Auto-ajuste)
        pdf.ln(5)
        nome_final = limpa(usuario_nome.upper().strip())
        
        # Começa com fonte 40 e diminui se não couber
        sz = 40
        pdf.set_font("Helvetica", "B", sz)
        while pdf.get_string_width(nome_final) > 250 and sz > 12:
            sz -= 2
            pdf.set_font("Helvetica", "B", sz)
            
        pdf.set_text_color(*C_DOURADO)
        pdf.cell(0, 15, nome_final, ln=True, align="C")

        # Texto "Foi aprovado..."
        pdf.ln(5)
        pdf.set_font("Helvetica", "", 16)
        pdf.set_text_color(*C_BRANCO)
        pdf.cell(0, 10, limpa("foi APROVADO(A) no Exame teórico, estando apto(a) à faixa:"), ln=True, align="C")
        
        # FAIXA
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 32)
        cor_fx = get_cor_faixa(faixa)
        if sum(cor_fx) < 100: pdf.set_text_color(255,255,255) # Branco se faixa for preta
        else: pdf.set_text_color(*cor_fx)
        
        pdf.cell(0, 15, limpa(faixa.upper()), ln=True, align="C")

        # 5. Rodapé
        
        # Esquerda: Data e Código
        pdf.set_y(155)
        pos_x_esq = 35
        
        pdf.set_xy(pos_x_esq, 160)
        pdf.set_font("Helvetica", "", 12)
        pdf.set_text_color(200, 200, 200)
        
        data_txt = datetime.now().strftime('%d/%m/%Y')
        pdf.cell(60, 6, limpa(f"Data de Emissão: {data_txt}"), ln=True, align="L")
        
        pdf.set_xy(pos_x_esq, 166)
        pdf.set_font("Courier", "", 9)
        pdf.cell(60, 5, f"Cód: {codigo}", align="L")

        # Direita: Assinatura
        centro_dir = 220 
        pdf.set_xy(centro_dir - 40, 150)
        
        # Nome Professor
        if fonte_ass == 'Allura': pdf.set_font('Allura', "", 28)
        else: pdf.set_font("Helvetica", "I", 24)
            
        pdf.set_text_color(*C_DOURADO)
        pdf.cell(80, 10, limpa(professor(a)), ln=True, align="C")
        
        # Linha
        pdf.set_xy(centro_dir - 30, 162)
        pdf.set_draw_color(255, 255, 255)
        pdf.set_line_width(0.5)
        pdf.line(centro_dir - 30, 162, centro_dir + 30, 162)
        
        # Cargo
        pdf.set_xy(centro_dir - 40, 165)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(200, 200, 200)
        pdf.cell(80, 5, limpa("Professor(a) Responsável"), align="C")

        # 6. QR Code
        qr_path = gerar_qrcode(codigo)
        if qr_path and os.path.exists(qr_path):
            # No centro inferior
            pdf.image(qr_path, x=136, y=160, w=25)
            
            pdf.set_xy(128, 186)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(150, 150, 150)
            pdf.cell(40, 4, limpa("Verificar Autenticidade"), align="C")

        # GERA O BINÁRIO
        # Importante: dest='S' retorna string em latin-1 por padrão no FPDF antigo
        return pdf.output(dest='S').encode('latin-1'), f"Certificado_{usuario_nome.split()[0]}.pdf"

    except Exception as e:
        # ISSO VAI MOSTRAR O ERRO NA TELA SE FALHAR
        st.error(f"Erro ao gerar PDF: {e}")
        return None, None

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
