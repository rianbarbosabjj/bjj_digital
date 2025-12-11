# bjj_digital/views/cursos.py

import streamlit as st
import pandas as pd

from courses_engine import (
    criar_curso,
    listar_cursos_do_professor,
    listar_cursos_disponiveis_para_usuario,
    inscrever_usuario_em_curso,
    obter_inscricao,
)


def _get_tipo(usuario):
    return usuario.get("tipo", "aluno")


def pagina_cursos(usuario: dict):
    """
    Página única de Cursos. 
    - Se for aluno → lista cursos disponíveis + meus cursos
    - Se for professor/admin → inclui aba de criação e gestão de cursos
    """
    tipo = _get_tipo(usuario)

    st.markdown(
        "<h1 style='color:#FFD770; text-transform:uppercase;'>📚 Cursos</h1>",
        unsafe_allow_html=True
    )

    if tipo in ["admin", "professor"]:
        _pagina_cursos_professor(usuario)
    else:
        _pagina_cursos_aluno(usuario)


# ============================
# VISÃO: PROFESSOR / ADMIN
# ============================

def _pagina_cursos_professor(usuario: dict):
    tab1, tab2 = st.tabs([
        "📘 Meus Cursos",
        "➕ Criar Novo Curso",
    ])

    with tab1:
        _bloco_meus_cursos_professor(usuario)

    with tab2:
        _bloco_criar_curso(usuario)


def _bloco_meus_cursos_professor(usuario: dict):
    st.subheader("📘 Meus Cursos")

    cursos = listar_cursos_do_professor(usuario["id"])
    if not cursos:
        st.info("Você ainda não criou nenhum curso.")
        return

    df = pd.DataFrame([
        {
            "Título": c.get("titulo"),
            "Modalidade": c.get("modalidade"),
            "Público": "Todos" if c.get("publico") == "geral" else "Equipe",
            "Pago?": "Sim" if c.get("pago") else "Não",
            "Preço (R$)": c.get("preco", 0.0),
            "Certificado Auto?": "Sim" if c.get("certificado_automatico") else "Não",
        }
        for c in cursos
    ])

    st.dataframe(df, use_container_width=True)


def _bloco_criar_curso(usuario: dict):
    st.subheader("➕ Criar Novo Curso")

    with st.form("form_criar_curso"):
        titulo = st.text_input("Título do Curso")
        descricao = st.text_area("Descrição do Curso")
        modalidade = st.selectbox("Modalidade", ["EAD", "Presencial"])
        publico = st.selectbox("Público", ["geral", "equipe"], format_func=lambda v: "Todos" if v == "geral" else "Somente minha Equipe")

        equipe_destino = None
        if publico == "equipe":
            # FUTURO: carregar equipes reais do professor
            equipe_destino = st.text_input("Identificador da Equipe (por enquanto texto livre)")

        pago = st.checkbox("Curso Pago?", value=False)
        preco = None
        if pago:
            preco = st.number_input("Preço (R$)", min_value=0.0, step=10.0)

        st.markdown("### Configuração de Split (App x Professor)")
        split_custom = st.slider(
            "Percentual do App sobre o valor do curso (pode ser alterado pelo Admin depois)",
            min_value=0,
            max_value=100,
            value=20,
            step=5,
            help="Esse valor poderá ser sobrescrito pelas regras globais ou específicas do Admin."
        )
        certificado_auto = st.checkbox("Emitir certificado automaticamente ao concluir o curso?", value=True)

        submitted = st.form_submit_button("Salvar Curso")

    if submitted:
        if not titulo.strip():
            st.error("Informe um título para o curso.")
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
            st.success(f"Curso criado com sucesso! ID: {course_id}")
            st.balloons()
        except Exception as e:
            st.error(f"Erro ao criar curso: {e}")


# ============================
# VISÃO: ALUNO
# ============================

def _pagina_cursos_aluno(usuario: dict):
    tab1, tab2 = st.tabs([
        "📚 Cursos Disponíveis",
        "🎓 Meus Cursos",
    ])

    with tab1:
        _bloco_cursos_disponiveis(usuario)

    with tab2:
        _bloco_meus_cursos_aluno(usuario)


def _bloco_cursos_disponiveis(usuario: dict):
    st.subheader("📚 Cursos Disponíveis")

    cursos = listar_cursos_disponiveis_para_usuario(usuario)
    if not cursos:
        st.info("Ainda não há cursos disponíveis.")
        return

    for curso in cursos:
        with st.container(border=True):
            st.markdown(f"### {curso.get('titulo')}")
            st.write(curso.get("descricao") or "")
            st.write(
                f"**Modalidade:** {curso.get('modalidade', '—')} | "
                f"**Público:** {'Todos' if curso.get('publico') == 'geral' else 'Equipe'}"
            )

            pago = curso.get("pago", False)
            if pago:
                st.write(f"💰 Curso pago — valor aproximado: R$ {curso.get('preco', 0.0):.2f}")
                st.caption("🚧 Pagamento e split ainda serão implementados. Por enquanto, a inscrição é livre para desenvolvimento.")
            else:
                st.write("✅ Curso gratuito")

            inscricao = obter_inscricao(usuario["id"], curso["id"])
            if inscricao:
                st.success("Você já está inscrita(o) neste curso.")
            else:
                if st.button(f"Inscrever-se em {curso.get('titulo')}", key=f"btn_inscrever_{curso['id']}"):
                    inscrever_usuario_em_curso(usuario["id"], curso["id"])
                    st.success("Inscrição realizada com sucesso! (sem pagamento neste momento)")
                    st.experimental_rerun()


def _bloco_meus_cursos_aluno(usuario: dict):
    st.subheader("🎓 Meus Cursos")

    # Simplesmente reutiliza a coleção de enrollments + courses
    from database import get_db
    db = get_db()
    if not db:
        st.error("Não foi possível conectar ao banco de dados.")
        return

    q = db.collection("enrollments").where("user_id", "==", usuario["id"])
    inscricoes = list(q.stream())
    if not inscricoes:
        st.info("Você ainda não está inscrita(o) em nenhum curso.")
        return

    cursos_por_id = {}
    for ins in inscricoes:
        d_ins = ins.to_dict()
        course_id = d_ins.get("course_id")
        if not course_id:
            continue
        if course_id not in cursos_por_id:
            snap_course = db.collection("courses").document(course_id).get()
            if snap_course.exists:
                cursos_por_id[course_id] = snap_course.to_dict() | {"id": course_id}

    for course_id, curso in cursos_por_id.items():
        ins_doc = obter_inscricao(usuario["id"], course_id)
        progresso = (ins_doc or {}).get("progresso", 0.0)

        with st.container(border=True):
            st.markdown(f"### {curso.get('titulo')}")
            st.write(curso.get("descricao") or "")
            st.write(f"Progresso: **{progresso:.0f}%**")
            pago = (ins_doc or {}).get("pago", False)
            if pago:
                st.write("💰 Situação: Pago")
            else:
                st.write("💰 Situação: Em aberto (pagamento ainda não implementado)")

            st.caption("Em breve: acesso direto às aulas, módulos, provas e certificados por aqui.")
