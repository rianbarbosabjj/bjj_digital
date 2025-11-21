import qrcode
import uuid
import unicodedata
import base64
from io import BytesIO


# ============================================================
# NORMALIZAÇÃO
# ============================================================

def remover_acentos(texto: str) -> str:
    """Remove acentos de um texto para uso em PDFs."""
    if not texto:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(c)
    )


def normalizar_nome(nome: str) -> str:
    """Normaliza espaços e capitaliza nomes."""
    if not nome:
        return ""
    nome = " ".join(nome.split())
    return nome.title()


# ============================================================
# QR CODE
# ============================================================

def gerar_qr_code(texto: str) -> BytesIO:
    """Gera QR code e retorna como imagem em memória."""
    img = qrcode.make(texto)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def gerar_qr_code_base64(texto: str) -> str:
    """Gera QR code e retorna como base64 para embutir em HTML."""
    buffer = gerar_qr_code(texto)
    return base64.b64encode(buffer.getvalue()).decode()


# ============================================================
# CÓDIGO ÚNICO (CERTIFICADO)
# ============================================================

def gerar_codigo_unico():
    """Gera um código seguro e único para certificados."""
    return uuid.uuid4().hex[:12].upper()


# ============================================================
# IMAGEM PARA BASE64
# ============================================================

def imagem_para_base64(path: str) -> str:
    """Converte imagem local para string base64."""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None


# ============================================================
# VERIFICAÇÕES E AUXILIARES
# ============================================================

def eh_vazio(valor):
    """Verifica se é vazio ou None."""
    return valor is None or str(valor).strip() == ""


def limitar_caracteres(texto: str, limite: int) -> str:
    """Corta texto para tamanho específico."""
    if not texto:
        return ""
    return texto[:limite]

