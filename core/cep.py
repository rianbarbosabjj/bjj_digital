import requests
import re

def limpar_cep(cep):
    return re.sub(r"\D", "", cep)


def formatar_cep(cep):
    cep = limpar_cep(cep)
    if len(cep) == 8:
        return f"{cep[:5]}-{cep[5:]}"
    return cep


def buscar_cep(cep):
    """Consulta CEP na API ViaCEP e retorna dicionário formatado."""

    cep = limpar_cep(cep)

    if len(cep) != 8:
        return None

    url = f"https://viacep.com.br/ws/{cep}/json/"

    try:
        response = requests.get(url, timeout=4)
        if response.status_code != 200:
            return None

        dados = response.json()

        if "erro" in dados:
            return None

        return {
            "logradouro": dados.get("logradouro", ""),
            "bairro": dados.get("bairro", ""),
            "localidade": dados.get("localidade", ""),
            "uf": dados.get("uf", ""),
            "cep": formatar_cep(cep)
        }

    except:
        return None
