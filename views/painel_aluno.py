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
        /* Estilos gerais para cards */
        .curso-card-moderno {
            background: linear-gradient(135deg, rgba(14, 45, 38, 0.9), rgba(5, 104, 83, 0.8));
            border: 1px solid rgba(255, 215, 112, 0.2);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 20px;
            transition: all 0.3s ease;
            height: 100%;
            display: flex;
            flex-direction: column;
        }
        
        .curso-card-moderno:hover {
            transform: translateY(-5px);
            border-color: #FFD770;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            background: linear-gradient(135deg, rgba(14, 45, 38, 0.95), rgba(5, 104, 83, 0.9));
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
        
        .titulo-curso {
            color: #FFD770;
            font-size: 1.2rem;
            font-weight: 800;
            margin-bottom: 12px;
            min-height: 60px;
            line-height: 1.3;
        }
        
        .descricao-curso {
            color: rgba(255, 255, 255, 0.8);
            font-size: 0.9rem;
            margin-bottom: 20px;
            flex-grow: 1;
            line-height: 1.5;
        }
        
        .btn-curso {
            width: 100%;
            padding: 12px 20px;
            border: none;
            border-radius: 10px;
            font-weight: 700;
            font-size: 0.95rem;
            cursor: pointer;
            transition: all 0.3s;
            margin-bottom: 15px;
            text-align: center;
            display: block;
            text-decoration: none !important;
        }
        
        .btn-continuar {
            background: linear-gradient(135deg, #FFD770, #FFC107);
            color: #0e2d26;
        }
        
        .btn-continuar:hover {
            background: linear-gradient(135deg, #FFC107, #FF9800);
            transform: scale(1.02);
        }
        
        .btn-comprar {
            background: linear-gradient(135deg, #4CAF50, #2E7D32);
            color: white;
        }
        
        .btn-comprar:hover {
            background: linear-gradient(135deg, #388E3C, #1B5E20);
            transform: scale(1.02);
        }
        
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
        
        .metadados-curso {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .metadado-item {
            background: rgba(255, 255, 255, 0.1);
            padding: 5px 10px;
            border-radius: 8px;
            color: rgba(255, 255, 255, 0.7);
            font-size: 0.8rem;
        }
        
        /* Hero section */
        .hero-cursos {
            text-align: center;
            padding: 40px 20px;
            background: linear-gradient(135deg, rgba(14, 45, 38, 0.9), rgba(5, 104, 83, 0.7));
            border-radius: 20px;
            margin-bottom: 30px;
            border: 1px solid rgba(255, 215, 112, 0.3);
        }
        
        /* Empty state */
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            background: rgba(14, 45, 38, 0.3);
            border-radius: 20px;
            border: 2px dashed rgba(255, 215, 112, 0.3);
        }
        
        .empty-state-icon {
            font-size: 4rem;
            margin-bottom: 20px;
            opacity: 0.5;
        }
        
        /* Player */
        .player-container {
            background: rgba(14, 45, 38, 0.9);
            border-radius: 20px;
            padding: 30px;
            border: 1px solid rgba(255, 215, 112, 0.3);
        }
        
        .player-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
        }
        
        .player-title {
            color: #FFD770;
            font-size: 1.8rem;
            font-weight: 800;
        }
        
        /* Tabs personalizadas */
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
        
        /* Container hover effects */
        div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
        }
        
        /* Grid de cursos */
        .cursos-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 25px;
            margin-top: 30px;
        }
    </style>
    """, unsafe_allow_html=True)

# ==================================================
# 🎴 FUNÇÕES DE RENDERIZAÇÃO DE COMPONENTES
# ==================================================
def render_hero_section(titulo, subtitulo, usuario_nome=""):
    """Renderiza seção hero moderna"""
    from datetime import datetime
    
    saudacao = f", {usuario_nome}" if usuario_nome else ""
    data_atual = datetime.now().strftime("%d/%m/%Y")
    
    hero_html = f"""
    <div class="hero-cursos">
        <div style="font-size: 3.5rem; margin-bottom: 15px;">🥋</div>
        <h1 style="color: #FFD770; font-size: 2.5rem; margin-bottom: 10px;">
            {titulo}
        </h1>
        <p style="color: rgba(255,255,255,0.9); font-size: 1.2rem; max-width: 800px; margin: 0 auto;">
            {subtitulo}
        </p>
        <div style="margin-top: 25px; color: rgba(255,255,255,0.6);">
            📅 {data_atual} | 🎯 Continue sua jornada{saudacao}
        </div>
    </div>
    """
    return hero_html

def render_card_curso(curso, usuario, tipo="meus"):
    """Renderiza um card de curso moderno"""
    
    # Determinar badges
    badges_html = ""
    if curso.get('pago', False):
        badges_html += '<span class="badge-curso badge-premium">💰 PREMIUM</span>'
    else:
        badges_html += '<span class="badge-curso badge-gratuito">🎯 GRATUITO</span>'
    
    if tipo == "meus":
        badges_html += f'<span class="badge-curso badge-andamento">📚 EM ANDAMENTO</span>'
    
    # Metadados
    metadados = []
    if curso.get('duracao_estimada'):
        metadados.append(f'⏱ {curso.get("duracao_estimada")}')
    if curso.get('nivel'):
        metadados.append(f'📊 {curso.get("nivel")}')
    if curso.get('professor_nome'):
        metadados.append(f'👤 {curso.get("professor_nome")}')
    
    metadados_html = ""
    for meta in metadados:
        metadados_html += f'<div class="metadado-item">{meta}</div>'
    
    # Botão
    botao_html = ""
    if tipo == "meus":
        progresso = curso.get('progresso', 0)
        botao_html = f"""
        <div class="progresso-container">
            <div class="progresso-bar" style="width: {progresso}%"></div>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 15px;">
            <span style="color: rgba(255,255,255,0.7);">Progresso</span>
            <span style="color: #FFD770; font-weight: 700;">{progresso}%</span>
        </div>
        <a href="#" class="btn-curso btn-continuar" onclick="continuarCurso('{curso["id"]}', '{usuario["id"]}')">
            ▶ CONTINUAR ESTUDANDO
        </a>
        """
    else:
        preco = curso.get('preco', 0)
        if preco > 0:
            botao_html = f"""
            <a href="#" class="btn-curso btn-comprar" onclick="comprarCurso('{curso["id"]}')">
                💰 COMPRAR AGORA - R$ {preco:.2f}
            </a>
            """
        else:
            botao_html = f"""
            <a href="#" class="btn-curso btn-continuar" onclick="inscreverCurso('{curso["id"]}', '{usuario["id"]}')">
                🎯 INSCREVER-SE GRATUITAMENTE
            </a>
            """
    
    # Descrição limitada
    descricao = curso.get('descricao', 'Descrição do curso em desenvolvimento...')
    if len(descricao) > 150:
        descricao = descricao[:150] + "..."
    
    # HTML completo do card
    card_html = f"""
    <div class="curso-card-moderno">
        {badges_html}
        <div class="titulo-curso">{curso.get('titulo', 'Curso')}</div>
        <div class="descricao-curso">{descricao}</div>
        {botao_html}
        <div class="metadados-curso">
            {metadados_html}
        </div>
    </div>
    """
    
    return card_html

def render_empty_state(icon="📚", titulo="Nada por aqui", mensagem=""):
    """Renderiza estado vazio estilizado"""
    empty_html = f"""
    <div class="empty-state">
        <div class="empty-state-icon">{icon}</div>
        <h3 style="color: rgba(255,255,255,0.9); margin-bottom: 10px;">{titulo}</h3>
        <p style="color: rgba(255,255,255,0.6);">{mensagem}</p>
    </div>
    """
    return empty_html

def render_player_aula(aula, curso):
    """Renderiza player de aula moderno"""
    
    # Verificar tipo de conteúdo
    conteudo_html = ""
    blocos = aula.get('conteudo', {}).get('blocos', [])
    
    if blocos:
        for bloco in blocos:
            tipo = bloco.get('tipo', '')
            if tipo == 'texto':
                conteudo_html += f"""
                <div style="background: rgba(255,255,255,0.03); padding: 20px; border-radius: 12px; margin-bottom: 15px;">
                    {bloco.get('conteudo', '')}
                </div>
                """
            elif tipo == 'imagem' and bloco.get('url'):
                conteudo_html += f"""
                <div style="margin-bottom: 20px;">
                    <img src="{bloco.get('url')}" style="width: 100%; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
                </div>
                """
            elif tipo == 'video' and bloco.get('url'):
                conteudo_html += f"""
                <div style="margin-bottom: 20px;">
                    <video controls style="width: 100%; border-radius: 12px;">
                        <source src="{bloco.get('url')}" type="video/mp4">
                    </video>
                </div>
                """
    else:
        conteudo_html = """
        <div style="text-align: center; padding: 40px;">
            <div style="font-size: 3rem; opacity: 0.3;">🎥</div>
            <p style="color: rgba(255,255,255,0.6);">Conteúdo da aula em desenvolvimento...</p>
        </div>
        """
    
    player_html = f"""
    <div class="player-container">
        <div class="player-header">
            <div>
                <div class="player-title">{aula.get('titulo', 'Aula')}</div>
                <div style="color: rgba(255,255,255,0.7); font-size: 1.1rem;">
                    📚 {curso.get('titulo')}
                </div>
            </div>
            <button style="
                background: linear-gradient(135deg, #078B6C, #056853);
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 12px;
                font-weight: 700;
                cursor: pointer;
                transition: all 0.3s;
            " onclick="voltarParaCursos()">
                ← Voltar ao Curso
            </button>
        </div>
        
        <div style="margin: 30px 0;">
            <div style="background: #000; aspect-ratio: 16/9; border-radius: 15px; display: flex; align-items: center; justify-content: center; color: white;">
                <div style="text-align: center;">
                    <div style="font-size: 4rem;">▶️</div>
                    <p>Player de vídeo integrado</p>
                </div>
            </div>
        </div>
        
        <div style="text-align: center; margin: 25px 0;">
            <button style="
                background: linear-gradient(135deg, #FFD770, #FFC107);
                color: #0e2d26;
                border: none;
                padding: 15px 40px;
                border-radius: 12px;
                font-weight: 800;
                font-size: 1.1rem;
                cursor: pointer;
                transition: all 0.3s;
                display: inline-flex;
                align-items: center;
                gap: 10px;
            " onclick="marcarConcluida()">
                ✅ Marcar como concluída
            </button>
        </div>
        
        <div class="conteudo-aula">
            <h3 style="color: #FFD770; margin-bottom: 20px;">📝 Conteúdo da Aula</h3>
            {conteudo_html}
        </div>
    </div>
    """
    
    return player_html

# ==================================================
# 💰 MODAL DE PAGAMENTO
# ==================================================
def mostrar_modal_pagamento(curso, usuario):
    """Mostra modal de pagamento"""
    
    with st.container():
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
                    st.rerun()

# ==================================================
# 🧱 RENDERIZAÇÃO DAS ABAS
# ==================================================
def render_tab_meus_cursos(usuario):
    """Renderiza aba 'Meus Cursos'"""
    
    cursos = ce.listar_cursos_inscritos(usuario["id"])
    
    if not cursos:
        st.components.v1.html(
            render_empty_state(
                icon="📖",
                titulo="Nenhum curso em andamento",
                mensagem="Explore nossos cursos disponíveis e comece sua jornada!"
            ),
            height=300
        )
    else:
        # Estatísticas
        col_stats1, col_stats2, col_stats3 = st.columns(3)
        with col_stats1:
            st.metric("📚 Cursos", len(cursos))
        with col_stats2:
            progresso_medio = sum(c.get('progresso', 0) for c in cursos) / len(cursos) if cursos else 0
            st.metric("📈 Progresso Médio", f"{progresso_medio:.0f}%")
        with col_stats3:
            horas_estudo = sum(int(c.get('duracao_estimada', '0h').replace('h', '')) for c in cursos if 'h' in str(c.get('duracao_estimada', '')))
            st.metric("⏱ Tempo Total", f"{horas_estudo}h")
        
        # Grid de cursos
        cols = st.columns(3)
        for idx, curso in enumerate(cursos):
            with cols[idx % 3]:
                # Card usando HTML/JavaScript
                card_html = render_card_curso(curso, usuario, tipo="meus")
                st.components.v1.html(card_html, height=350)
                
                # Botões nativos como fallback
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("▶ Continuar", key=f"cont_{curso['id']}", use_container_width=True):
                        st.session_state["curso_aluno_selecionado"] = curso
                        st.session_state["view_aluno"] = "aulas"
                        st.rerun()
                with col_btn2:
                    if st.button("📊 Detalhes", key=f"det_{curso['id']}", use_container_width=True):
                        with st.expander("📋 Detalhes do Curso", expanded=True):
                            st.write(curso.get('descricao', ''))
                            if curso.get('professor_nome'):
                                st.write(f"**Professor:** {curso.get('professor_nome')}")
                            if curso.get('duracao_estimada'):
                                st.write(f"**Duração:** {curso.get('duracao_estimada')}")
                            if curso.get('nivel'):
                                st.write(f"**Nível:** {curso.get('nivel')}")
                            if curso.get('progresso', 0) > 0:
                                st.write(f"**Progresso atual:** {curso.get('progresso')}%")

def render_tab_novos_cursos(usuario):
    """Renderiza aba 'Novos Cursos'"""
    
    # Filtros
    with st.container():
        st.markdown("### 🔍 Filtros")
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filtro_preco = st.selectbox("💰 Preço", ["Todos", "Gratuitos", "Premium"], key="filtro_preco")
        with col_f2:
            filtro_nivel = st.selectbox("📊 Nível", ["Todos", "Iniciante", "Intermediário", "Avançado"], key="filtro_nivel")
        with col_f3:
            filtro_duracao = st.selectbox("⏱ Duração", ["Todos", "Curto (<2h)", "Médio (2-5h)", "Longo (>5h)"], key="filtro_duracao")
    
    # Buscar cursos disponíveis
    novos = ce.listar_cursos_disponiveis_para_aluno(usuario)
    
    if not novos:
        st.components.v1.html(
            render_empty_state(
                icon="🎯",
                titulo="Todos os cursos já estão no seu radar!",
                mensagem="Continue focando nos seus estudos atuais ou fale com seu professor sobre novos conteúdos."
            ),
            height=300
        )
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
        
        cols = st.columns(3)
        for idx, curso in enumerate(cursos_filtrados):
            with cols[idx % 3]:
                with st.container(border=True):
                    # Card HTML
                    card_html = render_card_curso(curso, usuario, tipo="novos")
                    st.components.v1.html(card_html, height=320)
                    
                    # Botão nativo como fallback
                    preco = float(curso.get('preco', 0))
                    pago = curso.get('pago', False)
                    
                    if pago and preco > 0:
                        if st.button(f"💰 Comprar - R$ {preco:.2f}", 
                                   key=f"buy_{curso['id']}", 
                                   use_container_width=True, 
                                   type="primary"):
                            # Mostrar modal de pagamento
                            st.session_state.curso_para_compra = curso
                            st.session_state.show_pagamento_modal = True
                            st.rerun()
                    else:
                        if st.button("🎯 Inscrever-se Gratuitamente", 
                                   key=f"join_{curso['id']}", 
                                   use_container_width=True):
                            with st.spinner("Realizando matrícula..."):
                                sucesso = ce.inscrever_usuario_em_curso(usuario["id"], curso["id"])
                                if sucesso:
                                    st.balloons()
                                    st.success("Inscrição realizada com sucesso!")
                                    time.sleep(1.5)
                                    st.rerun()
                                else:
                                    st.error("Erro ao realizar inscrição. Tente novamente.")

def render_tab_concluidos(usuario):
    """Renderiza aba 'Cursos Concluídos'"""
    
    # Buscar cursos concluídos
    cursos_concluidos = ce.listar_cursos_concluidos(usuario["id"])
    
    if not cursos_concluidos:
        st.components.v1.html(
            render_empty_state(
                icon="🏆",
                titulo="Nenhum curso concluído ainda",
                mensagem="Continue estudando! Seus primeiros certificados estão chegando."
            ),
            height=300
        )
        
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
                    st.caption(f"Concluído em: {curso.get('data_conclusao', 'Data não disponível')}")
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
    """Renderiza a área de cursos do aluno com design moderno"""
    
    # Aplicar estilos CSS
    aplicar_estilos_cards()
    
    # Verificar modal de pagamento
    if st.session_state.get("show_pagamento_modal", False) and st.session_state.get("curso_para_compra"):
        mostrar_modal_pagamento(st.session_state.curso_para_compra, usuario)
    
    # Verificar se estamos no player de aula
    if st.session_state.get("view_aluno") == "aulas" and st.session_state.get("curso_aluno_selecionado"):
        # Renderizar player moderno
        curso = st.session_state["curso_aluno_selecionado"]
        
        # Buscar módulos e aulas
        modulos = ce.listar_modulos_e_aulas(curso['id'])
        aula = None
        if modulos and modulos[0].get('aulas'):
            aula = modulos[0]['aulas'][0]
        
        if aula:
            # Player HTML
            st.components.v1.html(render_player_aula(aula, curso), height=800)
            
            # JavaScript handlers inline
            js_code = """
            <script>
            function voltarParaCursos() {
                window.parent.postMessage({
                    type: 'streamlit:setComponentValue',
                    data: {action: 'voltar_cursos'}
                }, '*');
            }
            
            function marcarConcluida() {
                window.parent.postMessage({
                    type: 'streamlit:setComponentValue',
                    data: {action: 'concluir_aula'}
                }, '*');
                alert('Aula marcada como concluída!');
            }
            </script>
            """
            st.components.v1.html(js_code, height=0)
        else:
            st.error("Aula não encontrada")
        
        # Botão de voltar nativo
        if st.button("← Voltar aos Cursos", use_container_width=True, type="primary"):
            st.session_state["view_aluno"] = "lista"
            st.session_state["curso_aluno_selecionado"] = None
            st.rerun()
        
        return
    
    # ============= LAYOUT PRINCIPAL =============
    
    # Hero Section
    # Corrigido: usando a chave correta do dicionário 'nome' em vez de 'name'
    primeiro_nome = ""
    if usuario.get('nome'):
        primeiro_nome = usuario['nome'].split()[0] if len(usuario['nome'].split()) > 0 else usuario['nome']
    
    st.components.v1.html(
        render_hero_section(
            "🥋 Academia Digital BJJ",
            "Domine as técnicas, evolua nas faixas, transforme seu jogo.",
            primeiro_nome
        ),
        height=300
    )
    
    # Tabs modernas
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
    
    # JavaScript global para os cards
    js_global = """
    <script>
    function continuarCurso(cursoId, usuarioId) {
        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            data: {
                action: 'continuar_curso',
                curso_id: cursoId,
                usuario_id: usuarioId
            }
        }, '*');
    }
    
    function comprarCurso(cursoId) {
        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            data: {
                action: 'comprar_curso',
                curso_id: cursoId
            }
        }, '*');
    }
    
    function inscreverCurso(cursoId, usuarioId) {
        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            data: {
                action: 'inscrever_curso',
                curso_id: cursoId,
                usuario_id: usuarioId
            }
        }, '*');
    }
    </script>
    """
    st.components.v1.html(js_global, height=0)
