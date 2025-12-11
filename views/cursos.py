import streamlit as st
import pandas as pd

from courses_engine import (
    criar_curso,
    listar_cursos_do_professor,
    listar_cursos_disponiveis_para_usuario,
    inscrever_usuario_em_curso,
    obter_inscricao,
)

from database import get_db


# ----------------------------------------------------
#  Função principal da página
# ----------------------------------------------------

def pagina_cursos(usuario: dict):
    """
    Página de Cursos — interface adaptada ao tipo de usuário (aluno/professor/admin).
    """
    tipo = usuario.get("tipo", "aluno").lower()

    st.markdown("<h1>📚 Cursos</h1>", unsafe_allow_html=True)

    if tipo in ["admin", "professor"]:
        _interface_professor(usuario)
    else:
        _interface_aluno(usuario)


# ----------------------------------------------------
#  VISÃO DO PROFESSOR / ADMIN
# ----------------------------------------------------

def _interface_professor(usuario):
    tab1, tab2 = st.tabs(["📘 Meus Cursos", "➕ Criar Novo Curso"])

    with tab1:
        _prof_listar_cursos(usuario)

    with tab2:
        _prof_criar_curso(usuario)


def _prof_listar_cursos(usuario):
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
            "Certificado Automático": "Sim" if c.get("certificado_automatico") else "Não",
        }
        for c in cursos
    ])

    st.dataframe(df, use_container_width=True)


def _prof_criar_curso(usuario):
    st.subheader("➕ Criar Novo Curso")

    with st.form("form_criar_curso"):
        titulo = st.text_input("Título do Curso")
        descricao = st.text_area("Descrição do Curso")
        modalidade = st.selectbox("Modalidade", ["EAD", "Presencial"])
        publico = st.selectbox(
            "Público",
            ["geral", "equipe"],
            format_func=lambda v: "Todos" if v == "geral" else "Somente Minha Equipe"
        )

        equipe_destino = None
        if publico == "equipe":
            equipe_destino = st.text_input("Nome/ID da Equipe")

        pago = st.checkbox("Curso Pago?", value=False)
        preco = st.number_input("Preço (R$)", min_value=0.0, step=10.0) if pago else None

        certificado_auto = st.checkbox("Gerar Certificado Automaticamente?", value=True)

        split_custom = st.slider(
            "Percentual do App (Admin pode alterar depois)",
            min_value=0,
            max_value=100,
            value=20,
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
            st.success(f"Curso criado com sucesso! ID: {course_id}")
            st.balloons()
        except Exception as e:
            st.error(f"Erro ao criar curso: {e}")


# ----------------------------------------------------
#  VISÃO DO ALUNO
# ----------------------------------------------------

def _interface_aluno(usuario):
    tab1, tab2 = st.tabs(["📚 Cursos Disponíveis", "🎓 Meus Cursos"])

    with tab1:
        _aluno_cursos_disponiveis(usuario)

    with tab2:
        _aluno_meus_cursos(usuario)


def _aluno_cursos_disponiveis(usuario):
    st.subheader("📚 Cursos Disponíveis")

    cursos = listar_cursos_disponiveis_para_usuario(usuario)

    if not cursos:
        st.info("Ainda não há cursos disponíveis.")
        return

    for curso in cursos:
        inscricao = obter_inscricao(usuario["id"], curso["id"])

        with st.container(border=True):
            st.markdown(f"### {curso.get('titulo')}")
            st.write(curso.get("descricao") or "")

            st.write(
                f"**Modalidade:** {curso.get('modalidade')} | "
                f"**Público:** {'Todos' if curso.get('publico') == 'geral' else 'Equipe'}"
            )

            if curso.get("pago"):
                st.write(f"💰 Curso Pago — R$ {curso.get('preco', 0.0):.2f}")
            else:
                st.write("🆓 Curso Gratuito")

            if inscricao:
                st.success("Você já está inscrita(o) neste curso.")
            else:
                if st.button(
                    f"Inscrever-se em {curso['titulo']}",
                    key=f"btn_inscrever_{curso['id']}"
                ):
                    inscrever_usuario_em_curso(usuario["id"], curso["id"])
                    st.success("Inscrição realizada com sucesso!")
                    st.rerun()


def _aluno_meus_cursos(usuario):
    st.subheader("🎓 Meus Cursos")

    db = get_db()
    if not db:
        st.error("Erro ao conectar ao banco.")
        return

    q = db.collection("enrollments").where("user_id", "==", usuario["id"]).stream()
    inscricoes = list(q)

    if not inscricoes:
        st.info("Você ainda não está inscrita(o) em nenhum curso.")
        return

    for ins in inscricoes:
        d = ins.to_dict()
        curso_id = d.get("course_id")

        curso_snap = db.collection("courses").document(curso_id).get()
        if not curso_snap.exists:
            continue

        curso = curso_snap.to_dict()
        progresso = d.get("progresso", 0)

        with st.container(border=True):
            st.markdown(f"### {curso.get('titulo')}")
            st.write(curso.get("descricao", ""))

            st.write(f"📊 Progresso: **{progresso:.0f}%**")

            if curso.get("pago"):
                if d.get("pago"):
                    st.write("💰 Situação: Pagamento Confirmado")
                else:
                    st.warning("💰 Pagamento Pendente")
            else:
                st.write("🆓 Curso Gratuito")

            st.caption("Aulas, módulos e certificados serão exibidos aqui em breve.")
