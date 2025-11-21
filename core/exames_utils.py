import qrcode
import os
import base64
from fpdf import FPDF
from datetime import datetime
from core.db import executar_retorna_id, consultar_um

def gerar_codigo_certificado():
    ano = datetime.now().year

    # pega o último id da tabela
    ultimo = consultar_um("SELECT id FROM certificados ORDER BY id DESC LIMIT 1")
    numero = (ultimo["id"] + 1) if ultimo else 1

    return f"BJJDIGITAL-{ano}-{numero:04d}"


def gerar_qr_code(codigo):
    if not os.path.exists("qrcodes"):
        os.makedirs("qrcodes")

    qr = qrcode.QRCode(box_size=10, border=1)
    qr.add_data(f"https://bjjdigital.netlify.app/verificar.html?cert_id={codigo}")
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    path = f"qrcodes/{codigo}.png"
    img.save(path)
    return path


def gerar_pdf_certificado(nome, faixa, codigo, qr_path):
    pdf = FPDF("L", "mm", "A4")
    pdf.add_page()

    pdf.set_font("Arial", "B", 24)
    pdf.cell(0, 20, "CERTIFICADO DE APROVAÇÃO", 0, 1, "C")

    pdf.set_font("Arial", "", 20)
    pdf.cell(0, 15, f"Aluno(a): {nome}", 0, 1, "C")
    pdf.cell(0, 15, f"Faixa: {faixa}", 0, 1, "C")
    pdf.cell(0, 15, f"Código: {codigo}", 0, 1, "C")

    pdf.image(qr_path, x=120, y=90, w=60)

    out = f"certificados/{codigo}.pdf"
    if not os.path.exists("certificados"):
        os.makedirs("certificados")

    pdf.output(out)
    return out
