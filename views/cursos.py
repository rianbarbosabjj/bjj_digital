import streamlit as st
import time
import pandas as pd
from datetime import datetime
import utils as ce
import views.aulas as aulas_view 

try:
    from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
except ImportError:
    COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER = "#0e2d26", "#FFFFFF", "#FFD770", "#078B6C", "#FFD770"

def pagina_cursos(usuario):
    if 'cursos_view' not in st.session_state:
        st.session_state['cursos_view'] = 'lista'
    if 'curso_selecionado' not in st.session_state:
        st.session_state['curso_selecionado'] = None
    # Novo estado para controlar a edição
    if 'editando_curso' not in st.session_state:
        st.session_state['editando_curso'] = False

    if st.session_state['cursos_view'] == 'conteudo':
        if st.session_state['curso_selecionado']:
            aulas_view.gerenciar_conteudo_curso(st.session_state['curso_selecionado'], usuario)
        else:
            st.session_state['cursos_view'] = 'lista'
            st.rerun()

    elif st.session_state['cursos_view'] == 'detalhe':
        exibir_detalhes_curso(usuario)

    else:
        listar_cursos(usuario)

def listar_cursos(usuario):
    st.subheader("Meus Cursos")
    
    if usuario.get('tipo') in ['admin', 'professor']:
        with st.expander("Novo Curso"):
            with st.form("form_curso"):
                titulo = st.text_input("Título")
                desc = st.text_area("Descrição")
                preco = st.number_input("Preço (R$)", 0.0, step=10.0)
                if st.form_submit_button("Criar"):
                    ce.criar_curso(usuario['id'], usuario['nome'], usuario.get('equipe',''), titulo, desc, 'presencial', 'todos', '', True, preco, False, False, 10, 'iniciante')
                    st.success("Curso criado!")
                    time.sleep(1)
                    st.rerun()
    
    st.markdown("---")
    cursos = ce.listar_cursos_do_professor(usuario['id'])
    
    if not cursos:
        st.info("Nenhum curso encontrado.")
        return

    for c in cursos:
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"### {c.get('titulo')}")
                st.caption(c.get('descricao', '')[:100] + "...")
            with col2:
                if st.button("Ver Detalhes", key=f"btn_ver_{c['id']}", use_container_width=True):
                    st.session_state['curso_selecionado'] = c
                    st.session_state['cursos_view'] = 'detalhe'
                    st.session_state['editando_curso'] = False # Reseta edição ao abrir
                    st.rerun()

def exibir_detalhes_curso(usuario):
    curso = st.session_state['curso_selecionado']
    
    # Header de Navegação
    if st.button("← Voltar à Lista"):
        st.session_state['cursos_view'] = 'lista'
        st.rerun()

    st.title(curso.get('titulo', 'Curso Sem Nome'))
    
    # ABAS
    tab_sobre, tab_alunos = st.tabs(["📝 Visão Geral", "👥 Alunos & Rendimento"])
    
    # --- ABA 1: GERAL ---
    with tab_sobre:
        col_actions, col_info = st.columns([1, 2])
        
        with col_actions:
            st.markdown("#### Ações")
            
            # 1. Gerenciar Aulas
            if st.button("➕ Gerenciar Conteúdo/Aulas", type="primary", use_container_width=True):
                st.session_state['cursos_view'] = 'conteudo'
                st.rerun()
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # 2. Botão de Editar (Toggle)
            if st.button("✏️ Editar Informações", use_container_width=True):
                # Inverte o estado da edição (abre/fecha formulário)
                st.session_state['editando_curso'] = not st.session_state['editando_curso']
                st.rerun()
            
            # 3. Excluir
            if st.button("🗑️ Excluir Curso", type="secondary", use_container_width=True):
                 if ce.excluir_curso(curso['id']):
                     st.session_state['cursos_view'] = 'lista'
                     st.rerun()

        with col_info:
            # --- SE ESTIVER EDITANDO, MOSTRA O FORMULÁRIO ---
            if st.session_state['editando_curso']:
                with st.container(border=True):
                    st.markdown("##### ✏️ Editando Curso")
                    with st.form("form_editar_curso"):
                        novo_titulo = st.text_input("Título", value=curso.get('titulo', ''))
                        nova_desc = st.text_area("Descrição", value=curso.get('descricao', ''))
                        novo_preco = st.number_input("Preço (R$)", value=float(curso.get('preco', 0.0)), step=10.0)
                        
                        if st.form_submit_button("💾 Salvar Alterações"):
                            dados_atualizados = {
                                "titulo": novo_titulo,
                                "descricao": nova_desc,
                                "preco": novo_preco,
                                "pago": novo_preco > 0
                            }
                            # Chama a função de update no utils
                            sucesso = ce.editar_curso(curso['id'], dados_atualizados)
                            if sucesso:
                                st.success("Curso atualizado!")
                                # Atualiza o objeto na sessão local para refletir na hora
                                curso.update(dados_atualizados)
                                st.session_state['curso_selecionado'] = curso
                                st.session_state['editando_curso'] = False
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Erro ao atualizar.")
            
            # --- SE NÃO ESTIVER EDITANDO, MOSTRA O TEXTO ---
            else:
                st.markdown(f"**Descrição:**\n{curso.get('descricao', 'Sem descrição')}")
                st.markdown("---")
                c1, c2 = st.columns(2)
                c1.markdown(f"**Professor:** {curso.get('professor_nome', '-')}")
                c2.markdown(f"**Equipe:** {curso.get('professor_equipe', '-')}")
                c1.markdown(f"**Preço:** R$ {curso.get('preco', 0):.2f}")
                c2.markdown(f"**Nível:** {curso.get('nivel', '-')}")

    # --- ABA 2: FINANCEIRO ---
    with tab_alunos:
        st.markdown("### 📊 Indicadores")
        
        with st.spinner("Carregando dados..."):
            alunos = ce.listar_alunos_inscritos(curso['id'])
        
        total_alunos = len(alunos)
        preco_curso = float(curso.get('preco', 0))
        is_pago = curso.get('pago', False) or (preco_curso > 0)
        
        col_metrics = st.columns(3)
        col_metrics[0].metric("Total de Alunos", total_alunos, border=True)
        
        if is_pago:
            rendimento_real = total_alunos * preco_curso
            col_metrics[1].metric("Valor Unitário", f"R$ {preco_curso:.2f}", border=True)
            col_metrics[2].metric("Rendimento Alcançado", f"R$ {rendimento_real:,.2f}", border=True)
        else:
            col_metrics[1].metric("Tipo", "Gratuito", border=True)
            col_metrics[2].metric("Rendimento", "R$ 0,00", border=True)

        st.markdown("---")
        st.markdown("### 📋 Lista de Chamada")
        
        if alunos:
            df_alunos = pd.DataFrame(alunos)
            st.dataframe(
                df_alunos, 
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Ainda não há alunos inscritos.")
