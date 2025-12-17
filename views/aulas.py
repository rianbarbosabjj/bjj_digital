import streamlit as st
import time
import pandas as pd
from datetime import datetime
import utils as ce
import views.aulas as aulas_view # Importa a view de aulas para navegação

# Configuração de Cores
try:
    from config import COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER
except ImportError:
    COR_FUNDO, COR_TEXTO, COR_DESTAQUE, COR_BOTAO, COR_HOVER = "#0e2d26", "#FFFFFF", "#FFD770", "#078B6C", "#FFD770"

def pagina_cursos(usuario):
    # Inicializa o estado de navegação se não existir
    if 'cursos_view' not in st.session_state:
        st.session_state['cursos_view'] = 'lista'
    if 'curso_selecionado' not in st.session_state:
        st.session_state['curso_selecionado'] = None

    # --- ROTEAMENTO DE TELAS ---
    
    # 1. Tela de Gerenciamento de Conteúdo (Aulas)
    if st.session_state['cursos_view'] == 'conteudo':
        if st.session_state['curso_selecionado']:
            aulas_view.gerenciar_conteudo_curso(st.session_state['curso_selecionado'], usuario)
        else:
            st.session_state['cursos_view'] = 'lista'
            st.rerun()

    # 2. Tela de Detalhes do Curso ("Botão Ver") -> ONDE VAMOS MEXER
    elif st.session_state['cursos_view'] == 'detalhe':
        exibir_detalhes_curso(usuario)

    # 3. Tela de Listagem (Padrão)
    else:
        listar_cursos(usuario)

def listar_cursos(usuario):
    st.subheader("Meus Cursos")
    
    # Botão para criar novo curso (se for professor/admin)
    if usuario.get('tipo') in ['admin', 'professor']:
        with st.expander("Novo Curso"):
            with st.form("form_curso"):
                titulo = st.text_input("Título")
                desc = st.text_area("Descrição")
                preco = st.number_input("Preço (R$)", 0.0, step=10.0)
                if st.form_submit_button("Criar"):
                    # Exemplo simplificado de criação
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
                    st.rerun()

def exibir_detalhes_curso(usuario):
    curso = st.session_state['curso_selecionado']
    
    # Botão Voltar
    if st.button("← Voltar à Lista"):
        st.session_state['cursos_view'] = 'lista'
        st.rerun()

    st.title(curso.get('titulo', 'Curso Sem Nome'))
    
    # --- CRIAÇÃO DAS ABAS (NOVA ESTRUTURA) ---
    tab_sobre, tab_alunos = st.tabs(["📝 Sobre o Curso", "👥 Alunos & Rendimento"])
    
    # === ABA 1: VISÃO GERAL (O que já existia) ===
    with tab_sobre:
        col_actions, col_info = st.columns([1, 2])
        
        with col_actions:
            st.markdown("#### Ações Rápidas")
            # Botão para ir ao Gerenciador de Aulas
            if st.button("➕ Gerenciar Aulas/Conteúdo", type="primary", use_container_width=True):
                st.session_state['cursos_view'] = 'conteudo'
                st.rerun()
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✏️ Editar Informações", use_container_width=True):
                st.toast("Funcionalidade de edição aqui")
            
            # Botão de Excluir Curso
            if st.button("🗑️ Excluir Curso", type="secondary", use_container_width=True):
                 if ce.excluir_curso(curso['id']):
                     st.session_state['cursos_view'] = 'lista'
                     st.rerun()

        with col_info:
            st.markdown(f"**Descrição:**\n{curso.get('descricao', 'Sem descrição')}")
            st.markdown("---")
            c1, c2 = st.columns(2)
            c1.markdown(f"**Professor:** {curso.get('professor_nome', '-')}")
            c2.markdown(f"**Equipe:** {curso.get('professor_equipe', '-')}")
            c1.markdown(f"**Preço:** R$ {curso.get('preco', 0):.2f}")
            c2.markdown(f"**Nível:** {curso.get('nivel', '-')}")

    # === ABA 2: ALUNOS & RENDIMENTO (MOVIDA DO OUTRO ARQUIVO) ===
    with tab_alunos:
        st.markdown("### 📊 Performance do Curso")
        
        # Busca dados
        with st.spinner("Carregando dados..."):
            alunos = ce.listar_alunos_inscritos(curso['id'])
        
        total_alunos = len(alunos)
        is_pago = curso.get('pago', False) or (float(curso.get('preco', 0)) > 0)
        preco_curso = float(curso.get('preco', 0))
        
        # Métricas
        col_metrics = st.columns(3)
        col_metrics[0].metric("Total de Alunos", total_alunos, border=True)
        
        if is_pago:
            rendimento_real = total_alunos * preco_curso
            col_metrics[1].metric("Valor do Curso", f"R$ {preco_curso:.2f}", border=True)
            # MUDANÇA SOLICITADA: Texto alterado para "Rendimento Alcançado"
            col_metrics[2].metric("Rendimento Alcançado", f"R$ {rendimento_real:,.2f}", border=True)
        else:
            col_metrics[1].metric("Tipo", "Gratuito", border=True)
            col_metrics[2].metric("Rendimento", "R$ 0,00", border=True)

        st.markdown("---")
        st.markdown("### 📋 Lista de Chamada (Inscritos)")
        
        if alunos:
            df_alunos = pd.DataFrame(alunos)
            st.dataframe(
                df_alunos, 
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Nome": st.column_config.TextColumn("Aluno", width="medium"),
                    "Email": st.column_config.TextColumn("Contato", width="medium"),
                    "Progresso": st.column_config.ProgressColumn("Progresso", format="%s", min_value=0, max_value=100),
                    "Status": st.column_config.TextColumn("Status", width="small")
                }
            )
        else:
            st.info("Ainda não há alunos inscritos neste curso.")
