import streamlit as st
import utils as ce

def pagina_aulas_aluno(curso, usuario):
    st.subheader(curso.get("titulo", "Curso"))

    # ---------------- PROGRESSO ----------------
    prog = ce.obter_progresso_curso(usuario["id"], curso["id"]) or {}
    pct = prog.get("progresso_percentual", 0)
    aulas_concluidas = set(prog.get("aulas_concluidas", []))

    st.progress(pct / 100)
    st.caption(f"Progresso no curso: {pct}%")

    st.markdown("---")

    # ---------------- CONTEÚDO ----------------
    modulos = ce.listar_modulos_e_aulas(curso["id"]) or []

    if not modulos:
        st.info("Este curso ainda não possui conteúdo.")
        return

    for mod in modulos:
        titulo_mod = mod.get("titulo", "Módulo")
        aulas = mod.get("aulas", [])

        with st.expander(titulo_mod, expanded=False):
            if not aulas:
                st.caption("Nenhuma aula neste módulo.")
                continue

            for aula in aulas:
                aula_id = aula.get("id")
                concluida = aula_id in aulas_concluidas

                st.markdown(f"**{aula.get('titulo', 'Aula')}**")
                st.caption(f"⏱ {aula.get('duracao_min', 0)} min")

                if st.checkbox(
                    "Marcar como concluída",
                    value=concluida,
                    key=f"done_{usuario['id']}_{curso['id']}_{aula_id}"
                ):
                    ce.marcar_aula_concluida(
                        usuario_id=usuario["id"],
                        curso_id=curso["id"],
                        aula_id=aula_id
                    )
                    st.rerun()
