import streamlit as st
import utils as ce


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

                # O CONTEÚDO SEMPRE VEM DENTRO DE "conteudo"
                conteudo = aula.get("conteudo", {})

                # -------- NOVO FORMATO (AULAS_V2 / BLOCOS) --------
                blocos = conteudo.get("blocos", [])

                if blocos:
                    for bloco in blocos:
                        tipo = bloco.get("tipo")

                        if tipo == "texto":
                            st.markdown(bloco.get("conteudo", ""))

                        elif tipo == "video":
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
    file_path = bloco.get("arquivo_video") or bloco.get("file_path")
    if file_path:
        try:
            st.video(file_path)
            return
        except Exception:
            st.warning("Vídeo enviado, mas não foi possível reproduzir.")

    # 3️⃣ Bytes (fallback – se existir)
    video_bytes = bloco.get("video_bytes")
    if video_bytes:
        try:
            st.video(video_bytes)
        except Exception:
            st.warning("Formato de vídeo não suportado.")
