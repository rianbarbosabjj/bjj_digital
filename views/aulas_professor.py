import streamlit as st
import utils as ce


def gerenciar_conteudo_curso(curso: dict, usuario: dict):
    """
    Gestão de módulos e aulas (Professor / Editor)
    Compatível com Firestore + AULAS_V2
    """

    # ======================================================
    # CABEÇALHO
    # ======================================================
    st.markdown("## 📁 Gestão de Conteúdo do Curso")
    st.markdown(f"### {curso.get('titulo', 'Curso')}")

    if st.button("← Voltar para o curso"):
        st.session_state["cursos_view"] = "detalhe"
        st.rerun()

    st.divider()

    curso_id = curso.get("id")
    if not curso_id:
        st.error("Curso inválido.")
        return

    # ======================================================
    # LISTAGEM DE MÓDULOS E AULAS
    # ======================================================
    modulos = ce.listar_modulos_e_aulas(curso_id) or []

    if not modulos:
        st.info("Este curso ainda não possui módulos.")
    else:
        for mod in modulos:
            with st.expander(f"📦 {mod.get('titulo', 'Módulo')}"):
                aulas = mod.get("aulas", [])

                if not aulas:
                    st.caption("Nenhuma aula neste módulo.")
                else:
                    for aula in aulas:
                        st.markdown(f"**📘 {aula.get('titulo', 'Aula')}**")
                        st.caption(f"Duração: {aula.get('duracao_min', 0)} min")
                        st.markdown("---")

    st.divider()

    # ======================================================
    # CRIAR NOVO MÓDULO
    # ======================================================
    st.markdown("## ➕ Novo Módulo")

    with st.form("form_novo_modulo"):
        titulo_mod = st.text_input("Título do módulo")

        submit_mod = st.form_submit_button("Criar módulo")

        if submit_mod:
            if not titulo_mod.strip():
                st.warning("Informe o título do módulo.")
            else:
                ordem = len(modulos) + 1
                ce.criar_modulo(
                    curso_id=curso_id,
                    titulo=titulo_mod.strip(),
                    descricao="",
                    ordem=ordem
                )
                st.success("Módulo criado com sucesso.")
                st.rerun()

    st.divider()

    # ======================================================
    # CRIAR NOVA AULA (V2 – MISTA)
    # ======================================================
    st.markdown("## ➕ Nova Aula (Mista)")

    if not modulos:
        st.info("Crie um módulo antes de adicionar aulas.")
        return

    modulos_map = {
        m["titulo"]: m["id"]
        for m in modulos
        if m.get("id")
    }

    # -------- estado local de blocos --------
    if "blocos_aula" not in st.session_state:
        st.session_state["blocos_aula"] = []

    with st.form("form_nova_aula"):
        titulo_aula = st.text_input("Título da aula")
        duracao = st.number_input("Duração (minutos)", min_value=1, step=1)
        modulo_titulo = st.selectbox("Módulo", list(modulos_map.keys()))
        modulo_id = modulos_map.get(modulo_titulo)

        st.markdown("### 📦 Blocos da Aula")

        # -------- adicionar blocos --------
        tipo_bloco = st.selectbox(
            "Tipo de bloco",
            ["texto", "imagem", "video"],
            key="tipo_bloco_novo"
        )

        if tipo_bloco == "texto":
            conteudo_txt = st.text_area("Conteúdo do texto")

            if st.form_submit_button("➕ Adicionar texto"):
                if conteudo_txt.strip():
                    st.session_state["blocos_aula"].append({
                        "tipo": "texto",
                        "conteudo": conteudo_txt
                    })

        else:
            arquivo = st.file_uploader(
                "Upload do arquivo (opcional)",
                type=["jpg", "jpeg", "png", "mp4", "mov"],
                key=f"upload_{tipo_bloco}"
            )
            url = st.text_input("Ou URL", key=f"url_{tipo_bloco}")

            if st.form_submit_button(f"➕ Adicionar {tipo_bloco}"):
                st.session_state["blocos_aula"].append({
                    "tipo": tipo_bloco,
                    "arquivo": arquivo,
                    "url_link": url
                })

        # -------- preview blocos --------
        if st.session_state["blocos_aula"]:
            st.markdown("### 👀 Prévia dos Blocos")
            for i, b in enumerate(st.session_state["blocos_aula"]):
                st.caption(f"{i+1}. {b['tipo']}")

        submit_aula = st.form_submit_button("Criar aula")

        if submit_aula:
            if not titulo_aula.strip():
                st.warning("Informe o título da aula.")
                return

            if not modulo_id:
                st.warning("Selecione um módulo.")
                return

            ce.criar_aula_v2(
                curso_id=curso_id,
                modulo_id=modulo_id,
                titulo=titulo_aula.strip(),
                tipo="misto",
                blocos=st.session_state["blocos_aula"],
                duracao_min=int(duracao),
                autor_id=usuario.get("id"),
                autor_nome=usuario.get("nome")
            )

            st.session_state["blocos_aula"] = []
            st.success("Aula criada com sucesso.")
            st.rerun()
