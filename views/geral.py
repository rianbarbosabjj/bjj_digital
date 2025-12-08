import streamlit as st

def card(titulo, icone, desc, texto_botao, key_btn, acao=None):
    with st.container(border=True):
        st.markdown(f"<h3 style='text-align:center;'>{icone} {titulo}</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align:center; min-height:40px;'>{desc}</p>", unsafe_allow_html=True)
        if st.button(texto_botao, key=key_btn, use_container_width=True):
            if acao: acao()

def tela_inicio():
    if not st.session_state.get('usuario'): return
    
    u = st.session_state.usuario
    # Tenta pegar 'tipo_usuario' ou 'tipo' para garantir compatibilidade
    tipo = str(u.get("tipo_usuario", u.get("tipo", "aluno"))).lower()
    nome = u.get("nome", "Visitante")

    st.markdown(f"<h2 style='text-align:center; color:#FFD700;'>PAINEL BJJ DIGITAL</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center;'>Bem-vindo(a), {nome}!</p>", unsafe_allow_html=True)
    st.markdown("---")

    # Funções de navegação
    def ir_rola(): st.session_state.menu_selection = "Modo Rola"; st.rerun()
    def ir_exame(): st.session_state.menu_selection = "Exame de Faixa"; st.rerun()
    def ir_ranking(): st.session_state.menu_selection = "Ranking"; st.rerun()
    
    # Funções Admin/Prof
    def ir_questoes(): st.session_state.menu_selection = "Gestão de Questões"; st.rerun()
    def ir_equipes(): st.session_state.menu_selection = "Gestão de Equipe"; st.rerun() # CORRIGIDO AQUI
    def ir_montar_exame(): st.session_state.menu_selection = "Gestão de Exame"; st.rerun()

    # --- CARDS ALUNO (TODOS VEEM) ---
    c1, c2, c3 = st.columns(3)
    with c1: card("MODO ROLA", "🤼", "Treino livre.", "Acessar", "btn_rola", ir_rola)
    with c2: card("EXAME DE FAIXA", "🥋", "Avaliação teórica.", "Acessar", "btn_exame", ir_exame)
    with c3: card("RANKING", "🏆", "Posição no ranking.", "Acessar", "btn_rank", ir_ranking)

    # --- CARDS GESTÃO (SÓ PROF/ADMIN) ---
    if tipo in ["admin", "professor"]:
        st.markdown("<h3 style='text-align:center; margin-top:30px; color:#FFD700;'>GESTÃO</h3>", unsafe_allow_html=True)
        g1, g2, g3 = st.columns(3)
        with g1: card("QUESTÕES", "🧠", "Editar banco.", "Gerenciar", "btn_quest", ir_questoes)
        with g2: card("EQUIPES", "🏛️", "Gerenciar equipes.", "Gerenciar", "btn_team", ir_equipes) # CHAMA A FUNÇÃO CERTA
        with g3: card("EXAMES", "📜", "Montar provas.", "Gerenciar", "btn_montar", ir_montar_exame)

def tela_meu_perfil(usuario):
    st.title("👤 Meu Perfil")
    with st.container(border=True):
        st.write(f"**Nome:** {usuario.get('nome')}")
        st.write(f"**Email:** {usuario.get('email')}")
        st.write(f"**CPF:** {usuario.get('cpf')}")
        st.write(f"**Faixa:** {usuario.get('faixa_atual')}")
        st.write(f"**Equipe:** {usuario.get('equipe_nome', 'Não vinculado')}") # Se tiver esse dado
