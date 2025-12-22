import streamlit as st
import time
import utils as ce
# Importa o arquivo de PLAYER (aulas) que você me mostrou agora
import views.aulas_aluno as aulas_view

def pagina_cursos_aluno(usuario):
    """
    Controla a visualização principal do aluno:
    1. Lista de Cursos Matriculados (com progresso)
    2. Lista de Cursos Disponíveis (para inscrição)
    3. Player da Aula (quando um curso é selecionado)
    """

    # ====================================================
    # 1. VERIFICAÇÃO DE ROTEAMENTO (NAVEGAÇÃO INTERNA)
    # ====================================================
    # Se o aluno clicou em "Acessar", chamamos o player de aula
    if st.session_state.get("view_aluno") == "aulas" and st.session_state.get("curso_aluno_selecionado"):
        
        # Botão de Voltar para a lista
        if st.button("⬅️ Voltar para meus cursos"):
            st.session_state["view_aluno"] = "lista"
            st.session_state["curso_aluno_selecionado"] = None
            st.rerun()
            
        st.divider()
        
        # AQUI CHAMAMOS O CÓDIGO QUE VOCÊ ME MANDOU (PLAYER)
        aulas_view.pagina_aulas_aluno(
            st.session_state["curso_aluno_selecionado"],
            usuario
        )
        return  # <--- PARA A EXECUÇÃO AQUI

    # ====================================================
    # 2. TELA PRINCIPAL (ONDE FICAM AS ABAS)
    # ====================================================
    st.subheader(f"Painel do Aluno: {usuario.get('nome')}")
    
    # ----------------------------------------------------
    # MARCADOR VISUAL (Para você saber que atualizou)
    # ----------------------------------------------------
    st.warning("⚠️ SE VOCÊ ESTÁ VENDO ISSO, O ARQUIVO NOVO CARREGOU!") 
    
    # Criação das Abas
    tab_meus, tab_novos = st.tabs(["📚 Meus Cursos", "🔍 Cursos Disponíveis"])

    # --- ABA 1: MEUS CURSOS ---
    with tab_meus:
        cursos_inscritos = ce.listar_cursos_inscritos(usuario["id"])

        if not cursos_inscritos:
            st.info("Você ainda não iniciou nenhum curso.")
        else:
            for curso in cursos_inscritos:
                with st.container(border=True):
                    col_info, col_action = st.columns([4, 1])
                    
                    with col_info:
                        st.markdown(f"### {curso.get('titulo')}")
                        progresso = curso.get('progresso', 0)
                        st.progress(progresso / 100)
                        st.caption(f"{progresso}% concluído")

                    with col_action:
                        st.write("") 
                        if st.button("▶ Acessar", key=f"btn_go_{curso['id']}", use_container_width=True):
                            st.session_state["curso_aluno_selecionado"] = curso
                            st.session_state["view_aluno"] = "aulas"
                            st.rerun()

    # --- ABA 2: CURSOS DISPONÍVEIS ---
    with tab_novos:
        cursos_disponiveis = ce.listar_cursos_disponiveis_para_aluno(usuario)

        if not cursos_disponiveis:
            st.info("Não há novos cursos disponíveis no momento.")
        else:
            for curso in cursos_disponiveis:
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**{curso.get('titulo')}**")
                        st.caption(curso.get('descricao', ''))
                    with c2:
                        st.write("")
                        if st.button("Inscrever-se", key=f"insc_{curso['id']}", type="primary", use_container_width=True):
                            with st.spinner("Inscrevendo..."):
                                ce.inscrever_usuario_em_curso(usuario["id"], curso["id"])
                                time.sleep(1)
                                st.rerun()
