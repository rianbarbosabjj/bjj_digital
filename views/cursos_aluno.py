import streamlit as st
import time
import utils as ce
# Importa o player de aula que você já tem
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
    # Se o aluno clicou para entrar em um curso, mostramos o player de aulas
    if st.session_state.get("view_aluno") == "aulas" and st.session_state.get("curso_aluno_selecionado"):
        
        # Botão de Voltar para a lista
        if st.button("⬅️ Voltar para meus cursos"):
            st.session_state["view_aluno"] = "lista"
            st.session_state["curso_aluno_selecionado"] = None
            st.rerun()
            
        st.divider()
        
        # Renderiza a página de aulas (player)
        aulas_view.pagina_aulas_aluno(
            st.session_state["curso_aluno_selecionado"],
            usuario
        )
        return  # <--- PARA A EXECUÇÃO AQUI (Não mostra as listas abaixo)

    # ====================================================
    # 2. TELA PRINCIPAL (LISTAS DE CURSOS)
    # ====================================================
    st.subheader(f"Painel do Aluno: {usuario.get('nome', 'Visitante')}")
    st.markdown("---")

    # Criação das Abas
    tab_meus, tab_novos = st.tabs(["📚 Meus Cursos", "🔍 Cursos Disponíveis"])

    # ----------------------------------------------------
    # ABA 1: MEUS CURSOS (Matriculados)
    # ----------------------------------------------------
    with tab_meus:
        # Busca cursos em que o aluno já está inscrito (com progresso)
        # Nota: No seu utils.py a função chama 'listar_cursos_inscritos'
        cursos_inscritos = ce.listar_cursos_inscritos(usuario["id"])

        if not cursos_inscritos:
            st.info("Você ainda não iniciou nenhum curso.")
        else:
            # Grid de cursos
            for curso in cursos_inscritos:
                with st.container(border=True):
                    col_info, col_action = st.columns([4, 1])
                    
                    with col_info:
                        st.markdown(f"### {curso.get('titulo')}")
                        st.caption(curso.get("descricao", "Sem descrição"))
                        
                        # Barra de Progresso
                        progresso = curso.get('progresso', 0)
                        st.progress(progresso / 100)
                        st.caption(f"Progresso: {progresso}% concluído")

                    with col_action:
                        st.write("") # Espaço para alinhar verticalmente
                        st.write("")
                        if st.button("▶ Acessar", key=f"btn_go_{curso['id']}", use_container_width=True):
                            # Define o estado para mudar a tela
                            st.session_state["curso_aluno_selecionado"] = curso
                            st.session_state["view_aluno"] = "aulas"
                            st.rerun()

    # ----------------------------------------------------
    # ABA 2: CURSOS DISPONÍVEIS (Para Inscrição)
    # ----------------------------------------------------
    with tab_novos:
        # Busca novos cursos que o aluno PODE fazer (regra de equipe/nível)
        cursos_disponiveis = ce.listar_cursos_disponiveis_para_aluno(usuario)

        if not cursos_disponiveis:
            st.info("Não há novos cursos disponíveis para sua equipe/nível no momento.")
        else:
            for curso in cursos_disponiveis:
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    
                    with c1:
                        st.markdown(f"**{curso.get('titulo')}**")
                        st.markdown(f"<small>{curso.get('descricao', '')}</small>", unsafe_allow_html=True)
                        
                        # Badges de informação
                        badges = []
                        if curso.get('duracao_estimada'): badges.append(f"⏱ {curso['duracao_estimada']}")
                        if curso.get('nivel'): badges.append(f"📊 {curso['nivel']}")
                        if curso.get('certificado_automatico'): badges.append("🏅 Certificado")
                        
                        if badges:
                            st.caption("  |  ".join(badges))

                    with c2:
                        st.write("")
                        # Verifica preço
                        preco = float(curso.get("preco", 0))
                        pago = curso.get("pago", False)
                        
                        texto_btn = "Inscrever-se Grátis"
                        if pago and preco > 0:
                            texto_btn = f"Comprar (R$ {preco:.2f})"
                        
                        if st.button(texto_btn, key=f"insc_{curso['id']}", type="primary", use_container_width=True):
                            with st.spinner("Processando inscrição..."):
                                # Chama a função do seu utils.py
                                sucesso = ce.inscrever_usuario_em_curso(usuario["id"], curso["id"])
                                
                                if sucesso:
                                    st.success(f"Bem-vindo(a) ao curso {curso.get('titulo')}!")
                                    time.sleep(1.5)
                                    st.rerun() # Recarrega para o curso aparecer na aba "Meus Cursos"
                                else:
                                    st.error("Erro ao realizar inscrição. Tente novamente.")
