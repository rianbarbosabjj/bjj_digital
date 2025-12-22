import streamlit as st
import utils as ce


def gerenciar_conteudo_curso(curso, usuario):
    """
    Tela de gestão de conteúdo do curso (Professor)
    """

    # =========================
    # CABEÇALHO
    # =========================
    st.markdown("## 📁 Gestão de Conteúdo do Curso")
    st.markdown(f"### {curso.get('titulo', 'Curso')}")

    if st.button("← Voltar para o curso"):
        st.session_state['cursos_view'] = 'detalhe'
        st.rerun()

    st.markdown("---")

    # =========================
    # LISTAGEM DE MÓDULOS
    # =========================
    modulos = ce.listar_modulos_e_aulas(curso['id']) or []

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

    # =========================
    # CRIAÇÃO DE NOVO MÓDULO
    # =========================
    st.markdown("## ➕ Novo Módulo")

    with st.form("form_novo_modulo"):
        titulo_mod = st.text_input("Título do Módulo")

        if st.form_submit_button("Criar Módulo"):
            if not titulo_mod.strip():
                st.warning("Informe um título para o módulo.")
            else:
                ce.criar_modulo(
                curso['id'],
                titulo_mod,
                1  # ordem inicial do módulo
                )
                st.success("Módulo criado com sucesso!")
                st.rerun()

    st.markdown("---")

    # =========================
    # CRIAÇÃO DE NOVA AULA
    # =========================
    st.markdown("## ➕ Nova Aula")

    if not modulos:
        st.info("Crie um módulo antes de adicionar aulas.")
        return

    modulos_map = {m['titulo']: m['id'] for m in modulos}

    with st.form("form_nova_aula"):
        titulo_aula = st.text_input("Título da Aula")
        duracao = st.number_input("Duração (minutos)", min_value=1, step=1)
        modulo_sel = st.selectbox("Módulo", list(modulos_map.keys()))

        if st.form_submit_button("Criar Aula"):
            if not titulo_aula.strip():
                st.warning("Informe o título da aula.")
            else:
                ce.criar_aula(
                    curso_id=curso['id'],
                    modulo_id=modulos_map[modulo_sel],
                    titulo=titulo_aula,
                    duracao_min=duracao,
                    conteudo={}
                )
                st.success("Aula criada com sucesso!")
                st.rerun()
