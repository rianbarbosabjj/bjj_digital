import streamlit as st
import time
import pandas as pd
from datetime import datetime
import utils as ce
import re

try:
    from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
except ImportError:
    COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER = (
        "#0e2d26", "#FFFFFF", "#FFD770", "#078B6C", "#FFD770"
    )


# =====================================================
# PÁGINA PRINCIPAL – PROFESSOR
# =====================================================
def pagina_cursos_professor(usuario):
    st.title("📚 Gestão de Cursos (Professor)")

    # ---------------- ESTADO ----------------
    if 'cursos_view' not in st.session_state:
        st.session_state['cursos_view'] = 'lista'

    if 'curso_selecionado' not in st.session_state:
        st.session_state['curso_selecionado'] = None

    if 'editando_curso' not in st.session_state:
        st.session_state['editando_curso'] = False

    view = st.session_state['cursos_view']

    # ---------------- ROTEAMENTO ----------------
    if view == 'conteudo':
        curso = st.session_state.get('curso_selecionado')
        if curso:
            try:
                # 🔥 IMPORT LOCAL (remove dependência circular)
                from views.aulas_professor import gerenciar_conteudo_curso
                gerenciar_conteudo_curso(curso, usuario)
            except Exception as e:
                st.error("Erro ao carregar o gerenciador de aulas.")
                st.caption(str(e))
                st.session_state['cursos_view'] = 'lista'
                st.rerun()
        else:
            st.session_state['cursos_view'] = 'lista'
            st.rerun()
        return

    elif view == 'detalhe':
        exibir_detalhes_curso(usuario)
        return

    else:
        listar_cursos(usuario)


# =====================================================
# LISTAGEM DE CURSOS
# =====================================================
def listar_cursos(usuario):
    st.subheader("Meus Cursos")

    # ---------- CRIAÇÃO DE CURSO ----------
    if usuario.get('tipo') in ['admin', 'professor', 'mestre']:
        with st.expander("➕ Novo Curso"):
            with st.form("form_curso"):
                titulo = st.text_input("Título")
                desc = st.text_area("Descrição")

                c1, c2 = st.columns(2)
                modalidade = c1.selectbox("Modalidade", ["EAD", "Presencial", "Híbrido"])
                publico_sel = c2.selectbox(
                    "Público Alvo",
                    ["Aberto a Todos", "Restrito à Minha Equipe"]
                )

                st.markdown("###### Professores Auxiliares (opcional)")
                cpfs_input = st.text_area(
                    "CPFs (um por linha)",
                    height=70,
                    placeholder="111.222.333-44"
                )

                preco = st.number_input("Preço (R$)", 0.0, step=10.0)

                if st.form_submit_button("Criar Curso"):
                    ids_editores = []

                    if cpfs_input:
                        for cpf in re.split(r'[,\n]', cpfs_input):
                            cpf = cpf.strip()
                            if cpf:
                                u = ce.buscar_usuario_por_cpf(cpf)
                                if u and u['id'] != usuario['id']:
                                    ids_editores.append(u['id'])

                    publico_val = 'equipe' if "Restrito" in publico_sel else 'todos'
                    equipe_dest = usuario.get('equipe', '') if publico_val == 'equipe' else ''

                    ce.criar_curso(
                        usuario['id'],
                        usuario['nome'],
                        usuario.get('equipe', ''),
                        titulo,
                        desc,
                        modalidade,
                        publico_val,
                        equipe_dest,
                        True,
                        preco,
                        False,
                        False,
                        10,
                        'iniciante',
                        editores_ids=ids_editores
                    )

                    st.success("Curso criado com sucesso!")
                    time.sleep(1)
                    st.rerun()

    st.markdown("---")

    cursos = ce.listar_cursos_do_professor(usuario['id'])

    if not cursos:
        st.info("Nenhum curso encontrado.")
        return

    for c in cursos:
        inscritos = ce.listar_alunos_inscritos(c['id'])
        qtd_alunos = len(inscritos)
        preco = float(c.get('preco', 0))
        faturamento = qtd_alunos * preco

        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 2, 1])

            with col1:
                st.markdown(f"### {c.get('titulo')}")
                st.caption(c.get('descricao', '')[:100])

            with col2:
                st.metric("Alunos", qtd_alunos)
                st.metric("Rendimento", f"R$ {faturamento:,.2f}" if preco > 0 else "Grátis")

            with col3:
                if st.button("Gerenciar", key=f"ger_{c['id']}", use_container_width=True):
                    st.session_state['curso_selecionado'] = c
                    st.session_state['cursos_view'] = 'detalhe'
                    st.session_state['editando_curso'] = False
                    st.rerun()


# =====================================================
# DETALHES DO CURSO
# =====================================================
def exibir_detalhes_curso(usuario):
    curso = st.session_state['curso_selecionado']

    if st.button("← Voltar"):
        st.session_state['cursos_view'] = 'lista'
        st.rerun()

    st.title(curso.get('titulo', 'Curso'))

    tab1, tab2 = st.tabs(["📘 Visão Geral", "👥 Alunos & Rendimento"])

    # ---------- VISÃO GERAL ----------
    with tab1:
        if st.button("📂 Gerenciar Conteúdo", type="primary"):
            st.session_state['cursos_view'] = 'conteudo'
            st.rerun()

        st.markdown("---")
        st.markdown(f"**Descrição:** {curso.get('descricao', '-')}")
        st.markdown(f"**Modalidade:** {curso.get('modalidade')}")
        st.markdown(f"**Preço:** R$ {curso.get('preco', 0):.2f}")

    # ---------- ALUNOS ----------
    with tab2:
        alunos = ce.listar_alunos_inscritos(curso['id'])

        if alunos:
            st.dataframe(pd.DataFrame(alunos), use_container_width=True)
        else:
            st.info("Nenhum aluno inscrito.")
