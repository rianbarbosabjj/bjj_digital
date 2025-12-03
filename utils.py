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
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fpdf import FPDF
from database import get_db
from firebase_admin import firestore, storage 

# =========================================
# FUNÇÃO DE UPLOAD ROBUSTA (TIPO FIREBASE)
# =========================================
def fazer_upload_imagem(arquivo):
    """
    Envia imagem para o Storage e gera um link estilo Firebase (público e permanente).
    """
    if not arquivo: return None
    
    try:
        bucket = storage.bucket() 
        
        # Gera nomes únicos
        ext = arquivo.name.split('.')[-1]
        blob_name = f"questoes/{uuid.uuid4()}.{ext}"
        blob = bucket.blob(blob_name)
        
        # Gera um token de acesso manual (igual o Firebase faz no frontend)
        access_token = str(uuid.uuid4())
        metadata = {"firebaseStorageDownloadTokens": access_token}
        blob.metadata = metadata
        
        # Faz o upload
        blob.upload_from_file(arquivo, content_type=arquivo.type)
        
        # Reconecta para aplicar o metadata (garantia)
        blob.patch()

        # Monta a URL manual do Firebase (Essa funciona sempre!)
        # Formato: https://firebasestorage.googleapis.com/v0/b/[BUCKET]/o/[NOME_COM_SLASH_ENCODED]?alt=media&token=[TOKEN]
        bucket_name = blob.bucket.name
        blob_path_encoded = blob_name.replace("/", "%2F") # Encode na barra é obrigatório
        
        final_url = f"https://firebasestorage.googleapis.com/v0/b/{bucket_name}/o/{blob_path_encoded}?alt=media&token={access_token}"
        
        return final_url
        
    except Exception as e:
        print(f"Erro no upload: {e}")
        return None

# =========================================
# 1. FUNÇÕES DE QUESTÕES
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
        lista = [doc.to_dict() for doc in docs]
        if lista: return lista
    except: pass

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
# 2. FUNÇÕES GERAIS
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
                    "logradouro": data.get("logradouro", "").upper(),
                    "bairro": data.get("bairro", "").upper(),
                    "cidade": data.get("localidade", "").upper(),
                    "uf": data.get("uf", "").upper()
                }
    except: pass
    return None

# =========================================
# 3. SEGURANÇA E E-MAIL
# =========================================
def gerar_senha_temporaria(tamanho=8):
    caracteres = string.ascii_letters + string.digits
    return ''.join(secrets.choice(caracteres) for i in range(tamanho))

def enviar_email_recuperacao(email_destino, nova_senha):
    try:
        sender_email = st.secrets.get("EMAIL_SENDER")
        sender_password = st.secrets.get("EMAIL_PASSWORD")
        smtp_server = st.secrets.get("EMAIL_SERVER")
        smtp_port = st.secrets.get("EMAIL_PORT")
        if not (sender_email and sender_password): return False
    except: return False

    msg = MIMEMultipart()
    msg['From'] = f"BJJ Digital <{sender_email}>"
    msg['To'] = email_destino
    msg['Subject'] = "Recuperação de Senha - BJJ Digital"
    corpo = f"<h3>Nova Senha: {nova_senha}</h3>"
    msg.attach(MIMEText(corpo, 'html'))

    try:
        porta = int(smtp_port) if smtp_port else 587
        if porta == 465: server = smtplib.SMTP_SSL(smtp_server, porta)
        else:
            server = smtplib.SMTP(smtp_server, porta)
            server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, email_destino, msg.as_string())
        server.quit()
        return True
    except: return False

# =========================================
# 4. CÓDIGOS E QR CODE
# =========================================
def gerar_codigo_verificacao():
    try:
        db = get_db()
        docs = db.collection('resultados').count().get()
        total = docs[0][0].value 
    except:
        total = random.randint(1000, 9999)
    
    sequencia = total + 1
    ano_atual = datetime.now().year
    return f"BJJDIGITAL-{ano_atual}-{sequencia:04d}"

def gerar_qrcode(codigo):
    import os
    os.makedirs("temp", exist_ok=True)
    caminho_qr = f"temp/qr_{codigo}.png"
    if os.path.exists(caminho_qr): return caminho_qr

    base_url = "https://bjjdigital.com.br/verificar"
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(f"{base_url}?codigo={codigo}")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(caminho_qr)
    return caminho_qr

# =========================================
# 5. PDF PREMIUM
# =========================================
@st.cache_data(show_spinner=False)
def gerar_pdf(usuario_nome, faixa, pontuacao, total, codigo, professor=None):
    try:
        pdf = FPDF("L", "mm", "A4")
        pdf.set_auto_page_break(False)
        pdf.add_page()
        
        cor_dourado = (184, 134, 11) 
        cor_preto = (25, 25, 25)
        cor_cinza = (100, 100, 100)
        cor_fundo = (252, 252, 250)

        pdf.set_fill_color(*cor_fundo)
        pdf.rect(0, 0, 297, 210, "F")

        largura_barra = 25 
        pdf.set_fill_color(*cor_preto)
        pdf.rect(0, 0, largura_barra, 210, "F")
        pdf.set_fill_color(*cor_dourado)
        pdf.rect(largura_barra, 0, 2, 210, "F")

        if os.path.exists("assets/logo.jpg"):
            try: pdf.image("assets/logo.jpg", x=5, y=20, w=15)
            except: pass
        elif os.path.exists("assets/logo.png"):
             try: pdf.image("assets/logo.png", x=5, y=20, w=15)
             except: pass
        
        x_inicio = largura_barra + 15
        largura_util = 297 - x_inicio - 15 
        centro_x = x_inicio + (largura_util / 2)

        pdf.set_y(45)
        pdf.set_font("Helvetica", "B", 24)
        pdf.set_text_color(*cor_dourado)
        titulo = "CERTIFICADO DE EXAME TEÓRICO DE FAIXA"
        pdf.cell(largura_util, 12, titulo, ln=1, align="C")
        
        pdf.ln(20)
        pdf.set_font("Helvetica", "", 16)
        pdf.set_text_color(*cor_preto)
        texto_intro = "Certificamos que o aluno(a)"
        pdf.cell(largura_util, 10, texto_intro, ln=1, align="C")

        pdf.ln(8)
        try: nome_limpo = usuario_nome.upper().encode('latin-1', 'replace').decode('latin-1')
        except: nome_limpo = usuario_nome.upper()

        tamanho_fonte = 28
        largura_maxima_nome = largura_util - 40
        while True:
            pdf.set_font("Helvetica", "B", tamanho_fonte)
            largura_texto = pdf.get_string_width(nome_limpo)
            if largura_texto <= largura_maxima_nome or tamanho_fonte <= 16: break
            tamanho_fonte -= 1

        pdf.set_text_color(*cor_dourado)
        x_nome = centro_x - (largura_texto / 2)
        pdf.set_xy(x_nome, pdf.get_y())
        pdf.cell(largura_texto, 14, nome_limpo, align='L')
        
        pdf.ln(20)
        pdf.set_font("Helvetica", "", 16)
        pdf.set_text_color(*cor_preto)
        texto_aprovacao = "foi APROVADO(A) no Exame teórico para a faixa"
        pdf.cell(largura_util, 10, texto_aprovacao, ln=1, align="C")
        
        pdf.ln(2)
        texto_apto = "estando apto(a) a ser provido(a) a faixa:"
        pdf.cell(largura_util, 10, texto_apto, ln=1, align="C")

        pdf.ln(15)
        y_linha = pdf.get_y()
        largura_linha = 180
        x_linha = centro_x - (largura_linha / 2)
        pdf.set_draw_color(*cor_preto)
        pdf.set_line_width(0.5)
        pdf.line(x_linha, y_linha, x_linha + largura_linha, y_linha)

        pdf.ln(20)
        pdf.set_font("Helvetica", "B", 32)
        pdf.set_text_color(*cor_preto)
        texto_faixa = f"{str(faixa).upper()}"
        pdf.cell(largura_util, 16, texto_faixa, ln=1, align="C")

        y_rodape = 160
        y_assinatura = y_rodape + 20
        
        if os.path.exists("assets/Allura-Regular.ttf"):
            pdf.add_font('Allura', '', 'assets/Allura-Regular.ttf', uni=True)
            pdf.set_font("Allura", "", 30)
        else:
            pdf.set_font("Helvetica", "I", 12)

        assinatura_texto = professor if professor else "Professor Responsável"
        pdf.set_xy(x_inicio, y_assinatura - 10)
        pdf.set_text_color(*cor_preto)
        pdf.cell(largura_util, 10, assinatura_texto, ln=1, align="C")
        
        largura_linha_assinatura = 80
        x_assinatura = centro_x - (largura_linha_assinatura / 2)
        pdf.set_draw_color(*cor_preto)
        pdf.set_line_width(0.3)
        pdf.line(x_assinatura, y_assinatura, x_assinatura + largura_linha_assinatura, y_assinatura)
        
        pdf.set_xy(x_assinatura, y_assinatura + 2)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*cor_cinza)
        pdf.cell(largura_linha_assinatura, 5, "Professor Responsável", align="C")
        
        if os.path.exists("assets/selo_dourado.jpg"):
            pdf.image("assets/selo_dourado.jpg", x=240, y=140, w=35)

        return pdf.output(dest='S').encode('latin-1'), f"Certificado_{usuario_nome.split()[0]}.pdf"
    except Exception as e:
        print(f"Erro PDF: {e}")
        return None, None

# =========================================
# 6. REGRAS DO EXAME
# =========================================
def verificar_elegibilidade_exame(usuario_data):
    status = usuario_data.get('status_exame', 'pendente')
    if status == 'aprovado':
        return False, "Você já foi APROVADO neste exame. Parabéns!"
    if status == 'bloqueado':
        return False, "Exame BLOQUEADO. Contate o professor."
    if status == 'reprovado':
        ultimo_teste = usuario_data.get('data_ultimo_exame')
        if ultimo_teste:
            try:
                if isinstance(ultimo_teste, str):
                    dt_ultimo = datetime.fromisoformat(ultimo_teste.replace('Z', ''))
                else:
                    dt_ultimo = ultimo_teste
                
                dt_ultimo = dt_ultimo.replace(tzinfo=None)
                agora = datetime.utcnow()
                diff = agora - dt_ultimo
                segundos_passados = diff.total_seconds()
                segundos_espera = 72 * 3600
                if segundos_passados < segundos_espera:
                    horas_restantes = (segundos_espera - segundos_passados) / 3600
                    return False, f"Reprovado. Aguarde {int(horas_restantes)+1}h para tentar novamente."
            except Exception as e:
                print(f"Erro data: {e}")
                return False, "Erro ao verificar data."
    return True, "OK"

def registrar_inicio_exame(usuario_id):
    try:
        db = get_db()
        agora_br = datetime.utcnow() 
        db.collection('usuarios').document(usuario_id).update({
            "status_exame": "em_andamento",
            "inicio_exame_temp": agora_br.isoformat(),
            "status_exame_em_andamento": True
        })
    except: pass

def registrar_fim_exame(usuario_id, aprovado):
    try:
        db = get_db()
        status = "aprovado" if aprovado else "reprovado"
        agora_br = datetime.utcnow()
        dados = {
            "status_exame": status,
            "data_ultimo_exame": agora_br.isoformat(),
            "status_exame_em_andamento": False
        }
        if aprovado:
            dados["exame_habilitado"] = False
            dados["exame_inicio"] = firestore.DELETE_FIELD
            dados["exame_fim"] = firestore.DELETE_FIELD
        db.collection('usuarios').document(usuario_id).update(dados)
    except: pass

def bloquear_por_abandono(usuario_id):
    try:
        db = get_db()
        db.collection('usuarios').document(usuario_id).update({
            "status_exame": "bloqueado",
            "motivo_bloqueio": "Atualizou a página ou fechou o navegador (Anti-Cola)",
            "status_exame_em_andamento": False,
            "data_ultimo_exame": datetime.utcnow().isoformat()
        })
    except: pass
