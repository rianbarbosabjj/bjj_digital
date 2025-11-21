from fpdf import FPDF
from core.utils import remover_acentos, gerar_qr_code
import os


class CertificadoPDF(FPDF):
    def __init__(self):
        super().__init__("L", "mm", "A4")
        self.set_auto_page_break(False)

    def header(self):
        pass  # sem cabeçalho

    def footer(self):
        pass  # sem rodapé


# ===================================================================
# GERAÇÃO DO CERTIFICADO
# ===================================================================

def gerar_certificado(nome, faixa, codigo_unico, selo_path=None):
    """
    Gera certificado de aprovação em PDF.
    Salva em /relatorios/certificado_<codigo>.pdf
    Retorna caminho do arquivo.
    """

    # Garante que a pasta exista
    pasta = "relatorios"
    os.makedirs(pasta, exist_ok=True)

    nome_limpo = remover_acentos(nome)

    caminho_pdf = os.path.join(pasta, f"certificado_{codigo_unico}.pdf")

    pdf = CertificadoPDF()
    pdf.add_page()

    # Fundo branco
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(0, 0, 297, 210, "F")

    # Moldura dourada dupla
    pdf.set_draw_color(212, 175, 55)  # dourado
    pdf.set_line_width(4)
    pdf.rect(8, 8, 281, 194)  # borda externa

    pdf.set_line_width(1.5)
    pdf.rect(14, 14, 269, 182)  # borda interna

    # Título
    pdf.set_xy(0, 25)
    pdf.set_font("Arial", "B", 30)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(297, 10, "CERTIFICADO DE EXAME TEÓRICO DE FAIXA", align="C")

    # Nome do aluno
    pdf.set_xy(0, 70)
    pdf.set_font("Arial", "B", 45)
    pdf.set_text_color(212, 175, 55)  # dourado
    pdf.cell(297, 15, nome_limpo, align="C")

    # Texto inferior
    pdf.set_xy(0, 110)
    pdf.set_font("Arial", "", 20)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(
        297,
        10,
        f"A(o) foi aprovado(a) no exame teórico da faixa {faixa}.",
        align="C"
    )

    # QR CODE
    qr_buffer = gerar_qr_code(f"VALIDAR:{codigo_unico}")
    qr_path = f"relatorios/temp_qr_{codigo_unico}.png"
    with open(qr_path, "wb") as f:
        f.write(qr_buffer.getvalue())

    pdf.image(qr_path, x=125, y=135, w=45)

    # Remove o temporário após usar
    os.remove(qr_path)

    # Selo dourado opcional
    if selo_path and os.path.exists(selo_path):
        pdf.image(selo_path, x=240, y=20, w=35)

    # Salvar
    pdf.output(caminho_pdf)

    return caminho_pdf

