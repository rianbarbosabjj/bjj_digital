from core.db import consultar_todos, consultar_um, executar


# ============================================================
# CONSULTAS
# ============================================================

def listar_questoes_por_faixa(faixa):
    """Retorna todas as questões de uma faixa."""
    return consultar_todos(
        "SELECT * FROM questoes WHERE faixa = ? ORDER BY id DESC",
        (faixa,)
    )


def buscar_questao(id_questao):
    """Busca uma questão específica."""
    return consultar_um(
        "SELECT * FROM questoes WHERE id = ?",
        (id_questao,)
    )


def contar_questoes_por_faixa(faixa):
    """Conta quantas questões existem para uma faixa."""
    dados = consultar_um("SELECT COUNT(*) AS total FROM questoes WHERE faixa=?", (faixa,))
    return dados["total"] if dados else 0


# ============================================================
# MANIPULAÇÃO
# ============================================================

def adicionar_questao(faixa, pergunta, a, b, c, d, correta):
    """Adiciona uma nova questão."""
    executar("""
        INSERT INTO questoes (faixa, pergunta, alternativa_a, alternativa_b, alternativa_c, alternativa_d, correta)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (faixa, pergunta, a, b, c, d, correta))


def editar_questao(id_questao, pergunta, a, b, c, d, correta):
    """Edita uma questão existente."""
    executar("""
        UPDATE questoes
        SET pergunta=?, alternativa_a=?, alternativa_b=?, alternativa_c=?, alternativa_d=?, correta=?
        WHERE id=?
    """, (pergunta, a, b, c, d, correta, id_questao))


def excluir_questao(id_questao):
    """Remove uma questão do banco."""
    executar("DELETE FROM questoes WHERE id = ?", (id_questao,))


# ============================================================
# PROVAS / EXAMES
# ============================================================

def carregar_prova(faixa):
    """
    Carrega as questões de uma faixa e retorna uma lista.
    Pode ser embaralhada na página de exame.
    """
    questoes = listar_questoes_por_faixa(faixa)

    prova = []
    for q in questoes:
        prova.append({
            "id": q["id"],
            "pergunta": q["pergunta"],
            "a": q["alternativa_a"],
            "b": q["alternativa_b"],
            "c": q["alternativa_c"],
            "d": q["alternativa_d"],
            "correta": q["correta"],
        })

    return prova


def montar_prova_embaralhada(faixa):
    """Retorna uma prova randomizada."""
    import random
    prova = carregar_prova(faixa)
    random.shuffle(prova)
    return prova


# ============================================================
# AUXÍLIARES DE VISUALIZAÇÃO
# ============================================================

def questao_to_dict(registro):
    """Converte registro do banco em dicionário."""
    return {
        "id": registro["id"],
        "faixa": registro["faixa"],
        "pergunta": registro["pergunta"],
        "a": registro["alternativa_a"],
        "b": registro["alternativa_b"],
        "c": registro["alternativa_c"],
        "d": registro["alternativa_d"],
        "correta": registro["correta"],
    }

