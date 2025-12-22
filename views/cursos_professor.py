import streamlit as st
import time
import pandas as pd
import utils as ce
from views import aulas_professor as aulas_view

# ======================================================
# PÁGINA PRINCIPAL – PROFESSOR
# ======================================================
def pagina_cursos_professor(usuario):
    st.title("📚 Gestão de Cursos (Professor)")

    if 'cursos_view' not in st.session_state:
        st.session_state['cursos_view'] = 'lista'
    if 'curso_selecionado' not in st.session_state:
        st.session_state['curso_selecionado'] = None

    # ===== ROTEAMENTO =====
    if st.session_state['cursos_view'] == 'conteudo':
        if st.session_state['curso_selecionado']:
            from views.aulas_professor import gerenciar_conteudo_curso
            gerenciar_conteudo_curso(
                st.session_state['curso_selecionado'],
                usuario
            )
        else:
            st.session_state['cursos_view'] = 'lista'
            st.rerun()

    elif st.session_state['cursos_view'] == 'detalhe':
        exibir_detalhes_curso(usuario)

    else:
        listar_cursos(usuario)

# ======================================================
# LISTA DE CURSOS
# ======================================================
def listar_cursos(usuario):
    st.subheader("📘 Meus Cursos")

    cursos = ce.listar_cursos_do_professor(usuario["id"])

    if not cursos:
        st.info("Nenhum curso encontrado.")
        return

    for c in cursos:
        inscritos = ce.listar_alunos_inscritos(c["id"])
        qtd_alunos = len(inscritos)
        preco = float(c.get("preco", 0))
        rendimento = qtd_alunos * preco

        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 2, 1])

            with col1:
                st.markdown(f"### {c.get('titulo')}")
                st.caption(c.get("descricao", "")[:100])

            with col2:
                st.metric("Alunos", qtd_alunos)
                st.metric("Rendimento", "Grátis" if preco == 0 else f"R$ {rendimento:.2f}")

            with col3:
                if st.button("Gerenciar", key=f"ger_{c['id']}"):
                    st.session_state.curso_selecionado = c
                    st.session_state.cursos_view = "detalhe"
                    st.rerun()

# ======================================================
# DETALHES DO CURSO
# ======================================================
def exibir_detalhes_curso(usuario):
    curso = st.session_state.curso_selecionado

    if not curso:
        st.session_state.cursos_view = "lista"
        st.rerun()

    if st.button("← Voltar"):
        st.session_state.cursos_view = "lista"
        st.rerun()

    st.markdown(f"## {curso.get('titulo')}")

    tab1, tab2 = st.tabs(["📋 Visão Geral", "👥 Alunos & Rendimento"])

    # ---------- VISÃO GERAL ----------
    with tab1:
        st.markdown(f"**Descrição:** {curso.get('descricao','-')}")
        st.markdown(f"**Modalidade:** {curso.get('modalidade','-')}")
        st.markdown(f"**Preço:** R$ {curso.get('preco',0):.2f}")

        st.markdown("---")

    if st.button("📁 Gerenciar Conteúdo", type="primary"):
        st.session_state['cursos_view'] = 'conteudo'
        st.rerun()

    # ---------- ALUNOS ----------
    with tab2:
        alunos = ce.listar_alunos_inscritos(curso["id"])
        if alunos:
            st.dataframe(pd.DataFrame(alunos), use_container_width=True)
        else:
            st.info("Nenhum aluno matriculado.")
