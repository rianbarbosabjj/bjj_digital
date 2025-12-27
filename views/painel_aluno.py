# views/painel_aluno.py

import streamlit as st
import time
from datetime import datetime
import utils as ce

# ==================================================
# 🎨 ESTILOS CSS SIMPLES
# ==================================================
def aplicar_estilos():
    st.markdown("""
    <style>
    /* Melhorar visualização dos cards */
    div[data-testid="stHorizontalBlock"] > div {
        padding: 5px;
    }
    
    /* Cards com gradiente */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(135deg, rgba(14, 45, 38, 0.9), rgba(5, 104, 83, 0.8));
        border: 1px solid rgba(255, 215, 112, 0.2);
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 20px;
    }
    
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: #FFD770;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
    }
    
    /* Badges */
    .badge-pago {
        background: linear-gradient(135deg, #FFD770, #FF9800);
        color: #0e2d26;
        padding: 3px 10px;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: bold;
        display: inline-block;
        margin-right: 8px;
    }
    
    .badge-gratuito {
        background: linear-gradient(135deg, #4CAF50, #2E7D32);
        color: white;
        padding: 3px 10px;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: bold;
        display: inline-block;
        margin-right: 8px;
    }
    
    /* Tabs mais bonitas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 10px 20px;
        color: white;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #FFD770 !important;
        color: #0e2d26 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ==================================================
# 🎴 COMPONENTES DE UI
# ==================================================
def render_hero(usuario):
    """Renderiza cabeçalho do painel"""
    
    # Saudação personalizada
    saudacao = ""
    if usuario.get('nome'):
        primeiro_nome = usuario['nome'].split()[0] if len(usuario['nome'].split()) > 0 else usuario['nome']
        saudacao = f", {primeiro_nome}"
    
    # Layout do cabeçalho
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col1:
        st.markdown('<div style="font-size: 3.5rem; text-align: center;">🥋</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<h1 style="color: #FFD770; text-align: center; margin-bottom: 10px;">Academia Digital BJJ</h1>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: center; color: rgba(255, 255, 255, 0.9); font-size: 1.1rem; margin-bottom: 5px;">Domine as técnicas, evolua nas faixas, transforme seu jogo.</p>', unsafe_allow_html=True)
        
        # Informações do usuário
        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.caption(f"📅 {datetime.now().strftime('%d/%m/%Y')}")
        with col_info2:
            st.caption(f"👤 Continue sua jornada{saudacao}")
    
    with col3:
        # Estatística rápida
        cursos = ce.listar_cursos_inscritos(usuario["id"])
        progresso_geral = sum(c.get('progresso', 0) for c in cursos) / len(cursos) if cursos else 0
        st.metric("🎯 Progresso Geral", f"{progresso_geral:.0f}%")
    
    st.divider()

def render_card_curso(curso, usuario, tipo="meus"):
    """Renderiza um card de curso usando Streamlit nativo"""
    
    with st.container():
        # Badges no topo
        col_badges = st.columns([3, 1])
        with col_badges[0]:
            if tipo == "meus":
                st.markdown('<span class="badge-gratuito">📚 EM ANDAMENTO</span>', unsafe_allow_html=True)
            else:
                if curso.get('pago', False):
                    st.markdown('<span class="badge-pago">💰 PAGO</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="badge-gratuito">🎯 GRATUITO</span>', unsafe_allow_html=True)
        
        # Título do curso
        titulo = curso.get('titulo', 'Curso sem título')
        st.markdown(f'**{titulo}**')
        
        # Descrição (limitada)
        descricao = curso.get('descricao', 'Descrição do curso em desenvolvimento...')
        if len(descricao) > 100:
            descricao = descricao[:100] + "..."
        st.caption(descricao)
        
        # Metadados
        metadados = []
        if curso.get('duracao_estimada'):
            metadados.append(f"⏱ {curso['duracao_estimada']}")
        if curso.get('nivel'):
            metadados.append(f"📊 {curso['nivel']}")
        if curso.get('professor_nome'):
            metadados.append(f"👤 {curso['professor_nome']}")
        
        if metadados:
            st.write(" • ".join(metadados))
        
        # Progresso (para cursos meus)
        if tipo == "meus":
            progresso = curso.get('progresso', 0)
            st.progress(progresso / 100)
            st.caption(f"Progresso: {progresso}%")
        
        # Botões
        if tipo == "meus":
            if st.button("▶ Continuar Estudando", key=f"cont_{curso['id']}", use_container_width=True):
                st.session_state["curso_aluno_selecionado"] = curso
                st.session_state["view_aluno"] = "aulas"
                st.rerun()
        else:
            preco = float(curso.get('preco', 0))
            if preco > 0:
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button(f"💰 R$ {preco:.2f}", key=f"buy_{curso['id']}", use_container_width=True, type="primary"):
                        st.session_state.curso_para_compra = curso
                        st.session_state.show_pagamento_modal = True
                        st.rerun()
                with col_btn2:
                    if st.button("📋 Detalhes", key=f"det_{curso['id']}", use_container_width=True):
                        with st.expander("📋 Detalhes do Curso", expanded=True):
                            st.write(curso.get('descricao', ''))
                            st.write(f"**Professor:** {curso.get('professor_nome', 'Não informado')}")
                            st.write(f"**Duração:** {curso.get('duracao_estimada', 'Não informada')}")
                            st.write(f"**Nível:** {curso.get('nivel', 'Não informado')}")
            else:
                if st.button("🎯 Inscrever-se Gratuitamente", key=f"join_{curso['id']}", use_container_width=True):
                    with st.spinner("Realizando matrícula..."):
                        sucesso = ce.inscrever_usuario_em_curso(usuario["id"], curso["id"])
                        if sucesso:
                            st.balloons()
                            st.success("Inscrição realizada com sucesso!")
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error("Erro ao realizar inscrição. Tente novamente.")

# ==================================================
# 💰 MODAL DE PAGAMENTO
# ==================================================
def mostrar_modal_pagamento(curso, usuario):
    """Mostra modal de pagamento"""
    
    st.markdown("---")
    st.markdown(f"### 🛒 Checkout: {curso.get('titulo')}")
    valor = float(curso.get('preco', 0))
    st.markdown(f"## Total: R$ {valor:.2f}")
    st.divider()

    # Gerar link de pagamento
    if "mp_preference_id" not in st.session_state:
        st.session_state.mp_preference_id = None
        st.session_state.mp_link = None

    if not st.session_state.mp_preference_id:
        with st.spinner("Conectando ao Mercado Pago..."):
            link, pref_id = ce.gerar_preferencia_pagamento(curso, usuario)
            if link:
                st.session_state.mp_link = link
                st.session_state.mp_preference_id = pref_id
            else:
                st.error("Erro ao conectar com o banco.")
                return

    if st.session_state.mp_link:
        st.success("Link de pagamento gerado!")
        
        # Instruções
        st.info("""
        📝 **Como pagar sem logar:**
        1. Clique no botão abaixo.
        2. Na tela do Mercado Pago, escolha a opção **"Pagar como convidado"** ou **"Novo Cartão"**.
        3. Você **NÃO** precisa criar conta para pagar com Pix ou Cartão.
        """)
        
        # Botão para pagamento
        st.link_button(
            "👉 Ir para Pagamento (Pix/Cartão)", 
            st.session_state.mp_link, 
            type="primary", 
            use_container_width=True
        )
        
        st.markdown("---")
        st.write("Após pagar, clique abaixo para verificar:")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Verificar Pagamento", use_container_width=True):
                with st.spinner("Verificando..."):
                    time.sleep(1)
                    aprovado, msg = ce.verificar_status_pagamento_mp(st.session_state.mp_preference_id)
                    
                    if aprovado:
                        ok_db, msg_db = ce.processar_compra_curso(usuario['id'], curso['id'], valor)
                        if ok_db:
                            st.balloons()
                            st.success("Sucesso! Curso liberado.")
                            st.session_state.mp_preference_id = None
                            st.session_state.mp_link = None
                            st.session_state.show_pagamento_modal = False
                            st.session_state.curso_para_compra = None
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"Erro no sistema: {msg_db}")
                    else:
                        st.warning(f"Status: {msg}")
        
        with col2:
            if st.button("❌ Cancelar", use_container_width=True):
                st.session_state.mp_preference_id = None
                st.session_state.mp_link = None
                st.session_state.show_pagamento_modal = False
                st.session_state.curso_para_compra = None
                st.rerun()

# ==================================================
# 🧱 ABAS PRINCIPAIS
# ==================================================
def render_tab_meus_cursos(usuario):
    """Renderiza aba 'Meus Cursos'"""
    
    cursos = ce.listar_cursos_inscritos(usuario["id"])
    
    if not cursos:
        st.info("📖 Você ainda não está inscrito em nenhum curso.")
        st.write("Explore nossos cursos disponíveis na aba **'Descobrir Novos'**!")
        return
    
    # Estatísticas
    col_stats1, col_stats2, col_stats3 = st.columns(3)
    with col_stats1:
        st.metric("📚 Cursos", len(cursos))
    with col_stats2:
        progresso_medio = sum(c.get('progresso', 0) for c in cursos) / len(cursos) if cursos else 0
        st.metric("📈 Progresso Médio", f"{progresso_medio:.0f}%")
    with col_stats3:
        horas_estudo = 0
        for c in cursos:
            if c.get('duracao_estimada'):
                try:
                    horas = int(c['duracao_estimada'].replace('h', '').strip())
                    horas_estudo += horas
                except:
                    pass
        st.metric("⏱ Tempo Total", f"{horas_estudo}h")
    
    st.divider()
    st.markdown("### 🎯 Meus Cursos em Andamento")
    
    # Grid de cursos (3 colunas)
    cols = st.columns(3)
    for idx, curso in enumerate(cursos):
        with cols[idx % 3]:
            render_card_curso(curso, usuario, tipo="meus")

def render_tab_novos_cursos(usuario):
    """Renderiza aba 'Novos Cursos'"""
    
    # Filtros
    with st.container():
        st.markdown("### 🔍 Filtros")
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filtro_preco = st.selectbox("💰 Tipo", ["Todos", "Gratuitos", "Pagos"], key="filtro_preco")
        with col_f2:
            filtro_nivel = st.selectbox("📊 Nível", ["Todos", "Iniciante", "Intermediário", "Avançado"], key="filtro_nivel")
        with col_f3:
            filtro_duracao = st.selectbox("⏱ Duração", ["Todos", "Curto (<2h)", "Médio (2-5h)", "Longo (>5h)"], key="filtro_duracao")
    
    # Buscar cursos disponíveis
    novos = ce.listar_cursos_disponiveis_para_aluno(usuario)
    
    if not novos:
        st.info("🎯 Parabéns! Você já está inscrito em todos os cursos disponíveis.")
        return
    
    # Aplicar filtros
    cursos_filtrados = []
    for curso in novos:
        # Filtro de preço
        if filtro_preco == "Gratuitos" and curso.get('pago', False):
            continue
        if filtro_preco == "Pagos" and not curso.get('pago', False):
            continue
        
        # Filtro de nível
        if filtro_nivel != "Todos":
            nivel_curso = curso.get('nivel', '').lower()
            nivel_filtro = filtro_nivel.lower()
            if nivel_filtro not in nivel_curso:
                continue
        
        cursos_filtrados.append(curso)
    
    if not cursos_filtrados:
        st.info("Nenhum curso encontrado com os filtros selecionados.")
        return
    
    # Grid de cursos
    st.markdown(f"### 🚀 Cursos Disponíveis ({len(cursos_filtrados)})")
    
    cols = st.columns(3)
    for idx, curso in enumerate(cursos_filtrados):
        with cols[idx % 3]:
            render_card_curso(curso, usuario, tipo="novos")

def render_tab_concluidos(usuario):
    """Renderiza aba 'Cursos Concluídos'"""
    
    # Buscar cursos inscritos e filtrar por progresso 100%
    cursos_inscritos = ce.listar_cursos_inscritos(usuario["id"])
    cursos_concluidos = [curso for curso in cursos_inscritos if curso.get('progresso', 0) >= 100]
    
    if not cursos_concluidos:
        st.info("🏆 Você ainda não concluiu nenhum curso.")
        st.write("Continue estudando! Complete 100% de um curso para vê-lo aqui.")
        
        with st.expander("🎓 Como obter certificados"):
            st.info("""
            1. Complete 100% do progresso do curso
            2. Realize todas as atividades práticas
            3. Obtenha aprovação do seu professor
            4. Baixe seu certificado digital
            """)
        return
    
    # Lista de cursos concluídos
    st.markdown(f"### 🏆 Cursos Concluídos ({len(cursos_concluidos)})")
    
    for curso in cursos_concluidos:
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"#### {curso.get('titulo')}")
                st.caption(f"Professor: {curso.get('professor_nome', 'Não informado')}")
                st.caption(f"Concluído em: {datetime.now().strftime('%d/%m/%Y')}")
                st.progress(100)
            with col2:
                if st.button("📄 Certificado", key=f"cert_{curso['id']}", use_container_width=True):
                    st.info("Funcionalidade de certificado em desenvolvimento...")
            with col3:
                if st.button("🔁 Revisar", key=f"rev_{curso['id']}", use_container_width=True):
                    st.session_state["curso_aluno_selecionado"] = curso
                    st.session_state["view_aluno"] = "aulas"
                    st.rerun()

# ==================================================
# 🚀 FUNÇÃO PRINCIPAL
# ==================================================
def render_painel_aluno(usuario):
    """Renderiza a área de cursos do aluno"""
    
    # Aplicar estilos CSS
    aplicar_estilos()
    
    # Verificar modal de pagamento
    if st.session_state.get("show_pagamento_modal", False) and st.session_state.get("curso_para_compra"):
        mostrar_modal_pagamento(st.session_state.curso_para_compra, usuario)
        return
    
    # Verificar se estamos no player de aula
    if st.session_state.get("view_aluno") == "aulas" and st.session_state.get("curso_aluno_selecionado"):
        # Renderizar player simplificado
        curso = st.session_state["curso_aluno_selecionado"]
        
        st.markdown(f"## 🎥 Aula do Curso: {curso.get('titulo')}")
        st.divider()
        
        # Informações do curso
        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.markdown(f"**Professor:** {curso.get('professor_nome', 'Não informado')}")
            st.markdown(f"**Nível:** {curso.get('nivel', 'Não informado')}")
        with col_info2:
            progresso = curso.get('progresso', 0)
            st.metric("📊 Seu Progresso", f"{progresso}%")
        
        st.divider()
        
        # Player de vídeo
        st.markdown("### 📹 Vídeo da Aula")
        
        # Placeholder para o vídeo
        col_video, col_controles = st.columns([3, 1])
        with col_video:
            # Vídeo de exemplo (poderia ser substituído por URL real)
            st.video("https://www.w3schools.com/html/mov_bbb.mp4")
        
        with col_controles:
            if st.button("✅ Marcar como Concluída", type="primary", use_container_width=True):
                st.success("Aula marcada como concluída!")
                time.sleep(1)
                st.session_state["view_aluno"] = "lista"
                st.session_state["curso_aluno_selecionado"] = None
                st.rerun()
            
            if st.button("📝 Próxima Aula", use_container_width=True):
                st.info("Próxima aula em desenvolvimento...")
        
        # Conteúdo da aula
        st.divider()
        st.markdown("### 📋 Conteúdo da Aula")
        st.markdown("""
        - Introdução às técnicas apresentadas
        - Demonstração prática
        - Pontos importantes a observar
        - Exercícios recomendados
        - Dicas de segurança
        """)
        
        # Botão de voltar
        st.divider()
        if st.button("← Voltar aos Meus Cursos", use_container_width=True, type="secondary"):
            st.session_state["view_aluno"] = "lista"
            st.session_state["curso_aluno_selecionado"] = None
            st.rerun()
        
        return
    
    # ============= LAYOUT PRINCIPAL =============
    
    # Hero Section
    render_hero(usuario)
    
    # Tabs principais
    tab_meus, tab_novos, tab_concluidos = st.tabs([
        "🎯 **Meus Cursos**", 
        "🚀 **Descobrir Novos**", 
        "🏆 **Concluídos**"
    ])
    
    with tab_meus:
        render_tab_meus_cursos(usuario)
    
    with tab_novos:
        render_tab_novos_cursos(usuario)
    
    with tab_concluidos:
        render_tab_concluidos(usuario)
    
    # Footer
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**🥋 BJJ Digital**")
        st.caption("Sua evolução começa aqui")
    with col2:
        st.markdown("**📞 Suporte**")
        st.caption("suporte@bjjdigital.com.br")
    with col3:
        st.markdown("**🎯 Suas Metas**")
        # Calcular progresso geral
        cursos = ce.listar_cursos_inscritos(usuario["id"])
        if cursos:
            progresso_geral = sum(c.get('progresso', 0) for c in cursos) / len(cursos)
            st.caption(f"Progresso geral: {progresso_geral:.0f}%")
        else:
            st.caption("Comece seus estudos!")
