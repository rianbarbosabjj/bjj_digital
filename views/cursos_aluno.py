import streamlit as st
import utils as ce
# Certifique-se de que o import abaixo aponta para o arquivo correto de visualização de aulas
import views.aulas_aluno as aulas_view 

def pagina_cursos_aluno(usuario):
    # ====================================================
    # 1. LÓGICA DE NAVEGAÇÃO (DENTRO DO CURSO VS LISTA)
    # ====================================================
    
    # Se o estado estiver definido para ver aulas, mostra o player de aulas
    if st.session_state.get("view_aluno") == "aulas" and st.session_state.get("curso_aluno_selecionado"):
        
        # Botão de Voltar
        if st.button("⬅ Voltar para lista de cursos"):
            st.session_state["view_aluno"] = "lista"
            st.session_state["curso_aluno_selecionado"] = None
            st.rerun()
            
        # Carrega a visualização das aulas (seu primeiro arquivo enviado)
        aulas_view.pagina_aulas_aluno(
            st.session_state["curso_aluno_selecionado"],
            usuario
        )
        return  # Interrompe aqui para não mostrar as listas abaixo

    # ====================================================
    # 2. VISÃO GERAL (LISTAS DE CURSOS)
    # ====================================================
    st.subheader(f"Olá, {usuario.get('nome', 'Aluno')}!")

    # Criação de Abas para organizar a visão
    tab_meus, tab_disponiveis = st.tabs(["📚 Meus Cursos", "🔍 Cursos Disponíveis"])

    # --- ABA 1: MEUS CURSOS (Matriculados) ---
    with tab_meus:
        cursos_inscritos = ce.listar_cursos_do_aluno(usuario["id"]) # No utils antigo pode ser listar_cursos_inscritos

        if not cursos_inscritos:
            st.info("Você ainda não está matriculado em nenhum curso.")
        else:
            for c in cursos_inscritos:
                with st.container(border=True):
                    col_txt, col_btn = st.columns([4, 1])
                    
                    with col_txt:
                        st.markdown(f"### {c.get('titulo')}")
                        st.caption(c.get("descricao", "Sem descrição"))
                        # Mostra progresso se disponível
                        if 'progresso' in c:
                            st.progress(c['progresso'] / 100)
                            st.caption(f"Progresso: {c['progresso']}%")

                    with col_btn:
                        st.write("") # Espaçamento
                        if st.button("Acessar", key=f"btn_acc_{c['id']}", use_container_width=True):
                            st.session_state["curso_aluno_selecionado"] = c
                            st.session_state["view_aluno"] = "aulas"
                            st.rerun()

    # --- ABA 2: CURSOS DISPONÍVEIS (Para Inscrição) ---
    with tab_disponiveis:
        # Busca cursos disponíveis baseados na equipe/permissão do usuário
        cursos_disponiveis = ce.listar_cursos_disponiveis_para_aluno(usuario)

        if not cursos_disponiveis:
            st.info("No momento não há novos cursos disponíveis para você.")
        else:
            for curso in cursos_disponiveis:
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1])
                    
                    with c1:
                        st.markdown(f"**{curso.get('titulo')}**")
                        st.write(curso.get("descricao", ""))
                        
                        # Exibe infos extras
                        info = []
                        if curso.get('duracao_estimada'): info.append(f"⏱ {curso['duracao_estimada']}")
                        if curso.get('nivel'): info.append(f"📊 {curso['nivel']}")
                        st.caption(" • ".join(info))

                    with c2:
                        st.write("")
                        # Verifica se é gratuito ou pago (lógica simples)
                        texto_botao = "Inscrever-se"
                        if curso.get("pago"):
                            texto_botao = f"Comprar (R$ {curso.get('preco', 0)})"
                        
                        if st.button(texto_botao, key=f"inscrever_{curso['id']}", type="primary", use_container_width=True):
                            with st.spinner("Realizando inscrição..."):
                                sucesso = ce.inscrever_usuario_em_curso(usuario["id"], curso["id"])
                                if sucesso:
                                    st.success(f"Inscrição em '{curso['titulo']}' realizada!")
                                    st.rerun()
                                else:
                                    st.error("Erro ao realizar inscrição.")
