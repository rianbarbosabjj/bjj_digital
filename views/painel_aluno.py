import streamlit as st
import time
import utils as ce
import views.aulas_aluno as aulas_view

# ==================================================
# 🎨 ESTILOS CSS PERSONALIZADOS (MODERNIZAÇÃO)
# ==================================================
def aplicar_estilos_cards():
    st.markdown("""
    <style>
        /* Estilo dos Cards de Curso */
        div[data-testid="stContainer"] {
            background-color: rgba(14, 45, 38, 0.7); /* Fundo verde translúcido */
            border: 1px solid rgba(255, 215, 112, 0.2); /* Borda dourada sutil */
            border-radius: 12px;
            padding: 20px;
            transition: all 0.3s ease-in-out;
        }
        
        /* Efeito Hover (Levantar o card) */
        div[data-testid="stContainer"]:hover {
            transform: translateY(-5px);
            border-color: #FFD770;
            box-shadow: 0 10px 20px rgba(0,0,0,0.4);
            background-color: rgba(14, 45, 38, 0.95);
        }

        /* Títulos dos Cards */
        .card-title {
            color: #FFD770 !important;
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            min-height: 50px; /* Alinhamento */
        }

        /* Abas mais bonitas */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background-color: transparent;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: rgba(255,255,255,0.05);
            border-radius: 8px;
            padding: 10px 20px;
            color: white;
        }
        .stTabs [aria-selected="true"] {
            background-color: #FFD770 !important;
            color: #0e2d26 !important;
            font-weight: bold;
        }
    </style>
    """, unsafe_allow_html=True)

# ==================================================
# 💰 DIÁLOGO DE CHECKOUT (Pagamento)
# ==================================================
@st.dialog("🛒 Finalizar Compra")
def dialog_pagamento(curso, usuario):
    st.markdown(f"### {curso.get('titulo')}")
    st.markdown("Confirme os detalhes do seu pedido:")
    
    valor = float(curso.get('preco', 0))
    
    col1, col2 = st.columns(2)
    with col1:
        st.caption("Valor do Curso")
        st.markdown(f"## R$ {valor:.2f}")
    with col2:
        st.caption("Método")
        st.markdown("📦 **PIX / Cartão**")

    st.divider()
    
    st.info("ℹ️ Simulando integração com Gateway de Pagamento...")
    
    if st.button("✅ Confirmar Pagamento e Inscrever", type="primary", use_container_width=True):
        with st.spinner("Processando pagamento..."):
            time.sleep(2) # Simula tempo do banco
            
            # CHAMA A NOVA FUNÇÃO DO UTILS COM SPLIT
            sucesso, msg = ce.processar_compra_curso(usuario['id'], curso['id'], valor)
            
            if sucesso:
                st.balloons()
                st.success("Pagamento Aprovado! Você já pode acessar o curso.")
                time.sleep(2)
                st.rerun()
            else:
                st.error(msg)

# ==================================================
# 🧱 COMPONENTE: GRID DE CURSOS
# ==================================================
def renderizar_grid_cursos(cursos, usuario, tipo_lista="meus"):
    """
    Renderiza os cursos em um layout de GRADE (3 colunas)
    tipo_lista: 'meus' (matriculados) ou 'novos' (disponíveis)
    """
    if not cursos:
        msg = "Você não está inscrito em nenhum curso ainda." if tipo_lista == "meus" else "Nenhum curso novo disponível no momento."
        st.info(msg)
        return

    # Cria colunas para o Grid (3 cards por linha)
    colunas_grid = st.columns(3)
    
    for index, curso in enumerate(cursos):
        coluna_atual = colunas_grid[index % 3] # Distribui: 0, 1, 2, 0, 1, 2...
        
        with coluna_atual:
            with st.container(border=True):
                # 1. Ícone/Imagem (Placeholder ou Capa)
                st.markdown(f"<div style='font-size: 2rem; margin-bottom: 10px;'>🥋</div>", unsafe_allow_html=True)
                
                # 2. Título e Descrição curta
                titulo = curso.get('titulo', 'Sem Título')
                # Corta a descrição se for muito longa
                desc = curso.get('descricao', '') or ''
                if len(desc) > 80: desc = desc[:80] + "..."
                
                st.markdown(f"<div class='card-title'>{titulo}</div>", unsafe_allow_html=True)
                st.caption(desc)
                
                st.write("") # Espaçamento
                
                # 3. Conteúdo Específico por Tipo
                if tipo_lista == "meus":
                    # Barra de Progresso
                    progresso = curso.get('progresso', 0)
                    st.progress(progresso / 100)
                    st.caption(f"{progresso}% Concluído")
                    
                    if st.button("▶ Continuar", key=f"go_{curso['id']}", use_container_width=True):
                        st.session_state["curso_aluno_selecionado"] = curso
                        st.session_state["view_aluno"] = "aulas"
                        st.rerun()
                        
                else: # Novos cursos
                    # Badges de Info
                    info = []
                    if curso.get('duracao_estimada'): info.append(f"⏱ {curso['duracao_estimada']}")
                    if curso.get('nivel'): info.append(f"📊 {curso['nivel']}")
                    st.caption(" • ".join(info))
                    
                    # Verifica Pagamento
                    pago = curso.get('pago', False)
                    preco = float(curso.get('preco', 0))

                    # Botão de Inscrição
                    lbl_btn = "Inscrever-se"
                    if pago and preco > 0:
                        lbl_btn = f"Comprar (R$ {preco:.2f})"
                        
                    if st.button(lbl_btn, key=f"buy_{curso['id']}", type="primary", use_container_width=True):
                        # Se for pago e tiver preço
                        if pago and preco > 0:
                            dialog_pagamento(curso, usuario)
                        else:
                            # Inscrição Gratuita Direta (AQUI ESTAVA O ERRO)
                            with st.spinner("Realizando matrícula..."):
                                ce.inscrever_usuario_em_curso(usuario["id"], curso["id"])
                                
                                # AVISA O ALUNO
                                st.balloons() 
                                st.success(f"Inscrição realizada! O curso '{curso['titulo']}' foi movido para a aba 'Matriculados'.")
                                
                                time.sleep(2.5) 
                                st.rerun()

# ==================================================
# 🚀 FUNÇÃO PRINCIPAL
# ==================================================
def render_painel_aluno(usuario):
    # Aplica o CSS moderno
    aplicar_estilos_cards()

    # --- Lógica de Player (Vídeo) ---
    if st.session_state.get("view_aluno") == "aulas" and st.session_state.get("curso_aluno_selecionado"):
        c1, c2 = st.columns([1, 5])
        with c1:
            if st.button("⬅️ Voltar", use_container_width=True):
                st.session_state["view_aluno"] = "lista"
                st.session_state["curso_aluno_selecionado"] = None
                st.rerun()
        
        st.divider()
        aulas_view.pagina_aulas_aluno(st.session_state["curso_aluno_selecionado"], usuario)
        return

    # --- Cabeçalho com Título e Botão Voltar ---
    col_texto, col_botao = st.columns([4, 1])
    
    with col_texto:
        st.markdown(f"""
        <div>
            <h2 style='text-align: left; color: #FFD770; margin-bottom: 0;'>📚 Meus Cursos</h2>
            <p style='color: #ccc; margin-top: 5px;'>Bem-vindo de volta, <b>{usuario.get('nome').split()[0]}</b>.</p>
        </div>
        """, unsafe_allow_html=True)

    with col_botao:
        st.write("") # Espaçamento superior para alinhar verticalmente
        if st.button("🏠 Voltar ao Início", use_container_width=True):
            st.session_state.menu_selection = "Início"
            st.rerun()
    
    st.write("") # Espaço extra antes das abas

    # --- Abas ---
    tab_meus, tab_novos = st.tabs(["📚 Meus Cursos", "🚀 Catálogo de Cursos"])

    with tab_meus:
        cursos = ce.listar_cursos_inscritos(usuario["id"])
        renderizar_grid_cursos(cursos, usuario, tipo_lista="meus")

    with tab_novos:
        novos = ce.listar_cursos_disponiveis_para_aluno(usuario)
        renderizar_grid_cursos(novos, usuario, tipo_lista="novos")
