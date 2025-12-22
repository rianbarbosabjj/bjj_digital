import streamlit as st
import time
import utils as ce
# Importa o player (aulas_aluno.py)
import views.aulas_aluno as aulas_view

def render_painel_aluno(usuario):
    # ====================================================
    # 1. ROTEAMENTO PARA O PLAYER
    # ====================================================
    if st.session_state.get("view_aluno") == "aulas" and st.session_state.get("curso_aluno_selecionado"):
        if st.button("⬅️ Voltar para meus cursos"):
            st.session_state["view_aluno"] = "lista"
            st.session_state["curso_aluno_selecionado"] = None
            st.rerun()
            
        st.divider()
        aulas_view.pagina_aulas_aluno(st.session_state["curso_aluno_selecionado"], usuario)
        return

    # ====================================================
    # 2. TELA DAS ABAS (CÓDIGO NOVO)
    # ====================================================
    st.markdown(f"## 🎓 Painel do Aluno: {usuario.get('nome')}")
    
    # CRIAÇÃO DAS ABAS
    tab1, tab2 = st.tabs(["📚 Meus Cursos", "🔍 Novos Cursos"])

    # --- ABA 1: MEUS CURSOS ---
    with tab1:
        cursos = ce.listar_cursos_inscritos(usuario["id"])
        if not cursos:
            st.info("Você não está inscrito em nenhum curso.")
        else:
            for c in cursos:
                with st.container(border=True):
                    col_txt, col_btn = st.columns([4, 1])
                    with col_txt:
                        st.markdown(f"### {c.get('titulo')}")
                        st.progress(c.get('progresso', 0) / 100)
                        st.caption(f"{c.get('progresso', 0)}% Concluído")
                    with col_btn:
                        st.write("")
                        if st.button("Acessar", key=f"btn_old_{c['id']}", use_container_width=True):
                            st.session_state["curso_aluno_selecionado"] = c
                            st.session_state["view_aluno"] = "aulas"
                            st.rerun()

    # --- ABA 2: NOVOS CURSOS ---
    with tab2:
        novos = ce.listar_cursos_disponiveis_para_aluno(usuario)
        if not novos:
            st.warning("Sem cursos novos para você.")
        else:
            for c in novos:
                with st.container(border=True):
                    col_txt, col_btn = st.columns([3, 1])
                    with col_txt:
                        st.markdown(f"**{c.get('titulo')}**")
                        st.caption(c.get('descricao'))
                    with col_btn:
                        st.write("")
                        if st.button("Inscrever", key=f"btn_new_{c['id']}", type="primary", use_container_width=True):
                            ce.inscrever_usuario_em_curso(usuario["id"], c["id"])
                            st.toast("Inscrito com sucesso!")
                            time.sleep(1)
                            st.rerun()
