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
# 4. CÓDIGOS E QR CODE (FORMATO NOVO)
# =========================================
def gerar_codigo_verificacao():
    """Gera código no formato BJJDIGITAL-{ANO}-{SEQUENCIA}"""
    try:
        db = get_db()
        # Tenta contar quantos certificados já existem para gerar sequencial
        docs = db.collection('resultados').count().get()
        total = docs[0][0].value
    except:
        # Fallback se der erro no banco: gera número aleatório
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
# 5. PDF MODERNO (LAYOUT AJUSTADO)
# =========================================
@st.cache_data(show_spinner=False)
def gerar_pdf(usuario_nome, faixa, pontuacao, total, codigo, professor=None):
    try:
        pdf = FPDF("L", "mm", "A4")
        pdf.set_auto_page_break(False)
        pdf.add_page()
        
        # Cores
        cor_dourado = (184, 134, 11) 
        cor_preto = (25, 25, 25)
        cor_cinza = (100, 100, 100)
        cor_fundo = (252, 252, 250)

        # Fundo
        pdf.set_fill_color(*cor_fundo)
        pdf.rect(0, 0, 297, 210, "F")

        # Barra Lateral
        largura_barra = 60
        pdf.set_fill_color(*cor_preto)
        pdf.rect(0, 0, largura_barra, 210, "F")
        pdf.set_fill_color(*cor_dourado)
        pdf.rect(largura_barra, 0, 2, 210, "F")

        # Logo
        if os.path.exists("assets/logo.png"):
            try: pdf.image("assets/logo.png", x=10, y=30, w=40)
            except: pass
        
        # Configuração da Área de Texto
        x_inicio = largura_barra + 10 
        largura_util = 297 - x_inicio - 10 

        # Título Principal
        pdf.set_xy(x_inicio, 35) # Subi um pouco (era 40)
        pdf.set_font("Helvetica", "B", 32)
        pdf.set_text_color(*cor_dourado)
        pdf.cell(largura_util, 15, "CERTIFICADO DE DE EXAME TEÓRICO DE FAIXA"", ln=1, align="C")
        
        pdf.ln(12) 
        
        # Texto Introdutório
        pdf.set_font("Helvetica", "", 14)
        pdf.set_text_color(*cor_preto)
        pdf.cell(largura_util, 10, "Certificamos que o(a) aluno(a)", ln=1, align="C")

        # Nome do Aluno (Auto-Ajuste)
        pdf.ln(2)
        try: nome_limpo = usuario_nome.upper().encode('latin-1', 'replace').decode('latin-1')
        except: nome_limpo = usuario_nome.upper()

        tamanho_fonte = 36
        pdf.set_font("Helvetica", "B", tamanho_fonte)
        while pdf.get_string_width(nome_limpo) > (largura_util - 20) and tamanho_fonte > 12:
            tamanho_fonte -= 2
            pdf.set_font("Helvetica", "B", tamanho_fonte)
        
        pdf.set_text_color(*cor_dourado)
        pdf.cell(largura_util, 16, nome_limpo, ln=1, align="C")
        
        # Linha decorativa
        x_linha = x_inicio + 20
        y_linha = pdf.get_y()
        pdf.set_draw_color(*cor_cinza)
        pdf.set_line_width(0.2)
        pdf.line(x_linha, y_linha, 297 - 20, y_linha)

        pdf.ln(8)

        # Texto de Conclusão
        pdf.set_font("Helvetica", "", 14)
        pdf.set_text_color(*cor_preto)
        pdf.cell(largura_util, 10, "Concluiu com êxito o exame teóricos para a:", ln=1, align="C")

        # Faixa
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 24)
        pdf.set_text_color(*cor_preto)
        pdf.cell(largura_util, 12, f"FAIXA {str(faixa).upper()}", ln=1, align="C")

        # Detalhes (Data e Nota) - Mais organizados
        pdf.ln(10)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(*cor_cinza)
        try: percentual = int((pontuacao / total) * 100) if total > 0 else 0
        except: percentual = 0
        data_fmt = datetime.now().strftime("%d/%m/%Y")

        pdf.cell(largura_util, 6, f"Data de Emissão: {data_fmt}  |  Aproveitamento: {percentual}%", ln=1, align="C")

        # Rodapé (Assinatura e QR Code)
        y_rodape = 165 # Posição Y fixa para o rodapé
        
        # Assinatura (Esquerda da área branca)
        pdf.set_xy(x_inicio + 20, y_rodape + 10)
        pdf.set_draw_color(*cor_preto)
        pdf.line(x_inicio + 20, y_rodape + 10, x_inicio + 90, y_rodape + 10) # Linha da assinatura
        pdf.set_xy(x_inicio + 20, y_rodape + 11)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(70, 5, "Professor Responsável", align="C")

        # QR Code e Hash (Direita da área branca)
        y_qr = 155
        x_qr = 245
        tamanho_qr = 25
        
        try:
            caminho_qr = gerar_qrcode(codigo)
            pdf.image(caminho_qr, x=x_qr, y=y_qr, w=tamanho_qr)
        except: pass

        # Hash logo abaixo do QR Code
        pdf.set_xy(x_qr - 15, y_qr + tamanho_qr + 2) # Ajustei o X para centralizar melhor o texto longo
        pdf.set_font("Courier", "", 8) # Fonte Courier fica melhor para ler códigos
        pdf.set_text_color(*cor_cinza)
        pdf.cell(55, 4, f"{codigo}", align="C")

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
