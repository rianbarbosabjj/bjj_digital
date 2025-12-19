import streamlit as st
import utils as ce


def renderizar_video_bloco(bloco: dict):
    """
    Renderiza vídeo a partir de:
    - URL externa
    - UploadedFile (upload direto)
    - Arquivo local
    - Bytes
    """

    # 1️⃣ UploadedFile (upload direto)
    arquivo = bloco.get("arquivo")
    if arquivo:
        try:
            st.video(arquivo)
            return
        except Exception:
            st.warning("⚠️ Vídeo enviado, mas não foi possível reproduzir.")

    # 2️⃣ URL externa (qualquer chave comum)
    url = (
        bloco.get("url_link")
        or bloco.get("url")
        or bloco.get("arquivo_url")
    )
    if url:
        try:
            st.video(url)
            return
        except Exception:
            st.markdown(f"[▶ Assistir vídeo]({url})")

    # 3️⃣ Arquivo salvo localmente
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
            st.warning("⚠️ Vídeo salvo, mas não foi possível reproduzir.")

    # 4️⃣ Bytes
    video_bytes = bloco.get("video_bytes")
    if video_bytes:
        try:
            st.video(video_bytes)
            return
        except Exception:
            st.warning("⚠️ Formato de vídeo não suportado.")

    st.info("🎬 Vídeo indisponível.")


def renderizar_imagem_bloco(bloco: dict):
    """
    Renderiza imagem a partir de:
    - UploadedFile
    - URL
    """

    # 1️⃣ UploadedFile
    arquivo = bloco.get("arquivo")
    if arquivo:
        try:
            st.image(arquivo, use_container_width=True)
            return
        except Exception:
            pass

    # 2️⃣ URL (qualquer chave comum)
    url = (
        bloco.get("url_link")
        or bloco.get("url")
        or bloco.get("arquivo_url")
    )
    if url:
        st.image(url, use_container_width=True)
        return

    st.info("🖼️ Imagem indisponível.")


def pagina_aulas_aluno(curso, usuario):
    st.subheader(curso.get("titulo", "Curso"))

    # =========================
    # PROGRESSO
    # =========================
    prog = ce.obter_progresso_curso(usuario["id"], curso["id"]) or {}
    pct = prog.get("progresso_percentual", 0)
    aulas_concluidas = set(prog.get("aulas_concluidas", []))

    st.progress(pct / 100)
    st.caption(f"Progresso no curso: {pct}%")
    st.markdown("---")

    # =========================
    # CONTEÚDO
    # =========================
    modulos = ce.listar_modulos_e_aulas(curso["id"]) or []

    if not modulos:
        st.info("Este curso ainda não possui conteúdo.")
        return

    for mod in modulos:
        with st.expander(mod.get("titulo", "Módulo")):
            aulas = mod.get("aulas", [])

            if not aulas:
                st.caption("Nenhuma aula disponível.")
                continue

            for aula in aulas:
                aula_id = aula.get("id")
                concluida = aula_id in aulas_concluidas

                st.markdown(f"### {aula.get('titulo', 'Aula')}")
                st.caption(f"⏱ {aula.get('duracao_min', 0)} min")

                conteudo = aula.get("conteudo", {})
                blocos = conteudo.get("blocos", [])

                # ===== AULAS V2 (BLOCOS) =====
                if blocos:
                    for bloco in blocos:
                        tipo = bloco.get("tipo")

                        if tipo == "texto":
                            st.markdown(bloco.get("conteudo", ""))

                        elif tipo == "imagem":
                            renderizar_imagem_bloco(bloco)

                        elif tipo == "video":
                            renderizar_video_bloco(bloco)

                        st.write("")

                # ===== FORMATO LEGADO =====
                else:
                    if "texto" in conteudo:
                        st.markdown(conteudo.get("texto", ""))

                    if "url" in conteudo:
                        # tenta como vídeo primeiro
                        try:
                            st.video(conteudo["url"])
                        except Exception:
                            st.image(conteudo["url"], use_container_width=True)

                # ===== CONCLUSÃO =====
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
