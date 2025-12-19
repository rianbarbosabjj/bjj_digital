import streamlit as st
import utils as ce


def renderizar_video_bloco(bloco: dict):
    """
    Renderiza vídeo a partir de:
    - URL externa
    - Arquivo local (upload salvo)
    - Bytes (fallback)
    """

    # 1️⃣ URL externa
    url = bloco.get("url_link") or bloco.get("url")
    if url:
        try:
            st.video(url)
            return
        except Exception:
            st.markdown(f"[▶ Assistir vídeo]({url})")
            return

    # 2️⃣ Arquivo local (upload salvo)
    file_path = (
        bloco.get("arquivo_video")
        or bloco.get("file_path")
        or bloco.get("caminho_arquivo")
    )
    if file_path:
        try:
            st.video(file_path)
            return
        except Exception:
            st.warning("⚠️ Vídeo enviado, mas não foi possível reproduzir.")
            return

    # 3️⃣ Bytes (fallback)
    video_bytes = bloco.get("video_bytes")
    if video_bytes:
        try:
            st.video(video_bytes)
            return
        except Exception:
            st.warning("⚠️ Formato de vídeo não suportado.")
            return

    st.info("🎬 Vídeo indisponível para reprodução.")


def pagina_aulas_aluno(curso, usuario):
    # =========================
    # CABEÇALHO
    # =========================
    st.subheader(curso.get("titulo", "Curso"))

    # =========================
    # PROGRESSO DO CURSO
    # =========================
    prog = ce.obter_progresso_curso(usuario["id"], curso["id"]) or {}
    pct = prog.get("progresso_percentual", 0)
    aulas_concluidas = set(prog.get("aulas_concluidas", []))

    st.progress(pct / 100)
    st.caption(f"Progresso no curso: {pct}%")

    st.markdown("---")

    # =========================
    # LISTAGEM DE MÓDULOS
    # =========================
    modulos = ce.listar_modulos_e_aulas(curso["id"]) or []

    if not modulos:
        st.info("Este curso ainda não possui conteúdo.")
        return

    for mod in modulos:
        with st.expander(mod.get("titulo", "Módulo")):
            aulas = mod.get("aulas", [])

            if not aulas:
                st.caption("Nenhuma aula disponível neste módulo.")
                continue

            for aula in aulas:
                aula_id = aula.get("id")
                concluida = aula_id in aulas_concluidas

                # =========================
                # CABEÇALHO DA AULA
                # =========================
                st.markdown(f"### {aula.get('titulo', 'Aula')}")
                st.caption(f"⏱ {aula.get('duracao_min', 0)} min")

                # =========================
                # RENDERIZAÇÃO DO CONTEÚDO
                # =========================
                conteudo = aula.get("conteudo", {})
                blocos = conteudo.get("blocos", [])

                # -------- NOVO FORMATO (AULAS_V2 / BLOCOS) --------
                if blocos:
                    for bloco in blocos:
                        tipo = bloco.get("tipo")

                        if tipo == "texto":
                            st.markdown(bloco.get("conteudo", ""))

                        elif tipo == "imagem":
                            url = bloco.get("url_link") or bloco.get("url")
                            if url:
                                st.image(url, use_container_width=True)

                        elif tipo == "video":
                            renderizar_video_bloco(bloco)

                        st.write("")

                # -------- FORMATO ANTIGO (LEGADO) --------
                else:
                    if "texto" in conteudo:
                        st.markdown(conteudo.get("texto", ""))

                    if "url" in conteudo:
                        try:
                            st.video(conteudo["url"])
                        except Exception:
                            st.markdown(f"[▶ Assistir conteúdo]({conteudo['url']})")

                # =========================
                # MARCAR COMO CONCLUÍDA
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
