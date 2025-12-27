# views/painel_aluno.py

import streamlit as st
import time
from datetime import datetime
import utils as ce

# ==================================================
# 🎨 ESTILOS CSS PERSONALIZADOS
# ==================================================
def aplicar_estilos_cards():
    st.markdown("""
    <style>
        /* Estilos gerais */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        
        /* Hero section */
        .hero-section {
            background: linear-gradient(135deg, rgba(14, 45, 38, 0.9), rgba(5, 104, 83, 0.7));
            border-radius: 20px;
            padding: 40px 20px;
            margin-bottom: 30px;
            border: 1px solid rgba(255, 215, 112, 0.3);
            text-align: center;
        }
        
        .hero-title {
            color: #FFD770;
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 15px;
        }
        
        .hero-subtitle {
            color: rgba(255, 255, 255, 0.9);
            font-size: 1.2rem;
            max-width: 800px;
            margin: 0 auto 20px auto;
        }
        
        /* Cards de cursos */
        .curso-card {
            background: linear-gradient(135deg, rgba(14, 45, 38, 0.9), rgba(5, 104, 83, 0.8));
            border: 1px solid rgba(255, 215, 112, 0.2);
            border-radius: 16px;
            padding: 20px;
            height: 100%;
            transition: all 0.3s ease;
        }
        
        .curso-card:hover {
            transform: translateY(-5px);
            border-color: #FFD770;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        }
        
        .badge-curso {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 700;
            margin-right: 8px;
            margin-bottom: 10px;
        }
        
        .badge-premium {
            background: linear-gradient(135deg, #FFD770, #FF9800);
            color: #0e2d26;
        }
        
        .badge-gratuito {
            background: linear-gradient(135deg, #4CAF50, #2E7D32);
            color: white;
        }
        
        .badge-andamento {
            background: linear-gradient(135deg, #2196F3, #0D47A1);
            color: white;
        }
        
        .titulo-card {
            color: #FFD770;
            font-size: 1.2rem;
            font-weight: 800;
            margin-bottom: 12px;
            line-height: 1.3;
        }
        
        .descricao-card {
            color: rgba(255, 255, 255, 0.8);
            font-size: 0.9rem;
            margin-bottom: 20px;
            line-height: 1.5;
        }
        
        /* Progresso */
        .progresso-container {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 10px;
            height: 10px;
            margin-bottom: 15px;
            overflow: hidden;
        }
        
        .progresso-bar {
            background: linear-gradient(90deg, #4CAF50, #8BC34A);
            height: 100%;
            border-radius: 10px;
            transition: width 0.5s ease;
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background-color: transparent;
        }
        
        .stTabs [data-baseweb="tab"] {
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 12px 12px 0 0;
            padding: 15px 25px;
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-bottom: none;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: #FFD770 !important;
            color: #0e2d26 !important;
            font-weight: bold;
            border-color: #FFD770;
        }
        
        /* Empty state */
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            background: rgba(14, 45, 38, 0.3);
            border-radius: 20px;
            border: 2px dashed rgba(255, 215, 112, 0.3);
            margin: 20px 0;
        }
        
        /* Grid de cursos */
        .curso-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 25px;
            margin-top: 20px;
        }
        
        /* Responsividade */
        @media (max-width: 1200px) {
            .curso-grid {
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            }
        }
        
        @media (max-width: 768px) {
            .curso-grid {
                grid-template-columns: 1fr;
            }
            
            .hero-title {
                font-size: 2rem;
            }
            
            .hero-subtitle {
                font-size: 1rem;
            }
        }
    </style>
    """, unsafe_allow_html=True)

# ==================================================
# 🎴 FUNÇÕES DE RENDERIZAÇÃO DE COMPONENTES
# ==================================================
def render_hero_section(usuario):
    """Renderiza seção hero"""
    
    # Saudação
    saudacao = ""
    if usuario.get('nome'):
        primeiro_nome = usuario['nome'].split()[0] if len(usuario['nome'].split()) > 0 else usuario['nome']
        saudacao = f", {primeiro_nome}"
    
    # Data atual
    data_atual = datetime.now().strftime("%d/%m/%Y")
    
    # Hero section usando Streamlit nativo
    st.markdown('<div class="hero-section">', unsafe_allow_html=True)
    
    col_icon, col_content = st.columns([1, 4])
    with col_icon:
        st.markdown('<div style="font-size: 4rem; text-align: center;">🥋</div>', unsafe_allow_html=True)
    
    with col_content:
        st.markdown('<div class="hero-title">Academia Digital BJJ</div>', unsafe_allow_html=True)
        st.markdown('<div class="hero-subtitle">Domine as técnicas, evolua nas faixas, transforme seu jogo.</div>', unsafe_allow_html=True)
        
        # Informações extras
        col1, col2 = st.columns(2)
        with col1:
            st.caption(f"📅 {data_atual}")
        with col2:
            st.caption(f"🎯 Continue sua jornada{saudacao}")
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_card_curso_simples(curso, tipo="meus"):
    """Renderiza card de curso simplificado"""
    
    with st.container():
        # Badges
        col_badges = st.columns([4, 1])
        with col_badges[0]:
            if curso.get('pago', False):
                st.markdown('<span class="badge-curso badge-premium">💰 PREMIUM</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="badge-curso badge-gratuito">🎯 GRATUITO</span>', unsafe_allow_html=True)
            
            if tipo == "meus":
                st.markdown('<span class="badge-curso badge-andamento">📚 EM ANDAMENTO</span>', unsafe_allow_html=True)
        
        # Título
        st.markdown(f'<div class="titulo-card">{curso.get("titulo", "Curso")}</div>', unsafe_allow_html=True)
        
        # Descrição
        descricao = curso.get('descricao', 'Descrição do curso em desenvolvimento...')
        if len(descricao) > 120:
            descricao = descricao[:120] + "..."
        st.markdown(f'<div class="descricao-card">{descricao}</div>', unsafe_allow_html=True)
        
        # Metadados
        metadados = []
        if curso.get('duracao_estimada'):
            metadados.append(f'⏱ {curso.get("duracao_estimada")}')
        if curso.get('nivel'):
            metadados.append(f'📊 {curso.get("nivel")}')
        if curso.get('professor_nome'):
            metadados.append(f'👤 {curso.get("professor_nome")}')
        
        if metadados:
            st.caption(" • ".join(metadados))
        
        # Progresso (para cursos meus)
        if tipo == "meus":
            progresso = curso.get('progresso', 0)
            st.markdown(f"""
            <div class="progresso-container">
                <div class="progresso-bar" style="width: {progresso}%"></div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 5px;">
                <span style="color: rgba(255,255,255,0.7); font-size: 0.9rem;">Progresso</span>
                <span style="color: #FFD770; font-weight: 700; font-size: 0.9rem;">{progresso}%</span>
            </div>
            """, unsafe_allow_html=True)
        
        # Botões
        if tipo == "meus":
            if st.button("▶ Continuar Estudando", key=f"cont_{curso['id']}", use_container_width=True):
                st.session_state["curso_aluno_selecionado"] = curso
                st.session_state["view_aluno"] = "aulas"
                st.rerun()
        else:
            preco = curso.get('preco', 0)
            if preco > 0:
                if st.button(f"💰 Comprar - R$ {preco:.2f}", key=f"buy_{curso['id']}", type="primary", use_container_width=True):
                    st.session_state.curso_para_compra = curso
                    st.session_state.show_pagamento_modal = True
                    st.rerun()
            else:
                if st.button("🎯 Inscrever-se Gratuitamente", key=f"join_{curso['id']}", use_container_width=True):
                    with st.spinner("Realizando matrícula..."):
                        sucesso = ce.inscrever_usuario_em_curso(usuario["id"], curso["id"])
                        if sucesso:
                            st.balloons()
                            st.success("Inscrição realizada com sucesso!")
                            time.sleep(1.5)
                            st.rerun()

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
# 🧱 RENDERIZAÇÃO DAS ABAS
# ==================================================
def render_tab_meus_cursos(usuario):
    """Renderiza aba 'Meus Cursos'"""
    
    cursos = ce.listar_cursos_inscritos(usuario["id"])
    
    if not cursos:
        st.markdown("""
        <div class="empty-state">
            <div style="font-size: 4rem; margin-bottom: 20px; opacity: 0.5;">📖</div>
            <h3 style="color: rgba(255,255,255,0.9); margin-bottom: 10px;">Nenhum curso em andamento</h3>
            <p style="color: rgba(255,255,255,0.6);">Explore nossos cursos disponíveis e comece sua jornada!</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Estatísticas
        col_stats1, col_stats2, col_stats3 = st.columns(3)
        with col_stats1:
            st.metric("📚 Cursos", len(cursos))
        with col_stats2:
            progresso_medio = sum(c.get('progresso', 0) for c in cursos) / len(cursos) if cursos else 0
            st.metric("📈 Progresso Médio", f"{progresso_medio:.0f}%")
        with col_stats3:
            horas_estudo = sum(int(c.get('duracao_estimada', '0h').replace('h', '')) 
                            for c in cursos if c.get('duracao_estimada') and 'h' in str(c.get('duracao_estimada')))
            st.metric("⏱ Tempo Total", f"{horas_estudo}h")
        
        # Grid de cursos
        st.markdown('<div class="curso-grid">', unsafe_allow_html=True)
        
        cols = st.columns(3)
        for idx, curso in enumerate(cursos):
            with cols[idx % 3]:
                with st.container():
                    st.markdown('<div class="curso-card">', unsafe_allow_html=True)
                    render_card_curso_simples(curso, tipo="meus")
                    st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

def render_tab_novos_cursos(usuario):
    """Renderiza aba 'Novos Cursos'"""
    
    # Filtros
    with st.container():
        st.markdown("### 🔍 Filtros")
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filtro_preco = st.selectbox("💰 Preço", ["Todos", "Gratuitos", "Premium"], key="filtro_preco_novos")
        with col_f2:
            filtro_nivel = st.selectbox("📊 Nível", ["Todos", "Iniciante", "Intermediário", "Avançado"], key="filtro_nivel_novos")
        with col_f3:
            filtro_duracao = st.selectbox("⏱ Duração", ["Todos", "Curto (<2h)", "Médio (2-5h)", "Longo (>5h)"], key="filtro_duracao_novos")
    
    # Buscar cursos disponíveis
    novos = ce.listar_cursos_disponiveis_para_aluno(usuario)
    
    if not novos:
        st.markdown("""
        <div class="empty-state">
            <div style="font-size: 4rem; margin-bottom: 20px; opacity: 0.5;">🎯</div>
            <h3 style="color: rgba(255,255,255,0.9); margin-bottom: 10px;">Todos os cursos já estão no seu radar!</h3>
            <p style="color: rgba(255,255,255,0.6);">Continue focando nos seus estudos atuais ou fale com seu professor sobre novos conteúdos.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Aplicar filtros
        cursos_filtrados = []
        for curso in novos:
            # Filtro de preço
            if filtro_preco == "Gratuitos" and curso.get('pago', False):
                continue
            if filtro_preco == "Premium" and not curso.get('pago', False):
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
        st.markdown('<div class="curso-grid">', unsafe_allow_html=True)
        
        cols = st.columns(3)
        for idx, curso in enumerate(cursos_filtrados):
            with cols[idx % 3]:
                with st.container():
                    st.markdown('<div class="curso-card">', unsafe_allow_html=True)
                    render_card_curso_simples(curso, tipo="novos")
                    st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

def render_tab_concluidos(usuario):
    """Renderiza aba 'Cursos Concluídos'"""
    
    # Usar a mesma função de listar cursos inscritos e filtrar por progresso 100%
    cursos_inscritos = ce.listar_cursos_inscritos(usuario["id"])
    cursos_concluidos = [curso for curso in cursos_inscritos if curso.get('progresso', 0) >= 100]
    
    if not cursos_concluidos:
        st.markdown("""
        <div class="empty-state">
            <div style="font-size: 4rem; margin-bottom: 20px; opacity: 0.5;">🏆</div>
            <h3 style="color: rgba(255,255,255,0.9); margin-bottom: 10px;">Nenhum curso concluído ainda</h3>
            <p style="color: rgba(255,255,255,0.6);">Continue estudando! Seus primeiros certificados estão chegando.</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("🎓 Como obter certificados", expanded=False):
            st.info("""
            1. Complete 100% do progresso do curso
            2. Realize todas as atividades práticas
            3. Obtenha aprovação do seu professor
            4. Baixe seu certificado digital na aba 'Meus Certificados'
            """)
    else:
        st.markdown(f"### 🏆 Cursos Concluídos ({len(cursos_concluidos)})")
        
        for curso in cursos_concluidos:
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"#### {curso.get('titulo')}")
                    st.caption(f"Concluído em: {datetime.now().strftime('%d/%m/%Y')}")
                    st.progress(100)
                with col2:
                    if st.button("📄 Certificado", key=f"cert_{curso['id']}", use_container_width=True):
                        st.info("Funcionalidade de certificado em desenvolvimento...")
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
    aplicar_estilos_cards()
    
    # Verificar modal de pagamento
    if st.session_state.get("show_pagamento_modal", False) and st.session_state.get("curso_para_compra"):
        mostrar_modal_pagamento(st.session_state.curso_para_compra, usuario)
        return
    
    # Verificar se estamos no player de aula
    if st.session_state.get("view_aluno") == "aulas" and st.session_state.get("curso_aluno_selecionado"):
        # Renderizar player simplificado
        curso = st.session_state["curso_aluno_selecionado"]
        
        st.markdown(f"## 🎥 {curso.get('titulo')}")
        st.markdown(f"📚 **Curso:** {curso.get('titulo')}")
        st.divider()
        
        # Player de vídeo placeholder
        col_video, col_info = st.columns([2, 1])
        
        with col_video:
            st.markdown("### 📹 Aula em Vídeo")
            st.video("https://www.w3schools.com/html/mov_bbb.mp4")  # Vídeo de exemplo
            
            # Controles
            col_controls1, col_controls2 = st.columns(2)
            with col_controls1:
                if st.button("✅ Marcar como Concluída", use_container_width=True, type="primary"):
                    st.success("Aula marcada como concluída!")
                    time.sleep(1)
                    st.session_state["view_aluno"] = "lista"
                    st.session_state["curso_aluno_selecionado"] = None
                    st.rerun()
            
            with col_controls2:
                if st.button("📝 Próxima Aula", use_container_width=True):
                    st.info("Próxima aula em desenvolvimento...")
        
        with col_info:
            st.markdown("### 📋 Conteúdo da Aula")
            st.markdown("""
            - Introdução às técnicas básicas
            - Posicionamento inicial
            - Controle do adversário
            - Finalização básica
            - Exercícios práticos
            """)
            
            st.divider()
            
            st.markdown("### 📊 Progresso do Curso")
            progresso = curso.get('progresso', 0)
            st.progress(progresso / 100)
            st.caption(f"{progresso}% concluído")
            
            st.divider()
            
            st.markdown("### 🎯 Próximos Passos")
            st.markdown("""
            1. Pratique as técnicas demonstradas
            2. Faça os exercícios propostos
            3. Grave um vídeo praticando
            4. Envie para avaliação do professor
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
    render_hero_section(usuario)
    
    # Tabs
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
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption("🥋 **BJJ Digital**")
        st.caption("Sua evolução começa aqui")
    with col2:
        st.caption("📞 Suporte")
        st.caption("suporte@bjjdigital.com.br")
    with col3:
        # Calcular progresso geral
        cursos = ce.listar_cursos_inscritos(usuario["id"])
        progresso_geral = sum(c.get('progresso', 0) for c in cursos) / len(cursos) if cursos else 0
        st.caption("🎯 Metas")
        st.caption(f"Progresso geral: {progresso_geral:.0f}%")
