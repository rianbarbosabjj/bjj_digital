import streamlit as st
import utils as ce
import views.aulas_aluno as aulas_view

def pagina_cursos_aluno(usuario):
    st.subheader("Meus Cursos")

    cursos = ce.listar_cursos_do_aluno(usuario["id"])

    if not cursos:
        st.info("Você ainda não está matriculada em nenhum curso.")
        return

    for c in cursos:
        with st.container(border=True):
            st.markdown(f"### {c.get('titulo')}")
            st.caption(c.get("descricao", ""))

            if st.button(
                "📖 Acessar Curso",
                key=f"acessar_{c['id']}",
                use_container_width=True
            ):
                st.session_state["curso_aluno_selecionado"] = c
                st.session_state["view_aluno"] = "aulas"
                st.rerun()

    # roteamento interno
    if st.session_state.get("view_aluno") == "aulas":
        aulas_view.pagina_aulas_aluno(
            st.session_state["curso_aluno_selecionado"],
            usuario
        )
