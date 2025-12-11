# bjj_digital/views/cursos.py

import streamlit as st
from typing import Optional

from courses_engine import (
    criar_curso,
    listar_cursos_do_professor,
    listar_cursos_disponiveis_para_usuario,
    inscrever_usuario_em_curso,
    obter_inscricao,
)
from database import get_db


# ======================================================
# PÁGINA PRINCIPAL
# ======================================================

def pagina_cursos(usuario: dict):
    """
    Interface de cursos, adaptada ao tipo de usuário.
    """
    tipo = str(usuario.get("tipo", "aluno")).lower()

    st.markdown("<h1>📚 Cursos</h1>", unsafe_allow_html=True)

    if tipo in ["admin", "professor"]:
        _interface_professor(usuario)
    else:
        _interface_aluno(usuario)


# ======================================================
# VISÃO DO PROFESSOR / ADMIN
# ======================================================

def _interface_professor(usuario: dict):
    tab1, tab2 = st.tabs(["📘 Meus Cursos", "➕ Criar Novo Curso"])

    with tab1:
        _prof_listar_cursos(usuario)

    with tab2:
        _prof_criar_curso(usuario)


def _prof_listar_cursos(usuario: dict):
    st.subheader("📘 Meus Cursos")

    cursos = listar_cursos_do_professor(usuario["id"])

    if not cursos:
        st.info("Você ainda não criou nenhum curso.")
        return

    st.write("")

    # Cards modernos
    for curso in cursos:
        ativo = curso.get("ativo", True)

        with st.container(border=True):
            st.markdown(f"### {curso.get('titulo')}")

            desc = (curso.get("descricao") or "").strip()
            if desc:
                st.markdown(
                    f"<p style='color:#dddddd; font-size:0.9rem;'>{desc[:200]}{'...' if len(desc)>200 else ''}</p>",
                    unsafe_allow_html=True
                )

            col1, col2, col3 = st.columns([1.5, 1, 0.8])

            # Informações do curso
            with col1:
                st.write(f"**Modalidade:** {curso.get('modalidade', '-')}")
                st.write(
                    f"**Público:** "
                    f"{'Todos' if curso.get('publico') == 'geral' else 'Equipe'}"
                )
                st.write(f"**Status:** {'🟢 Ativo' if ativo else '🔴 Inativo'}")

            # Pagamento, certificado e split
            with col2:
                if curso.get("pago"):
                    st.write(f"💰 **Pago — R$ {curso.get('preco', 0.0):.2f}**")
                else:
                    st.write("🆓 **Gratuito**")

                st.write(
                    f"**Certificado Auto.:** "
                    f"{'Sim' if curso.get('certificado_automatico') else 'Não'}"
                )

                split = curso.get("split_custom", 10)
                st.write(f"**% App:** {int(split)}%")

            # Botões
            with col3:
                if st.button(
                    "✏️ Editar",
                    key=f"edit_{curso['id']}",
                    use_container_width=True
                ):
                    st.session_state["edit_course"] = curso

                if st.button(
                    "🔴 Desativar" if ativo else "🟢 Ativar",
                    key=f"toggle_{curso['id']}",
                    use_container_width=True
                ):
                    _toggle_status_curso(curso["id"], not ativo)
                    st.rerun()

    # Editor lateral
    if "edit_course" in st.session_state:
        _editor_curso(st.session_state["edit_course"])


def _prof_criar_curso(usuario: dict):
    st.subheader("➕ Criar Novo Curso")

    with st.form("form_criar_curso"):
        titulo = st.text_input("Título do Curso")
        descricao = st.text_area("Descrição")
        modalidade = st.selectbox("Modalidade", ["EAD", "Presencial"])

        publico = st.selectbox(
            "Público",
            ["geral", "equipe"],
            format_func=lambda v: "Todos" if v == "geral" else "Somente Minha Equipe"
        )

        equipe_destino = None
        if publico == "equipe":
            equipe_destino = st.text_input("Nome/ID da Equipe")

        pago = st.checkbox("Curso Pago?")
        preco = st.number_input("Preço (R$)", min_value=0.0, step=10.0) if pago else None

        certificado_auto = st.checkbox("Certificado Automático?", value=True)

        # 🔥 ALTERADO: padrão 10%
        split_custom = st.slider(
            "Percentual do App",
            min_value=0,
            max_value=100,
            value=10,   # PADRÃO ALTERADO PARA 10%
            step=5
        )

        enviar = st.form_submit_button("Salvar Curso")

    if enviar:
        if not titulo.strip():
            st.error("O título é obrigatório.")
            return

        try:
            course_id = criar_curso(
                professor_id=usuario["id"],
                nome_professor=usuario.get("nome", ""),
                titulo=titulo,
                descricao=descricao,
                modalidade=modalidade,
                publico=publico,
                equipe_destino=equipe_destino,
                pago=pago,
                preco=preco,
                split_custom=split_custom,
                certificado_automatico=certificado_auto
            )

            st.success(f"Curso criado! ID: {course_id}")
            st.balloons()

        except Exception as e:
            st.error(f"Erro ao criar curso: {e}")


# ======================================================
# EDITOR DE CURSOS (SIDEBAR)
# ======================================================

def _editor_curso(curso: dict):
    import streamlit as st

    st.markdown("""
        <style>
        .modal-fundo {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.65);
            z-index: 9999;
        }
        .modal-corpo {
            background: #0e2d26;
            border: 1px solid rgba(255,215,112,0.4);
            padding: 30px;
            border-radius: 12px;
            width: 60%;
            margin: 5% auto;
            box-shadow: 0 0 25px rgba(0,0,0,0.5);
        }
        </style>
    """, unsafe_allow_html=True)

    # fundo escurecido
    with st.container():
        st.markdown('<div class="modal-fundo">', unsafe_allow_html=True)

        # corpo do modal
        st.markdown('<div class="modal-corpo">', unsafe_allow_html=True)

        st.markdown("## ✏️ Editar Curso")

        with st.form("form_edit_course"):

            novo_titulo = st.text_input("Título", curso.get("titulo", ""))
            nova_desc = st.text_area("Descrição", curso.get("descricao", ""))

            modalidade = st.selectbox(
                "Modalidade",
                ["EAD", "Presencial"],
                index=0 if curso.get("modalidade") == "EAD" else 1
            )

            publico = st.selectbox(
                "Público",
                ["geral", "equipe"],
                index=0 if curso.get("publico") == "geral" else 1
            )

            equipe_destino = None
            if publico == "equipe":
                equipe_destino = st.text_input(
                    "Equipe",
                    curso.get("equipe_destino", "")
                )

            pago = st.checkbox("Curso Pago?", value=curso.get("pago", False))
            preco = st.number_input("Preço (R$)", value=float(curso.get("preco", 0.0))) if pago else None

            certificado_auto = st.checkbox(
                "Certificado Automático",
                value=curso.get("certificado_automatico", True)
            )

            split_custom = st.slider(
                "Percentual do App",
                0, 100,
                value=int(curso.get("split_custom", 10)),
                step=5
            )

            col1, col2 = st.columns(2)
            salvar = col1.form_submit_button("Salvar Alterações")
            cancelar = col2.form_submit_button("Cancelar")

        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if cancelar:
        del st.session_state["edit_course"]
        st.rerun()

    if salvar:
        try:
            _salvar_edicao_curso(
                curso_id=curso["id"],
                titulo=novo_titulo,
                descricao=nova_desc,
                modalidade=modalidade,
                publico=publico,
                equipe_destino=equipe_destino,
                pago=pago,
                preco=preco,
                split_custom=split_custom,
                certificado_automatico=certificado_auto
            )
            del st.session_state["edit_course"]
            st.success("Curso atualizado!")
            st.rerun()

        except Exception as e:
            st.error(f"Erro ao atualizar curso: {e}")



# ======================================================
# VISÃO DO ALUNO
# ======================================================

def _interface_aluno(usuario: dict):
    tab1, tab2 = st.tabs(["📚 Cursos Disponíveis", "🎓 Meus Cursos"])

    with tab1:
        _aluno_cursos_disponiveis(usuario)

    with tab2:
        _aluno_meus_cursos(usuario)


def _aluno_cursos_disponiveis(usuario: dict):
    st.subheader("📚 Cursos Disponíveis")

    cursos = listar_cursos_disponiveis_para_usuario(usuario)

    if not cursos:
        st.info("Nenhum curso disponível no momento.")
        return

    for curso in cursos:
        inscricao = obter_inscricao(usuario["id"], curso["id"])

        with st.container(border=True):
            st.markdown(f"### {curso.get('titulo')}")

            desc = (curso.get("descricao") or "").strip()
            if desc:
                st.markdown(
                    f"<p style='color:#dddddd; font-size:0.9rem;'>{desc}</p>",
                    unsafe_allow_html=True
                )

            st.write(
                f"**Modalidade:** {curso.get('modalidade')} | "
                f"**Público:** {'Todos' if curso.get('publico') == 'geral' else 'Equipe'}"
            )

            if curso.get("pago"):
                st.write(f"💰 Pago — **R$ {curso.get('preco', 0.0):.2f}**")
            else:
                st.write("🆓 Gratuito")

            if inscricao:
                st.success("Você já está inscrita(o).")
            else:
                if st.button(
                    f"Inscrever-se em {curso['titulo']}",
                    key=f"btn_inscrever_{curso['id']}"
                ):
                    inscrever_usuario_em_curso(usuario["id"], curso["id"])
                    st.success("Inscrição feita!")
                    st.rerun()


def _aluno_meus_cursos(usuario: dict):
    st.subheader("🎓 Meus Cursos")

    db = get_db()
    if not db:
        st.error("Erro de conexão com banco.")
        return

    q = db.collection("enrollments").where("user_id", "==", usuario["id"]).stream()
    inscricoes = list(q)

    if not inscricoes:
        st.info("Você ainda não está inscrita(o) em nenhum curso.")
        return

    for ins in inscricoes:
        d = ins.to_dict()
        curso_id = d.get("course_id")

        snap = db.collection("courses").document(curso_id).get()
        if not snap.exists:
            continue

        curso = snap.to_dict()
        progresso = d.get("progresso", 0)

        with st.container(border=True):
            st.markdown(f"### {curso.get('titulo')}")

            desc = (curso.get("descricao") or "").strip()
            if desc:
                st.markdown(
                    f"<p style='color:#dddddd; font-size:0.9rem;'>{desc}</p>",
                    unsafe_allow_html=True
                )

            st.write(f"📊 **Progresso:** {progresso:.0f}%")

            if curso.get("pago"):
                if d.get("pago"):
                    st.write("💰 Pagamento confirmado")
                else:
                    st.warning("💰 Pagamento pendente")
            else:
                st.write("🆓 Curso gratuito")

            st.caption("Em breve: acesso a módulos, aulas e certificados.")


# ======================================================
# FUNÇÕES AUXILIARES
# ======================================================

def _salvar_edicao_curso(
    curso_id: str,
    titulo: str,
    descricao: str,
    modalidade: str,
    publico: str,
    equipe_destino: Optional[str],
    pago: bool,
    preco: Optional[float],
    split_custom: Optional[int],
    certificado_automatico: bool
):
    db = get_db()
    doc = {
        "titulo": titulo.strip(),
        "descricao": descricao.strip(),
        "modalidade": modalidade,
        "publico": publico,
        "equipe_destino": equipe_destino or None,
        "pago": bool(pago),
        "preco": float(preco) if (pago and preco is not None) else 0.0,
        "split_custom": int(split_custom) if split_custom is not None else 10,
        "certificado_automatico": bool(certificado_automatico),
    }
    db.collection("courses").document(curso_id).update(doc)


def _toggle_status_curso(curso_id: str, novo_ativo: bool):
    db = get_db()
    db.collection("courses").document(curso_id).update({
        "ativo": bool(novo_ativo),
        "status": "ativo" if novo_ativo else "inativo"
    })
