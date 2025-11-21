import re

def limpar_cpf(cpf):
    """Remove pontos e traços."""
    return re.sub(r'\D', '', cpf)


def validar_cpf(cpf: str) -> bool:
    """Valida CPF com o algoritmo oficial."""

    cpf = limpar_cpf(cpf)

    if len(cpf) != 11:
        return False

    # Rejeita CPFs repetidos
    if cpf in [c * 11 for c in "0123456789"]:
        return False

    # Validação do primeiro dígito
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    dig1 = (soma * 10) % 11
    dig1 = 0 if dig1 == 10 else dig1

    if dig1 != int(cpf[9]):
        return False

    # Segundo dígito
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    dig2 = (soma * 10) % 11
    dig2 = 0 if dig2 == 10 else dig2

    if dig2 != int(cpf[10]):
        return False

    return True

