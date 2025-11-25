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
        # Usamos stream() para contar (em produção com muitos dados, usar count() aggregation é melhor)
        docs = db.collection('resultados').stream()
        total = len(list(docs))
    except Exception as e:
        print(f"Erro ao contar resultados: {e}")
        # Fallback: gera um número aleatório para não travar
        import random
        total = random.randint(1000, 9999)

    sequencial = total + 1
    ano = datetime.now().year
    codigo = f"BJJDIGITAL-{ano}-{sequencial:04d}" # Ex: BJJDIGITAL-2025-0012
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
    """Gera certificado PDF oficial."""
    
    # Configuração do PDF
    pdf = FPDF("L", "mm", "A4")
    pdf.set_auto_page_break(False)
    pdf.add_page()

    # Cores
    dourado = (218, 165, 32)
    preto = (40, 40, 40)
    branco = (255, 255, 255)

    # Fundo e Borda
    pdf.set_fill_color(*branco)
    pdf.rect(0, 0, 297, 210, "F")
    
    pdf.set_draw_color(*dourado)
    pdf.set_line_width(2)
    pdf.rect(10, 10, 277, 190)
    
    pdf.set_line_width(0.5)
    pdf.rect(13, 13, 271, 184)

    # Logo
    if os.path.exists("assets/logo.png"):
        pdf.image("assets/logo.png", x=130, y=20, w=35)

    # Título
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
    pdf.cell(297, 15, usuario.upper(), align="C")

    # Texto Central
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(*preto)
    pdf.set_xy(0, 115)
    pdf.cell(297, 10, f"concluiu com êxito o Exame Teórico para a faixa {faixa}", align="C")
    
    percentual = int((pontuacao/total)*100) if total > 0 else 0
    data_hoje = datetime.now().strftime("%d/%m/%Y")
    
    pdf.set_xy(0, 125)
    pdf.cell(297, 10, f"Aproveitamento: {percentual}% | Data: {data_hoje}", align="C")

    # Código e QR Code
    pdf.set_font("Courier", "", 10)
    pdf.set_xy(20, 175)
    pdf.cell(100, 5, f"Código de Autenticidade: {codigo}")
    
    # Gera e insere QR
    try:
        qr_path = gerar_qrcode(codigo)
        pdf.image(qr_path, x=250, y=160, w=25)
    except: pass

    # Rodapé
    pdf.set_y(190)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 10, "BJJ Digital - Sistema de Gestão de Graduação", align="C")

    # Salva
    os.makedirs("relatorios", exist_ok=True)
    nome_arq = f"Certificado_{normalizar_nome(usuario)}_{normalizar_nome(faixa)}.pdf"
    caminho = os.path.abspath(f"relatorios/{nome_arq}")
    pdf.output(caminho)
    
    return caminho
