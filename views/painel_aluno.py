#/views/painel_aluno.py

import streamlit as st
import time
import utils as ce
import views.aulas_aluno as aulas_view

# ==================================================
# 🎨 ESTILOS CSS PERSONALIZADOS
# ==================================================
def aplicar_estilos_cards():
    st.markdown("""
    <style>
        div[data-testid="stContainer"] {
            background-color: rgba(14, 45, 38, 0.7);
            border: 1px solid rgba(255, 215, 112, 0.2);
            border-radius: 12px;
            padding: 20px;
            transition: all 0.3s ease-in-out;
        }
        div[data-testid="stContainer"]:hover {
            transform: translateY(-5px);
            border-color: #FFD770;
            box-shadow: 0 10px 20px rgba(0,0,0,0.4);
            background-color: rgba(14, 45, 38, 0.95);
        }
        .card-title {
            color: #FFD770 !important;
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            min-height: 50px;
        }
        .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: transparent; }
        .stTabs [data-baseweb="tab"] {
            background-color: rgba(255,255,255,0.05);
            border-radius: 8px; padding: 10px 20px; color: white;
        }
        .stTabs [aria-selected="true"] {
            background-color: #FFD770 !important; color: #0e2d26 !important; font-weight: bold;
        }
    </style>
    """, unsafe_allow_html=True)
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
        <button class="btn-curso btn-continuar" onclick="continuarCurso('{curso["id"]}', '{usuario["id"]}')">
            ▶ CONTINUAR ESTUDANDO
        </button>
        """
    else:
        preco = curso.get('preco', 0)
        if preco > 0:
            botao_html = f"""
            <button class="btn-curso btn-comprar" onclick="comprarCurso('{curso["id"]}')">
                💰 COMPRAR AGORA - R$ {preco:.2f}
            </button>
            """
        else:
            botao_html = f"""
            <button class="btn-curso btn-continuar" onclick="inscreverCurso('{curso["id"]}', '{usuario["id"]}')">
                🎯 INSCREVER-SE GRATUITAMENTE
            </button>
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

def render_hero_section(titulo, subtitulo, usuario_nome=""):
    """Renderiza seção hero moderna"""
    
    saudacao = f", {usuario_nome}" if usuario_nome else ""
    
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
            📅 {datetime.now().strftime("%d/%m/%Y")} | 🎯 Continue sua jornada{saudacao}
        </div>
    </div>
    """
    
    return hero_html

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
                background: linear-gradient(135deg, {st.session_state.get('COR_BOTAO', '#078B6C')}, #056853);
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
            <!-- Aqui iria o player de vídeo real -->
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

# JavaScript para os botões
def add_javascript_handlers():
    """Adiciona handlers JavaScript para os botões"""
    
    js_code = """
    <script>
    function continuarCurso(cursoId, usuarioId) {
        // Envia para Streamlit
        window.parent.postMessage({
            type: 'STREAMLIT',
            data: {
                action: 'continuar_curso',
                curso_id: cursoId,
                usuario_id: usuarioId
            }
        }, '*');
    }
    
    function comprarCurso(cursoId) {
        window.parent.postMessage({
            type: 'STREAMLIT',
            data: {
                action: 'comprar_curso',
                curso_id: cursoId
            }
        }, '*');
    }
    
    function inscreverCurso(cursoId, usuarioId) {
        window.parent.postMessage({
            type: 'STREAMLIT',
            data: {
                action: 'inscrever_curso',
                curso_id: cursoId,
                usuario_id: usuarioId
            }
        }, '*');
    }
    
    function voltarParaCursos() {
        window.parent.postMessage({
            type: 'STREAMLIT',
            data: {
                action: 'voltar_cursos'
            }
        }, '*');
    }
    
    function marcarConcluida() {
        window.parent.postMessage({
            type: 'STREAMLIT',
            data: {
                action: 'concluir_aula'
            }
        }, '*');
    }
    
    // Listener para Streamlit
    window.addEventListener('message', function(event) {
        if (event.data.type === 'STREAMLIT_COMMAND') {
            // Processar comandos do Streamlit
            console.log('Comando recebido:', event.data);
        }
    });
    </script>
    """
    
    st.components.v1.html(js_code, height=0)

# ==================================================
# 💰 DIÁLOGO DE CHECKOUT (CORRIGIDO)
# ==================================================
@st.dialog("🛒 Checkout Seguro")
def dialog_pagamento(curso, usuario):
    st.markdown(f"### {curso.get('titulo')}")
    valor = float(curso.get('preco', 0))
    st.markdown(f"## Total: R$ {valor:.2f}")
    
    st.divider()

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
        
        # --- AVISO IMPORTANTE PARA O ALUNO ---
        st.info("""
        📝 **Como pagar sem logar:**
        1. Clique no botão abaixo.
        2. Na tela do Mercado Pago, escolha a opção **"Pagar como convidado"** ou **"Novo Cartão"** (geralmente no final da tela).
        3. Você **NÃO** precisa criar conta para pagar com Pix ou Cartão.
        """)
        # -------------------------------------
        
        st.link_button("👉 Ir para Pagamento (Pix/Cartão)", st.session_state.mp_link, type="primary", use_container_width=True)
        
        st.markdown("---")
        st.write("Após pagar, clique abaixo:")
        
        if st.button("🔄 Confirmar Pagamento", use_container_width=True):
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
                        time.sleep(3)
                        st.rerun()
                    else:
                        st.error(f"Erro no sistema: {msg_db}")
                else:
                    st.warning(f"Status: {msg}")
# ==================================================
# 🧱 GRID DE CURSOS
# ==================================================
def renderizar_grid_cursos(cursos, usuario, tipo_lista="meus"):
    if not cursos:
        msg = "Você não está inscrito em nenhum curso." if tipo_lista == "meus" else "Nenhum curso novo disponível."
        st.info(msg)
        return

    colunas_grid = st.columns(3)
    
    for index, curso in enumerate(cursos):
        coluna_atual = colunas_grid[index % 3]
        
        with coluna_atual:
            with st.container(border=True):
                st.markdown(f"<div style='font-size: 2rem; margin-bottom: 10px;'>🥋</div>", unsafe_allow_html=True)
                
                titulo = curso.get('titulo', 'Sem Título')
                desc = curso.get('descricao', '') or ''
                if len(desc) > 80: desc = desc[:80] + "..."
                
                st.markdown(f"<div class='card-title'>{titulo}</div>", unsafe_allow_html=True)
                st.caption(desc)
                st.write("") 
                
                if tipo_lista == "meus":
                    progresso = curso.get('progresso', 0)
                    st.progress(progresso / 100)
                    st.caption(f"{progresso}% Concluído")
                    
                    if st.button("▶ Continuar", key=f"go_{curso['id']}", use_container_width=True):
                        st.session_state["curso_aluno_selecionado"] = curso
                        st.session_state["view_aluno"] = "aulas"
                        st.rerun()
                        
                else: # NOVOS CURSOS
                    info = []
                    if curso.get('duracao_estimada'): info.append(f"⏱ {curso['duracao_estimada']}")
                    if curso.get('nivel'): info.append(f"📊 {curso['nivel']}")
                    st.caption(" • ".join(info))
                    
                    pago = curso.get('pago', False)
                    preco = float(curso.get('preco', 0))
                    
                    lbl_btn = "Inscrever-se"
                    if pago and preco > 0:
                        lbl_btn = f"Comprar (R$ {preco:.2f})"
                        
                    if st.button(lbl_btn, key=f"buy_{curso['id']}", type="primary", use_container_width=True):
                        if pago and preco > 0:
                            # LIMPEZA DE SEGURANÇA
                            if "mp_preference_id" in st.session_state:
                                del st.session_state["mp_preference_id"]
                            if "mp_link" in st.session_state:
                                del st.session_state["mp_link"]
                                
                            dialog_pagamento(curso, usuario)
                        else:
                            # Inscrição Gratuita
                            with st.spinner("Realizando matrícula..."):
                                ce.inscrever_usuario_em_curso(usuario["id"], curso["id"])
                                st.balloons()
                                st.success(f"Inscrição realizada! O curso foi movido para a aba 'Matriculados'.")
                                time.sleep(2.5)
                                st.rerun()

# ==================================================
# 🚀 FUNÇÃO PRINCIPAL
# ==================================================
def render_painel_aluno(usuario):
    """Renderiza a área de cursos do aluno com design moderno"""
    
    from datetime import datetime
    import utils as ce
    
    # Adicionar handlers JavaScript
    add_javascript_handlers()
    
    # Verificar se estamos no player de aula
    if st.session_state.get("view_aluno") == "aulas" and st.session_state.get("curso_aluno_selecionado"):
        # Renderizar player moderno
        curso = st.session_state["curso_aluno_selecionado"]
        
        # Buscar a primeira aula (simulação)
        modulos = ce.listar_modulos_e_aulas(curso['id'])
        aula = None
        if modulos and modulos[0].get('aulas'):
            aula = modulos[0]['aulas'][0]
        
        if aula:
            st.components.v1.html(render_player_aula(aula, curso), height=800)
        else:
            st.error("Aula não encontrada")
        
        # Botão de voltar (Streamlit nativo como fallback)
        if st.button("← Voltar aos Cursos", use_container_width=True, type="primary"):
            st.session_state["view_aluno"] = "lista"
            st.session_state["curso_aluno_selecionado"] = None
            st.rerun()
        
        return
    
    # ============= LAYOUT PRINCIPAL =============
    
    # Hero Section
    st.components.v1.html(
        render_hero_section(
            "📚 Academia Digital BJJ",
            "Domine as técnicas, evolua nas faixas, transforme seu jogo.",
            usuario.get('nome', '').split()[0]
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
        st.caption("🎯 Metas")
        st.caption(f"Progresso geral: 65%")

def render_tab_meus_cursos(usuario):
    """Renderiza aba 'Meus Cursos'"""
    import utils as ce
    
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
        # Estatísticas rápidas
        col_stats1, col_stats2, col_stats3 = st.columns(3)
        with col_stats1:
            st.metric("📚 Cursos", len(cursos))
        with col_stats2:
            progresso_medio = sum(c.get('progresso', 0) for c in cursos) / len(cursos) if cursos else 0
            st.metric("📈 Progresso Médio", f"{progresso_medio:.0f}%")
        with col_stats3:
            horas_estudo = sum(10 for c in cursos)  # Exemplo
            st.metric("⏱ Tempo de Estudo", f"{horas_estudo}h")
        
        # Grid de cursos
        st.markdown('<div class="cursos-grid">', unsafe_allow_html=True)
        
        # Dividir em colunas para layout grid simulado
        cols = st.columns(3)
        for idx, curso in enumerate(cursos):
            with cols[idx % 3]:
                # Usar componente nativo do Streamlit com HTML customizado
                with st.container():
                    # Card HTML
                    st.components.v1.html(
                        render_card_curso(curso, usuario, tipo="meus"),
                        height=350
                    )
                    
                    # Botões nativos do Streamlit como fallback
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
                                st.write(f"**Professor:** {curso.get('professor_nome')}")
                                st.write(f"**Duração:** {curso.get('duracao_estimada')}")
        
        st.markdown('</div>', unsafe_allow_html=True)

def render_tab_novos_cursos(usuario):
    """Renderiza aba 'Novos Cursos'"""
    import utils as ce
    
    # Filtros modernos
    with st.container():
        st.markdown('<div class="filtros-container">', unsafe_allow_html=True)
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filtro_preco = st.selectbox("💰 Preço", ["Todos", "Gratuitos", "Premium"])
        with col_f2:
            filtro_nivel = st.selectbox("📊 Nível", ["Todos", "Iniciante", "Intermediário", "Avançado"])
        with col_f3:
            filtro_duracao = st.selectbox("⏱ Duração", ["Todos", "Curto (<2h)", "Médio (2-5h)", "Longo (>5h)"])
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Buscar cursos
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
        # Grid de cursos
        st.markdown('<div class="cursos-grid">', unsafe_allow_html=True)
        
        cols = st.columns(3)
        for idx, curso in enumerate(novos):
            with cols[idx % 3]:
                with st.container():
                    # Card HTML
                    st.components.v1.html(
                        render_card_curso(curso, usuario, tipo="novos"),
                        height=320
                    )
                    
                    # Botão nativo como fallback
                    preco = curso.get('preco', 0)
                    if preco > 0:
                        if st.button(f"💰 R$ {preco:.2f}", key=f"buy_{curso['id']}", use_container_width=True, type="primary"):
                            # Lógica de compra
                            pass
                    else:
                        if st.button("🎯 Inscrever-se", key=f"join_{curso['id']}", use_container_width=True):
                            ce.inscrever_usuario_em_curso(usuario["id"], curso["id"])
                            st.success("Inscrição realizada!")
                            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

def render_tab_concluidos(usuario):
    """Renderiza aba 'Cursos Concluídos'"""
    st.components.v1.html(
        render_empty_state(
            icon="🏆",
            titulo="Nenhum curso concluído ainda",
            mensagem="Continue estudando! Seus primeiros certificados estão chegando."
        ),
        height=300
    )
    
    # Placeholder para cursos concluídos
    with st.expander("🎓 Como obter certificados"):
        st.info("""
        1. Complete 100% do progresso do curso
        2. Realize todas as atividades práticas
        3. Obtenha aprovação do seu professor
        4. Baixe seu certificado digital na aba 'Meus Certificados'
        """)
