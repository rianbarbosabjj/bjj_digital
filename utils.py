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
def gerar_pdf(usuario_nome, faixa, pontuacao, total, codigo, professor=None):
    """Gera certificado PDF moderno com ajuste automático de nome."""
    try:
        # Configuração Inicial
        pdf = FPDF("L", "mm", "A4")
        pdf.set_auto_page_break(False)
        pdf.add_page()

        # --- PALETA DE CORES ---
        # Dourado mais elegante (Ouro Velho)
        cor_dourado = (184, 134, 11) 
        # Preto Suave (Carvão)
        cor_preto = (25, 25, 25)
        # Cinza para textos secundários
        cor_cinza = (100, 100, 100)
        # Branco
        cor_branco = (255, 255, 255)
        # Fundo Off-white (creme bem suave)
        cor_fundo = (252, 252, 250)

        # --- 1. FUNDO E DESIGN MODERNO ---
        pdf.set_fill_color(*cor_fundo)
        pdf.rect(0, 0, 297, 210, "F")

        # Barra Lateral Esquerda (Estilo Moderno)
        largura_barra = 60
        pdf.set_fill_color(*cor_preto)
        pdf.rect(0, 0, largura_barra, 210, "F")

        # Linha de destaque Dourada vertical
        pdf.set_fill_color(*cor_dourado)
        pdf.rect(largura_barra, 0, 2, 210, "F")

        # --- 2. LOGO (Na barra escura) ---
        if os.path.exists("assets/logo.png"):
            # Centraliza a logo na barra lateral de 60mm
            # x = (60 - 40) / 2 = 10
            try: 
                pdf.image("assets/logo.png", x=10, y=30, w=40)
            except: pass
        
        # --- 3. CONTEÚDO PRINCIPAL (Lado Direito) ---
        # Definir margem esquerda para o conteúdo (pula a barra)
        x_inicio = largura_barra + 10 
        largura_util = 297 - x_inicio - 10 # Largura da página - barra - margem direita

        # TÍTULO
        pdf.set_xy(x_inicio, 40)
        pdf.set_font("Helvetica", "B", 32)
        pdf.set_text_color(*cor_dourado)
        pdf.cell(largura_util, 15, "CERTIFICADO", ln=1, align="C")
        
        pdf.set_font("Helvetica", "", 12)
        pdf.set_text_color(*cor_cinza)
        pdf.cell(largura_util, 8, "DE CONCLUSÃO DE EXAME DE FAIXA", ln=1, align="C")

        pdf.ln(15) # Espaço

        # TEXTO INTRODUTÓRIO
        pdf.set_font("Helvetica", "", 14)
        pdf.set_text_color(*cor_preto)
        pdf.cell(largura_util, 10, "Certificamos que o(a) aluno(a)", ln=1, align="C")

        # --- 4. ALGORITMO DE NOME GRANDE (AJUSTE AUTOMÁTICO) ---
        pdf.ln(5)
        
        # Tratamento de caracteres
        try:
            nome_limpo = usuario_nome.upper().encode('latin-1', 'replace').decode('latin-1')
        except:
            nome_limpo = usuario_nome.upper()

        # Lógica de Redução de Fonte
        tamanho_fonte = 36 # Começa grande
        pdf.set_font("Helvetica", "B", tamanho_fonte)
        
        # Enquanto a largura do texto for maior que a largura útil (com margem de segurança de 20mm)
        while pdf.get_string_width(nome_limpo) > (largura_util - 20) and tamanho_fonte > 12:
            tamanho_fonte -= 2
            pdf.set_font("Helvetica", "B", tamanho_fonte)
        
        pdf.set_text_color(*cor_dourado)
        pdf.cell(largura_util, 15, nome_limpo, ln=1, align="C")
        
        # Linha decorativa abaixo do nome
        x_linha = x_inicio + 20
        y_linha = pdf.get_y()
        pdf.set_draw_color(*cor_cinza)
        pdf.set_line_width(0.2)
        pdf.line(x_linha, y_linha, 297 - 20, y_linha)

        pdf.ln(10)

        # TEXTO DE CONCLUSÃO
        pdf.set_font("Helvetica", "", 14)
        pdf.set_text_color(*cor_preto)
        pdf.cell(largura_util, 10, "Concluiu com êxito os requisitos técnicos e teóricos para a:", ln=1, align="C")

        # FAIXA
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 24)
        pdf.set_text_color(*cor_preto)
        pdf.cell(largura_util, 10, f"FAIXA {str(faixa).upper()}", ln=1, align="C")

        # DADOS TÉCNICOS
        pdf.ln(15)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(*cor_cinza)
        
        # Cálculos de nota
        try:
            percentual = int((pontuacao / total) * 100) if total > 0 else 0
        except: percentual = 0
        data_fmt = datetime.now().strftime("%d/%m/%Y")

        pdf.cell(largura_util, 6, f"Data de Emissão: {data_fmt}", ln=1, align="C")
        pdf.cell(largura_util, 6, f"Aproveitamento no Exame: {percentual}%", ln=1, align="C")

        # --- 5. RODAPÉ, QR CODE E CÓDIGO ---
        # Posicionamento do bloco QR Code no canto inferior direito
        y_qr = 155
        x_qr = 245
        tamanho_qr = 25

        # Renderizar QR Code
        try:
            from utils import gerar_qrcode # Garantir que importa a função
            caminho_qr = gerar_qrcode(codigo)
            pdf.image(caminho_qr, x=x_qr, y=y_qr, w=tamanho_qr)
        except Exception as e:
            print(f"Erro QR: {e}")
            pass

        # Código de Verificação logo abaixo do QR Code
        pdf.set_xy(x_qr - 10, y_qr + tamanho_qr + 2) # X um pouco recuado para centralizar com o QR
        pdf.set_font("Courier", "", 8) # Courier para parecer código
        pdf.set_text_color(*cor_cinza)
        # Cell com largura fixa de 45mm (largura visual do bloco QR) para centralizar o texto
        pdf.cell(45, 4, f"Cod: {codigo}", align="C")
        
        # Assinatura do Professor (Opcional - Lado Esquerdo do conteúdo)
        pdf.set_xy(x_inicio + 20, 175)
        pdf.set_draw_color(*cor_preto)
        pdf.line(x_inicio + 20, 175, x_inicio + 90, 175) # Linha da assinatura
        pdf.set_xy(x_inicio + 20, 176)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(70, 5, "Professor Responsável", align="C")

        # Output
        pdf_output = pdf.output(dest='S').encode('latin-1')
        nome_arquivo = f"Certificado_{usuario_nome.split()[0]}.pdf"
        
        return pdf_output, nome_arquivo

    except Exception as e:
        print(f"Erro na geração do PDF: {e}")
        return None, None
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
