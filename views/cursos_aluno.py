import streamlit as st
import time
import utils as ce
import views.aulas_aluno as aulas_view

def pagina_cursos_aluno(usuario):
    # ====================================================
    # 🕵️ MARCADOR DE DEPURAÇÃO (SE ISSO NÃO APARECER, O ARQUIVO NÃO ATUALIZOU)
    # ====================================================
    st.error(f"⚠️ VERSÃO ATUALIZADA CARREGADA! Olá {usuario.get('nome')}") 
    # ====================================================

    # 1. VERIFICAÇÃO DE ROTEAMENTO
    if st.session_state.get("view_aluno") == "aulas" and st.session_state.get("curso_aluno_selecionado"):
        if st.button("⬅️ Voltar para meus cursos"):
            st.session_state["view_aluno"] = "lista"
            st.session_state["curso_aluno_selecionado"] = None
            st.rerun()
            
        st.divider()
        aulas_view.pagina_aulas_aluno(st.session_state["curso_aluno_selecionado"], usuario)
        return

    # 2. TELA PRINCIPAL COM ABAS
    st.subheader(f"Painel do Aluno") # <--- Título diferente da sua imagem
    
    # AS ABAS ESTÃO AQUI 👇
    tab_meus, tab_novos = st.tabs(["📚 Meus Cursos", "🔍 Cursos Disponíveis"])

    # --- ABA 1: MEUS CURSOS ---
    with tab_meus:
        cursos_inscritos = ce.listar_cursos_inscritos(usuario["id"])

        if not cursos_inscritos:
            st.info("Você ainda não iniciou nenhum curso.")
        else:
            for curso in cursos_inscritos:
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.markdown(f"### {curso.get('titulo')}")
                        st.caption(f"Status: {curso.get('status', 'Ativo')}")
                        progresso = curso.get('progresso', 0)
                        st.progress(progresso / 100)
                        st.caption(f"{progresso}% Concluído")
                    with c2:
                        st.write("")
                        if st.button("▶ Acessar", key=f"btn_go_{curso['id']}", use_container_width=True):
                            st.session_state["curso_aluno_selecionado"] = curso
                            st.session_state["view_aluno"] = "aulas"
                            st.rerun()

    # --- ABA 2: NOVOS CURSOS ---
    with tab_novos:
        cursos_disponiveis = ce.listar_cursos_disponiveis_para_aluno(usuario)

        if not cursos_disponiveis:
            st.warning("Não há cursos novos disponíveis para sua equipe no momento.")
        else:
            for curso in cursos_disponiveis:
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**{curso.get('titulo')}**")
                        st.markdown(f"<small>{curso.get('descricao', '')}</small>", unsafe_allow_html=True)
                        st.caption(f"⏱ {curso.get('duracao_estimada', '?')} min")
                    with c2:
                        st.write("")
                        if st.button("Inscrever-se", key=f"new_{curso['id']}", type="primary", use_container_width=True):
                            with st.spinner("Inscrevendo..."):
                                ce.inscrever_usuario_em_curso(usuario["id"], curso["id"])
                                time.sleep(1)
                                st.rerun()
