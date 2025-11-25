import os
import json
import unicodedata
import qrcode
import requests
from datetime import datetime
from fpdf import FPDF
from firebase_admin import firestore
from database import get_db # Importa conexão do Firestore

# =========================================
# FUNÇÕES DE QUESTÕES (LEGADO/FALLBACK)
# =========================================
def carregar_questoes(tema):
    """Carrega as questões do arquivo JSON correspondente (Fallback)."""
    path = f"questions/{tema}.json"
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return []
    return []

def salvar_questoes(tema, questoes):
    """Salva lista de questões no arquivo JSON (Fallback)."""
    os.makedirs("questions", exist_ok=True)
    with open(f"questions/{tema}.json", "w", encoding="utf-8") as f:
        json.dump(questoes, f, indent=4, ensure_ascii=False)

def carregar_todas_questoes():
    """Carrega questões de todos os JSONs (Fallback)."""
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
# FUNÇÕES DE UTILIDADE GERAL
# =========================================

def gerar_codigo_verificacao():
    """
    Gera código de verificação único no formato BJJDIGITAL-ANO-XXXX.
    CONECTADO AO FIREBASE FIRESTORE.
    """
    db = get_db()
    total = 0
    
    try:
        # Conta quantos documentos existem na coleção 'resultados'
        docs = db.collection('resultados').stream()
        total = len(list(docs))
    except Exception as e:
        print(f"Erro ao contar resultados: {e}")
        # Fallback: gera um número aleatório para não travar
        import random
        total = random.randint(1000, 9999)

    sequencial = total + 1
    ano = datetime.now().year
    codigo = f"BJJDIGITAL-{ano}-{sequencial:04d}" 
    return codigo

def normalizar_nome(nome):
    """Remove acentos e formata o nome para uso em arquivos."""
    if not nome: return "sem_nome"
    return "_".join(
        unicodedata.normalize("NFKD", nome)
        .encode("ASCII", "ignore")
        .decode()
        .split()
    ).lower()

def formatar_e_validar_cpf(cpf):
    """Remove pontuação e verifica se tem 11 dígitos."""
    if not cpf: return None
    cpf_limpo = ''.join(filter(str.isdigit, cpf))
    return cpf_limpo if len(cpf_limpo) == 11 else None

def formatar_cep(cep):
    """Remove pontuação e verifica se tem 8 dígitos."""
    if not cep: return None
    cep_limpo = ''.join(filter(str.isdigit, cep))
    return cep_limpo if len(cep_limpo) == 8 else None

def buscar_cep(cep):
    """Busca endereço no ViaCEP."""
    cep_fmt = formatar_cep(cep)
    if not cep_fmt: return None
    try:
        resp = requests.get(f"https://viacep.com.br/ws/{cep_fmt}/json/", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            if "erro" not in data:
                return {
                    "logradouro": data.get("logradouro", ""),
                    "bairro": data.get("bairro", ""),
                    "cidade": data.get("localidade", ""),
                    "uf": data.get("uf", "")
                }
    except: pass
    return None

def gerar_qrcode(codigo):
    """Gera imagem do QR Code."""
    os.makedirs("temp_qr", exist_ok=True)
    caminho_qr = f"temp_qr/{codigo}.png"
    
    # Link fictício de validação
    link = f"https://bjjdigital.com.br/validar?code={codigo}"
    
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(caminho_qr)
    return caminho_qr

# =========================================
# GERADOR DE PDF
# =========================================
def gerar_pdf(usuario, faixa, pontuacao, total, codigo, professor=None):
    """Gera certificado oficial do exame de faixa com assinatura caligráfica (Allura)."""
    pdf = FPDF("L", "mm", "A4") # Layout paisagem
    pdf.set_auto_page_break(False)
    pdf.add_page()

    # 🎨 Cores e layout base
    dourado, preto, branco = (218, 165, 32), (40, 40, 40), (255, 255, 255)
    percentual = int((pontuacao / total) * 100)
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Fundo branco e moldura dourada dupla
    pdf.set_fill_color(*branco)
    pdf.rect(0, 0, 297, 210, "F")
    pdf.set_draw_color(*dourado)
    pdf.set_line_width(2)
    pdf.rect(8, 8, 281, 194)
    pdf.set_line_width(0.8)
    pdf.rect(11, 11, 275, 188)

    # Cabeçalho
    pdf.set_text_color(*dourado)
    pdf.set_font("Helvetica", "BI", 30)
    pdf.set_y(25)
    pdf.cell(0, 10, "CERTIFICADO DE EXAME TEÓRICO DE FAIXA", align="C")
    pdf.set_draw_color(*dourado)
    pdf.line(30, 35, 268, 35)

    # Logo
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=133, y=40, w=32)

    # ---------------------------------------------------
    # BLOCO CENTRAL
    # ---------------------------------------------------
    pdf.set_text_color(*preto)
    pdf.set_font("Helvetica", "", 16)
    pdf.set_y(80)
    pdf.cell(0, 10, "Certificamos que o(a) aluno(a)", align="C")

    pdf.set_text_color(*dourado)
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_y(92)
    pdf.cell(0, 10, usuario.upper(), align="C")

    cores_faixa = {
        "Cinza": (169, 169, 169),
        "Amarela": (255, 215, 0),
        "Laranja": (255, 140, 0),
        "Verde": (0, 128, 0),
        "Azul": (30, 144, 255),
        "Roxa": (128, 0, 128),
        "Marrom": (139, 69, 19),
        "Preta": (0, 0, 0),
    }
    cor_faixa = cores_faixa.get(faixa, preto)

    pdf.set_text_color(*preto)
    pdf.set_font("Helvetica", "", 16)
    pdf.set_y(108)
    pdf.cell(0, 8, "concluiu o exame teórico para a faixa", align="C")

    pdf.set_text_color(*cor_faixa)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_y(118)
    pdf.cell(0, 8, faixa.upper(), align="C")

    pdf.set_text_color(*dourado)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_y(132)
    pdf.cell(0, 8, "APROVADO", align="C")

    pdf.set_text_color(*preto)
    pdf.set_font("Helvetica", "", 14)
    texto_final = f"obtendo {percentual}% de aproveitamento, realizado em {data_hora}."
    pdf.set_y(142)
    pdf.cell(0, 6, texto_final, align="C")

    # ---------------------------------------------------
    # SELO E QR CODE
    # ---------------------------------------------------
    selo_path = "assets/selo_dourado.png"
    if os.path.exists(selo_path):
        pdf.image(selo_path, x=23, y=155, w=30)

    caminho_qr = gerar_qrcode(codigo)
    pdf.image(caminho_qr, x=245, y=155, w=25)

    pdf.set_text_color(*preto)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_xy(220, 180)
    pdf.cell(60, 6, f"Código: {codigo}", align="R")

    # ---------------------------------------------------
    # ASSINATURA DO PROFESSOR (Allura)
    # ---------------------------------------------------
    if professor:
        fonte_assinatura = "assets/fonts/Allura-Regular.ttf"
        if os.path.exists(fonte_assinatura):
            try:
                pdf.add_font("Assinatura", "", fonte_assinatura, uni=True)
                pdf.set_font("Assinatura", "", 30)
            except Exception:
                pdf.set_font("Helvetica", "I", 18)
        else:
            pdf.set_font("Helvetica", "I", 18)

        pdf.set_text_color(*preto)
        pdf.set_y(158)
        pdf.cell(0, 12, professor, align="C")

        pdf.set_draw_color(*dourado)
        pdf.line(100, 173, 197, 173)

        pdf.set_font("Helvetica", "", 10)
        pdf.set_y(175)
        pdf.cell(0, 6, "Assinatura do Professor Responsável", align="C")

    # ---------------------------------------------------
    # RODAPÉ
    # ---------------------------------------------------
    pdf.set_draw_color(*dourado)
    pdf.line(30, 190, 268, 190)
    pdf.set_text_color(*dourado)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_y(190)
    pdf.cell(0, 6, "Plataforma BJJ Digital", align="C")

    # ---------------------------------------------------
    # EXPORTAÇÃO
    # ---------------------------------------------------
    os.makedirs("relatorios", exist_ok=True)
    nome_arquivo = f"Certificado_{normalizar_nome(usuario)}_{normalizar_nome(faixa)}.pdf"
    caminho_pdf = os.path.abspath(f"relatorios/{nome_arquivo}")
    pdf.output(caminho_pdf)
    return caminho_pdf
