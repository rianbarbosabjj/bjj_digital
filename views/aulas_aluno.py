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
        st.info("Este curso ainda não possui aulas.")
        return

    for mod in modulos:
        titulo_mod = mod.get("titulo", "Módulo")
        aulas = mod.get("aulas", [])

        with st.expander(titulo_mod, expanded=True):
            if not aulas:
                st.caption("Sem aulas neste módulo.")
                continue

            for aula in aulas:
                aula_id = aula.get("id")
                concluida = aula_id in aulas_concluidas

                st.markdown(f"### {aula.get('titulo', 'Aula')}")
                st.caption(f"⏱ {aula.get('duracao_min', 0)} min")

# =========================
# RENDERIZAÇÃO DO CONTEÚDO
# =========================

conteudo = aula.get("conteudo", {})
blocos = conteudo.get("blocos", [])

# --- NOVO FORMATO (V2 / BLOCOS) ---
if blocos:
    for bloco in blocos:
        tipo = bloco.get("tipo")

        if tipo == "texto":
            st.markdown(bloco.get("conteudo", ""))

        elif tipo == "video":
            url = bloco.get("url_link") or bloco.get("url")
            if url:
                try:
                    st.video(url)
                except:
                    st.markdown(f"[▶ Assistir vídeo]({url})")

        elif tipo == "imagem":
            url = bloco.get("url_link") or bloco.get("url")
            if url:
                st.image(url, use_container_width=True)

# --- FORMATO ANTIGO (LEGADO) ---
else:
    if "texto" in conteudo:
        st.markdown(conteudo.get("texto", ""))

    if "url" in conteudo:
        try:
            st.video(conteudo["url"])
        except:
            st.markdown(f"[▶ Assistir conteúdo]({conteudo['url']})")


                # =========================
                # CHECKBOX DE CONCLUSÃO
                # =========================
                if st.checkbox(
                    "Marcar como concluída",
                    value=concluida,
                    key=f"done_{usuario['id']}_{aula_id}"
                ):
                    ce.marcar_aula_concluida(
                        usuario_id=usuario["id"],
                        curso_id=curso["id"],
                        aula_id=aula_id
                    )
                    st.rerun()

                st.markdown("---")
