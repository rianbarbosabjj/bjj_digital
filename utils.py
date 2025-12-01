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
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fpdf import FPDF
from database import get_db
from firebase_admin import firestore

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
    """Gera código no formato BJJDIGITAL-{ANO}-{SEQUENCIA}"""
    try:
        db = get_db()
        # Conta quantos documentos existem na coleção 'resultados'
        docs = db.collection('resultados').count().get()
        # O count() do firestore retorna uma lista de agregações, pegamos o valor da primeira
        total = docs[0][0].value 
    except:
        # Fallback: Gera um número aleatório se não conseguir conectar
        total = random.randint(1000, 9999)
    
    sequencia = total + 1
    ano_atual = datetime.now().year
    
    # Formato: BJJDIGITAL-2025-0042
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
# 5. PDF PREMIUM (DARK MODE / DOURADO)
# =========================================
@st.cache_data(show_spinner=False)
def gerar_pdf(usuario_nome, faixa, pontuacao, total, codigo, professor=None):
    try:
        pdf = FPDF("L", "mm", "A4")
        pdf.set_auto_page_break(False)
        pdf.add_page()
        
        # --- CORES ---
        # Fundo Escuro (Quase Preto, levemente esverdeado/digital)
        cor_fundo = (15, 20, 20) 
        # Dourado Metálico
        cor_dourado = (218, 165, 32)
        # Branco para textos gerais
        cor_texto = (240, 240, 240)

        # 1. PREENCHER FUNDO
        pdf.set_fill_color(*cor_fundo)
        pdf.rect(0, 0, 297, 210, "F")

        # 2. BORDA DOURADA (Moldura)
        margem = 8
        pdf.set_draw_color(*cor_dourado)
        pdf.set_line_width(2)
        pdf.rect(margem, margem, 297 - (2*margem), 210 - (2*margem))
        
        # Borda interna fina (efeito duplo)
        pdf.set_line_width(0.5)
        pdf.rect(margem + 2, margem + 2, 297 - (2*margem) - 4, 210 - (2*margem) - 4)

        # 3. LOGO (Centralizada no Topo)
        if os.path.exists("assets/logo.png"):
            try: 
                # Centraliza imagem de 40mm
                x_logo = (297 - 40) / 2
                pdf.image("assets/logo.png", x=x_logo, y=15, w=40)
            except: pass
        
        # 4. CABEÇALHO
        pdf.set_xy(0, 55)
        pdf.set_font("Helvetica", "B", 27)
        pdf.set_text_color(*cor_dourado)
        pdf.cell(297, 15, "CERTIFICADO DE EXAME TEÓRICO DE FAIXA", ln=1, align="C")
        
        pdf.ln(10) 
        
        # 5. CORPO DO TEXTO
        pdf.set_font("Helvetica", "", 16)
        pdf.set_text_color(*cor_texto)
        pdf.cell(297, 10, "Certificamos que o(a) aluno(a)", ln=1, align="C")

        # NOME DO ALUNO (Auto-Ajuste Dourado)
        pdf.ln(5)
        try: nome_limpo = usuario_nome.upper().encode('latin-1', 'replace').decode('latin-1')
        except: nome_limpo = usuario_nome.upper()

        tamanho_fonte = 40
        pdf.set_font("Helvetica", "B", tamanho_fonte)
        # Reduz fonte se o nome for muito grande
        while pdf.get_string_width(nome_limpo) > 240 and tamanho_fonte > 14:
            tamanho_fonte -= 2
            pdf.set_font("Helvetica", "B", tamanho_fonte)
        
        pdf.set_text_color(*cor_dourado)
        pdf.cell(297, 20, nome_limpo, ln=1, align="C")
        
        # Texto de aprovação
        pdf.set_font("Helvetica", "", 16)
        pdf.set_text_color(*cor_texto)
        pdf.cell(297, 10, "Foi aprovado(a) no exame teórico estando apto(a) à faixa:", ln=1, align="C")

        # FAIXA (Gigante Dourada)
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 32)
        pdf.set_text_color(*cor_dourado)
        pdf.cell(297, 15, str(faixa).upper(), ln=1, align="C")

        # 6. RODAPÉ
        pdf.ln(15)
        
        # Data
        data_fmt = datetime.now().strftime("%d/%m/%Y")
        pdf.set_font("Helvetica", "", 12)
        pdf.set_text_color(*cor_texto)
        pdf.cell(297, 6, f"Data de Emissão: {data_fmt}, ln=1, align="C")

        y_rodape = 175
        
        # Assinatura (Esquerda)
        # Linha branca para assinatura
        pdf.set_draw_color(*cor_texto)
        pdf.set_line_width(0.5)
        pdf.line(40, y_rodape, 110, y_rodape)
        
        pdf.set_xy(40, y_rodape + 2)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(70, 5, "Professor Responsável", align="C")

        # QR Code e Hash (Direita)
        y_qr = 160
        x_qr = 230
        tamanho_qr = 25
        
        try:
            caminho_qr = gerar_qrcode(codigo)
            # Desenha um quadrado branco atrás do QR code para contraste
            pdf.set_fill_color(255, 255, 255)
            pdf.rect(x_qr-1, y_qr-1, tamanho_qr+2, tamanho_qr+2, "F")
            pdf.image(caminho_qr, x=x_qr, y=y_qr, w=tamanho_qr)
        except: pass

        # Hash abaixo do QR
        pdf.set_xy(x_qr - 15, y_qr + tamanho_qr + 2)
        pdf.set_font("Courier", "B", 10)
        pdf.set_text_color(*cor_dourado)
        pdf.cell(55, 5, f"{codigo}", align="C")

        return pdf.output(dest='S').encode('latin-1'), f"Certificado_{usuario_nome.split()[0]}.pdf"
    except Exception as e:
        print(f"Erro PDF: {e}")
        return None, None

# =========================================
# 6. REGRAS DO EXAME
# =========================================
def verificar_elegibilidade_exame(usuario_data):
    return True, "OK" 

def registrar_inicio_exame(usuario_id):
    try:
        db = get_db()
        agora_br = datetime.utcnow() - timedelta(hours=3)
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
        agora_br = datetime.utcnow() - timedelta(hours=3)
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
            "motivo_bloqueio": "Abandono de tela",
            "status_exame_em_andamento": False
        })
    except: pass
