import re
import requests
import streamlit as st
import smtplib
import secrets
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# =========================================
# FUNÇÕES DE VALIDAÇÃO E FORMATAÇÃO (CPF/CEP)
# =========================================

def formatar_e_validar_cpf(cpf):
    """
    Remove caracteres não numéricos, valida o CPF e retorna formatado (XXX.XXX.XXX-XX).
    Retorna None se for inválido.
    """
    if not cpf: return None
    
    # Remove tudo que não é dígito
    cpf_limpo = re.sub(r'\D', '', str(cpf))
    
    # Verifica tamanho
    if len(cpf_limpo) != 11: return None
    
    # Verifica sequências iguais (ex: 111.111.111-11)
    if cpf_limpo == cpf_limpo[0] * 11: return None
    
    # Validação dos dígitos verificadores
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
    """Remove caracteres não numéricos do CEP."""
    if not cep: return ""
    return re.sub(r'\D', '', str(cep))

def buscar_cep(cep):
    """
    Consulta a API ViaCEP e retorna um dicionário com o endereço.
    """
    cep_limpo = formatar_cep(cep)
    if len(cep_limpo) != 8: return None
    
    try:
        url = f"https://viacep.com.br/ws/{cep_limpo}/json/"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            dados = resp.json()
            if "erro" not in dados:
                return {
                    "logradouro": dados.get("logradouro", "").upper(),
                    "bairro": dados.get("bairro", "").upper(),
                    "cidade": dados.get("localidade", "").upper(),
                    "uf": dados.get("uf", "").upper()
                }
    except Exception as e:
        print(f"Erro ao buscar CEP: {e}")
    return None

# =========================================
# FUNÇÕES DE SEGURANÇA E E-MAIL
# =========================================

def gerar_codigo_verificacao(tamanho=6):
    """
    Gera um código numérico aleatório (OTP).
    Adicionado para compatibilidade com partes antigas do código.
    """
    return ''.join(secrets.choice(string.digits) for i in range(tamanho))

def gerar_senha_temporaria(tamanho=8):
    """Gera uma senha aleatória segura com letras e números."""
    caracteres = string.ascii_letters + string.digits
    # Garante mistura de letras e números
    senha = ''.join(secrets.choice(caracteres) for i in range(tamanho))
    return senha

def enviar_email_recuperacao(email_destino, nova_senha):
    """
    Envia a nova senha por e-mail usando SMTP configurado no secrets.toml.
    """
    try:
        sender_email = st.secrets.get("EMAIL_SENDER")
        sender_password = st.secrets.get("EMAIL_PASSWORD")
        smtp_server = st.secrets.get("EMAIL_SERVER")
        smtp_port = st.secrets.get("EMAIL_PORT")
        
        if not (sender_email and sender_password):
            print("Configurações de e-mail ausentes no secrets.toml")
            return False
            
    except Exception as e:
        print(f"Secrets Error: {e}")
        return False

    msg = MIMEMultipart()
    msg['From'] = f"BJJ Digital <{sender_email}>"
    msg['To'] = email_destino
    msg['Subject'] = "Recuperação de Senha - BJJ Digital"

    corpo = f"""
    <html>
    <body>
        <div style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
            <h2 style="color: #0044cc;">BJJ Digital - Recuperação de Senha</h2>
            <p>Olá,</p>
            <p>Recebemos uma solicitação para redefinir sua senha de acesso.</p>
            <p>Sua nova senha temporária é:</p>
            <div style="background-color: #f4f4f4; padding: 15px; font-size: 20px; font-weight: bold; text-align: center; border-radius: 5px; margin: 20px 0;">
                {nova_senha}
            </div>
            <p>Acesse a plataforma e altere sua senha o quanto antes.</p>
            <br>
            <p style="font-size: 12px; color: #777;">Atenciosamente,<br>Equipe BJJ Digital</p>
        </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(corpo, 'html'))

    try:
        # Lógica para converter a porta se vier como string do secrets
        porta = int(smtp_port) if smtp_port else 587
        
        # Configuração flexível para SSL (465) ou TLS (587)
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
        print(f"Erro ao enviar email SMTP: {e}")
        return False
