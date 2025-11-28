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
from datetime import datetime, timedelta  # Adicionado timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fpdf import FPDF
from database import get_db

# =========================================
# FUNÇÕES DE QUESTÕES (GERENCIAMENTO)
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
# FUNÇÕES GERAIS E FORMATAÇÃO
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
# FUNÇÕES DE SEGURANÇA E E-MAIL
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
        
        if not (sender_email and sender_password):
            return False
    except Exception:
        return False

    msg = MIMEMultipart()
    msg['From'] = f"BJJ Digital <{sender_email}>"
    msg['To'] = email_destino
    msg['Subject'] = "Recuperação de Senha - BJJ Digital"

    corpo = f"""
    <html>
    <body>
        <div style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #0044cc;">BJJ Digital - Recuperação de Senha</h2>
            <p>Sua nova senha temporária é:</p>
            <div style="background-color: #f4f4f4; padding: 15px; font-weight: bold; font-size: 18px;">
                {nova_senha}
            </div>
            <p>Acesse a plataforma e altere sua senha.</p>
        </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(corpo, 'html'))

    try:
        porta = int(smtp_port) if smtp_port else 587
        if porta == 465:
            server = smtplib.SMTP_SSL(smtp_server, porta)
        else:
            server = smtplib.SMTP(smtp_server, porta)
            server.starttls()

        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, email_destino, text)
        server.quit()
        return True
    except Exception as e:
        print(f"Erro SMTP: {e}")
        return False

# =========================================
# GERAÇÃO DE CÓDIGOS E QR CODE
# =========================================

def gerar_codigo_verificacao():
    db = get_db()
    total = 0
    try:
        docs = db.collection('resultados').stream()
        total = len(list(docs))
    except:
        import random
        total = random.randint(1000, 9999)

    sequencial = total + 1
    ano = datetime.now().year
    return f"BJJDIGITAL-{ano}-{sequencial:04d}" 

def gerar_qrcode(codigo):
    os.makedirs("temp_qr", exist_ok=True)
    caminho_qr = f"temp_qr/{codigo}.png"
    if os.path.exists(caminho_qr): return caminho_qr

    base_url = "https://bjjdigital.com.br/verificar.html"
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(f"{base_url}?codigo={codigo}")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(caminho_qr)
    return caminho_qr

# =========================================
# GERADOR DE CERTIFICADO (PDF)
# =========================================
@st.cache_data(show_spinner=False)
def gerar_pdf(usuario, faixa, pontuacao, total, codigo, professor=None):
    """Gera certificado PDF oficial com layout dourado."""
    pdf = FPDF("L", "mm", "A4")
    pdf.set_auto_page_break(False)
    pdf.add_page()

    dourado, preto, branco = (218, 165, 32), (40, 40, 40), (255, 255, 255)
    percentual = int((pontuacao / total) * 100) if total > 0 else 0
    data_hora = datetime.now().strftime("%d/%m/%Y")

    # Fundo e Bordas
    pdf.set_fill_color(*branco)
    pdf.rect(0, 0, 297, 210, "F")
    pdf.set_draw_color(*dourado)
    pdf.set_line_width(2)
    pdf.rect(10, 10, 277, 190)
    pdf.set_line_width(0.5)
    pdf.rect(13, 13, 271, 184)

    if os.path.exists("assets/logo.png"):
        pdf.image("assets/logo.png", x=130, y=20, w=35)

    # Títulos
    pdf.set_text_color(*dourado)
    pdf.set_font("Helvetica", "B", 36)
    pdf.set_xy(0, 60)
    pdf.cell(297, 15, "CERTIFICADO DE CONCLUSÃO", align="C")
    
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(*preto)
    pdf.set_xy(0, 80)
    pdf.cell(297, 10, "Certificamos que", align="C")

    # Nome do Aluno
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(*dourado)
    pdf.set_xy(0, 95)
    try:
        nome_display = usuario.upper().encode('latin-1', 'replace').decode('latin-1')
    except:
        nome_display = usuario.upper()
    pdf.cell(297, 15, nome_display, align="C")

    # Cores das faixas
    cores_faixa = {
        "Cinza": (169, 169, 169), "Amarela": (255, 215, 0),
        "Laranja": (255, 140, 0), "Verde": (0, 128, 0),
        "Azul": (30, 144, 255), "Roxa": (128, 0, 128),
        "Marrom": (139, 69, 19), "Preta": (0, 0, 0),
    }
    r, g, b = cores_faixa.get(faixa, preto)

    # Texto de conclusão
    pdf.set_font("Helvetica", "", 16)
    pdf.set_text_color(*preto)
    pdf.set_xy(0, 115)
    pdf.cell(297, 10, f"concluiu com êxito o Exame Teórico para a faixa", align="C")
    
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(r, g, b)
    pdf.set_xy(0, 125)
    try: f_disp = faixa.upper().encode('latin-1', 'replace').decode('latin-1')
    except: f_disp = faixa.upper()
    pdf.cell(297, 10, f_disp, align="C")

    # Dados finais
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(*preto)
    pdf.set_xy(0, 135)
    pdf.cell(297, 10, f"Aproveitamento: {percentual}% | Data: {data_hora}", align="C")

    pdf.set_font("Courier", "", 10)
    pdf.set_xy(20, 175)
    pdf.cell(100, 5, f"Código: {codigo}", align="L")
    
    # QR Code e Selo
    try:
        caminho_qr = gerar_qrcode(codigo)
        pdf.image(caminho_qr, x=250, y=155, w=25)
    except: pass

    if os.path.exists("assets/selo_dourado.png"):
        pdf.image("assets/selo_dourado.png", x=20, y=150, w=30)

    # Assinatura do Professor
    if professor:
        try: prof_nome = professor.encode('latin-1', 'replace').decode('latin-1')
        except: prof_nome = professor
        
        fonte_ass = "assets/fonts/Allura-Regular.ttf"
        if os.path.exists(fonte_ass):
            try:
                pdf.add_font("Assinatura", "", fonte_ass, uni=True)
                pdf.set_font("Assinatura", "", 30)
            except: pdf.set_font("Helvetica", "I", 18)
        else: pdf.set_font("Helvetica", "I", 18)

        pdf.set_text_color(*preto)
        pdf.set_y(155)
        pdf.cell(0, 10, prof_nome, align="C")
        
        pdf.set_draw_color(*dourado)
        pdf.line(100, 168, 197, 168)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_y(170)
        pdf.cell(0, 5, "Professor Responsável", align="C")

    pdf.set_draw_color(*dourado)
    pdf.line(30, 190, 268, 190)
    pdf.set_text_color(*dourado)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_y(192)
    pdf.cell(0, 5, "Plataforma BJJ Digital - bjjdigital.com.br", align="C")

    # Retorna Bytes para download
    pdf_bytes = pdf.output(dest='S').encode('latin-1')
    nome_arquivo = f"Certificado_{normalizar_nome(usuario)}_{normalizar_nome(faixa)}.pdf"
    
    return pdf_bytes, nome_arquivo

# =========================================
# FUNÇÕES DE CONTROLE DE EXAME (REGRAS DE NEGÓCIO)
# =========================================

def verificar_elegibilidade_exame(usuario_data):
    """
    Verifica se o aluno pode fazer o exame.
    Regras:
    1. Não está bloqueado (por fraude ou abandono).
    2. Não está aprovado (já passou).
    3. Se reprovado, aguardar 72h.
    """
    status = usuario_data.get("status_exame", "pendente")
    ultima_tentativa = usuario_data.get("data_ultimo_exame")
    
    # 1. Bloqueio por infração
    if status == "bloqueado":
        return False, "🚫 Exame bloqueado por segurança. Contate seu professor."

    # 2. Já aprovado
    if status == "aprovado":
        return False, "✅ Você já foi aprovado neste exame!"

    # 3. Reprovado (Carência de 72h)
    if status == "reprovado" and ultima_tentativa:
        try:
            # Tenta converter se vier com fuso horário ou formato diferente
            dt_ultima = ultima_tentativa.replace(tzinfo=None)
        except:
            dt_ultima = ultima_tentativa # Assume que já é datetime naive ou compatível
            
        if isinstance(dt_ultima, datetime):
            agora = datetime.now()
            diferenca = agora - dt_ultima
            
            if diferenca < timedelta(hours=72):
                horas_restantes = 72 - (diferenca.total_seconds() / 3600)
                return False, f"⏳ Aguarde 72h após reprovação. Liberado em {int(horas_restantes)} horas."

    return True, "OK"

def registrar_inicio_exame(user_id):
    """Marca o início para detectar abandono."""
    db = get_db()
    db.collection('usuarios').document(user_id).update({
        "status_exame": "em_andamento",
        "inicio_exame_temp": datetime.now()
    })

def registrar_fim_exame(user_id, aprovado):
    """Finaliza o exame e define status."""
    db = get_db()
    status = "aprovado" if aprovado else "reprovado"
    
    db.collection('usuarios').document(user_id).update({
        "status_exame": status,
        "data_ultimo_exame": datetime.now(),
        "status_exame_em_andamento": False # Remove flag de andamento
    })

def bloquear_por_abandono(user_id):
    """Bloqueia o aluno se detectar saída da página."""
    db = get_db()
    db.collection('usuarios').document(user_id).update({
        "status_exame": "bloqueado",
        "motivo_bloqueio": "Saída da página durante a prova"
    })
