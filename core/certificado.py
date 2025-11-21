import os
from fpdf import FPDF
import qrcode
import base64
import io
from datetime import datetime
from core.db import executar, consultar_retorna_id, consultar_um


# ============================================================
# FUNÇÃO PARA GERAR QR CODE EM BASE64
# ============================================================

def gerar_qrcode_base64(texto):
    qr = qrcode.make(texto)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode()
    return encoded


# ============================================================
# FUNÇÃO PRINCIPAL: GERAR CERTIFICADO EM PDF
# ============================================================

def gerar_certificado_pdf(cert_id, nome_aluno, faixa, professor, data_emissao):

    arquivo_saida = f"certificado_{cert_id}.pdf"

    pdf = FPDF(format="A4", orientation="L")
    pdf.add_page()

    # ----------------------------------------------------------
    # ESTILO / CORES
    # ----------------------------------------------------------

    pdf.set_auto_page_break(False)

    # Moldura dourada
    pdf.set_draw_color(200, 150, 20)
    pdf.set_line_width(3)
    pdf.rect(10, 10, 277, 190)

    # ----------------------------------------------------------
    # TÍTULO
    # ----------------------------------------------------------

    pdf.set_font("Arial", "B", 28)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(20)
    pdf.cell(0, 15, "CERTIFICADO DE EXAME TEÓRICO", 0, 1, "C")

    # ----------------------------------------------------------
    # NOME DO ALUNO
    # ----------------------------------------------------------

    pdf.set_font("Arial", "B", 36)
    pdf.set_text_color(30, 30, 30)
    pdf.ln(10)
    pdf.cell(0, 20, nome_aluno.upper(), 0, 1, "C")

    # ----------------------------------------------------------
    # TEXTO PRINCIPAL
    # ----------------------------------------------------------

    pdf.set_font("Arial", "", 18)
    pdf.ln(10)
    texto = f"A aluna foi aprovada no exame da faixa {faixa}."
    pdf.multi_cell(0, 14, texto, align="C")

    # ----------------------------------------------------------
    # PROF E DATA
    # ----------------------------------------------------------

    pdf.ln(10)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 12, f"Professor Responsável: {professor}", 0, 1, "C")

    pdf.set_font("Arial", "", 14)
    pdf.cell(0, 10, f"Data: {data_emissao}", 0, 1, "C")

# ============================================================
# CÓDIGO DO CERTIFICADO: BJJDIGITAL-YYYY-XXXX
# ============================================================

ano_atual = datetime.now().year
numero_formatado = str(cert_id).zfill(4)
codigo_certificado = f"BJJDIGITAL-{ano_atual}-{numero_formatado}"

# Exibir o código no PDF
pdf.set_font("Arial", "B", 16)
pdf.ln(8)
pdf.cell(0, 10, f"Código de Validação: {codigo_certificado}", 0, 1, "C")

# ============================================================
# QR CODE PARA VALIDAÇÃO EXTERNA
# ============================================================

validacao_url = f"https://bjjdigital.netlify.app/verificar.html?cert_id={codigo_certificado}"

qr_base64 = gerar_qrcode_base64(validacao_url)

qr_bytes = base64.b64decode(qr_base64)
qr_path = f"qr_{cert_id}.png"
with open(qr_path, "wb") as f:
    f.write(qr_bytes)

# Inserir QR Code no PDF (lado direito inferior)
pdf.image(qr_path, x=230, y=120, w=40)

# Apagar arquivo temporário
if os.path.exists(qr_path):
    os.remove(qr_path)

# ============================================================
# REGISTRAR CERTIFICADO NO BANCO
# ============================================================

def registrar_certificado(usuario_id, exame_config_id):

    data = datetime.now().strftime("%d/%m/%Y %H:%M")

    cert_id = executar_retorna_id("""
        INSERT INTO certificados (usuario_id, exame_config_id, data_emissao)
        VALUES (?, ?, ?)
    """, (usuario_id, exame_config_id, data))

    return cert_id
