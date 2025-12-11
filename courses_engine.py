# bjj_digital/courses_engine.py

from typing import Optional, Dict, List
from datetime import datetime
from firebase_admin import firestore

from database import get_db


def _get_db():
    db = get_db()
    if not db:
        raise RuntimeError("Não foi possível conectar ao banco de dados.")
    return db


# ======================================================
# CURSOS
# ======================================================

def criar_curso(
    professor_id: str,
    nome_professor: str,
    titulo: str,
    descricao: str,
    modalidade: str,         # "EAD" ou "Presencial"
    publico: str,            # "geral" ou "equipe"
    equipe_destino: Optional[str],
    pago: bool,
    preco: Optional[float],
    split_custom: Optional[float],
    certificado_automatico: bool
) -> str:
    """
    Cria um curso no Firestore.
    A coleção 'courses' será criada automaticamente na primeira gravação.
    """
    db = _get_db()

    doc = {
        "titulo": (titulo or "").strip(),
        "descricao": (descricao or "").strip(),

        "modalidade": modalidade,           # "EAD" | "Presencial"
        "publico": publico,                 # "geral" | "equipe"
        "equipe_destino": equipe_destino or None,

        "pago": bool(pago),
        "preco": float(preco) if (pago and preco is not None) else 0.0,

        "split_custom": float(split_custom) if split_custom is not None else None,
        "certificado_automatico": bool(certificado_automatico),

        "professor_id": professor_id,
        "professor_nome": nome_professor,

        # status de publicação
        "status": "ativo",     # "ativo", "inativo", "rascunho"
        "ativo": True,

        "criado_em": firestore.SERVER_TIMESTAMP,
    }

    ref = db.collection("courses").document()
    ref.set(doc)
    return ref.id


def listar_cursos_do_professor(professor_id: str) -> List[Dict]:
    """
    Lista cursos criados por um professor.
    """
    db = _get_db()
    cursos: List[Dict] = []

    q = db.collection("courses").where("professor_id", "==", professor_id)
    for snap in q.stream():
        d = snap.to_dict()
        d["id"] = snap.id
        cursos.append(d)

    # Ordena por data de criação (mais recentes primeiro), se houver timestamp
    def _key(c):
        dt = c.get("criado_em")
        if isinstance(dt, datetime):
            return dt
        return datetime.min

    cursos.sort(key=_key, reverse=True)
    return cursos


def listar_cursos_disponiveis_para_usuario(usuario: Dict) -> List[Dict]:
    """
    Lista cursos que o usuário pode ver.
    Regra simples inicial:
      - cursos com status == "ativo"
      - não filtra ainda por equipe_destino (isso pode ser refinado depois)
    """
    db = _get_db()
    cursos: List[Dict] = []

    # Busca apenas cursos com status "ativo"
    q = db.collection("courses").where("status", "==", "ativo")
    for snap in q.stream():
        d = snap.to_dict()
        d["id"] = snap.id

        # FUTURO: se publico == "equipe", filtrar por equipes do usuário
        cursos.append(d)

    # Ordena por data de criação, se existir
    def _key(c):
        dt = c.get("criado_em")
        if isinstance(dt, datetime):
            return dt
        return datetime.min

    cursos.sort(key=_key, reverse=True)
    return cursos


# ======================================================
# MATRÍCULAS / INSCRIÇÕES
# ======================================================

def get_inscricao_id(user_id: str, course_id: str) -> str:
    """Convenção de ID para matrícula."""
    return f"{user_id}__{course_id}"


def obter_inscricao(user_id: str, course_id: str) -> Optional[Dict]:
    """
    Busca a inscrição de um usuário em um curso, se existir.
    """
    db = _get_db()
    doc_id = get_inscricao_id(user_id, course_id)
    ref = db.collection("enrollments").document(doc_id)
    snap = ref.get()
    if not snap.exists:
        return None
    d = snap.to_dict()
    d["id"] = snap.id
    return d


def inscrever_usuario_em_curso(user_id: str, course_id: str) -> str:
    """
    Cria a inscrição do usuário em um curso (sem cobrança ainda).
    Posteriormente vamos acoplar a lógica de pagamento/split aqui.
    """
    db = _get_db()
    doc_id = get_inscricao_id(user_id, course_id)
    ref = db.collection("enrollments").document(doc_id)

    if ref.get().exists:
        # Já inscrito
        return doc_id

    dados = {
        "user_id": user_id,
        "course_id": course_id,
        "pago": False,          # FUTURO: atualizar após pagamento
        "progresso": 0.0,
        "certificado_emitido": False,
        "criado_em": firestore.SERVER_TIMESTAMP,
    }
    ref.set(dados)
    return doc_id


# ======================================================
# PROGRESSO
# ======================================================

def atualizar_progresso(user_id: str, course_id: str, progresso: float):
    """
    Atualiza o progresso do aluno no curso (0–100).
    Isso será usado quando criarmos a estrutura de módulos e aulas.
    """
    db = _get_db()
    doc_id = get_inscricao_id(user_id, course_id)
    ref = db.collection("enrollments").document(doc_id)

    snap = ref.get()
    if not snap.exists:
        return

    progresso = max(0.0, min(100.0, float(progresso)))
    ref.update({"progresso": progresso})


# ======================================================
# PAGAMENTO (GANCHO FUTURO)
# ======================================================

def registrar_pagamento_sucesso(
    user_id: str,
    course_id: str,
    valor: float,
    metodo: str = "manual"
):
    """
    Hook para ser chamado quando o pagamento for confirmado.
    No futuro será ligado ao webhook do Mercado Pago com split.
    """
    db = _get_db()
    doc_id = get_inscricao_id(user_id, course_id)
    ref = db.collection("enrollments").document(doc_id)

    if not ref.get().exists:
        # Se por algum motivo ainda não tiver inscrição, cria
        inscrever_usuario_em_curso(user_id, course_id)

    ref.update({
        "pago": True,
        "valor_pago": float(valor),
        "metodo_pagamento": metodo,
        "data_pagamento": firestore.SERVER_TIMESTAMP,
    })
