import streamlit as st
import time
import pandas as pd
import re
from datetime import datetime
import utils as ce

# IMPORT SEGURO DO GERENCIADOR DE AULAS
from views import aulas_professor as aulas_view

try:
    from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
except ImportError:
    COR_FUNDO = "#0e2d26"
    COR_TEXTO = "#FFFFFF"
    COR_DESTAQUE = "#FFD770"
    COR_BOTAO = "#078B6C"
    COR_HOVER = "#FFD770"


# ======================================================
# PÁGINA PRINCIPAL – PROFESSOR
# ======================================================
def pagina_cursos_professor(usuario):
    st.title("📚 Gestão de Cursos (Professor)")

    # -----------------------------
    # CONTROLE DE ESTADO (NÃO RESETAR!)
    # -----------------------------
    st.session_state.setdefault('cursos_view', 'lista')
    st.session_state.setdefault('curso_selecionado', None)
    st.session_state.setdefault('editando_curso', False)

    view = st.session_state.get('cursos_view')

    # -----------------------------
    # ROTEAMENTO
    # -----------------------------
    if view == 'conteudo':
        curso = st.session_state.get('curso_selecionado')
        if curso:
            aulas_view.gerenciar_conteudo_curso(curso, usuario)
        else:
            st.session_state['cursos_view'] = 'lista'
            st.rerun()

    elif view == 'detalhe':
        exibir_detalhes_curso(usuario)

    else:
        listar_cursos(usuario)


# ======================================================
# LISTAGEM DE CURSOS
# ======================================================
def listar_cursos(usuario):
    st.subheader("Meus Cursos")

    # -----------------------------
    # CRIAÇÃO DE NOVO CURSO
    # -----------------------------
    if usuario.get('tipo') in ['admin', 'professor', 'mestre']:
        with st.expander("➕ Novo Curso"):
            with st.form("form_curso"):
                titulo = st.text_input("Título")
                desc = st.text_area("Descrição")

                c1, c2 = st.columns(2)
                modalidade = c1.selectbox("Modalidade", ["EAD", "Presencial", "Híbrido"])
                publico_sel = c2.selectbox("Público", ["Aberto a Todos", "Restrito à Minha Equipe"])

                st.markdown("###### Professores Auxiliares (opcional)")
                cpfs_input = st.text_area("CPFs (um por linha)", height=80)

                preco = st.number_input("Preço (R$)", 0.0, step=10.0)

                if st.form_submit_button("Criar Curso"):
                    editores_ids = []

                    if cpfs_input:
                        for cpf in re.split(r'[,\n]', cpfs_input):
                            cpf = cpf.strip()
                            if cpf:
                                u = ce.buscar_usuario_por_cpf(cpf)
                                if u and u['id'] != usuario['id']:
                                    editores_ids.append(u['id'])

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
                        editores_ids=editores_ids
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
        alunos = ce.listar_alunos_inscritos(c['id'])
        qtd_alunos = len(alunos)
        preco = float(c.get('preco', 0))
        rendimento = qtd_alunos * preco

        with st.container(border=True):
            col_txt, col_info, col_btn = st.columns([3, 2, 1])

            with col_txt:
                st.markdown(f"### {c.get('titulo')}")
                st.caption(c.get('descricao', '')[:100])

            with col_info:
                st.metric("Alunos", qtd_alunos)
                if preco > 0:
                    st.metric("Rendimento", f"R$ {rendimento:,.2f}")
                else:
                    st.metric("Rendimento", "Grátis")

            with col_btn:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Gerenciar", key=f"ger_{c['id']}", use_container_width=True):
                    st.session_state['curso_selecionado'] = c
                    st.session_state['cursos_view'] = 'detalhe'
                    st.session_state['editando_curso'] = False
                    st.rerun()


# ======================================================
# DETALHES DO CURSO
# ======================================================
def exibir_detalhes_curso(usuario):
    curso = st.session_state.get('curso_selecionado')

    if not curso:
        st.session_state['cursos_view'] = 'lista'
        st.rerun()

    if st.button("← Voltar"):
        st.session_state['cursos_view'] = 'lista'
        st.rerun()

    st.title(curso.get('titulo'))

    tab1, tab2 = st.tabs(["📝 Visão Geral", "👥 Alunos"])

    # -----------------------------
    # ABA VISÃO GERAL
    # -----------------------------
    with tab1:
        if st.button("📂 Gerenciar Conteúdo", type="primary", use_container_width=True):
            st.session_state['cursos_view'] = 'conteudo'
            st.rerun()

        st.markdown("---")
        st.markdown(f"**Descrição:** {curso.get('descricao', '-')}")
        st.markdown(f"**Modalidade:** {curso.get('modalidade')}")
        st.markdown(f"**Preço:** R$ {curso.get('preco', 0):.2f}")

    # -----------------------------
    # ABA ALUNOS
    # -----------------------------
    with tab2:
        alunos = ce.listar_alunos_inscritos(curso['id'])
        if alunos:
            df = pd.DataFrame(alunos)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Nenhum aluno matriculado ainda.")
